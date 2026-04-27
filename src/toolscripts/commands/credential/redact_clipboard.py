"""``redact-clipboard`` - mask credentials/secrets in clipboard text."""

from __future__ import annotations

import argparse
import re
import sys

from toolscripts.core.clipboard import copy_to_clipboard, paste_from_clipboard
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)

MASK = "[REDACTED]"

SENSITIVE_KEYWORDS: tuple[str, ...] = (
    "api_key", "apikey", "api-key",
    "secret", "secret_key", "secretkey", "secret-key",
    "token", "access_token", "access-token", "auth_token", "auth-token",
    "refresh_token", "refresh-token", "bearer",
    "password", "passwd", "pwd",
    "credential",
    "private_key", "privatekey", "private-key",
    "public_key", "publickey", "public-key",
    "client_secret", "client-secret",
    "aws_access_key_id", "aws_secret_access_key",
    "connection_string", "connection-string",
    "database_url", "database-url",
    "db_password", "db-password", "db_secret", "db-secret",
    "encryption_key", "encryption-key",
    "signing_key", "signing-key",
    "session_id", "sessionid", "session-id",
    "session_secret", "session-secret",
    "jwt_secret", "jwt-secret",
    "oauth_secret", "oauth-secret",
    "webhook_secret", "webhook-secret",
    "stripe_key", "stripe-key", "stripe_secret", "stripe-secret",
    "github_token", "github-token",
    "gitlab_token", "gitlab-token",
    "slack_token", "slack-token", "slack_secret", "slack-secret",
    "sendgrid_key", "sendgrid-key",
    "twilio_token", "twilio-token", "twilio_secret", "twilio-secret",
    "firebase_key", "firebase-key",
    "openai_key", "openai-key",
    "anthropic_key", "anthropic-key",
    "hf_token", "hf-token", "huggingface_token", "huggingface-token",
    "cohere_key", "cohere-key",
    "replicate_token", "replicate-token",
    "groq_key", "groq-key",
    "perplexity_key", "perplexity-key",
    "together_key", "together-key",
    "mistral_key", "mistral-key",
    "deepseek_key", "deepseek-key",
    "xai_key", "xai-key",
    "gemini_key", "gemini-key",
)

_PLACEHOLDERS = (
    "", "null", "none", "undefined", "changeme",
    "your_key_here", "your_secret_here", "<your-key-here>",
)

_SENTINEL = "\x00REDACTED\x00"


def _keyword_pattern() -> str:
    return "|".join(re.escape(k) for k in SENSITIVE_KEYWORDS)


def mask_text(text: str) -> tuple[str, int]:
    """Mask sensitive values; returns (masked_text, replacement_count)."""
    kw = _keyword_pattern()
    count = 0

    pem_re = re.compile(
        r"(-----BEGIN\s+(?:RSA\s+)?(?:EC\s+)?(?:OPENSSH\s+)?PRIVATE\s+KEY-----)"
        r"(.*?)"
        r"(-----END\s+(?:RSA\s+)?(?:EC\s+)?(?:OPENSSH\s+)?PRIVATE\s+KEY-----)",
        re.DOTALL | re.IGNORECASE,
    )

    def pem_repl(m: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return f"{m.group(1)}\n{_SENTINEL}\n{m.group(3)}"

    text = pem_re.sub(pem_repl, text)

    export_quoted = re.compile(
        rf'(export\s+)({kw})\s*=\s*(["\'])(.+?)\3', re.IGNORECASE | re.MULTILINE
    )

    def export_quoted_repl(m: re.Match[str]) -> str:
        nonlocal count
        count += 1
        q = m.group(3)
        return f"{m.group(1)}{m.group(2)}={q}{_SENTINEL}{q}"

    text = export_quoted.sub(export_quoted_repl, text)

    export_unquoted = re.compile(
        rf"(export\s+)({kw})\s*=\s*(\S+)", re.IGNORECASE | re.MULTILINE
    )

    def export_unquoted_repl(m: re.Match[str]) -> str:
        nonlocal count
        if m.group(3).lower() in _PLACEHOLDERS:
            return m.group(0)
        count += 1
        return f"{m.group(1)}{m.group(2)}={_SENTINEL}"

    text = export_unquoted.sub(export_unquoted_repl, text)

    dotenv_quoted = re.compile(
        rf'^({kw})\s*=\s*(["\'])(.+?)\2\s*$', re.IGNORECASE | re.MULTILINE
    )

    def dotenv_quoted_repl(m: re.Match[str]) -> str:
        nonlocal count
        count += 1
        q = m.group(2)
        return f"{m.group(1)}={q}{_SENTINEL}{q}"

    text = dotenv_quoted.sub(dotenv_quoted_repl, text)

    dotenv_unquoted = re.compile(
        rf"^({kw})\s*=\s*(\S+)\s*$", re.IGNORECASE | re.MULTILINE
    )

    def dotenv_unquoted_repl(m: re.Match[str]) -> str:
        nonlocal count
        if m.group(2).lower() in _PLACEHOLDERS:
            return m.group(0)
        count += 1
        return f"{m.group(1)}={_SENTINEL}"

    text = dotenv_unquoted.sub(dotenv_unquoted_repl, text)

    quoted_key = re.compile(
        rf'(["\'])({kw})\1\s*[:=]\s*(["\'])(.+?)\3', re.IGNORECASE
    )

    def quoted_key_repl(m: re.Match[str]) -> str:
        nonlocal count
        count += 1
        q = m.group(3)
        return f"{m.group(1)}{m.group(2)}{m.group(1)}: {q}{_SENTINEL}{q}"

    text = quoted_key.sub(quoted_key_repl, text)

    quoted_value = re.compile(
        rf'({kw})\s*[:=]\s*(["\'])(.+?)\2', re.IGNORECASE
    )

    def quoted_value_repl(m: re.Match[str]) -> str:
        nonlocal count
        count += 1
        q = m.group(2)
        return f"{m.group(1)}: {q}{_SENTINEL}{q}"

    text = quoted_value.sub(quoted_value_repl, text)

    unquoted_value = re.compile(rf"({kw})\s*[:=]\s*(\S+)", re.IGNORECASE)

    def unquoted_value_repl(m: re.Match[str]) -> str:
        nonlocal count
        value = m.group(2)
        if _SENTINEL in value or value.lower() in _PLACEHOLDERS:
            return m.group(0)
        count += 1
        return f"{m.group(1)}: {_SENTINEL}"

    text = unquoted_value.sub(unquoted_value_repl, text)

    bearer = re.compile(
        r"(Bearer\s+)([A-Za-z0-9\-_]+(?:\.[A-Za-z0-9\-_]+){2,})", re.IGNORECASE
    )

    def bearer_repl(m: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return f"{m.group(1)}{_SENTINEL}"

    text = bearer.sub(bearer_repl, text)

    jwt = re.compile(r"\b(eyJ[A-Za-z0-9\-_]+(?:\.[A-Za-z0-9\-_]+){2,})\b")

    def jwt_repl(_m: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return _SENTINEL

    text = jwt.sub(jwt_repl, text)

    text = text.replace(_SENTINEL, MASK)
    return text, count


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="redact-clipboard",
        description="Mask credentials and secrets in the clipboard so it can be safely shared.",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    text = paste_from_clipboard()
    if text is None:
        log.error("could not read from clipboard")
        sys.exit(1)
    if not text.strip():
        log.warning("clipboard is empty; nothing to do")
        return

    masked, count = mask_text(text)
    if count == 0:
        log.warning("no credentials detected; nothing changed")
        return

    log.success("masked %d credential(s)", count)
    print()
    print(masked)
    print()
    note = f"[Note: {count} sensitive value(s) above have been masked with [REDACTED] for security.]"
    print(note)
    print()

    clipboard_text = masked.rstrip() + "\n\n" + note + "\n"
    if copy_to_clipboard(clipboard_text):
        log.success("copied to clipboard")
    else:
        log.warning("could not copy to clipboard")


if __name__ == "__main__":
    main()
