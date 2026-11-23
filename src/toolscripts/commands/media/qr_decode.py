"""``qr-decode`` - decode all QR codes in an image."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="qr-decode",
        description="Decode all QR codes in an image and print their contents.",
    )
    parser.add_argument("image", help="path to the image")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        import zxingcpp
        from PIL import Image
    except ImportError:
        log.error("missing dependency: install with `./manage.py install --extras qrcode`")
        sys.exit(1)

    path = Path(args.image).expanduser()
    if not path.is_file():
        log.error("file not found: %s", path)
        sys.exit(1)

    try:
        with Image.open(path) as image:
            results = zxingcpp.read_barcodes(image, formats=zxingcpp.BarcodeFormat.QRCode)
    except OSError as exc:
        log.error("could not read image %s: %s", path, exc)
        sys.exit(1)

    if not results:
        log.error("no QR code found in %s", path)
        sys.exit(1)

    if len(results) > 1:
        log.info("found %d QR codes", len(results))
    for result in results:
        print(result.text)


if __name__ == "__main__":
    main()
