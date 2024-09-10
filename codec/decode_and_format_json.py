import base64
import json
import sys

def decode_base64_to_json(base64_string):
    try:
        # 处理填充问题
        missing_padding = len(base64_string) % 4
        if missing_padding != 0:
            base64_string += '=' * (4 - missing_padding)

        # 解码 base64 字符串
        decoded_bytes = base64.b64decode(base64_string)
        decoded_str = decoded_bytes.decode('utf-8')

        # 解析 JSON 数据
        json_data = json.loads(decoded_str)

        # 格式化 JSON 数据
        formatted_json = json.dumps(json_data, indent=4, ensure_ascii=False)
        return formatted_json
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python decode_and_format_json.py <base64_string>")
        sys.exit(1)

    base64_string = sys.argv[1]
    formatted_json = decode_base64_to_json(base64_string)
    print(formatted_json)
