# 算法工程师智能体设计方案

## 一、智能体定位

算法工程师智能体负责团队中与模型训练、验证、导出相关的所有算法任务。接收来自产品经理或 OpenClaw 的任务指令，自动执行模型开发流程，返回可部署的模型文件和评估报告。

## 二、核心功能

| 功能模块 | 具体能力 |
|---------|---------|
| 模型训练 | 接收数据集配置和训练参数，自动执行 YOLO 训练，输出模型文件 |
| 模型验证 | 在验证集上评估模型，输出 mAP、精确率、召回率等指标 |
| 模型导出 | 将训练好的模型导出为 ONNX / TensorRT 格式，便于边缘端部署 |
| 模型监控 | 定期检查模型效果，低于阈值时自动触发重新训练 |

## 三、数据集

来源：Kaggle - Hardhat Vest Dataset v3  
链接：https://www.kaggle.com/datasets/muhammetzahitaydn/hardhat-vest-dataset-v3  
总图片数：22,141 张  
类别：Helmet（戴安全帽）、NoHelmet（未戴帽）、Vest（穿反光衣）  
划分：训练集 17,248 / 验证集 2,438 / 测试集 2,455（8:1:1）  
配置文件：archive.yaml  

## 四、技术方案

### 4.1 开发环境

- Python 3.10
- PyTorch + CUDA 11.8
- Ultralytics YOLO

### 4.2 脚本设计

| 脚本 | 功能 | 输入 | 输出 |
|------|------|------|------|
| train.py | 模型训练 | 数据集配置、训练轮数、批次大小 | 模型文件 + JSON 结果 |
| val.py | 模型验证 | 模型路径、数据集配置 | mAP、精确率、召回率 |
| export.py | 模型导出 | 模型路径、导出格式 | ONNX / TensorRT 文件 |
| monitor.py | 模型监控 | 模型路径、阈值 | 触发重训信号 |

### 4.3 调用方式

所有脚本支持命令行调用，输出 JSON 格式结果，方便 OpenClaw 解析：

```bash
# 训练
python train.py --data archive.yaml --epochs 100 --batch 8

# 验证
python val.py --model best.pt --data archive.yaml

# 导出
python export.py --model best.pt --format onnx

