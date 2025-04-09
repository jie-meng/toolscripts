#!/usr/bin/env python3

import sys
import pyperclip
from translate import Translator
from langdetect import detect_langs

def main():
    lang = 'en'
    from_lang = 'zh'

    if len(sys.argv) > 1:
        lang = sys.argv[1]
        if lang not in ['en', 'zh']:
            print("Error: Only 'en' or 'zh' are supported")
            return
    else:
        print("Select target language:")
        print("1. English (en)")
        print("2. Chinese (zh)")
        choice = input("Enter choice (1/2): ").strip()
        if choice == '1':
            lang = 'en'
            from_lang = 'zh'
        elif choice == '2':
            lang = 'zh'
            from_lang = 'en'
        else:
            print("Invalid choice")
            return

    text = input("Enter text to translate: ").strip()
    if not text:
        print("No text entered")
        return

    translator = Translator(from_lang=from_lang, to_lang=lang)
    try:
        translation = translator.translate(text)
        print(f"Translation: {translation}")
        
        pyperclip.copy(translation)
        print("(Copied to clipboard)")
    except Exception as e:
        print(f"Translation failed: {e}")

if __name__ == '__main__':
    main()
