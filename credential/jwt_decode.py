#!/usr/bin/env python3
"""Decode a JWT token and display its header, payload, and signature — like jwt.io in the terminal."""

import argparse
import base64
import json
import sys
from datetime import datetime, timezone

RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[0;33m'
CYAN = '\033[0;36m'
BOLD = '\033[1m'
DIM = '\033[2m'
NC = '\033[0m'

KNOWN_TIMESTAMP_CLAIMS = {'exp', 'iat', 'nbf', 'auth_time'}


def _b64_decode(segment: str) -> bytes:
    padding = 4 - len(segment) % 4
    if padding != 4:
        segment += '=' * padding
    return base64.urlsafe_b64decode(segment)


def _decode_json(segment: str, label: str) -> dict:
    try:
        return json.loads(_b64_decode(segment))
    except Exception as e:
        print(f"{RED}Error decoding {label}: {e}{NC}", file=sys.stderr)
        sys.exit(1)


def _format_timestamp(ts) -> str:
    try:
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except (ValueError, TypeError, OSError):
        return ''


def _print_json(data: dict, color: str) -> None:
    formatted = json.dumps(data, indent=2, ensure_ascii=False)
    for line in formatted.splitlines():
        print(f"  {color}{line}{NC}")


def _print_claim_annotations(data: dict) -> None:
    annotations = []
    for key in KNOWN_TIMESTAMP_CLAIMS:
        if key in data:
            human = _format_timestamp(data[key])
            if human:
                annotations.append(f"  {DIM}{key}: {data[key]} → {human}{NC}")

    if 'exp' in data:
        try:
            exp_dt = datetime.fromtimestamp(int(data['exp']), tz=timezone.utc)
            now = datetime.now(tz=timezone.utc)
            if exp_dt < now:
                annotations.append(f"  {RED}⚠ Token EXPIRED ({_format_timestamp(data['exp'])}){NC}")
            else:
                delta = exp_dt - now
                annotations.append(f"  {GREEN}✓ Token valid (expires in {delta}){NC}")
        except (ValueError, TypeError, OSError):
            pass

    if annotations:
        print()
        for a in annotations:
            print(a)


def decode_jwt(token: str) -> None:
    token = token.strip()
    if token.lower().startswith('bearer '):
        token = token[7:]

    parts = token.split('.')
    if len(parts) != 3:
        print(f"{RED}Error: Invalid JWT — expected 3 parts separated by '.', got {len(parts)}{NC}", file=sys.stderr)
        sys.exit(1)

    header = _decode_json(parts[0], 'header')
    payload = _decode_json(parts[1], 'payload')
    signature_b64 = parts[2]

    print(f"\n{BOLD}{'─' * 60}{NC}")
    print(f"{BOLD}  JWT Decoded{NC}")
    print(f"{BOLD}{'─' * 60}{NC}")

    print(f"\n{BOLD}{CYAN}▸ HEADER{NC} {DIM}(Algorithm & Token Type){NC}")
    _print_json(header, CYAN)

    print(f"\n{BOLD}{GREEN}▸ PAYLOAD{NC} {DIM}(Claims){NC}")
    _print_json(payload, GREEN)
    _print_claim_annotations(payload)

    print(f"\n{BOLD}{YELLOW}▸ SIGNATURE{NC}")
    print(f"  {YELLOW}{signature_b64}{NC}")

    alg = header.get('alg', 'unknown')
    print(f"  {DIM}Algorithm: {alg}{NC}")

    print(f"\n{BOLD}{'─' * 60}{NC}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Decode a JWT token and display its header, payload, and signature.',
        epilog='Example: jwt-decode eyJhbGciOiJIUzI1NiIs...',
    )
    parser.add_argument(
        'token',
        nargs='?',
        help='JWT token string (also accepts "Bearer <token>" format). If omitted, reads from stdin.',
    )
    args = parser.parse_args()

    if args.token:
        token = args.token
    elif not sys.stdin.isatty():
        token = sys.stdin.read().strip()
    else:
        parser.print_help()
        sys.exit(1)

    if not token:
        print(f"{RED}Error: No token provided.{NC}", file=sys.stderr)
        sys.exit(1)

    decode_jwt(token)


if __name__ == '__main__':
    main()
