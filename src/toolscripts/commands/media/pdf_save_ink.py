"""``pdf-save-ink`` - strip light backgrounds/washes from a PDF to save printer ink.

Handles color PDFs with light tints (e.g. light-blue worksheet backgrounds) and
grayscale PDFs with large gray regions. The algorithm never hard-thresholds to
pure black/white (that breaks anti-aliased strokes on low-DPI scans):

1. render the page to a raster at (roughly) its native image DPI,
2. estimate the local background with a large median filter,
3. divide-normalize so background becomes ~white everywhere,
4. push near-white tones to pure white through a continuous S-curve knee,
   keeping mid-tones and dark strokes as smooth grayscale.

The grayscale plane is per-pixel min(R,G,B), so small saturated-color elements
(lesson chips, red circled numbers) stay visible as gray while only large
low-contrast regions get whitened away. A connected-component pass then removes
any large color block *in full* - including its thin rounded corners that a
local median would otherwise leave behind.

Requires the ``pdf`` extra: pymupdf, pillow, numpy, scipy.
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)


def _odd(value: int, lo: int, hi: int) -> int:
    value = max(lo, min(hi, value))
    return value if value % 2 == 1 else value + 1


def _tone_curve(knee: int, floor: int) -> list[int]:
    """256-entry LUT: v >= knee -> white, v <= floor -> unchanged, smoothstep between.

    Continuity at both joins is what keeps anti-aliased text strokes intact.
    """
    lut = []
    for v in range(256):
        if v >= knee:
            out = 255
        elif v <= floor:
            out = v
        else:
            t = (v - floor) / (knee - floor)
            s = t * t * (3 - 2 * t)
            out = round(floor + (255 - floor) * s)
        lut.append(min(255, max(0, out)))
    return lut


def _parse_pages(spec: str | None, page_count: int) -> list[int]:
    """Parse "1-3,8,12-" into 0-based page indices."""
    if not spec:
        return list(range(page_count))
    pages: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        lo_s, dash, hi_s = part.partition("-")
        try:
            lo = int(lo_s) if lo_s else 1
            if not dash:
                hi = lo
            else:
                hi = int(hi_s) if hi_s else page_count
        except ValueError:
            raise SystemExit(f"invalid --pages range: {part!r}") from None
        if lo < 1 or hi > page_count or lo > hi:
            raise SystemExit(f"page range out of bounds: {part!r} (1..{page_count})")
        pages.extend(range(lo - 1, hi))
    return sorted(set(pages))


def _auto_dpi(fitz_doc, page) -> int:
    """Match the render DPI to the largest painted embedded image; 300 for vector pages."""
    best = 0.0
    for info in page.get_images(full=True):
        xref = info[0]
        rects = page.get_image_rects(xref)
        if not rects:
            continue
        try:
            data = fitz_doc.extract_image(xref)
        except Exception:  # noqa: BLE001
            continue
        rect_w_pt = max(r.width for r in rects)
        if rect_w_pt > 0:
            best = max(best, data["width"] / (rect_w_pt / 72.0))
    if best <= 0:
        return 300
    return _odd(round(best), 60, 300)


def _background_estimate(np, Image, ImageFilter, plane_u8, kernel: int):
    """Large-kernel median at 1/4 resolution, then upscale.

    The background is a low-frequency signal, so quarter-res estimation is
    visually identical to a full-res median while ~16x cheaper.
    """
    h, w = plane_u8.shape
    small = Image.fromarray(plane_u8).resize((max(1, w // 4), max(1, h // 4)), Image.BOX)
    k_small = _odd(max(3, kernel // 4), 3, 61)
    bg = small.filter(ImageFilter.MedianFilter(k_small)).resize((w, h), Image.BILINEAR)
    return np.asarray(bg, dtype=np.float32)


def _big_color_mask(np, ndi, arr, frac: float):
    """Boolean mask of saturated pixels belonging to a large connected color region.

    A large-kernel median can't tell a thin rounded corner off a big color block
    from a small colored chip - both are locally thin. But the corner is *connected*
    to the block while a chip is isolated. So we label connected components of the
    saturated-color mask and flag any component covering more than ``frac`` of the
    page; those get whitened as one piece. Returns None when disabled or nothing qualifies.
    """
    mx = arr.max(axis=2)
    mn = arr.min(axis=2)
    colored = ((mx - mn) > 25) & (mn < 235)
    if not colored.any():
        return None
    # 8-connectivity so anti-aliased / diagonally-attached parts of a shape stay one region
    structure = np.ones((3, 3), dtype=bool)
    labels, count = ndi.label(colored, structure=structure)
    if count == 0:
        return None
    sizes = ndi.sum(np.ones_like(labels), labels, index=range(1, count + 1))
    big_ids = np.nonzero(sizes > frac * colored.size)[0] + 1
    if big_ids.size == 0:
        return None
    return np.isin(labels, big_ids)


def _process_pixels(
    np,
    Image,
    ImageFilter,
    samples: bytes,
    width: int,
    height: int,
    knee: int,
    floor: int,
    kernel: int,
    keep_color: bool,
    ndi=None,
    big_color_frac: float = 0.05,
):
    """Return (PIL image to embed, ink fraction before, ink fraction after)."""
    arr = np.frombuffer(samples, dtype=np.uint8)
    arr = arr.reshape(height, width, 3).astype(np.float32)

    # "before" ink: plain grayscale coverage of the rendered page
    gray = 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]
    ink_before = float((255.0 - gray).mean() / 255.0)

    curve = np.asarray(_tone_curve(knee, floor), dtype=np.uint8)
    channels = []
    if keep_color:
        planes = [arr[..., c] for c in range(3)]
    else:
        # per-pixel min channel: any saturated color (even a light-blue chip or red
        # ①) stays dark and survives as gray, while large neutral washes are
        # background-normalized away
        planes = [arr.min(axis=2)]

    for plane in planes:
        plane_u8 = np.clip(plane, 0, 255).astype(np.uint8)
        bg = _background_estimate(np, Image, ImageFilter, plane_u8, kernel)
        norm = np.clip(255.0 * plane / np.maximum(bg, 1.0), 0, 255)
        channels.append(curve[norm.astype(np.uint8)])

    # remove large connected color blocks (and their thin rounded corners) as a whole
    big = (
        _big_color_mask(np, ndi, arr, big_color_frac)
        if (ndi is not None and big_color_frac > 0)
        else None
    )
    if big is not None:
        for ch in channels:
            ch[big] = 255

    if keep_color:
        out = Image.fromarray(np.stack(channels, axis=2), "RGB")
        out_arr = np.asarray(out, dtype=np.float32).min(axis=2)
    else:
        out = Image.fromarray(channels[0], "L")
        out_arr = np.asarray(out, dtype=np.float32)
    ink_after = float((255.0 - out_arr).mean() / 255.0)
    return out, ink_before, ink_after


def _to_jpeg(image, quality: int) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pdf-save-ink",
        description=(
            "Remove light backgrounds and gray washes from a PDF for ink-saving "
            "printing while keeping text strokes smooth (no broken anti-aliasing). "
            "Best for scanned/image-based PDFs; vector pages are rendered at 300 DPI."
        ),
    )
    parser.add_argument("input", help="source PDF file")
    parser.add_argument("-o", "--output", help="output PDF (default: <input>-inksave.pdf)")
    parser.add_argument("--pages", help='pages to process, e.g. "1-3,8,12-" (default: all)')
    parser.add_argument("--dpi", type=int, help="override render DPI (default: auto per page)")
    parser.add_argument(
        "--color",
        action="store_true",
        help="keep text colors (per-channel wash removal) instead of grayscale",
    )
    parser.add_argument(
        "--knee",
        type=int,
        default=232,
        metavar="V",
        help="normalized level (0-255) at and above which pixels go pure "
        "white (default: 232; lower = more ink saving, thinner strokes)",
    )
    parser.add_argument(
        "--floor",
        type=int,
        default=140,
        metavar="V",
        help="normalized level (0-255) at and below which tones are kept "
        "unchanged (default: 140)",
    )
    parser.add_argument(
        "--kernel",
        type=int,
        default=0,
        help="background median-filter size; 0 = auto. Larger regions are "
        "treated as background and whitened, smaller colored elements "
        "(chips, circled numbers) survive as gray (default: auto ~ page/12)",
    )
    parser.add_argument("--jpeg-quality", type=int, default=85, help="embedded JPEG quality")
    parser.add_argument(
        "--big-color",
        type=float,
        default=0.05,
        metavar="FRAC",
        help="whiten any connected color region larger than this fraction of the "
        "page (removes big color blocks and their rounded corners as a whole; "
        "0 disables)",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        import numpy as np
        from PIL import Image, ImageFilter
        from scipy import ndimage

        try:
            import pymupdf as fitz
        except ImportError:  # PyMuPDF < 1.24 only ships the legacy name
            import fitz
    except ImportError as exc:
        log.error("missing dependency (%s); install with: ./manage.py install --extras pdf", exc)
        sys.exit(1)

    src = Path(args.input).expanduser()
    if not src.is_file():
        log.error("not a file: %s", src)
        sys.exit(1)
    dest = (
        Path(args.output).expanduser() if args.output else src.with_name(f"{src.stem}-inksave.pdf")
    )

    if not (0 <= args.floor < args.knee <= 255):
        log.error("--floor must be < --knee (both 0-255)")
        sys.exit(1)

    doc = fitz.open(src)
    if doc.needs_pass:
        log.error("encrypted PDFs are not supported")
        sys.exit(1)

    pages = _parse_pages(args.pages, doc.page_count)
    out = fitz.open()
    rows = []
    total_before = total_after = total_area = 0.0

    for n, pno in enumerate(pages, 1):
        page = doc[pno]
        dpi = args.dpi or _auto_dpi(doc, page)
        zoom = dpi / 72.0
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        kernel = args.kernel or _odd(min(pix.width, pix.height) // 12, 9, 241)
        image, ink_before, ink_after = _process_pixels(
            np,
            Image,
            ImageFilter,
            pix.samples,
            pix.width,
            pix.height,
            args.knee,
            args.floor,
            kernel,
            args.color,
            ndi=ndimage,
            big_color_frac=args.big_color,
        )
        rect = page.rect
        npage = out.new_page(width=rect.width, height=rect.height)
        npage.insert_image(npage.rect, stream=_to_jpeg(image, args.jpeg_quality))
        area = rect.get_area()
        total_before += ink_before * area
        total_after += ink_after * area
        total_area += area
        rows.append((pno + 1, dpi, ink_before * 100, ink_after * 100))
        log.info("page %d/%d processed at %d DPI", n, len(pages), dpi)

    out.set_metadata(doc.metadata)
    doc.close()
    out.save(dest, garbage=3, deflate=True)
    out.close()

    before = total_before / total_area * 100
    after = total_after / total_area * 100
    saved = (1 - after / before) * 100 if before > 0 else 0.0

    print(f"{'Page':>5}  {'DPI':>4}  {'Ink before':>10}  {'Ink after':>9}  {'Saved':>6}")
    for pno, dpi, b, a in rows:
        pct = (1 - a / b) * 100 if b > 0 else 0.0
        print(f"{pno:>5}  {dpi:>4}  {b:>9.2f}%  {a:>8.2f}%  {pct:>5.1f}%")
    src_mb = src.stat().st_size / 1e6
    dst_mb = dest.stat().st_size / 1e6
    print(
        f"\n{len(pages)} page(s): ink coverage {before:.2f}% -> {after:.2f}% "
        f"(-{saved:.1f}%), size {src_mb:.1f}MB -> {dst_mb:.1f}MB"
    )
    print(dest)
    log.success("saved: %s", dest)


if __name__ == "__main__":
    main()
