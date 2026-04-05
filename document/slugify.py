#!/usr/bin/env python3
"""
slugify.py - Interactive slug generator with curses UI.

Converts a phrase like "App Store Connect Version Information" into a slug
like "app-store-connect-version-information" by letting the user choose:
  1. Separator: '-' or '_'
  2. Case: unchanged, UPPERCASE, or lowercase

The result is printed to stdout and copied to the clipboard.

Usage:
    python3 slugify.py "App Store Connect Version Information Complete Filling Guide"
"""

import argparse
import curses
import os
import re
import sys

# Add project root to path so we can import utils.clipboard
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from libs.clipboard import copy_to_clipboard


def main():
    parser = argparse.ArgumentParser(
        description="Convert a phrase to a slug with interactive separator and case selection."
    )
    parser.add_argument(
        "phrase",
        nargs="+",
        help="The phrase to convert (pass as one quoted string or multiple words)",
    )
    args = parser.parse_args()

    phrase = " ".join(args.phrase)

    # Normalize whitespace: collapse multiple spaces into one
    phrase = " ".join(phrase.split())

    # Remove punctuation characters that shouldn't appear in filenames
    phrase = re.sub(r'[!,:.?;\'"()\[\]{}/\\|*<>@#$%^&+=~`]', "", phrase)

    separator = "-"
    case_mode = "unchanged"  # default: unchanged

    def menu(stdscr):
        nonlocal separator, case_mode

        curses.curs_set(0)  # Hide cursor
        stdscr.clear()

        separator_options = ["-", "_"]
        case_options = ["unchanged", "UPPERCASE", "lowercase"]

        sep_idx = 0
        case_idx = 0  # default to unchanged
        section = 0  # 0 = separator, 1 = case

        while True:
            stdscr.clear()
            h, w = stdscr.getmaxyx()

            title = " Slug Generator "
            title_x = max(0, (w - len(title)) // 2)
            try:
                stdscr.addstr(0, title_x, title, curses.A_BOLD | curses.A_REVERSE)
            except curses.error:
                pass

            try:
                stdscr.addstr(2, 2, f"Input: {phrase}", curses.A_DIM)
            except curses.error:
                pass

            # Separator section
            try:
                stdscr.addstr(4, 2, "Separator:", curses.A_BOLD)
            except curses.error:
                pass
            for i, opt in enumerate(separator_options):
                prefix = " > " if (section == 0 and i == sep_idx) else "   "
                style = (
                    curses.A_REVERSE
                    if (section == 0 and i == sep_idx)
                    else curses.A_NORMAL
                )
                line = f"{prefix}[{opt}]"
                try:
                    stdscr.addstr(5 + i, 4, line, style)
                except curses.error:
                    pass

            # Case section
            try:
                stdscr.addstr(8, 2, "Case:", curses.A_BOLD)
            except curses.error:
                pass
            for i, opt in enumerate(case_options):
                prefix = " > " if (section == 1 and i == case_idx) else "   "
                style = (
                    curses.A_REVERSE
                    if (section == 1 and i == case_idx)
                    else curses.A_NORMAL
                )
                line = f"{prefix}[{opt}]"
                try:
                    stdscr.addstr(9 + i, 4, line, style)
                except curses.error:
                    pass

            # Preview
            sep = separator_options[sep_idx]
            case = case_options[case_idx]
            words = phrase.split()
            preview = sep.join(words)
            if case == "UPPERCASE":
                preview = preview.upper()
            elif case == "lowercase":
                preview = preview.lower()

            try:
                stdscr.addstr(13, 2, "Preview:", curses.A_BOLD)
                stdscr.addstr(14, 4, preview, curses.A_UNDERLINE)
            except curses.error:
                pass

            try:
                stdscr.addstr(
                    16,
                    2,
                    "↑/↓: navigate  Enter: select  Tab: switch section  q: quit",
                    curses.A_DIM,
                )
            except curses.error:
                pass

            stdscr.refresh()

            key = stdscr.getch()

            if key in (ord("q"), ord("Q")):
                sys.exit(0)

            if key == 9:  # Tab
                section = 1 - section
            elif key == curses.KEY_UP or key == ord("k"):
                if section == 0:
                    sep_idx = (sep_idx - 1) % len(separator_options)
                else:
                    case_idx = (case_idx - 1) % len(case_options)
            elif key == curses.KEY_DOWN or key == ord("j"):
                if section == 0:
                    sep_idx = (sep_idx + 1) % len(separator_options)
                else:
                    case_idx = (case_idx + 1) % len(case_options)
            elif key == curses.KEY_LEFT or key == ord("h"):
                if section == 0:
                    sep_idx = (sep_idx - 1) % len(separator_options)
                else:
                    case_idx = (case_idx - 1) % len(case_options)
            elif key == curses.KEY_RIGHT or key == ord("l"):
                if section == 0:
                    sep_idx = (sep_idx + 1) % len(separator_options)
                else:
                    case_idx = (case_idx + 1) % len(case_options)
            elif key in (curses.KEY_ENTER, 10, 13):
                separator = separator_options[sep_idx]
                case_mode = case_options[case_idx]
                return

    curses.wrapper(menu)

    # Build result
    words = phrase.split()
    result = separator.join(words)
    if case_mode == "UPPERCASE":
        result = result.upper()
    elif case_mode == "lowercase":
        result = result.lower()

    print(result)

    # Copy to clipboard
    if copy_to_clipboard(result):
        print("Copied to clipboard.", file=sys.stderr)
    else:
        print("Warning: could not copy to clipboard.", file=sys.stderr)


if __name__ == "__main__":
    main()
