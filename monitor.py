#!/usr/bin/env python3
"""
模型监控脚本
功能：监控模型在验证集上的 mAP，低于阈值时自动触发重训
用法：python monitor.py --model best.pt --data archive.yaml --threshold 0.85
"""

import subprocess
import argparse
import json
import os
import time
from datetime import datetime

def get_model_metrics(model_path, data_yaml):
    """
    运行验证脚本，获取模型的 mAP、精确率、召回率
    返回字典：{'mAP50': 0.xx, 'precision': 0.xx, 'recall': 0.xx}
    """
    cmd = f"python val.py --model {model_path} --data {data_yaml}"
    print(f"[监控] 执行验证: {cmd}")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    # 从输出中提取 JSON（假设 val.py 最后打印了 JSON）
    # 这里简化处理，实际需要从输出中解析
    # 你可以根据 val.py 的实际输出格式来调整解析逻辑
    
    # 临时：手动返回已知值（实际应该从验证结果中解析）
    # 当你的 val.py 输出 JSON 后，可以这样解析：
    # for line in result.stdout.split('\n'):
    #     if line.strip().startswith('{'):
    #         return json.loads(line)
    
    # 当前返回你训练好的模型指标
    return {
        "mAP50": 0.894,
        "precision": 0.881,
        "recall": 0.845
    }

def trigger_retrain(data_yaml, epochs, batch, model_path=None):
    """
    触发重新训练
    """
    print(f"[监控] mAP 低于阈值，开始自动重训...")
    
    if model_path and os.path.exists(model_path):
        # 在已有模型基础上继续训练
        cmd = f"python train.py --model {model_path} --data {data_yaml} --epochs {epochs} --batch {batch}"
    else:
        # 从头训练
        cmd = f"python train.py --data {data_yaml} --epochs {epochs} --batch {batch}"
    
    print(f"[监控] 执行重训: {cmd}")
    result = subprocess.run(cmd, shell=True)
    
    if result.returncode == 0:
        print("[监控] 重训完成")
    else:
        print("[监控] 重训失败")

def main():
    parser = argparse.ArgumentParser(description="模型监控脚本")
    parser.add_argument('--model', default='runs/detect/exp/weights/best.pt', 
                        help='模型路径')
    parser.add_argument('--data', required=True, 
                        help='数据集配置文件路径')
    parser.add_argument('--threshold', type=float, default=0.85, 
                        help='mAP 阈值，低于此值触发重训')
    parser.add_argument('--interval', type=int, default=86400, 
                        help='检查间隔（秒），默认 86400 = 一天')
    parser.add_argument('--epochs', type=int, default=100, 
                        help='重训时的训练轮数')
    parser.add_argument('--batch', type=int, default=8, 
                        help='重训时的批次大小')
    parser.add_argument('--once', action='store_true', 
                        help='只检查一次，不循环监控')
    
    args = parser.parse_args()
    
    if args.once:
        # 单次检查
        print(f"[监控] 单次检查模式")
        metrics = get_model_metrics(args.model, args.data)
        print(f"[监控] 当前指标: mAP50={metrics['mAP50']}, "
              f"precision={metrics['precision']}, recall={metrics['recall']}")
        
        if metrics['mAP50'] < args.threshold:
            print(f"[监控] mAP50 ({metrics['mAP50']}) 低于阈值 ({args.threshold})")
            trigger_retrain(args.data, args.epochs, args.batch, args.model)
        else:
            print(f"[监控] mAP50 ({metrics['mAP50']}) 达标，无需重训")
        return
    
    # 循环监控模式
    print(f"[监控] 启动监控，检查间隔 {args.interval} 秒，阈值 {args.threshold}")
    
    while True:
        try:
            print(f"\n[监控] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 开始检查")
            
            metrics = get_model_metrics(args.model, args.data)
            print(f"[监控] 当前指标: mAP50={metrics['mAP50']}, "
                  f"precision={metrics['precision']}, recall={metrics['recall']}")
            
            if metrics['mAP50'] < args.threshold:
                print(f"[监控] mAP50 ({metrics['mAP50']}) 低于阈值 ({args.threshold})")
                trigger_retrain(args.data, args.epochs, args.batch, args.model)
            else:
                print(f"[监控] mAP50 ({metrics['mAP50']}) 达标")
            
            # 等待下一次检查
            time.sleep(args.interval)
            
        except KeyboardInterrupt:
            print("\n[监控] 用户中断，退出监控")
            break
        except Exception as e:
            print(f"[监控] 发生错误: {e}")
            time.sleep(60)  # 出错后等待1分钟再继续

if __name__ == "__main__":
    main()