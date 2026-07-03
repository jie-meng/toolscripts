"""``llamacmd`` - interactive browser for llama.cpp model management.

Requires ``llama-cli`` (Homebrew: ``brew install llama.cpp``).
Optional: ``huggingface_hub`` for downloading models from HuggingFace
(``pip install huggingface_hub``).
"""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, require, run

log = get_logger(__name__)


@dataclass
class LlamaCommand:
    name: str
    description: str
    examples: list[str]
    needs_model: bool = False
    needs_hf: bool = False


_LLAMA_COMMANDS: list[LlamaCommand] = [
    LlamaCommand(
        name="List local models",
        description="Scan local directories for downloaded GGUF files "
        "(HuggingFace cache + $LLAMA_MODELS_DIR). Shows model path, size, "
        "and type information.",
        examples=[
            "export LLAMA_MODELS_DIR=~/models/llama  # custom directory",
            "find ~/.cache/huggingface -name '*.gguf' -ls",
            "ls -lh ~/models/llama/",
        ],
    ),
    LlamaCommand(
        name="Search & Download (HuggingFace)",
        description="Search HuggingFace for GGUF models by keyword, "
        "browse results sorted by downloads, pick one or more to download. "
        "Requires: pip install huggingface_hub",
        examples=[
            "huggingface-cli download bartowski/Qwen2.5-1.5B-Instruct-GGUF '--include=*.gguf'",
        ],
        needs_hf=True,
    ),
    LlamaCommand(
        name="Download from URL",
        description="Download a GGUF file directly from a raw URL. "
        "Files are saved to $LLAMA_MODELS_DIR or ~/models/llama/.",
        examples=[
            "wget -P ~/models/llama <url>",
            "export LLAMA_MODELS_DIR=~/models/llama",
        ],
    ),
    LlamaCommand(
        name="Run chat",
        description="Select a local model and start an interactive chat session "
        "with llama-cli. Supports conversation mode.",
        examples=[
            "llama-cli -m <model.gguf> -cnv",
            "llama-cli -hf ggml-org/Qwen2.5-Coder-1.5B-Q8_0-GGUF -cnv",
        ],
        needs_model=True,
    ),
    LlamaCommand(
        name="Run chat (from HF)",
        description="Enter a HuggingFace repo and let llama-cli download and "
        "start a chat session directly — no pre-download needed.",
        examples=[
            "llama-cli -hf ggml-org/Qwen2.5-Coder-1.5B-Q8_0-GGUF -cnv",
            "llama-cli -hf bartowski/Llama-3.2-3B-Instruct-GGUF:Q4_K_M -cnv",
        ],
    ),
    LlamaCommand(
        name="Quick prompt",
        description="Run a single prompt with a local model and print the response. "
        "Non-interactive, returns to the browser afterwards.",
        examples=[
            "llama-cli -m <model.gguf> -p 'hello' -n 256 --no-display-prompt",
            "llama-cli -hf ggml-org/Qwen2.5-Coder-1.5B-Q8_0-GGUF -p 'hello' -n 256",
        ],
        needs_model=True,
    ),
    LlamaCommand(
        name="Start server",
        description="Select a local model and start llama-server (HTTP API, "
        "OpenAI-compatible endpoint at http://localhost:8080/v1).",
        examples=[
            "llama-server -m <model.gguf> --host 127.0.0.1 --port 8080",
            "curl http://localhost:8080/v1/chat/completions -d '...'",
        ],
        needs_model=True,
    ),
    LlamaCommand(
        name="Start server (from HF)",
        description="Enter a HuggingFace repo and let llama-server download and "
        "serve it directly — no pre-download needed. Convenient for testing.",
        examples=[
            "llama-server -hf ggml-org/Qwen2.5-Coder-1.5B-Q8_0-GGUF --port 8012 -ngl 99 -fa",
            "llama-server -hf bartowski/Llama-3.2-3B-Instruct-GGUF:Q4_K_M -ngl 99",
        ],
    ),
    LlamaCommand(
        name="Model info",
        description="Show metadata for a local GGUF model: architecture, "
        "context size, parameter count, quantization, tokenizer, etc.",
        examples=[
            "llama-gguf <model.gguf> r",
        ],
        needs_model=True,
    ),
    LlamaCommand(
        name="Delete model(s)",
        description="Select one or more local models to delete. "
        "Shows model path and size before confirming.",
        examples=[
            "rm ~/.cache/huggingface/hub/.../<model>.gguf",
        ],
    ),
    LlamaCommand(
        name="Clean orphan cache",
        description="Scan HuggingFace cache for GGUF files that are no longer "
        "referenced and reclaim disk space. "
        "Uses huggingface_hub delete-cache if available.",
        examples=[],
        needs_hf=True,
    ),
]


@dataclass
class _ModelEntry:
    filepath: Path
    size_mb: float


def _get_model_dirs() -> list[Path]:
    dirs: list[Path] = []
    custom = os.environ.get("LLAMA_MODELS_DIR")
    if custom:
        for d in custom.split(":"):
            p = Path(d).expanduser().resolve()
            if p.is_dir():
                dirs.append(p)
    if not dirs:
        default = Path.home() / "models" / "llama"
        if default.is_dir():
            dirs.append(default)
    hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
    if hf_cache.is_dir():
        dirs.append(hf_cache)
    return dirs


def _find_gguf_files(dirs: list[Path]) -> list[_ModelEntry]:
    found: dict[str, _ModelEntry] = {}
    for d in dirs:
        for f in d.rglob("*.gguf"):
            key = f.resolve().as_posix()
            if key not in found:
                try:
                    size_mb = f.stat().st_size / (1024 * 1024)
                except OSError:
                    size_mb = 0.0
                found[key] = _ModelEntry(filepath=f, size_mb=size_mb)
    return list(found.values())


def _human_size(mb: float) -> str:
    if mb >= 1024:
        return f"{mb / 1024:.1f} GB"
    return f"{mb:.0f} MB"


def _format_model_path(entry: _ModelEntry) -> str:
    p = entry.filepath
    return f"{p}  ({_human_size(entry.size_mb)})"


def _get_hf_api():
    try:
        from huggingface_hub import HfApi

        return HfApi()
    except ImportError:
        log.error("huggingface_hub not installed; run: pip install huggingface_hub")
        return None


def _handle_list_models() -> None:
    dirs = _get_model_dirs()
    if not dirs:
        print("No model directories found. Set $LLAMA_MODELS_DIR to a directory with .gguf files.")
        return
    models = _find_gguf_files(dirs)
    if not models:
        print("No .gguf files found in:")
        for d in dirs:
            print(f"  {d}")
        print("\nHint: use 'Search & Download' to get models from HuggingFace.")
        return

    labels = [_format_model_path(m) for m in models]
    print(f"Found {len(models)} model(s):\n")
    for label in labels:
        print(f"  {label}")
    print()


def _handle_search_download() -> None:
    api = _get_hf_api()
    if api is None:
        return

    try:
        raw = input("Search keyword (e.g. 'qwen2.5 1.5b', 'llama3 8b'): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    if not raw:
        print("Cancelled.")
        return

    print(f"Searching HuggingFace for GGUF models matching '{raw}'...")
    try:
        results = list(api.list_models(search=raw, filter="gguf", limit=50, sort="downloads"))
    except Exception as exc:
        log.error("Search failed: %s", exc)
        return

    if not results:
        print("No GGUF models found for this query.")
        return

    from toolscripts.core.ui_curses import select_many

    labels: list[str] = []
    for m in results:
        dl = m.downloads or 0
        likes = m.likes or 0
        labels.append(f"{m.modelId:60s}  downloads={dl:>8,}  likes={likes:>5,}")

    indices = select_many("Select models to download (Space=toggle, Enter=confirm)", labels)
    if indices is None or not indices:
        print("Cancelled.")
        return

    selected = [results[i] for i in indices]

    for m in selected:
        print(f"\nDownloading {m.modelId} ...")
        try:
            from huggingface_hub import snapshot_download

            snapshot_download(m.modelId, allow_patterns=["*.gguf"])
            log.success("Downloaded %s", m.modelId)
        except Exception as exc:
            log.error("Failed to download %s: %s", m.modelId, exc)

    print("\nDone. Run 'List local models' to see your models.")


def _handle_download_url() -> None:
    try:
        url = input("GGUF download URL: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    if not url:
        print("Cancelled.")
        return

    filename = url.rsplit("/", 1)[-1].split("?")[0]
    if not filename.endswith(".gguf"):
        filename += ".gguf"

    dest_dir = os.environ.get("LLAMA_MODELS_DIR", str(Path.home() / "models" / "llama"))
    dest = Path(dest_dir) / filename
    dest.parent.mkdir(parents=True, exist_ok=True)

    print(f"Downloading to {dest} ...")
    import urllib.request

    try:
        urllib.request.urlretrieve(url, str(dest))
        log.success("Downloaded to %s", dest)
    except Exception as exc:
        log.error("Download failed: %s", exc)


def _handle_run_chat() -> None:
    models = _find_gguf_files(_get_model_dirs())
    if not models:
        print("No models found. Download one first with 'Search & Download'.")
        return

    from toolscripts.core.ui_curses import select_one

    labels = [_format_model_path(m) for m in models]
    idx = select_one("Select model to run", labels)
    if idx is None:
        print("Cancelled.")
        return

    model = models[idx]
    ctx_size = 2048
    try:
        raw = input(f"Context size [{ctx_size}]: ").strip()
        if raw:
            ctx_size = int(raw)
    except (EOFError, KeyboardInterrupt):
        print()
        return
    except ValueError:
        print("Invalid number, using default.")
    run(["llama-cli", "-m", str(model.filepath), "-c", str(ctx_size), "-cnv"])


def _handle_run_chat_hf() -> None:
    try:
        repo = input("HF repo (e.g. ggml-org/Qwen2.5-Coder-1.5B-Q8_0-GGUF): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    if not repo:
        print("Cancelled.")
        return

    ctx_size = 2048
    try:
        raw = input(f"Context size [{ctx_size}]: ").strip()
        if raw:
            ctx_size = int(raw)
    except (EOFError, KeyboardInterrupt):
        print()
        return
    except ValueError:
        print("Invalid number, using default.")

    ngl = 99
    try:
        raw = input(f"GPU layers (-ngl) [{ngl}]: ").strip()
        if raw:
            ngl = int(raw)
    except (EOFError, KeyboardInterrupt):
        print()
        return
    except ValueError:
        print("Invalid number, using default.")

    run(["llama-cli", "-hf", repo, "-c", str(ctx_size), "-ngl", str(ngl), "-cnv"])


def _handle_quick_prompt() -> None:
    models = _find_gguf_files(_get_model_dirs())
    if not models:
        print("No models found. Download one first with 'Search & Download'.")
        return

    from toolscripts.core.ui_curses import select_one

    labels = [_format_model_path(m) for m in models]
    idx = select_one("Select model", labels)
    if idx is None:
        print("Cancelled.")
        return

    try:
        prompt = input("Prompt: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    if not prompt:
        print("Cancelled.")
        return

    run(
        [
            "llama-cli",
            "-m",
            str(models[idx].filepath),
            "-p",
            prompt,
            "-n",
            "512",
            "--no-display-prompt",
        ]
    )


def _handle_start_server() -> None:
    models = _find_gguf_files(_get_model_dirs())
    if not models:
        print("No models found. Download one first with 'Search & Download'.")
        return

    from toolscripts.core.ui_curses import select_one

    labels = [_format_model_path(m) for m in models]
    idx = select_one("Select model for server", labels)
    if idx is None:
        print("Cancelled.")
        return

    host = "127.0.0.1"
    port = 8080
    try:
        raw = input(f"Host [{host}]: ").strip()
        if raw:
            host = raw
        raw = input(f"Port [{port}]: ").strip()
        if raw:
            port = int(raw)
    except (EOFError, KeyboardInterrupt):
        print()
        return

    print(f"Starting server at http://{host}:{port} ...")
    print("Press Ctrl+C to stop.\n")
    run(
        [
            "llama-server",
            "-m",
            str(models[idx].filepath),
            "--host",
            host,
            "--port",
            str(port),
        ]
    )


def _handle_start_server_hf() -> None:
    try:
        repo = input("HF repo (e.g. ggml-org/Qwen2.5-Coder-1.5B-Q8_0-GGUF): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    if not repo:
        print("Cancelled.")
        return

    port = 8012
    ngl = 99
    try:
        raw = input(f"Port [{port}]: ").strip()
        if raw:
            port = int(raw)
        raw = input(f"GPU layers (-ngl) [{ngl}]: ").strip()
        if raw:
            ngl = int(raw)
    except (EOFError, KeyboardInterrupt):
        print()
        return
    except ValueError:
        print("Invalid number, using default.")

    print(f"Starting server at http://localhost:{port} ...")
    print("Press Ctrl+C to stop.\n")
    run(["llama-server", "-hf", repo, "--port", str(port), "-ngl", str(ngl), "-fa"])


def _handle_model_info() -> None:
    models = _find_gguf_files(_get_model_dirs())
    if not models:
        print("No models found.")
        return

    from toolscripts.core.ui_curses import select_one

    labels = [_format_model_path(m) for m in models]
    idx = select_one("Select model for info", labels)
    if idx is None:
        print("Cancelled.")
        return

    run(["llama-gguf", str(models[idx].filepath), "r"])


def _handle_delete_models() -> None:
    models = _find_gguf_files(_get_model_dirs())
    if not models:
        print("No models found.")
        return

    from toolscripts.core.ui_curses import select_many

    labels = [_format_model_path(m) for m in models]
    indices = select_many("Select models to delete (Space=toggle, Enter=confirm)", labels)
    if indices is None or not indices:
        print("Cancelled.")
        return

    total_size = sum(models[i].size_mb for i in indices)
    from toolscripts.core.prompts import yes_no

    confirmed = yes_no(
        f"Delete {len(indices)} model(s) ({_human_size(total_size)})? " "This cannot be undone."
    )
    if not confirmed:
        print("Cancelled.")
        return

    for i in indices:
        p = models[i].filepath
        try:
            p.unlink()
            log.success("Deleted %s", p)
        except OSError as exc:
            log.error("Failed to delete %s: %s", p, exc)


def _handle_clean_cache() -> None:
    try:
        from huggingface_hub import scan_cache_dir
    except ImportError:
        log.error("huggingface_hub not installed; run: pip install huggingface_hub")
        return

    print("Scanning HuggingFace cache for unreferenced GGUF files ...")
    try:
        cache = scan_cache_dir()
    except Exception as exc:
        log.error("Failed to scan cache: %s", exc)
        return

    orphan_repos = []
    for repo in cache.repos:
        if repo.repo_type == "model" and any(
            f.file_name.endswith(".gguf") for rev in repo.revisions for f in rev.files
        ):
            if repo.no_revisions:
                orphan_repos.append(repo)

    if not orphan_repos:
        print("No orphan GGUF cache entries found.")
        return

    total_size = sum(r.size_on_disk for r in orphan_repos) / (1024**3)
    print(f"Found {len(orphan_repos)} orphan GGUF cache entries ({total_size:.1f} GB).")
    from toolscripts.core.prompts import yes_no

    if yes_no("Delete them?"):
        delete_strategy = cache.delete_revisions(*[r.revisions for r in orphan_repos])
        print(f"Freed {delete_strategy.freed_size / (1024**3):.1f} GB")
    else:
        print("Cancelled.")


def _run_interactive_command(cmd: LlamaCommand) -> None:
    if cmd.needs_model:
        models = _find_gguf_files(_get_model_dirs())
        if not models:
            print(
                "No GGUF models found locally.\n"
                "Hint: use 'Search & Download (HuggingFace)' or 'Download from URL' "
                "to get a model first."
            )
            return

    if cmd.name == "List local models":
        _handle_list_models()
    elif cmd.name == "Search & Download (HuggingFace)":
        _handle_search_download()
    elif cmd.name == "Download from URL":
        _handle_download_url()
    elif cmd.name == "Run chat":
        _handle_run_chat()
    elif cmd.name == "Run chat (from HF)":
        _handle_run_chat_hf()
    elif cmd.name == "Quick prompt":
        _handle_quick_prompt()
    elif cmd.name == "Start server":
        _handle_start_server()
    elif cmd.name == "Start server (from HF)":
        _handle_start_server_hf()
    elif cmd.name == "Model info":
        _handle_model_info()
    elif cmd.name == "Delete model(s)":
        _handle_delete_models()
    elif cmd.name == "Clean orphan cache":
        _handle_clean_cache()


def _ensure_curses() -> None:
    try:
        import curses  # noqa: F401
    except ImportError:
        from toolscripts.core.log import get_logger

        log_ = get_logger(__name__)
        if sys.platform == "win32":
            log_.error("curses not available on Windows. Install with: pip install windows-curses")
        else:
            log_.error("curses module not available on this Python build.")
        sys.exit(1)


def _run_curses(stdscr) -> None:
    import curses

    def _init_colors() -> None:
        curses.curs_set(0)
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_WHITE, -1)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)
        curses.init_pair(6, curses.COLOR_RED, -1)

    _init_colors()

    def cp(n: int) -> int:
        return curses.color_pair(n)

    commands = _LLAMA_COMMANDS
    cursor = 0
    top = 0

    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        preview_top = height - 13
        list_height = max(1, preview_top - 4)

        title = " llamacmd - llama.cpp model manager "
        stdscr.addstr(0, 0, title.center(width, " "), cp(1) | curses.A_BOLD)
        hint = "j/k or arrows: move  |  gg/G top/bottom  |  Enter: execute  |  q: quit"
        stdscr.addstr(1, 0, hint[:width], cp(3))
        stdscr.hline(2, 0, curses.ACS_HLINE, width)

        cmd = commands[cursor]

        visible_count = list_height
        if cursor < top:
            top = cursor
        elif cursor >= top + visible_count:
            top = cursor - visible_count + 1
        top = max(0, min(top, len(commands) - visible_count))

        for i in range(visible_count):
            idx = top + i
            if idx >= len(commands):
                break
            c = commands[idx]
            is_selected = idx == cursor
            marker = ">" if is_selected else " "
            attr = curses.A_REVERSE if is_selected else 0
            color = cp(2) if is_selected else cp(4)

            name_text = f" {marker}  {c.name}"
            if c.needs_hf:
                name_text += "  [req: huggingface_hub]"
            with contextlib.suppress(curses.error):
                stdscr.addstr(3 + i, 0, name_text[: width - 1], attr | color)

        stdscr.hline(preview_top - 1, 0, curses.ACS_HLINE, width)

        with contextlib.suppress(curses.error):
            stdscr.addstr(preview_top, 2, "Description:", cp(5) | curses.A_BOLD)

        desc_lines = _wrap(cmd.description, width - 4)
        with contextlib.suppress(curses.error):
            for li, line in enumerate(desc_lines[:3]):
                stdscr.addstr(preview_top + 1 + li, 4, line[: width - 4], cp(4))

        offset = preview_top + 1 + len(desc_lines[:3]) + 1
        if cmd.examples:
            with contextlib.suppress(curses.error):
                stdscr.addstr(offset, 2, "Examples:", cp(5) | curses.A_BOLD)
            for li, ex in enumerate(cmd.examples[:3]):
                line = f"  $ {ex}"
                with contextlib.suppress(curses.error):
                    stdscr.addstr(offset + 1 + li, 4, line[: width - 4], cp(1))

        status = f"  {cursor + 1}/{len(commands)}"
        with contextlib.suppress(curses.error):
            stdscr.addstr(height - 1, 0, status[: width - 1], cp(3))

        stdscr.refresh()
        key = stdscr.getch()

        if key in (curses.KEY_UP, ord("k")):
            cursor = max(0, cursor - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            cursor = min(len(commands) - 1, cursor + 1)
        elif key == ord("g"):
            key2 = stdscr.getch()
            if key2 == ord("g"):
                cursor = 0
        elif key == ord("G"):
            cursor = len(commands) - 1
        elif key in (curses.KEY_ENTER, 10, 13):
            curses.endwin()
            try:
                _run_interactive_command(commands[cursor])
            except Exception as exc:
                print(f"Error: {exc}")
            input("\nPress Enter to return to the browser...")
            curses.noecho()
            curses.cbreak()
            stdscr.keypad(True)
            _init_colors()
            stdscr.clearok(True)
            stdscr.refresh()
        elif key in (ord("q"), 27):
            break


def _wrap(text: str, width: int) -> list[str]:
    if width <= 0:
        return []
    out: list[str] = []
    for raw_line in text.splitlines():
        if not raw_line.strip():
            out.append("")
            continue
        line = raw_line.rstrip()
        while len(line) > width:
            cut = line.rfind(" ", 0, width)
            if cut <= 0:
                cut = width
            out.append(line[:cut])
            line = line[cut:].lstrip()
        if line:
            out.append(line)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="llamacmd",
        description="Interactive browser for llama.cpp model management.",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("llama-cli")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        log.warning("install llama.cpp: brew install llama.cpp")
        sys.exit(1)

    _ensure_curses()
    import curses

    curses.wrapper(_run_curses)


if __name__ == "__main__":
    main()
