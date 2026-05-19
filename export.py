#!/usr/bin/env python3
"""
模型导出脚本
用法: python export.py --model best.pt --format onnx
支持格式: onnx, engine, torchscript, coreml, openvino, tflite
"""

import subprocess
import argparse

def main():
    parser = argparse.ArgumentParser(description="模型导出脚本")
    parser.add_argument('--model', required=True, help='模型路径 (.pt)')
    parser.add_argument('--format', default='onnx', 
                        choices=['onnx', 'engine', 'torchscript', 'coreml', 'openvino', 'tflite'],
                        help='导出格式')
    parser.add_argument('--imgsz', type=int, default=640, help='输入图片尺寸')
    parser.add_argument('--half', action='store_true', help='FP16量化（仅engine格式有效）')
    parser.add_argument('--device', default='0', help='设备（0表示第一张GPU，cpu表示CPU）')
    args = parser.parse_args()

    # 构建导出命令
    cmd = f"yolo export model={args.model} format={args.format} imgsz={args.imgsz} device={args.device}"
    if args.half and args.format == 'engine':
        cmd += " half=True"
    
    print(f"[导出开始] {cmd}")
    subprocess.run(cmd, shell=True)
    print(f"[导出完成] 模型已保存为 {args.model.replace('.pt', f'.{args.format}')}")

if __name__ == '__main__':
    main()