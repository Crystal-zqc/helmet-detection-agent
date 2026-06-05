# 算法工程师 Agent — 规格说明书

> **版本：** v2.0.0
> **最后更新：** 2026-05-30
> **更新内容：** 对标规格说明书标准全面重写：新增架构图、接口定义、测试用例、验收标准、文件结构附录、消息 JSON 示例、快速接入指南
> **项目路径：** `.\algo-agent`
> **本文档用途：** 作为算法工程师 Agent 的完整规格定义，供开发、测试、验证及多 Agent 协作对接使用。

---

## 目录

1. [智能体概述](#1-智能体概述)
2. [核心功能](#2-核心功能)
3. [设计架构](#3-设计架构)
4. [输入接口定义](#4-输入接口定义)
5. [输出接口定义](#5-输出接口定义)
6. [模块详解](#6-模块详解)
7. [多 Agent 协作规范](#7-多-agent-协作规范)
8. [数据持久化](#8-数据持久化)
9. [运行环境](#9-运行环境)
10. [测试用例](#10-测试用例)
11. [验收标准](#11-验收标准)
12. [附录 A：文件结构清单](#附录-a文件结构清单)
13. [附录 B：AgentMessage JSON 示例](#附录-bagentmessage-json-示例)
14. [附录 C：配置参考](#附录-c配置参考)
15. [附录 D：错误处理策略](#附录-d错误处理策略)
16. [附录 E：快速接入指南](#附录-e快速接入指南)

---

## 1. 智能体概述

### 1.1 智能体名称

**算法工程师 Agent**（AlgoAgent）

### 1.2 一句话定义

面向安全帽检测系统的算法工程智能体，负责模型训练、验证、导出、监控的全生命周期管理，并通过标准化消息协议接入多 Agent 协作网络。

### 1.3 核心价值

- 将"接收任务指令 → 执行算法任务 → 输出结构化结果"的全流程自动化
- 通过版本管理机制保证模型可追溯、可回滚
- 通过监控模块实现生产模型质量的持续保障
- 通过 AgentMessage 标准协议无缝接入多 Agent 系统

### 1.4 应用场景

| 场景 | 说明 |
|------|------|
| 独立训练 | 直接触发，完成数据预处理 → 训练 → 验证 → 版本归档 |
| 指令下发 | 接收产品经理 Agent 的任务指令，执行指定参数的训练任务 |
| 自动重训 | OpenClaw 调度器检测到模型退化时，自动触发重训流程 |
| 模型导出 | 验证通过后，导出边缘端可用格式，供部署 Agent 使用 |

---

## 2. 核心功能

### 2.1 模型训练（train）

- 接收数据集配置（`archive.yaml`）和训练超参数
- 自动执行数据预处理校验（合法性、完整性、隐私脱敏）
- 调用 YOLOv8 训练流程，输出带版本号的权重文件和训练报告
- GPU OOM 时自动将 batch 减半重试（最多 3 次）

### 2.2 模型验证（val）

- 在验证集上评估模型性能
- 输出 mAP@0.5、mAP@0.5:0.95、Precision、Recall 及各类别指标
- 结果写入 `val_report.json`，供监控模块比对

### 2.3 模型导出（export）

- 支持导出 ONNX（边缘端通用）和 TensorRT Engine（NVIDIA GPU 加速）
- 支持 FP32 / FP16 精度（FP16 仅限 NVIDIA GPU）
- 导出后自动执行 ONNX Runtime 兼容性测试

### 2.4 模型监控（monitor）

- 通过 APScheduler 定时评估生产模型的 mAP
- mAP 低于设定阈值时自动触发重训
- 连续重训失败 ≥ 3 次后推送人工告警，停止自动重试
- 支持 `--dry-run` 干运行模式，模拟流程不实际执行

### 2.5 模型版本管理

- 所有版本统一命名为 `vYYYYMMDD_xx` 格式
- `latest` 软链接指向当前生产版本，验证通过后自动更新
- 重复训练不覆盖历史结果，每次训练独立归档

---

## 3. 设计架构

### 3.1 总览

```
┌──────────────────────────────────────────────────────────────┐
│                   算法工程师 Agent v2.0.0                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────┐   │
│  │  CLI 入口     │   │  Multi-Agent │   │  OpenClaw Skill │   │
│  │  (cli.py)    │   │  协作入口     │   │  (SKILL.md)    │   │
│  └──────┬───────┘   └──────┬───────┘   └────────┬───────┘   │
│         │                  │                    │            │
│         └──────────────────┼────────────────────┘            │
│                            ▼                                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                  AlgoAgent 核心包                     │    │
│  │                                                      │    │
│  │  ┌──────────────────────────────────────────────┐   │    │
│  │  │  AlgoAgent (agent.py)                         │   │    │
│  │  │  ┌───────────┬───────────┬───────────────┐    │   │    │
│  │  │  │  train()  │   val()   │  export()     │    │   │    │
│  │  │  │  monitor()│  receive_task()           │    │   │    │
│  │  │  └─────┬─────┴─────┬─────┴───────┬───────┘    │   │    │
│  │  └────────┼───────────┼─────────────┼────────────┘   │    │
│  │           │           │             │                 │    │
│  │           ▼           ▼             ▼                 │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐        │    │
│  │  │preprocess│  │ versioner│  │ agent_message│        │    │
│  │  │ .py      │  │ .py      │  │ .py          │        │    │
│  │  └──────────┘  └──────────┘  └──────────────┘        │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  数据层                                                │   │
│  │  models/ ── vYYYYMMDD_xx/ (best.pt, train_report.json)│   │
│  │             latest -> (软链接)                         │   │
│  │  logs/   ── train_*.csv / val_*.json / monitor_*.log  │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 模块依赖关系

```
AlgoAgent ──┬── preprocess.py    （数据预处理与校验）
            ├── versioner.py     （模型版本管理与软链接维护）
            ├── agent_message.py  （多 Agent 通信协议）
            └── monitor.py       （定时监控与重训调度）

train()  ──→ preprocess → YOLOv8 YOLO.train() → versioner.save()
val()    ──→ YOLOv8 YOLO.val()  → versioner.save_report()
export() ──→ YOLOv8 YOLO.export() → onnxruntime 兼容测试
monitor() ──→ val() → 比对阈值 → 触发 train() / 推送告警
```

---

## 4. 输入接口定义

### 4.1 独立命令行模式

每个功能模块独立作为可执行脚本调用：

| 脚本 | 入口 | 必填参数 |
|------|------|---------|
| `train.py` | `python train.py` | `--data` |
| `val.py` | `python val.py` | `--model`、`--data` |
| `export.py` | `python export.py` | `--model`、`--format` |
| `monitor.py` | `python monitor.py` | `--model`、`--data`、`--threshold` |

### 4.2 协作模式（receive_task）

| 属性 | 说明 |
|------|------|
| **入口** | `AlgoAgent.receive_task(msg: AgentMessage) → str` |
| **输入格式** | `AgentMessage` 对象 |
| **输入示例** | `AgentMessage(sender="pm", receiver="algo", task_type="train", content="...")` |
| **响应** | JSON 字符串（任务结果报告） |

**AgentMessage 详细字段：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `sender` | str | ✅ | 发送方 Agent 标识，如 `"pm"`（产品经理）、`"orchestrator"` |
| `receiver` | str | ✅ | 接收方标识，固定为 `"algo"` |
| `task_type` | str | ✅ | 任务类型（见下方枚举） |
| `content` | str | ✅ | 任务参数 JSON 字符串 |
| `msg_id` | str | 自动 | 时间戳生成，格式 `YYYYMMDD_HHMMSS_ffffff` |
| `priority` | str | 可选（默认 `normal`） | `high / normal / low` |
| `callback_url` | str | 可选 | 任务完成后的回调地址；无则 Agent 不主动回调 |
| `timeout` | int | 可选（默认 3600） | 任务超时时间（秒） |
| `status` | str | 自动 | 生命周期：`pending → processing → done / error` |
| `result` | str | 自动 | 执行结果，完成后填充 |

**支持的 task_type：**

| task_type | 对应功能 | 必要参数（content 中） |
|-----------|----------|----------------------|
| `train` | 模型训练 | `data`（yaml 路径） |
| `val` | 模型验证 | `model`（权重路径）、`data` |
| `export` | 模型导出 | `model`、`format`（`onnx`/`engine`） |
| `monitor` | 启动监控 | `model`、`data`、`threshold` |

> **非法 `task_type`**：直接返回错误码 `4`，拒绝执行，不进入任务流程。

---

## 5. 输出接口定义

### 5.1 输出格式

所有脚本和协作接口均输出 **JSON 字符串**，包含统一的状态字段。

### 5.2 通用输出结构

```json
{
  "status": "success | error",
  "task_type": "train | val | export | monitor",
  "version": "v20260530_01",
  "message": "执行结果摘要",
  "metrics": { ... },
  "model_path": "./models/v20260530_01/best.pt",
  "log_path": "./logs/train_20260530_01.csv",
  "error_code": null
}
```

### 5.3 各任务输出字段

| 输出场景 | 关键字段 |
|----------|----------|
| 训练完成 | `version`、`best_epoch`、`train_time_seconds`、`metrics`（mAP50/mAP50-95/precision/recall）|
| 验证完成 | `metrics`（各类别 mAP）、`val_report` 路径 |
| 导出完成 | `export_path`（`.onnx`/`.engine`）、`format`、`onnx_compatible`（bool）|
| 监控告警 | `alert_type`（`retrain_triggered`/`max_retrain_exceeded`/`disk_warning`）、`current_map`、`threshold` |
| 任务失败 | `status: "error"`、`error_code`（见 §6.4）、`error_message` |

---

## 6. 模块详解

### 6.1 核心 Agent — AlgoAgent（`agent.py`）

**类：** `AlgoAgent`

**公开方法：**

| 方法 | 签名 | 说明 |
|------|------|------|
| `run_train()` | `(params: dict) → dict` | 执行训练流程 |
| `run_val()` | `(params: dict) → dict` | 执行验证流程 |
| `run_export()` | `(params: dict) → dict` | 执行导出流程 |
| `run_monitor()` | `(params: dict) → None` | 启动监控定时任务 |
| `receive_task()` | `(msg: AgentMessage) → str` | 协作模式统一入口 |

**内部处理流程（`receive_task` 路由）：**

```
接收 AgentMessage
        │
        ├── 验签（HMAC-SHA256）
        │         ↓ 失败 → 返回错误码 4，拒绝执行
        │
        ├── task_type 路由
        │   ├── "train"   → run_train(params)
        │   ├── "val"     → run_val(params)
        │   ├── "export"  → run_export(params)
        │   ├── "monitor" → run_monitor(params)
        │   └── 非法值   → 返回错误码 4
        │
        └── 执行结果序列化为 JSON → 回调 callback_url（若有）→ 返回
```

**属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `name` | str | 固定为 `"algo"` |
| `model_dir` | str | 模型版本根目录（默认 `./models/`） |
| `log_dir` | str | 日志根目录（默认 `./logs/`） |

### 6.2 数据预处理模块（`preprocess.py`）

在训练前执行，任何校验失败均终止训练并返回错误码 `1`。

| 校验类型 | 规则 | 失败处理 |
|----------|------|----------|
| 合法性校验 | 坐标归一化至 `[0,1]`，类别 ID 在 `[0,2]` 内 | 过滤异常样本，输出 `bad_annotations.txt` |
| 完整性校验 | 剔除缺失标注文件、图片损坏样本 | 过滤并记录 |
| 数据量校验 | 训练集 < 100 张时告警 | 打印 WARNING，不强制终止 |
| 隐私合规 | 对人脸区域执行高斯模糊（σ=2） | 自动处理，原始含人脸数据不存档 |

### 6.3 版本管理模块（`versioner.py`）

**版本号规则：** `vYYYYMMDD_xx`（日期 + 当日序号，从 `01` 开始递增）

**`latest` 软链接更新规则：**
1. 训练后验证通过（mAP 达标）→ 自动将 `latest` 指向新版本；
2. 更新完成后回调通知 OpenClaw 调度器（若配置了 `callback_url`）；
3. 验证未通过时 `latest` 保持不变，生产服务不受影响。

**目录结构：**

```
models/
├── v20260526_01/
│   ├── best.pt              # 最优权重（按 val loss 最低）
│   ├── last.pt              # 最终 epoch 权重
│   └── train_report.json    # 训练完整报告
├── v20260530_01/
│   └── ...
└── latest -> v20260530_01/  # 软链接，指向当前生产版本
```

### 6.4 通信协议（`agent_message.py`）

**数据类：** `AgentMessage`

**`msg_id` 生成规则：**
- 格式：`{YYYYMMDD}_{HHMMSS}_{microsec6}`
- 示例：`20260530_215900_123456`
- 在同一 Agent 进程内唯一；跨 Agent 时通过 `sender + msg_id` 实现全局唯一

**TaskType 常量：**

```python
class TaskType:
    TRAIN   = "train"
    VAL     = "val"
    EXPORT  = "export"
    MONITOR = "monitor"
```

**序列化 / 反序列化：**
- `to_dict()` → JSON 兼容的 dict
- `AgentMessage.from_dict(data: dict)` → AgentMessage 实例（未提供的可选字段自动填充默认值）

### 6.5 脚本参数规范

#### train.py

| 参数 | 类型 | 必填 | 默认值 | 取值范围 | 说明 |
|------|------|------|--------|----------|------|
| `--data` | str | ✅ | — | — | 数据集配置文件路径 |
| `--epochs` | int | ❌ | 100 | 1–1000 | 训练轮数 |
| `--batch` | int | ❌ | 8 | 1–32 | 批次大小（OOM 时自动减半重试）|
| `--model` | str | ❌ | `yolo26s.pt` | — | 预训练权重路径或型号名 |
| `--output-dir` | str | ❌ | `./models/<date>/` | — | 输出目录（自动创建，不覆盖）|

#### val.py

| 参数 | 类型 | 必填 | 默认值 | 取值范围 | 说明 |
|------|------|------|--------|----------|------|
| `--model` | str | ✅ | — | — | 模型权重路径（加载前校验 MD5）|
| `--data` | str | ✅ | — | — | 数据集配置文件路径 |
| `--iou-thres` | float | ❌ | 0.6 | 0.1–0.9 | IoU 阈值 |
| `--conf-thres` | float | ❌ | 0.25 | 0.01–0.99 | 置信度阈值 |

#### export.py

| 参数 | 类型 | 必填 | 默认值 | 取值范围 | 说明 |
|------|------|------|--------|----------|------|
| `--model` | str | ✅ | — | — | 模型权重路径 |
| `--format` | str | ✅ | — | `onnx` / `engine` | 导出格式 |
| `--half` | flag | ❌ | False | — | FP16，**仅限 NVIDIA GPU** |
| `--opset` | int | ❌ | 11 | 9–17 | ONNX opset 版本 |
| `--device` | str | ❌ | `0` | `0` / `cpu` | 导出设备 |

#### monitor.py

| 参数 | 类型 | 必填 | 默认值 | 取值范围 | 说明 |
|------|------|------|--------|----------|------|
| `--model` | str | ✅ | — | — | 模型权重路径 |
| `--data` | str | ✅ | — | — | 数据集配置文件路径 |
| `--threshold` | float | ✅ | — | 0.5–0.95 | mAP 下限阈值，超出范围拒绝执行 |
| `--interval` | int | ❌ | 86400 | 3600–604800 | 定时检查间隔（秒）|
| `--once` | flag | ❌ | False | — | 单次执行，不启动定时任务 |
| `--max-retrain` | int | ❌ | 3 | 1–10 | 最大自动重训次数 |
| `--dry-run` | flag | ❌ | False | — | 干运行：模拟流程，不实际执行重训 |

> **`--dry-run` 示例输出：**
> ```
> [DRY RUN] Current mAP: 0.82 | Threshold: 0.85
> [DRY RUN] Would trigger RETRAIN — no files modified.
> ```

### 6.6 返回码规范

| 返回码 | 含义 | 处理建议 |
|--------|------|----------|
| `0` | 成功 | — |
| `1` | 数据集错误（路径不存在 / 格式异常 / 未定义类别）| 检查数据集路径与 yaml 配置 |
| `2` | CUDA 错误（OOM 超重试上限 / 不支持 FP16）| 降低 batch 或切换 CPU 模式 |
| `3` | 模型文件错误（MD5 校验失败 / 不存在）| 重新下载或重新训练 |
| `4` | 参数非法（超出取值范围 / 非法 task_type / 签名失败）| 检查输入参数与签名 |
| `5` | 磁盘空间不足（使用率 > 80% 且清理后仍不足）| 手动清理旧模型后重试 |

---

## 7. 多 Agent 协作规范

### 7.1 当前协作架构

```
┌─────────────────┐    AgentMessage    ┌──────────────────┐
│  产品经理 Agent  │ ─────────────────→ │  算法工程师 Agent  │
│  (pm)           │  [task_type+params] │  (algo)          │
│                 │ ←───────────────── │                  │
└─────────────────┘   result (JSON str) └──────────────────┘

┌─────────────────┐    MQ 触发         ┌──────────────────┐
│  OpenClaw 调度  │ ─────────────────→ │  算法工程师 Agent  │
│  (orchestrator) │  [定时/监控重训]    │  (algo)          │
└─────────────────┘                   └──────────────────┘
```

### 7.2 协作流程

```
发送方构造 AgentMessage（含 HMAC-SHA256 签名）
        ↓
AlgoAgent.receive_task(msg) 接收并验签
        ↓
    验签失败 → 返回错误码 4，终止
        ↓
task_type 路由 → 执行对应模块
        ↓
结果序列化为 JSON 字符串
        ↓
有 callback_url → 回调推送
        ↓
返回 result 字符串
```

### 7.3 指令鉴权

所有来自 OpenClaw 的指令须附带 **HMAC-SHA256** 签名：

```
签名字段：HMAC-SHA256(msg_id + task_type + content, SECRET_KEY)
验签失败：返回错误码 4，不执行任务，记录安全日志
```

### 7.4 扩展协作规范（供新增 Agent 对接）

1. **消息格式统一：** 所有 Agent 使用 `AgentMessage` 进行通信
2. **接口签名：** 接收端方法签名必须为 `(msg: AgentMessage) → str`
3. **task_type 扩展：** 先在 `TaskType` 类中添加常量，再在 `AlgoAgent` 路由分支中添加处理逻辑
4. **错误处理：** 无法处理的 task_type 降级返回错误码 `4`，不崩溃

---

## 8. 数据持久化

### 8.1 文件清单

| 文件 / 目录 | 位置 | 说明 |
|------------|------|------|
| 模型权重 | `models/<version>/best.pt` | 每次训练独立归档，不覆盖 |
| 训练报告 | `models/<version>/train_report.json` | 训练结果、指标、耗时 |
| 验证报告 | `models/<version>/val_report.json` | 验证集评估指标 |
| 训练日志 | `logs/train_<version>.csv` | 逐 epoch 指标记录 |
| 监控日志 | `logs/monitor_<date>.log` | 每次监控检查记录 |
| 异常标注 | `logs/bad_annotations.txt` | 预处理过滤的异常样本清单 |

### 8.2 日志规范

```
logs/
├── train_20260530_01.csv    # 训练逐 epoch 日志（loss、mAP 等）
├── val_20260530_01.json     # 验证结果
└── monitor_20260530.log     # 监控运行日志
```

- 日志按天滚动，**自动清理 7 天前**的日志文件
- 日志级别：`INFO`（正常）/ `WARNING`（阈值临近、数据量少）/ `ERROR`（任务失败）
- 磁盘使用率 > 80% 时，优先清理 7 天前的日志；清理后仍不足则暂停任务并告警

### 8.3 清理策略

| 数据 | 保留策略 |
|------|----------|
| 训练日志 `logs/*.csv` | 自动清理 7 天前，手动清理模型时同步清理 |
| 模型权重 `models/` | 不自动清理；磁盘不足时由运维手动归档旧版本 |
| 监控日志 | 同训练日志，7 天自动滚动 |

---

## 9. 运行环境

### 9.1 系统要求

- Python 3.11.9（推荐）
- CUDA 11.8，驱动 ≥ 520.61（CPU 模式可忽略）
- 磁盘空间 ≥ 20GB（含数据集 + 多版本权重）

### 9.2 Python 依赖

| 包 | 版本 | 用途 |
|----|------|------|
| torch | 2.6.0 | 深度学习框架 |
| torchvision | 0.17.0 | 图像处理 |
| ultralytics | 8.3.0 | YOLOv8 官方包 |
| onnx | 1.14.0 | ONNX 模型格式支持 |
| onnxruntime-gpu | 1.15.0 | ONNX 推理验证（可选）|
| tensorrt | 8.6.1 | TensorRT 引擎导出（仅 NVIDIA GPU）|
| APScheduler | 3.10.4 | 定时监控调度 |

> `requirements.txt` 中不含 `+cu118` 后缀。安装时请根据实际 CUDA 版本选择对应 PyTorch 安装命令：
> ```bash
> # CUDA 11.8
> pip install torch==2.6.0 torchvision==0.17.0 --index-url https://download.pytorch.org/whl/cu118
> # CUDA 12.1
> pip install torch==2.6.0 torchvision==0.17.0 --index-url https://download.pytorch.org/whl/cu121
> ```

**支持的操作系统 / 硬件：**

| 环境 | 说明 |
|------|------|
| Ubuntu 20.04 / 22.04 | 推荐训练环境 |
| Windows 10/11（WSL2）| 开发调试可用 |
| NVIDIA T4 / A100 | 云端训练 GPU |
| NVIDIA Jetson Xavier NX | 边缘部署目标硬件 |
| CPU（无 CUDA）| 降级支持，仅用于功能验证 |

### 9.3 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 下载数据集
pip install kaggle
kaggle datasets download -d muhammetzahitaydn/hardhat-vest-dataset-v3 --unzip -p ./data/

# 3. 训练
python train.py --data ./data/archive.yaml --epochs 100 --batch 8

# 4. 验证
python val.py --model ./models/v20260530_01/best.pt --data ./data/archive.yaml

# 5. 导出
python export.py --model ./models/v20260530_01/best.pt --format onnx --opset 11

# 6. 启动监控（每日定时）
python monitor.py --model ./models/latest/best.pt --data ./data/archive.yaml --threshold 0.85
```

---

## 10. 测试用例

> ⚠️ 以下测试用例对应 `tests/test_agent.py` 中的自动化测试。
> 运行方式：`python tests/test_agent.py`（覆盖全部用例）

### 10.1 独立命令行测试

| 编号 | 测试用例 | 输入 | 预期输出 | 验证点 |
|------|----------|------|----------|--------|
| TC-01 | 正常训练 | `--data archive.yaml --epochs 5 --batch 4` | `train_report.json` 生成 | `status: success`、`mAP50 > 0` |
| TC-02 | 模型验证 | `--model ./models/latest/best.pt --data archive.yaml` | `val_report.json` 生成 | 包含 mAP50、precision、recall |
| TC-03 | ONNX 导出 | `--model ./models/latest/best.pt --format onnx --opset 11` | `best.onnx` 生成 | 文件存在且 `onnx_compatible: true` |
| TC-04 | TensorRT 导出 | `--model ./models/latest/best.pt --format engine --half` | `best.engine` 生成 | 仅 NVIDIA GPU 环境通过 |
| TC-05 | 监控单次执行 | `--model ... --threshold 0.85 --once` | 打印当前 mAP 与阈值比较 | 不启动定时任务，进程正常退出 |
| TC-06 | 干运行模式 | `--model ... --threshold 0.85 --dry-run` | 输出 `[DRY RUN]` 日志 | 无文件变更，重训未实际执行 |

### 10.2 协作模式测试

| 编号 | 测试用例 | 输入 | 预期输出 | 验证点 |
|------|----------|------|----------|--------|
| TC-07 | 接收训练指令 | `AgentMessage(task_type="train", content="{data:...}")` | 返回 `train_report.json` 内容 | `status: success`，含版本号 |
| TC-08 | 接收非法 task_type | `AgentMessage(task_type="deploy")` | 返回错误 | `error_code: 4` |
| TC-09 | 签名验证失败 | 篡改签名字段 | 拒绝执行 | `error_code: 4`，任务未启动 |
| TC-10 | 回调触发 | 配置 `callback_url`，任务完成后 | HTTP POST 发送至 callback_url | 回调内容包含 `version` 和 `metrics` |

### 10.3 异常场景测试

| 编号 | 测试用例 | 输入 | 预期行为 | 验证点 |
|------|----------|------|----------|--------|
| TC-11 | 数据集路径不存在 | `--data ./data/nonexist.yaml` | 终止并返回错误 | `error_code: 1`，无崩溃 |
| TC-12 | 模型文件损坏 | MD5 校验失败的权重文件 | 终止并告警 | `error_code: 3`，输出校验失败日志 |
| TC-13 | GPU OOM 自动重试 | 超大 batch | 自动减半 batch 并重试 | 重试 3 次后终止，`error_code: 2` |
| TC-14 | 磁盘使用 > 80% | 磁盘几乎满时触发训练 | 自动清理 7 天日志，仍不足则暂停 | 任务暂停，推送告警 |
| TC-15 | 阈值超出范围 | `--threshold 0.3`（< 0.5）| 拒绝执行 | `error_code: 4`，提示合理区间 |
| TC-16 | 连续重训失败 3 次 | monitor 持续触发重训均失败 | 停止自动重训，推送人工告警 | 日志记录 `max_retrain_exceeded` |
| TC-17 | `--half` 在 CPU 环境 | 无 CUDA 环境使用 `--half` | 前置检测拦截，友好提示 | `error_code: 2`，不崩溃 |

### 10.4 边缘场景测试（手动 / 集成验证）

| 编号 | 测试用例 | 预期行为 | 验证点 |
|------|----------|----------|--------|
| TC-EDGE-01 | 跨架构导出（A100 → Jetson）| 提示需在目标硬件重编译 | 不允许 `.engine` 跨架构使用 |
| TC-EDGE-02 | `latest` 软链接更新 | 验证通过后 `latest` 自动指向新版本 | 软链接目标路径更新 |
| TC-EDGE-03 | 同时触发多个训练任务 | 第二个任务进入等待队列 | `gpu.lock` 有效，无 GPU 资源冲突 |
| TC-EDGE-04 | 等待超 10 分钟 | 返回 `429 Too Many Requests` | 等待任务超时清理 |

---

## 11. 验收标准

### 11.1 功能完整性

- [ ] 四大核心功能（train / val / export / monitor）均能正常执行并输出结构化报告
- [ ] 协作模式支持 AgentMessage 接收、路由和返回
- [ ] 版本管理正确，`latest` 软链接在验证通过后自动更新
- [ ] 监控模块能检测 mAP 退化并自动触发重训
- [ ] `--dry-run` 模式下无任何文件被修改

### 11.2 性能要求

- [ ] 训练任务（100 epoch，NVIDIA T4）：< 90 分钟
- [ ] 验证任务（22K 张图片）：< 5 分钟
- [ ] ONNX 导出：< 60 秒
- [ ] 监控检查单次（含验证）：< 5 分钟
- [ ] 任务接收到开始执行的响应延迟：< 5 秒

> **性能测量环境：** Ubuntu 22.04，NVIDIA T4（16GB），CUDA 11.8，Python 3.11.9

### 11.3 健壮性

- [ ] 网络中断不崩溃（数据集下载支持断点续传）
- [ ] GPU OOM 自动降级（batch 减半重试）
- [ ] 模型文件损坏有 MD5 检测并友好提示
- [ ] 磁盘不足自动清理日志并告警
- [ ] 所有脚本入口参数非法时返回码 `4` 并提示，不崩溃

### 11.4 可扩展性

- [ ] 新增 task_type 只需添加 `TaskType` 常量 + Agent 路由分支，无需修改核心逻辑
- [ ] 新增 Agent 对接只需实现 `(AgentMessage) → str` 接口
- [ ] 部署目标硬件变更时，仅重新导出模型，无需修改训练代码

---

## 附录 A：文件结构清单

```
algo-agent/
├── README.md                         # 项目说明
├── AGENT_SPECIFICATION.md            # ← 本文档
├── requirements.txt                  # Python 依赖
├── train.py                          # 模型训练脚本
├── val.py                            # 模型验证脚本
├── export.py                         # 模型导出脚本
├── monitor.py                        # 模型监控脚本
├── algo_agent/                       # 核心 Python 包
│   ├── __init__.py
│   ├── agent.py                      # AlgoAgent 核心类
│   ├── agent_message.py              # 通信协议
│   ├── preprocess.py                 # 数据预处理与校验
│   └── versioner.py                  # 模型版本管理
├── data/
│   ├── archive.yaml                  # 数据集配置
│   ├── train/                        # 训练集图片 + 标注
│   ├── val/                          # 验证集图片 + 标注
│   └── test/                         # 测试集图片 + 标注
├── models/                           # 模型版本（自动生成）
│   ├── v20260530_01/
│   │   ├── best.pt
│   │   ├── last.pt
│   │   └── train_report.json
│   └── latest -> v20260530_01/
├── logs/                             # 运行日志（自动生成）
│   ├── train_20260530_01.csv
│   ├── val_20260530_01.json
│   └── monitor_20260530.log
├── tests/
│   └── test_agent.py                 # 自动化测试（含 TC-01 ~ TC-17）
└── skills/
    └── algo-agent/
        └── SKILL.md                  # OpenClaw Skill 定义
```

---

## 附录 B：AgentMessage JSON 示例

**发送训练任务：**

```json
{
  "msg_id": "20260530_215900_123456",
  "sender": "pm",
  "receiver": "algo",
  "task_type": "train",
  "content": "{\"data\": \"./data/archive.yaml\", \"epochs\": 100, \"batch\": 8, \"model\": \"yolo26s.pt\"}",
  "priority": "high",
  "callback_url": "http://orchestrator/api/task/callback",
  "timeout": 7200,
  "status": "pending",
  "result": null
}
```

**任务完成后的返回结果（result 字段内容）：**

```json
{
  "status": "success",
  "task_type": "train",
  "version": "v20260530_01",
  "best_epoch": 87,
  "train_time_seconds": 3621,
  "metrics": {
    "mAP50": 0.921,
    "mAP50-95": 0.763,
    "precision": 0.914,
    "recall": 0.889
  },
  "model_path": "./models/v20260530_01/best.pt",
  "log_path": "./logs/train_20260530_01.csv",
  "error_code": null
}
```

**任务失败示例：**

```json
{
  "status": "error",
  "task_type": "train",
  "error_code": 1,
  "error_message": "Dataset not found: ./data/archive.yaml",
  "model_path": null
}
```

---

## 附录 C：配置参考

### C.1 环境变量总表

| 变量 | 必填 | 默认值 | 用途 |
|------|------|--------|------|
| `HMAC_SECRET_KEY` | 否（规划中） | — | OpenClaw 指令签名验证密钥 |
| `DEFAULT_DATA_PATH` | 否 | `./data/archive.yaml` | 默认数据集配置路径 |
| `DEFAULT_MODEL_DIR` | 否 | `./models/` | 模型版本根目录 |
| `DEFAULT_LOG_DIR` | 否 | `./logs/` | 日志根目录 |
| `ALERT_CALLBACK_URL` | 否 | — | 监控告警回调地址 |
| `DISK_WARNING_THRESHOLD` | 否 | `0.8` | 磁盘使用率告警阈值（0–1）|

### C.2 启动前检查清单

- [ ] CUDA 驱动版本 ≥ 520.61（GPU 训练）
- [ ] 数据集已下载至 `./data/` 目录
- [ ] 磁盘剩余空间 ≥ 20GB
- [ ]（可选）`ALERT_CALLBACK_URL` 已配置 → 启用告警推送

---

## 附录 D：错误处理策略

### D.1 分层韧性策略

```
┌──────────────────────────┐
│  用户层 / 调度层          │
│  ── 结构化 JSON 错误返回  │
├──────────────────────────┤
│  业务层                  │
│  ┌──────┬───────┬──────┐ │
│  │训练  │ 验证  │ 导出 │ │
│  │OOM重试│MD5检查│兼容测│ │
│  └──────┴───────┴──────┘ │
├──────────────────────────┤
│  数据层                  │
│  磁盘不足 → 自动清理日志  │
└──────────────────────────┘
```

### D.2 各场景错误处理

| 场景 | 处理策略 | 返回码 |
|------|----------|--------|
| GPU OOM | 自动将 batch 减半重试，最多 3 次；超限终止 | `2` |
| 磁盘 > 80% | 自动清理 7 天前日志；仍不足则暂停任务并告警 | `5` |
| 模型文件损坏 | MD5 校验失败，标记异常，触发人工核查告警 | `3` |
| 数据集路径不存在 | 立即终止，输出具体路径错误信息 | `1` |
| 未定义类别 | 验证 yaml 类别一致性，不一致时终止 | `1` |
| 非法参数 | 入口强校验，拒绝执行，提示合理区间 | `4` |
| 签名失败 | 拒绝执行，记录安全日志 | `4` |
| 连续重训失败 ≥ 3 次 | 终止重训循环，推送人工告警 | — |
| `--half` 在 CPU 使用 | 前置 GPU 检测，友好提示后终止 | `2` |
| 跨架构使用 `.engine` | 导出时检测目标架构差异，提示重编译 | `2` |

---

## 附录 E：快速接入指南

### E.1 新增一个 task_type

**场景：** 需要支持新的算法任务，如 `"benchmark"`（性能基准测试）。

**步骤：**

1. 在 `agent_message.py` 的 `TaskType` 中添加常量：
   ```python
   class TaskType:
       BENCHMARK = "benchmark"
   ```

2. 在 `agent.py` 的 `receive_task` 路由分支中添加处理逻辑：
   ```python
   elif msg.task_type == TaskType.BENCHMARK:
       result = self.run_benchmark(params)
   ```

3. 实现 `run_benchmark()` 方法，返回统一结构的 dict。

**耗时估计：** 30–60 分钟（含开发和测试）。

### E.2 新增一个子 Agent 与本 Agent 对接

**前置条件：** 目标 Agent 接收 `AgentMessage`，返回 `str`。

```python
# 以部署 Agent 为例
msg = AgentMessage(
    sender="deploy",
    receiver="algo",
    task_type="export",
    content='{"model": "./models/latest/best.pt", "format": "onnx"}'
)
result = algo_agent.receive_task(msg)
```

**注意事项：**
- `content` 字段为 JSON 字符串，接收端自行 `json.loads()` 解析
- 必须携带合法的 HMAC-SHA256 签名，否则被拒绝

### E.3 替换 YOLOv8 为其他检测框架

**步骤：**
1. 修改 `train.py`、`val.py`、`export.py` 中的模型调用逻辑
2. 保持入参、返回码、输出 JSON 结构不变
3. `AlgoAgent.receive_task()` 和 `agent_message.py` 无需修改

**耗时估计：** 2–4 小时（含适配和测试）。

### E.4 模块独立性检查清单

新增或修改模块后，对照检查：

- [ ] 参数非法时是否通过返回码 `4` 拒绝，而非崩溃？
- [ ] 关键 I/O 操作是否有 try/except 包裹？
- [ ] 新增的 task_type 是否同时添加了常量和路由分支？
- [ ] 新增的输出文件是否在附录 A 文件结构清单中记录？
- [ ] 是否在第 10 节补充了对应的测试用例？
- [ ] 是否在第 11 节验收标准中补充了对应的验收项？
