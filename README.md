# ⚡ 产品能效标签智能检测系统

> Energy Label Intelligent Detection System

基于 **YOLO 知识蒸馏 + PaddleOCR** 的产品能效标签检测系统，支持标签识别、缺陷检测、位置检测和综合判定。提供 Web、移动端、OpenHarmony 鸿蒙端三端覆盖，通过 WebSocket 实现多端实时同步。

第十七届中国大学生服务外包创新创业大赛 · A02 · 诚迈科技命题 · 智能计算方向

---

## 目录

- [项目背景](#项目背景)
- [功能特性](#功能特性)
- [系统架构](#系统架构)
- [技术栈](#技术栈)
- [模型性能](#模型性能)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [部署方式](#部署方式)
  - [后端部署（必备）](#后端部署必备所有方式都依赖后端)
  - [⭐ 必选：OpenHarmony 鸿蒙端](#-必选openharmony-鸿蒙端)
  - [🏅 推荐：Web 前端](#-推荐web-前端)
  - [💡 加分项：uni-app 移动端](#-加分项uni-app-移动端)
  - [💡 加分项：Docker 部署](#-加分项docker-部署)
- [功能页面](#功能页面)
- [API 接口](#api-接口)
- [ML 引擎](#ml-引擎)
- [知识蒸馏训练](#知识蒸馏训练)
- [文档导航](#文档导航)
- [Contributing](#contributing)
- [License](#license)
- [团队](#团队)

---

## 项目背景

在家电生产线上，产品能效标签的质量直接影响产品合规性。传统人工检测效率低、易疲劳、一致性差。本系统通过摄像头采集产品能效标签图片，利用深度学习实现自动化检测，覆盖以下场景：

- 标签文字是否正确（OCR 识别能效等级、型号等）
- 标签是否有物理缺陷（破损、污渍、褶皱、划痕）
- 标签粘贴位置是否偏移
- 综合判定产品是否合格

系统面向工业产线部署，支持 OpenHarmony 开发板（DAYU200）作为边缘终端，通过知识蒸馏将大模型压缩到 5.3 MB，在 CPU 上也能实现约 100ms 的推理速度。

---

## 功能特性

- 🔍 **标签识别** — PaddleOCR 读取能效等级、型号、年耗电量、容积、品牌等信息
- 📋 **标签比对** — 与预设产品标准自动比对，判断 OCR 识别结果是否匹配
- 🔎 **缺陷检测** — YOLO 识别 5 种类型：正常、偏移、划痕、污渍、褶皱
- 📐 **位置检测** — 计算标签归一化坐标，3×3 宫格可视化粘贴位置偏移
- ✅ **综合判定** — 无缺陷 + 位置正常 + 能效达标 = 合格（OK），否则不合格（NG）
- 📊 **统计报表** — 7 天检测趋势柱状图、缺陷类型分布、位置缺陷分布、各型号合格率
- 📋 **历史记录** — 日期/状态筛选、卡片式记录展示、分页、CSV 导出
- 🔄 **多端实时同步** — WebSocket 广播，Web 端和鸿蒙端同步接收检测结果
- ⚙️ **配置热更新** — 修改灵敏度、光照补偿、相机参数后自动重载检测器，无需重启
- 🏭 **产品型号管理** — 支持多产品型号预设，每个型号独立配置标准能效等级

---

## 系统架构

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   Vue 3 Web │  │  uni-app    │  │ OpenHarmony │
│   前端      │  │  移动端     │  │  鸿蒙端     │
│  (5 页面)   │  │  (5 页面)   │  │  (4 页面)   │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
       └────────────────┼────────────────┘
                        │ HTTP REST + WebSocket
                        ▼
              ┌─────────────────────┐
              │    FastAPI 后端     │
              │    (端口 8000)      │
              │                     │
              │  ┌───────────────┐  │
              │  │ 路由层        │  │
              │  │ detection.py  │  │
              │  │ ml_detection  │  │
              │  │ export.py     │  │
              │  └───────┬───────┘  │
              │          │          │
              │  ┌───────┴───────┐  │
              │  │ 业务层        │  │
              │  │ crud / utils  │  │
              │  │ schemas       │  │
              │  └───────┬───────┘  │
              │          │          │
              │  ┌───────┴───────┐  │
              │  │ 数据层        │  │
              │  │ SQLAlchemy    │  │
              │  │ SQLite        │  │
              │  └───────────────┘  │
              └─────────┬───────────┘
                        │
           ┌────────────┼────────────┐
           ▼            ▼            ▼
    ┌───────────┐ ┌──────────┐ ┌──────────┐
    │ YOLO 推理 │ │ PaddleOCR│ │ 配置文件 │
    │ (蒸馏模型)│ │ (文字识别)│ │ (JSON)   │
    │ 5.3 MB    │ │ (可选)   │ │          │
    └───────────┘ └──────────┘ └──────────┘
```

**检测流程**：

```
用户上传图片 → 保存到 static/uploads/
  → 读取配置（灵敏度、光照补偿、预设型号）
  → 光照补偿预处理（OpenCV 亮度调整）
  → PaddleOCR 文字识别（可选，提取能效等级/型号等）
  → YOLO 推理（检测标签位置和缺陷类型）
  → 综合判定（缺陷 + 位置 + 能效 → OK/NG）
  → 写入数据库
  → WebSocket 广播结果到所有连接的客户端
  → 返回 JSON 响应给上传者
```

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端框架 | FastAPI | 异步 Python Web 框架，自带 Swagger 文档 |
| ORM | SQLAlchemy | 数据库抽象层 |
| 数据库 | SQLite | 轻量级，单文件，零配置 |
| Web 前端 | Vue 3 + Vite | Composition API，暗色主题，glass-morphism 风格 |
| 移动端 | uni-app | 跨平台，支持微信小程序 / H5 |
| 鸿蒙端 | OpenHarmony ArkTS | 面向 DAYU200 开发板，原生 UI |
| ML 推理 | YOLOv11 | 目标检测，支持 5 类标签状态 |
| 知识蒸馏 | DPFD (Decoupled Prototype Feature Distillation) | 教师-学生蒸馏框架 |
| OCR | PaddleOCR | 中文文字识别，可选依赖 |
| 实时通信 | WebSocket | 检测结果实时推送 |
| 容器化 | Docker + docker-compose | 一键部署 |

---

## 模型性能

通过 DPFD 知识蒸馏，将 YOLO11m 教师模型的知识迁移到 YOLO11n 学生模型：

| 指标 | Teacher (YOLO11m) | Student DPFD (YOLO11n) | 压缩效果 |
|------|-------------------|------------------------|----------|
| mAP@50 | 0.994 | 0.992 | -0.2% |
| mAP@50-95 | 0.989 | 0.986 | -0.3% |
| FPS (GPU) | 150 | 166 | 1.1x 加速 |
| 模型大小 | 38.6 MB | 5.3 MB | **86% 缩减** |
| 参数量 | 20.1M | 2.6M | **7.7x 压缩** |
| ONNX 大小 | — | 10.1 MB | 适合边缘部署 |

**检测类别**（5 类）：

| class_id | 名称 | 说明 | 是否缺陷 |
|----------|------|------|----------|
| 0 | label_normal | 正常标签 | 否 |
| 1 | label_offset | 标签偏移 | 是 |
| 2 | label_scratch | 标签划痕 | 是 |
| 3 | label_stain | 标签污渍 | 是 |
| 4 | label_wrinkle | 标签褶皱 | 是 |

---

## 项目结构

```
├── Service-Outsourcing/              # 主应用
│   ├── backend/                      # FastAPI 后端
│   │   ├── main.py                   # 应用入口、WebSocket、静态托管
│   │   ├── requirements.txt          # Python 核心依赖
│   │   ├── requirements-ml.txt       # ML 依赖（YOLO/OpenCV）
│   │   ├── .env.example              # 环境变量示例
│   │   ├── app/
│   │   │   ├── database.py           # SQLAlchemy 引擎 & Session
│   │   │   ├── models.py             # ORM 模型 (DetectionRecord)
│   │   │   ├── schemas.py            # Pydantic 请求/响应模型
│   │   │   ├── crud.py               # 数据库 CRUD 操作
│   │   │   ├── utils.py              # 工具函数（判定逻辑、配置读写）
│   │   │   ├── config_store.json     # 运行时配置持久化
│   │   │   └── routers/
│   │   │       ├── detection.py      # 核心 API（历史、统计、配置）
│   │   │       ├── ml_detection.py   # ML 检测 API（YOLO 推理 + 入库）
│   │   │       └── export.py         # 数据导出（CSV、摘要）
│   │   ├── static/uploads/           # 上传图片存储
│   │   └── tests/                    # 测试用例（15 个）
│   │
│   ├── frontend/
│   │   ├── web/                      # Vue 3 Web 前端（主力前端，5 页面）
│   │   │   ├── src/
│   │   │   │   ├── App.vue           # 根组件（侧边栏布局）
│   │   │   │   ├── router.js         # 路由定义
│   │   │   │   ├── api.js            # 统一 API 封装层
│   │   │   │   └── views/
│   │   │   │       ├── Home.vue      # 首页（项目介绍）
│   │   │   │       ├── Monitor.vue   # 实时监控（上传检测）
│   │   │   │       ├── History.vue   # 历史记录
│   │   │   │       ├── Statistic.vue # 统计报表
│   │   │   │       └── Setup.vue     # 系统配置
│   │   │   └── vite.config.js        # Vite 配置（API 代理）
│   │   │
│   │   ├── front/                    # uni-app 移动端（5 页面）
│   │   │   ├── pages/
│   │   │   │   ├── index/            # 首页（检测）
│   │   │   │   ├── history/          # 历史记录
│   │   │   │   ├── statistic/        # 统计
│   │   │   │   ├── setup/            # 设置
│   │   │   │   └── about/            # 关于
│   │   │   └── utils/api.js          # API 封装
│   │   │
│   │   └── front-homo/               # OpenHarmony 鸿蒙端（4 页面）
│   │       └── empty/src/main/ets/
│   │           ├── pages/
│   │           │   ├── Index.ets     # 监控（检测）
│   │           │   ├── History.ets   # 历史记录
│   │           │   ├── Statistics.ets# 统计
│   │           │   └── Settings.ets  # 设置
│   │           └── common/
│   │               ├── Api.ets       # HTTP API 封装
│   │               └── WebSocketClient.ets  # WebSocket 客户端
│   │
│   ├── Dockerfile                    # Docker 镜像定义
│   ├── docker-compose.yml            # Docker Compose 编排
│   └── .dockerignore
│
├── yolo-distiller/                   # YOLO 知识蒸馏训练框架
│   ├── scripts/
│   │   ├── inference_service.py      # 推理服务（EnergyLabelDetector 类）
│   │   ├── ocr_service.py            # OCR 服务（PaddleOCR 封装）
│   │   ├── train_teacher.py          # 教师模型训练
│   │   ├── train_student_dpfd.py     # 学生模型蒸馏训练
│   │   ├── prepare_dataset.py        # 数据集准备
│   │   ├── generate_synthetic_data.py# 合成数据增强
│   │   ├── merge_datasets.py         # 合并数据集
│   │   ├── evaluate_models.py        # 模型评估对比
│   │   ├── export_model.py           # 模型导出（ONNX 等）
│   │   ├── train_all.sh              # 一键训练脚本
│   │   └── run_pipeline.sh           # 完整流水线
│   ├── ultralytics/                  # 修改版 ultralytics（支持蒸馏）
│   │   ├── engine/trainer.py         # 训练器（添加蒸馏 loss）
│   │   ├── nn/tasks.py              # 网络结构
│   │   └── utils/loss.py            # 损失函数
│   └── runs/                         # 训练输出
│       ├── teacher/                  # 教师模型权重 + 训练日志
│       └── student/                  # 学生模型权重 + 训练日志
│
├── README.md                         # 本文档
├── DEPLOY_GUIDE.md                   # 全端部署指南（保姆级）
├── DEV_DOC.md                        # 完整技术参考文档
└── LOCAL_FILES_CHECKLIST.md          # 本地文件备份清单
```

---

## 快速开始

### 第一步：克隆仓库

```bash
git clone https://github.com/Stardep-lmc/EnergyLabel-Detection-System.git
cd EnergyLabel-Detection-System
```

### 第二步：恢复本地文件（重要！）

Git 仓库中不包含模型权重、训练数据集等大文件。克隆后需要从备份中恢复以下 4 个文件/目录到 `yolo-distiller/` 下：

| 文件/目录 | 路径 | 大小 | 是否必须 |
|-----------|------|------|----------|
| datasets | `yolo-distiller/datasets/` | ~793 MB | 训练时需要，仅推理可不放 |
| runs | `yolo-distiller/runs/` | ~60 MB | ⭐ **必须**（包含推理模型 best.pt） |
| yolo11m.pt | `yolo-distiller/yolo11m.pt` | 39 MB | 训练时需要，仅推理可不放 |
| yolo11n.pt | `yolo-distiller/yolo11n.pt` | 5.4 MB | 训练时需要，仅推理可不放 |

> 最小必须：只需要 `runs/` 目录（里面包含 `best.pt` 推理模型）。没有它后端检测接口返回 503。
>
> 完整文件清单和备份说明见 [LOCAL_FILES_CHECKLIST.md](LOCAL_FILES_CHECKLIST.md)。

### 第三步：部署

部署分为后端（必备）+ 前端（四选），详细的保姆级步骤见 [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md)。

| 环境要求 | 版本 |
|----------|------|
| Python | 3.9+ |
| Node.js | 16+（推荐 18+） |
| GPU | 可选（CPU 也能跑） |

---

## 部署方式

> 📌 以下为各部署方式的概述，每个方式都有超链接跳转到 [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md) 中的详细步骤。

### 后端（必备，所有前端都依赖后端）

后端是整个系统的核心，负责 YOLO 推理、数据库、API 服务。无论选择哪种前端，都必须先部署后端。

→ [查看后端部署详细步骤](DEPLOY_GUIDE.md#二后端部署必须先完成所有前端都依赖后端)

部署好后端后，选择前端方式：

| 方式 | 标记 | 适用场景 | 技术 | 硬件要求 |
|------|------|----------|------|----------|
| OpenHarmony 鸿蒙端 | ⭐ **必选** | 开发板硬件部署（比赛核心） | ArkTS | DAYU200 开发板 + DevEco Studio |
| Web 前端 | 🏅 **推荐** | 电脑大屏演示、多端协同展示 | Vue 3 + Vite | 无，任意浏览器 |
| uni-app 移动端 | 💡 加分项 | 手机浏览器 / 微信小程序 | uni-app | 手机或浏览器 |
| Docker | 💡 加分项 | 服务器一键部署 | Docker Compose | 安装了 Docker 的服务器 |

---

### ⭐ 必选：OpenHarmony 鸿蒙端

比赛核心展示端，部署到 DAYU200 开发板。需要 DevEco Studio + OpenHarmony SDK，修改后端 IP 后编译部署。

→ [查看鸿蒙端部署详细步骤](DEPLOY_GUIDE.md#三-openharmony-鸿蒙端部署必选比赛核心)

### 🏅 推荐：Web 前端

功能最完整的前端（5 页面），适合电脑大屏演示。开发模式 `npm run dev`，生产模式 `npm run build` 后由后端托管。

→ [查看 Web 前端部署详细步骤](DEPLOY_GUIDE.md#四-web-前端部署推荐大屏演示)

### 💡 加分项：uni-app 移动端

跨平台移动端，支持 H5 / 微信小程序。修改 `BASE_URL` 后用 HBuilderX 或 CLI 运行。

→ [查看 uni-app 部署详细步骤](DEPLOY_GUIDE.md#五-uni-app-移动端部署加分项)

### 💡 加分项：Docker 部署

后端 + Web 前端打包成容器，一条命令部署。

→ [查看 Docker 部署详细步骤](DEPLOY_GUIDE.md#六-docker-部署加分项适合服务器部署)

---

## 功能页面

### Web 端（5 页面）

| 页面 | 路径 | 功能 |
|------|------|------|
| 首页 | `/` | 项目介绍、canvas 星空背景动画、数字计数器、系统架构流程图、五维检测能力展示、技术栈标签 |
| 实时监控 | `/monitor` | ML 状态指示器、图片上传（点击/拖拽）、YOLO 推理结果展示（状态条+OCR+缺陷网格+位置宫格）、WebSocket 实时推送、最近记录表格 |
| 历史记录 | `/history` | 日期范围筛选、状态筛选（ALL/OK/NG）、卡片式记录（缩略图+型号+标签+缺陷+位置）、分页器、CSV 导出 |
| 统计报表 | `/statistic` | 7 天检测趋势柱状图（总数 vs 缺陷数）、缺陷类型分布条形图、位置缺陷分布、各型号合格率进度条 |
| 系统配置 | `/setup` | 产品型号管理（添加/删除/启用禁用）、位置偏移容忍度滑块、灵敏度（低/中/高）、光照补偿、相机参数、保存后自动重载检测器 |

### uni-app 移动端（5 页面）

| 页面 | 功能 |
|------|------|
| 首页 | ML 状态、图片上传检测、检测结果展示、最近记录 |
| 历史 | 状态筛选、记录列表、分页 |
| 统计 | 概览卡片、缺陷分布、型号合格率 |
| 设置 | 产品型号管理、检测参数、相机参数 |
| 关于 | 项目信息 |

### 鸿蒙端（4 页面）

| 页面 | 功能 |
|------|------|
| 📡 监控 | ML/WS 状态指示、图片上传检测、结果展示（状态条+OCR+缺陷网格+位置宫格）、最近记录 |
| 📋 历史 | 状态筛选 Chip、卡片式记录、分页加载 |
| 📊 统计 | 4 卡片概览、缺陷分布进度条、型号合格率 |
| ⚙️ 设置 | 产品型号管理、灵敏度/光照/曝光/分辨率参数、保存后自动重载检测器 |

---

## API 接口

### 核心接口

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/ml/detect` | 上传图片 → YOLO 推理 → OCR → 入库 → WebSocket 广播 → 返回结果 |
| GET | `/api/ml/status` | ML 服务状态（模型是否加载成功） |
| POST | `/api/ml/reload` | 重新加载模型（配置变更后调用） |

### 数据接口

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/current` | 获取最新一条检测结果 |
| GET | `/api/recent?limit=10` | 最近 N 条记录 |
| GET | `/api/history?page=1&pageSize=25&startDate=&endDate=&statusFilter=ALL` | 分页历史记录 |
| GET | `/api/statistic?startDate=&endDate=` | 统计数据（按日期范围） |
| GET/POST | `/api/config` | 系统配置读写 |

### 导出接口

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/export/csv` | 导出 CSV（带 BOM，支持 Excel 中文） |
| GET | `/api/export/summary` | 导出统计摘要 JSON |

### WebSocket

| 端点 | 说明 |
|------|------|
| `ws://host:8000/ws/detection` | 实时检测结果推送，支持心跳（ping/pong） |

完整 API 文档：启动后端后访问 `http://localhost:8000/docs`（Swagger UI）

---

## ML 引擎

### 推理服务 (`inference_service.py`)

`EnergyLabelDetector` 类负责模型加载和推理：

- 模型查找优先级：DPFD Student → CWD Student → Teacher
- 灵敏度映射：低 → conf 0.45、中 → conf 0.25、高 → conf 0.15
- 光照补偿：通过 OpenCV 调整亮度（`beta = offset * 25`）
- 位置检测：计算标签归一化坐标，与标准位置 (0.5, 0.5) 比较偏移量

### OCR 服务 (`ocr_service.py`)

基于 PaddleOCR 的文字识别（可选依赖，未安装时静默降级）：

- 提取信息：能效等级(1-5级)、能效标识(A++~C)、产品型号、年耗电量、容积、品牌
- 支持中文数字识别（一/二/三...）
- 正则匹配模式

### 综合判定逻辑

```
合格条件 = 无缺陷 AND 位置正常 AND 能效等级 ≤ 配置阈值 AND 检测到标签
```

---

## 知识蒸馏训练

如果需要自行训练模型（需要 GPU，约 16 小时），项目提供完整的训练流水线，包括数据集准备、教师模型训练、DPFD 知识蒸馏、模型评估和导出。

→ 详细训练流程和脚本说明见 [DEV_DOC.md 第五节 ML 引擎详解](DEV_DOC.md)

---

## 文档导航

| 文档 | 说明 | 适合谁看 |
|------|------|----------|
| [README.md](README.md)（本文档） | 项目全面介绍 | 所有人 |
| [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md) | 全端部署指南，保姆级步骤 | 需要部署的队员 |
| [DEV_DOC.md](DEV_DOC.md) | 技术参考（架构、API、数据流、ML 引擎） | 需要改代码的开发者 |
| [LOCAL_FILES_CHECKLIST.md](LOCAL_FILES_CHECKLIST.md) | 被 gitignore 排除的本地文件清单 | 需要迁移/备份环境的人 |

---

## 测试

后端包含 15 个单元测试（工具函数 + API 接口），运行 `cd Service-Outsourcing/backend && python -m pytest tests/ -v`。

---

## Contributing

欢迎提交 Issue 和 Pull Request。

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/xxx`)
3. 提交更改 (`git commit -m 'Add xxx'`)
4. 推送到分支 (`git push origin feature/xxx`)
5. 创建 Pull Request

---

## License

本项目仅供学习和竞赛使用。YOLO 训练框架基于 [Ultralytics](https://github.com/ultralytics/ultralytics)（AGPL-3.0）。

---

## 团队

第十七届中国大学生服务外包创新创业大赛参赛团队
