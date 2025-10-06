"""
A utility to fetch a webpage and convert its main content to Markdown.

Dependencies:
    pip install requests beautifulsoup4 markdownify
"""

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md


def web2md(url: str) -> str:
    """
    Fetch a webpage and convert its main content to Markdown.

    Args:
        url (str): The URL of the webpage to fetch.

    Returns:
        str: The Markdown representation of the webpage's main content.
    """
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    html = resp.text
    soup = BeautifulSoup(html, 'html.parser')

    # Try to extract <main> or <article> or fallback to <body>
    main_content = soup.find('main') or soup.find('article') or soup.body
    if not main_content:
        main_content = soup

    markdown = md(str(main_content), heading_style="ATX")
    return markdown


def main():
    import sys
    import pyperclip
    if len(sys.argv) != 2:
        print("Usage: python fetch.py <url>")
        sys.exit(1)
    url = sys.argv[1]
    markdown = web2md(url)
    pyperclip.copy(markdown)
    print("Markdown content copied to clipboard.")

if __name__ == "__main__":
    main()

