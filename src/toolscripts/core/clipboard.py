"""Cross-platform clipboard helpers.

Tries the ``pyperclip`` package first (if installed via the ``[clipboard]``
extra), then falls back to platform-native tools:

- macOS:   pbcopy / pbpaste
- Linux:   wl-copy / wl-paste, xclip, xsel
- Windows: clip / powershell Get-Clipboard
"""

from __future__ import annotations

import shutil
import subprocess
import sys


def _try_pyperclip_copy(text: str) -> bool:
    try:
        import pyperclip
    except ImportError:
        return False
    try:
        pyperclip.copy(text)
        return True
    except Exception:
        return False


def _try_pyperclip_paste() -> str | None:
    try:
        import pyperclip
    except ImportError:
        return None
    try:
        return pyperclip.paste()
    except Exception:
        return None


def copy_to_clipboard(text: str) -> bool:
    """Copy ``text`` to the clipboard. Returns True on success."""
    if _try_pyperclip_copy(text):
        return True

    if sys.platform == "darwin":
        tool = shutil.which("pbcopy")
        if tool:
            try:
                subprocess.run([tool], input=text, text=True, check=True)
                return True
            except subprocess.CalledProcessError:
                return False

    elif sys.platform.startswith("linux"):
        for cmd in ("wl-copy", "xclip", "xsel"):
            tool = shutil.which(cmd)
            if not tool:
                continue
            try:
                if cmd == "xclip":
                    subprocess.run(
                        [tool, "-selection", "clipboard"],
                        input=text,
                        text=True,
                        check=True,
                    )
                elif cmd == "xsel":
                    subprocess.run(
                        [tool, "--clipboard", "--input"],
                        input=text,
                        text=True,
                        check=True,
                    )
                else:
                    subprocess.run([tool], input=text, text=True, check=True)
                return True
            except subprocess.CalledProcessError:
                continue

    elif sys.platform in ("win32", "cygwin"):
        tool = shutil.which("clip")
        if tool:
            try:
                subprocess.run([tool], input=text, text=True, check=True)
                return True
            except subprocess.CalledProcessError:
                return False

    return False


def paste_from_clipboard() -> str | None:
    """Read text from the clipboard. Returns None on failure."""
    pyperclip_result = _try_pyperclip_paste()
    if pyperclip_result is not None:
        return pyperclip_result

    if sys.platform == "darwin":
        tool = shutil.which("pbpaste")
        if tool:
            try:
                result = subprocess.run(
                    [tool], capture_output=True, text=True, check=True
                )
                return result.stdout
            except subprocess.CalledProcessError:
                return None

    elif sys.platform.startswith("linux"):
        for cmd in ("wl-paste", "xclip", "xsel"):
            tool = shutil.which(cmd)
            if not tool:
                continue
            try:
                if cmd == "xclip":
                    result = subprocess.run(
                        [tool, "-selection", "clipboard", "-output"],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                elif cmd == "xsel":
                    result = subprocess.run(
                        [tool, "--clipboard", "--output"],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                else:
                    result = subprocess.run(
                        [tool],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                return result.stdout
            except subprocess.CalledProcessError:
                continue

    elif sys.platform in ("win32", "cygwin"):
        powershell = shutil.which("powershell")
        if powershell:
            try:
                result = subprocess.run(
                    [powershell, "-Command", "Get-Clipboard"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                return result.stdout
            except subprocess.CalledProcessError:
                return None

    return None
