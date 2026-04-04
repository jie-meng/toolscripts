#!/usr/bin/env python3
"""
redact-clipboard.py - Mask credentials and secrets from clipboard text.

Reads the current clipboard content, replaces sensitive values (API keys,
secrets, tokens, passwords, etc.) with a masked placeholder, prints the
result, and copies it back to the clipboard.

Usage:
    redact-clipboard
"""

import argparse
import re
import sys

# Add project root to path so we can import utils.clipboard
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from libs.clipboard import copy_to_clipboard, paste_from_clipboard

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
NC = "\033[0m"

MASK = "[REDACTED]"

# Keywords that indicate a sensitive field (case-insensitive matching)
SENSITIVE_KEYWORDS = [
    "api_key",
    "apikey",
    "api-key",
    "secret",
    "secret_key",
    "secretkey",
    "secret-key",
    "token",
    "access_token",
    "access-token",
    "auth_token",
    "auth-token",
    "refresh_token",
    "refresh-token",
    "bearer",
    "password",
    "passwd",
    "pwd",
    "credential",
    "private_key",
    "privatekey",
    "private-key",
    "public_key",
    "publickey",
    "public-key",
    "client_secret",
    "client-secret",
    "aws_access_key_id",
    "aws_secret_access_key",
    "connection_string",
    "connection-string",
    "database_url",
    "database-url",
    "db_password",
    "db-password",
    "db_secret",
    "db-secret",
    "encryption_key",
    "encryption-key",
    "signing_key",
    "signing-key",
    "session_secret",
    "session-secret",
    "jwt_secret",
    "jwt-secret",
    "oauth_secret",
    "oauth-secret",
    "webhook_secret",
    "webhook-secret",
    "stripe_key",
    "stripe-key",
    "stripe_secret",
    "stripe-secret",
    "github_token",
    "github-token",
    "gitlab_token",
    "gitlab-token",
    "slack_token",
    "slack-token",
    "slack_secret",
    "slack-secret",
    "sendgrid_key",
    "sendgrid-key",
    "twilio_token",
    "twilio-token",
    "twilio_secret",
    "twilio-secret",
    "firebase_key",
    "firebase-key",
    "openai_key",
    "openai-key",
    "anthropic_key",
    "anthropic-key",
    "hf_token",
    "hf-token",
    "huggingface_token",
    "huggingface-token",
    "cohere_key",
    "cohere-key",
    "replicate_token",
    "replicate-token",
    "groq_key",
    "groq-key",
    "perplexity_key",
    "perplexity-key",
    "together_key",
    "together-key",
    "mistral_key",
    "mistral-key",
    "deepseek_key",
    "deepseek-key",
    "xai_key",
    "xai-key",
    "gemini_key",
    "gemini-key",
]


def build_pattern():
    """Build a regex that matches key-value pairs with sensitive keys."""
    escaped = [re.escape(kw) for kw in SENSITIVE_KEYWORDS]
    keyword_pattern = "|".join(escaped)

    patterns = [
        # PEM private key blocks
        r"(-----BEGIN\s+(?:RSA\s+)?(?:EC\s+)?(?:OPENSSH\s+)?PRIVATE\s+KEY-----)(.*?)(-----END\s+(?:RSA\s+)?(?:EC\s+)?(?:OPENSSH\s+)?PRIVATE\s+KEY-----)",
        # Quoted key: "key" = "value" or 'key' = 'value' (JSON/YAML style)
        rf'(["\'])({keyword_pattern})\1\s*[:=]\s*(["\'])(.+?)\3',
        # Unquoted key with quoted value: key = "value" or key: 'value'
        rf'({keyword_pattern})\s*[:=]\s*(["\'])(.+?)\2',
        # Unquoted key with unquoted value: key = value or key: value
        rf"({keyword_pattern})\s*[:=]\s*(\S+)",
        # Environment variable style: export KEY=value
        rf'(export\s+)({keyword_pattern})\s*=\s*(["\']?)(.+?)\3(?=\s|$)',
        # Dotenv style: KEY=value (no spaces around =)
        rf'^({keyword_pattern})\s*=\s*(["\']?)(.+?)\2\s*$',
    ]

    return patterns, keyword_pattern


def mask_text(text: str) -> tuple[str, int]:
    """Mask all sensitive values in text.

    Returns:
        Tuple of (masked_text, count_of_replacements).
    """
    _, keyword_pattern = build_pattern()
    count = 0
    sentinel = "\x00REDACTED\x00"

    # 1. Handle PEM private key blocks first (multiline, DOTALL)
    pem_regex = re.compile(
        r"(-----BEGIN\s+(?:RSA\s+)?(?:EC\s+)?(?:OPENSSH\s+)?PRIVATE\s+KEY-----)(.*?)(-----END\s+(?:RSA\s+)?(?:EC\s+)?(?:OPENSSH\s+)?PRIVATE\s+KEY-----)",
        re.DOTALL | re.IGNORECASE,
    )

    def pem_replacer(m):
        nonlocal count
        count += 1
        return f"{m.group(1)}\n{sentinel}\n{m.group(3)}"

    text = pem_regex.sub(pem_replacer, text)

    # 2. Handle export KEY="value" (must come before general patterns)
    export_quoted_regex = re.compile(
        rf'(export\s+)({keyword_pattern})\s*=\s*(["\'])(.+?)\3',
        re.IGNORECASE | re.MULTILINE,
    )

    def export_quoted_replacer(m):
        nonlocal count
        count += 1
        quote = m.group(3)
        return f"{m.group(1)}{m.group(2)}={quote}{sentinel}{quote}"

    text = export_quoted_regex.sub(export_quoted_replacer, text)

    # Handle export KEY=value without quotes
    export_unquoted_regex = re.compile(
        rf"(export\s+)({keyword_pattern})\s*=\s*(\S+)",
        re.IGNORECASE | re.MULTILINE,
    )

    def export_unquoted_replacer(m):
        nonlocal count
        value = m.group(3)
        if value.lower() in ("", "null", "none", "undefined", "changeme"):
            return m.group(0)
        count += 1
        return f"{m.group(1)}{m.group(2)}={sentinel}"

    text = export_unquoted_regex.sub(export_unquoted_replacer, text)

    # 3. Handle dotenv KEY=value at line start (must come before general patterns)
    dotenv_quoted_regex = re.compile(
        rf'^({keyword_pattern})\s*=\s*(["\'])(.+?)\2\s*$',
        re.IGNORECASE | re.MULTILINE,
    )

    def dotenv_quoted_replacer(m):
        nonlocal count
        count += 1
        quote = m.group(2)
        return f"{m.group(1)}={quote}{sentinel}{quote}"

    text = dotenv_quoted_regex.sub(dotenv_quoted_replacer, text)

    # Handle dotenv KEY=value without quotes
    dotenv_unquoted_regex = re.compile(
        rf"^({keyword_pattern})\s*=\s*(\S+)\s*$",
        re.IGNORECASE | re.MULTILINE,
    )

    def dotenv_unquoted_replacer(m):
        nonlocal count
        value = m.group(2)
        if value.lower() in (
            "",
            "null",
            "none",
            "undefined",
            "changeme",
            "your_key_here",
            "your_secret_here",
            "<your-key-here>",
        ):
            return m.group(0)
        count += 1
        return f"{m.group(1)}={sentinel}"

    text = dotenv_unquoted_regex.sub(dotenv_unquoted_replacer, text)

    # 4. Handle quoted key: "key" = "value" or 'key' = 'value' (JSON style)
    quoted_key_regex = re.compile(
        rf'(["\'])({keyword_pattern})\1\s*[:=]\s*(["\'])(.+?)\3',
        re.IGNORECASE,
    )

    def quoted_key_replacer(m):
        nonlocal count
        count += 1
        quote = m.group(3)
        return f"{m.group(1)}{m.group(2)}{m.group(1)}: {quote}{sentinel}{quote}"

    text = quoted_key_regex.sub(quoted_key_replacer, text)

    # 5. Handle unquoted key with quoted value: key = "value" or key: 'value'
    quoted_value_regex = re.compile(
        rf'({keyword_pattern})\s*[:=]\s*(["\'])(.+?)\2',
        re.IGNORECASE,
    )

    def quoted_value_replacer(m):
        nonlocal count
        count += 1
        quote = m.group(2)
        return f"{m.group(1)}: {quote}{sentinel}{quote}"

    text = quoted_value_regex.sub(quoted_value_replacer, text)

    # 6. Handle unquoted key with unquoted value: key = value or key: value
    unquoted_value_regex = re.compile(
        rf"({keyword_pattern})\s*[:=]\s*(\S+)",
        re.IGNORECASE,
    )

    def unquoted_value_replacer(m):
        nonlocal count
        value = m.group(2)
        # Skip already-masked values and placeholders
        if sentinel in value or value.lower() in (
            "",
            "null",
            "none",
            "undefined",
            "changeme",
            "your_key_here",
            "your_secret_here",
            "<your-key-here>",
        ):
            return m.group(0)
        count += 1
        return f"{m.group(1)}: {sentinel}"

    text = unquoted_value_regex.sub(unquoted_value_replacer, text)

    # Replace sentinel with final mask
    text = text.replace(sentinel, MASK)

    return text, count


def main():
    parser = argparse.ArgumentParser(
        description="Mask credentials and secrets from clipboard text so it can be safely shared with AI."
    )
    parser.parse_args()

    # Read from clipboard
    text = paste_from_clipboard()
    if text is None:
        print(f"{RED}Error: could not read from clipboard.{NC}", file=sys.stderr)
        sys.exit(1)

    if not text.strip():
        print(f"{YELLOW}Clipboard is empty. Nothing to do.{NC}", file=sys.stderr)
        sys.exit(0)

    masked, count = mask_text(text)

    if count == 0:
        print(
            f"{YELLOW}No credentials detected. Nothing changed.{NC}",
            file=sys.stderr,
        )
        sys.exit(0)

    print(f"{GREEN}Masked {count} credential(s).{NC}", file=sys.stderr)

    print()
    print(masked)
    print()

    # Build clipboard output with trailing note
    clipboard_text = masked.rstrip() + "\n\n"
    clipboard_text += f"[Note: {count} sensitive value(s) above have been masked with [REDACTED] for security.]\n"

    # Copy to clipboard
    if copy_to_clipboard(clipboard_text):
        print(f"{GREEN}Copied to clipboard.{NC}", file=sys.stderr)
    else:
        print(f"{YELLOW}Warning: could not copy to clipboard.{NC}", file=sys.stderr)


if __name__ == "__main__":
    main()
