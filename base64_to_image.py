#!/usr/bin/env python3
"""
Base64 to Image Converter
支持直接输入 base64 字符串或 JSON 格式
"""

import argparse
import base64
import json
import sys
import os
from pathlib import Path
from datetime import datetime


def decode_base64_to_image(base64_string: str, output_path: str) -> bool:
    """将 base64 字符串解码为图片文件"""
    # 移除可能的 data URI 前缀 (如 "data:image/png;base64,")
    if "," in base64_string:
        base64_string = base64_string.split(",", 1)[1]
    
    # 移除空白字符
    base64_string = base64_string.strip().replace("\n", "").replace("\r", "").replace(" ", "")
    
    try:
        image_data = base64.b64decode(base64_string)
        with open(output_path, "wb") as f:
            f.write(image_data)
        return True
    except Exception as e:
        print(f"解码错误: {e}", file=sys.stderr)
        return False


def detect_image_format(base64_string: str) -> str:
    """检测图片格式"""
    # 检查 data URI 前缀
    if base64_string.startswith("data:image/"):
        format_part = base64_string.split(";")[0]
        return format_part.replace("data:image/", "")
    
    # 通过解码后的魔数判断
    if "," in base64_string:
        base64_string = base64_string.split(",", 1)[1]
    
    base64_string = base64_string.strip()
    
    try:
        data = base64.b64decode(base64_string[:32])
        if data[:8] == b'\x89PNG\r\n\x1a\n':
            return "png"
        elif data[:2] == b'\xff\xd8':
            return "jpg"
        elif data[:6] in (b'GIF87a', b'GIF89a'):
            return "gif"
        elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
            return "webp"
        elif data[:4] == b'\x00\x00\x00\x0c' or data[:4] == b'\x00\x00\x00\x18':
            return "heic"
    except:
        pass
    
    return "png"  # 默认


def find_base64_recursive(data, path="", results=None):
    """递归查找嵌套结构中的 base64 字符串"""
    if results is None:
        results = []
    
    if isinstance(data, dict):
        for k, v in data.items():
            current_path = f"{path}_{k}" if path else k
            find_base64_recursive(v, current_path, results)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            current_path = f"{path}_{i}" if path else str(i)
            find_base64_recursive(item, current_path, results)
    elif isinstance(data, str) and len(data) > 100:
        # 简单判断是否可能是 base64
        try:
            # 尝试解码前 32 字节验证
            test_str = data.split(",", 1)[-1].strip()[:44]
            base64.b64decode(test_str)
            results.append((path, data))
        except:
            pass
    
    return results


def process_json_input(json_input: str, output_dir: str, key: str = None) -> int:
    """处理 JSON 输入，支持嵌套结构中的 base64 字符串"""
    try:
        data = json.loads(json_input)
    except json.JSONDecodeError as e:
        print(f"JSON 解析错误: {e}", file=sys.stderr)
        return 0
    
    os.makedirs(output_dir, exist_ok=True)
    count = 0
    
    # 递归查找所有 base64 字符串
    results = find_base64_recursive(data)
    
    # 如果指定了 key，过滤结果
    if key:
        results = [(path, val) for path, val in results if key in path]
    
    # 生成时间戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for i, (path, base64_str) in enumerate(results):
        ext = detect_image_format(base64_str)
        # 清理路径名
        safe_name = path.replace(".", "_").replace("/", "_")
        # 添加时间戳防止覆盖
        output_path = os.path.join(output_dir, f"{safe_name}_{timestamp}.{ext}")
        if decode_base64_to_image(base64_str, output_path):
            print(f"已保存: {output_path}")
            count += 1
    
    return count


def main():
    parser = argparse.ArgumentParser(
        description="将 base64 转换为图片文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 直接输入 base64 字符串
  python base64_to_image.py -b "iVBORw0KGgo..." -o output.png
  
  # 从文件读取 base64
  python base64_to_image.py -f base64.txt -o output.png
  
  # 处理 JSON 文件
  python base64_to_image.py -j data.json -d ./images
  
  # 处理 JSON 字符串
  python base64_to_image.py -j '{"image": "iVBORw0KGgo..."}' -d ./images
  
  # 从剪贴板读取 (macOS)
  pbpaste | python base64_to_image.py -b - -o output.png
        """
    )
    
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("-b", "--base64", help="Base64 字符串 (使用 '-' 从 stdin 读取)")
    input_group.add_argument("-f", "--file", help="包含 base64 的文件路径")
    input_group.add_argument("-j", "--json", help="JSON 字符串或 JSON 文件路径")
    
    parser.add_argument("-o", "--output", help="输出图片路径 (用于单个 base64)")
    parser.add_argument("-d", "--dir", default="./output", help="输出目录 (用于 JSON，默认: ./output)")
    parser.add_argument("-k", "--key", help="JSON 中的指定 key (可选)")
    
    args = parser.parse_args()
    
    # 处理 base64 字符串
    if args.base64:
        if args.base64 == "-":
            base64_str = sys.stdin.read()
        else:
            base64_str = args.base64
        
        if not args.output:
            ext = detect_image_format(base64_str)
            args.output = f"output.{ext}"
        
        if decode_base64_to_image(base64_str, args.output):
            print(f"已保存: {args.output}")
            return 0
        return 1
    
    # 从文件读取 base64
    if args.file:
        try:
            with open(args.file, "r") as f:
                base64_str = f.read()
        except Exception as e:
            print(f"读取文件错误: {e}", file=sys.stderr)
            return 1
        
        if not args.output:
            ext = detect_image_format(base64_str)
            args.output = f"output.{ext}"
        
        if decode_base64_to_image(base64_str, args.output):
            print(f"已保存: {args.output}")
            return 0
        return 1
    
    # 处理 JSON
    if args.json:
        # 判断是文件还是字符串
        if os.path.isfile(args.json):
            try:
                with open(args.json, "r") as f:
                    json_str = f.read()
            except Exception as e:
                print(f"读取 JSON 文件错误: {e}", file=sys.stderr)
                return 1
        else:
            json_str = args.json
        
        count = process_json_input(json_str, args.dir, args.key)
        if count > 0:
            print(f"共转换 {count} 张图片")
            return 0
        else:
            print("未找到有效的 base64 数据", file=sys.stderr)
            return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
