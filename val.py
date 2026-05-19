#!/usr/bin/env python3
"""
模型验证脚本
用法: python val.py --model best.pt --data data.yaml
"""

import subprocess
import argparse

def main():
    parser = argparse.ArgumentParser(description="模型验证脚本")
    parser.add_argument('--model', required=True, help='模型路径 (.pt)')
    parser.add_argument('--data', required=True, help='数据集配置文件路径')
    parser.add_argument('--imgsz', type=int, default=640, help='输入图片尺寸')
    parser.add_argument('--batch', type=int, default=8, help='批次大小')
    parser.add_argument('--conf', type=float, default=0.001, help='置信度阈值')
    parser.add_argument('--iou', type=float, default=0.6, help='NMS的IoU阈值')
    args = parser.parse_args()

    # 构建验证命令
    cmd = f"yolo detect val model={args.model} data={args.data} imgsz={args.imgsz} batch={args.batch} conf={args.conf} iou={args.iou}"
    
    print(f"[验证开始] {cmd}")
    subprocess.run(cmd, shell=True)
    print("[验证完成]")

if __name__ == '__main__':
    main()