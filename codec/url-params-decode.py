#!/usr/bin/env python3
"""
解码并展示URL编码的查询参数。
支持完整的URL或纯查询字符串，自动识别并美化JSON值。
"""

import sys
import urllib.parse
import json
from pathlib import Path

# ANSI 颜色
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
BLUE = "\033[0;34m"
CYAN = "\033[0;36m"
NC = "\033[0m"  # No Color


def try_parse_json(value):
    """尝试解析可能是JSON的字符串"""
    value = value.strip()
    if not (value.startswith("{") and value.endswith("}")) and not (
        value.startswith("[") and value.endswith("]")
    ):
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, ValueError):
        return None


def format_value(key, value):
    """格式化显示值，对JSON进行美化"""
    # 尝试解析JSON
    parsed = try_parse_json(value)
    if parsed is not None:
        return f"{GREEN}{key}{NC}={CYAN}{json.dumps(parsed, indent=2, ensure_ascii=False)}{NC}"

    # 普通值
    return f"{GREEN}{key}{NC}={CYAN}{value}{NC}"


def decode_url_params(param_str):
    """
    解码URL参数字符串。
    输入可以是 "key1=val1&key2=val2" 的形式，也可以包含开头的'?'。
    """
    # 移除可能的开头的?
    param_str = param_str.lstrip("?")

    # 使用urllib.parse.parse_qs来解析，它会自动URL解码
    # parse_qs返回字典，值为列表（因为一个键可以对应多个值）
    params = urllib.parse.parse_qs(param_str, keep_blank_values=True)

    return params


def main():
    if len(sys.argv) != 2:
        print(f"{RED}Usage: url-decode-params <url_encoded_string> or <full_url>{NC}")
        print(
            f"Example: {sys.argv[0]} 'timestamp=2026-04-04+22%3A28%3A44&biz_content=%7B%22body%22%3A%22...%22%7D'"
        )
        print(f"Example: {sys.argv[0]} 'https://example.com?foo=bar&baz=qux'")
        sys.exit(1)

    input_str = sys.argv[1]

    # 如果是完整URL，提取查询部分
    if "?" in input_str:
        # 分割URL和查询字符串
        parts = input_str.split("?", 1)
        base_url = parts[0]
        query_string = parts[1]
        print(f"{YELLOW}Base URL:{NC} {base_url}")
        print(f"{YELLOW}Query String:{NC} {query_string}")
        print()
    else:
        query_string = input_str

    try:
        params = decode_url_params(query_string)
    except Exception as e:
        print(f"{RED}Error decoding parameters: {e}{NC}")
        sys.exit(1)

    if not params:
        print(f"{YELLOW}No parameters found.{NC}")
        sys.exit(0)

    print(f"{BLUE}Decoded Parameters:{NC}")
    for key, values in sorted(params.items()):
        # 由于parse_qs返回列表，但通常我们只有一个值
        for value in values:
            print(format_value(key, value))


if __name__ == "__main__":
    main()
