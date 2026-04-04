#!/usr/bin/env python3
"""
clipboard.py - Cross-platform clipboard utility.

Provides copy_to_clipboard() and paste_from_clipboard() functions that work
on macOS, Linux, and Windows using the best available method for each platform.

Usage:
    from utils.clipboard import copy_to_clipboard, paste_from_clipboard

    copy_to_clipboard("Hello, world!")
    text = paste_from_clipboard()
"""

import platform
import shutil
import subprocess


def copy_to_clipboard(text: str) -> bool:
    """Copy text to clipboard using the best available method.

    Tries pyperclip first, then falls back to platform-specific tools:
      - macOS: pbcopy
      - Linux: wl-copy > xclip > xsel
      - Windows: clip

    Args:
        text: The text to copy to the clipboard.

    Returns:
        True if the copy succeeded, False otherwise.
    """
    # Try pyperclip first (most reliable if installed)
    try:
        import pyperclip

        pyperclip.copy(text)
        return True
    except ImportError:
        pass

    # Try platform-specific tools
    system = platform.system()

    if system == "Darwin":
        pbcopy = shutil.which("pbcopy")
        if pbcopy:
            try:
                subprocess.run([pbcopy], input=text, text=True, check=True)
                return True
            except subprocess.CalledProcessError:
                return False

    elif system == "Linux":
        for cmd in ("wl-copy", "xclip", "xsel"):
            tool = shutil.which(cmd)
            if tool:
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

    elif system == "Windows":
        clip = shutil.which("clip")
        if clip:
            try:
                subprocess.run([clip], input=text, text=True, check=True)
                return True
            except subprocess.CalledProcessError:
                return False

    return False


def paste_from_clipboard() -> str | None:
    """Read text from clipboard using the best available method.

    Tries pyperclip first, then falls back to platform-specific tools:
      - macOS: pbpaste
      - Linux: wl-paste > xclip > xsel
      - Windows: powershell Get-Clipboard

    Returns:
        The clipboard text, or None if reading failed.
    """
    # Try pyperclip first
    try:
        import pyperclip

        return pyperclip.paste()
    except ImportError:
        pass

    # Try platform-specific tools
    system = platform.system()

    if system == "Darwin":
        pbpaste = shutil.which("pbpaste")
        if pbpaste:
            try:
                result = subprocess.run(
                    [pbpaste], capture_output=True, text=True, check=True
                )
                return result.stdout
            except subprocess.CalledProcessError:
                return None

    elif system == "Linux":
        for cmd in ("wl-paste", "xclip", "xsel"):
            tool = shutil.which(cmd)
            if tool:
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

    elif system == "Windows":
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
