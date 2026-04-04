# 产品能效标签智能检测系统 — 开发文档

> 第十七届中国大学生服务外包创新创业大赛 · A02 · 诚迈科技命题
> 基于 OpenHarmony 的产品能效标签与缺陷检测系统 · 智能计算方向

本文档是项目的完整技术参考，供 AI 助手或新开发者快速理解项目全貌。

---

## 一、项目总览

### 1.1 项目目标

在家电生产线上，通过摄像头采集产品能效标签图片，利用 YOLO 目标检测 + PaddleOCR 文字识别，实现：
- 标签识别（OCR 读取能效等级、型号等）
- 标签比对（与预设标准自动比对）
- 缺陷检测（破损、污渍、褶皱、划痕）
- 位置检测（标签粘贴位置是否偏移）
- 综合判定（合格/不合格）

### 1.2 技术栈

| 层级 | 技术 |
|------|------|
| 后端 API | FastAPI + SQLAlchemy + SQLite |
| Web 前端 | Vue 3 + Vite (SPA) |
| 移动端 | uni-app (微信小程序/H5) |
| 鸿蒙端 | OpenHarmony ArkTS |
| ML 引擎 | YOLOv8/v11 + 知识蒸馏 (CWD/DPFD) |
| OCR | PaddleOCR (可选依赖) |
| 实时通信 | WebSocket |

### 1.3 仓库结构

```
LMC/
├── Service-Outsourcing/          # 主应用
│   ├── backend/                  # FastAPI 后端
│   │   ├── main.py              # 应用入口、WebSocket、前端静态托管
│   │   ├── requirements.txt     # Python 核心依赖
│   │   ├── requirements-ml.txt  # ML 可选依赖 (YOLO/PaddleOCR)
│   │   ├── app/
│   │   │   ├── database.py      # SQLAlchemy 引擎 & Session
│   │   │   ├── models.py        # ORM 模型 (DetectionRecord)
│   │   │   ├── schemas.py       # Pydantic 请求/响应模型
│   │   │   ├── crud.py          # 数据库 CRUD 操作
│   │   │   ├── utils.py         # 工具函数 (判定逻辑、配置读写)
│   │   │   ├── config_store.json # 运行时配置持久化
│   │   │   └── routers/
│   │   │       ├── detection.py  # 核心API (上传、记录、历史、统计、配置)
│   │   │       ├── ml_detection.py # ML检测API (YOLO推理+入库)
│   │   │       └── export.py     # 数据导出 (CSV、摘要)
│   │   └── static/uploads/       # 上传图片存储
│   │
│   └── frontend/
│       ├── web/                  # Vue 3 Web 前端 (主力前端)
│       │   ├── vite.config.js
│       │   ├── src/
│       │   │   ├── main.js       # Vue 应用入口
│       │   │   ├── router.js     # 路由定义
│       │   │   ├── App.vue       # 根组件 (侧边栏布局)
│       │   │   └── views/
│       │   │       ├── Home.vue      # 首页 (项目介绍)
│       │   │       ├── Monitor.vue   # 实时监控 (上传检测)
│       │   │       ├── History.vue   # 历史记录
│       │   │       ├── Statistic.vue # 统计报表
│       │   │       └── Setup.vue     # 系统配置
│       │   └── package.json
│       ├── front/                # uni-app 移动端
│       └── front-homo/           # OpenHarmony 鸿蒙端
│
└── yolo-distiller/               # YOLO 知识蒸馏训练框架
    ├── scripts/
    │   ├── inference_service.py  # 推理服务 (EnergyLabelDetector)
    │   ├── ocr_service.py        # OCR 服务 (PaddleOCR)
    │   ├── train_teacher.py      # 教师模型训练
    │   ├── train_student_dpfd.py # 学生模型蒸馏训练
    │   ├── prepare_dataset.py    # 数据集准备
    │   ├── generate_synthetic_data.py
    │   ├── merge_datasets.py
    │   ├── evaluate_models.py
    │   ├── export_model.py
    │   ├── train_all.sh
    │   └── run_pipeline.sh
    ├── datasets/
    ├── ultralytics/              # 修改版 ultralytics (支持蒸馏)
    └── runs/                     # 训练输出 (模型权重)
```

---

## 二、后端详解

### 2.1 入口 `main.py`

- FastAPI 应用，端口 8000
- 初始化 SQLite 数据库表 `Base.metadata.create_all(bind=engine)`
- CORS 中间件：通过环境变量 `CORS_ORIGINS` 配置允许的源（默认 `http://localhost:5173,http://localhost:8000`），`allow_credentials=True`
- 以 `backend/` 目录为基准计算 `BACKEND_DIR` 绝对路径，挂载 `/static` 静态文件目录（不依赖启动目录）
- 注册路由：`detection.router`、`ml_detection.router`、`export.router`
- WebSocket 端点 `/ws/detection`，`ConnectionManager` 管理连接，支持心跳 ping/pong
- `ws_manager` 挂载到 `app.state` 供 ml_detection 路由广播使用
- 前端静态托管：优先 `frontend/web/dist`，回退 `frontend/front/dist/build/h5`
- catch-all 路由支持 Vue Router history mode；对 `api/`、`static/`、`docs`、`openapi` 前缀的未匹配路径返回 HTTP 404（`JSONResponse`），避免误返回 200

### 2.2 数据库 `database.py`

- 以 `backend/` 目录为基准计算绝对路径 `BACKEND_DIR`，数据库文件固定为 `backend/detection.db`
- 支持通过环境变量 `DATABASE_URL` 覆盖数据库路径
- `check_same_thread=False` 允许多线程访问
- `get_db()` 生成器作为 FastAPI 依赖注入

### 2.3 数据模型 `models.py`

`DetectionRecord` 表 `detection_records`：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增主键 |
| device_id | String(64) | 设备ID，有索引 |
| batch_id | String(64) | 批次ID，有索引 |
| image_path | String(255) | 图片存储路径 |
| energy_level | Float | 能效等级数值 |
| defect_type | String(64) | 缺陷类型 |
| confidence | Float | 检测置信度 |
| is_qualified | Boolean | 是否合格 |
| created_at | DateTime | 创建时间（UTC，`datetime.now(timezone.utc)`），有索引 |

| preset_model | String(128) | 产品型号（ML 检测时写入） |
| position_status | String(32) | 位置状态（默认"正常"） |
| position_x | Float | 标签位置 X 归一化坐标 |
| position_y | Float | 标签位置 Y 归一化坐标 |
| ocr_text | String(255) | OCR 识别文本 |

格式化函数优先读取数据库字段，旧记录（字段为空）自动降级到推算逻辑（`getattr` + `or` 回退）。

### 2.4 Pydantic Schema `schemas.py`

两套模型体系：
1. **原有接口模型**：`DetectionRecordCreate`（含 `position_status`、`is_qualified: Optional[bool]` 字段，ML 路径直接传入推理判定结果，普通接口留 None 走 `judge_qualified`）、`DetectionRecordOut`、`DetectionStatistics`、`HistoryResponse`
2. **前端兼容模型**：`CurrentResultResponse`、`RecentRecordResponse`、`HistoryRecordResponse`、`FrontendHistoryResponse`、`StatisticsItemResponse`、`ConfigResponse`、`SaveConfigResponse`

### 2.5 CRUD `crud.py`

核心函数：
- `create_detection_record(db, record)` — 创建记录，若 `record.is_qualified` 不为 None 则直接使用（ML 路径），否则调用 `judge_qualified` 判定合格（普通接口路径）
- `get_history_with_stats(db, skip, limit, device_id, batch_id)` — 原有历史+统计（SQL聚合）
- `get_latest_record(db)` — 最新一条记录
- `get_recent_records(db, limit)` — 最近N条
- `build_filtered_query(db, start_date, end_date, status_filter)` — 构建筛选查询
- `get_frontend_history(db, page, page_size, ...)` — 前端分页历史
- `get_statistics_records(db, start_date, end_date)` — 统计数据（按时间升序）

### 2.6 工具函数 `utils.py`

- `get_max_energy_level()` — 从配置文件读取标准能效等级（`standardLabel` 字段，如 A++→1.0、A→2.0、B→3.0），返回允许的最大能效等级数值，默认 3.0
- `generate_filename(filename)` — UUID 重命名上传文件
- `judge_qualified(energy_level, defect_type, position_status)` — 综合判定：能效等级不超过配置阈值 且无缺陷且位置正常
- `normalize_defect_type(defect_type)` — 标准化缺陷类型字符串
- `build_ocr_text(energy_level)` — 非 ML 接口的降级方案：数字→"x级能效"文本；ML 检测路径入库时写入真实 OCR 文本，格式化函数优先使用数据库 `ocr_text` 字段
- `load_config()` / `save_config(data)` — JSON 配置文件读写（`save_config` 使用原子写入：先写临时文件再 `os.replace`，避免并发写入导致文件损坏）

### 2.7 配置文件 `config_store.json`

```json
{
  "models": [{"name":"冰箱","model":"BCD-520W","standardLabel":"A++","enabled":true}],
  "positionTolerance": 10,
  "sensitivity": "中",
  "lightCompensation": 0,
  "camera": {"exposure": 0, "resolution": "1280x720"}
}
```

---

## 三、API 接口清单

### 3.1 detection.py 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/detect/upload_image` | 上传图片（仅存储，不检测） |
| POST | `/api/v1/detect/record` | 手动创建检测记录 |
| GET | `/api/v1/detect/history` | 原有历史接口（含统计） |
| GET | `/api/current` | 获取最新检测结果 |
| GET | `/api/recent?limit=10` | 最近N条记录 |
| GET | `/api/history?page=1&pageSize=25&startDate=&endDate=&statusFilter=ALL` | 前端分页历史 |
| GET | `/api/config` | 获取系统配置 |
| POST | `/api/config` | 保存系统配置 |
| GET | `/api/statistic` 或 `/api/statistics` | 统计数据（按日期范围） |

**字段适配函数**（detection.py 内部）：
- `build_image_url(request, image_path)` — 拼接完整图片URL
- `pick_preset_model(record)` — 优先读取数据库 `preset_model` 字段，为空时从配置文件读取第一个启用型号作为降级
- `to_status(record)` — `is_qualified` → "OK"/"NG"
- `to_position_status(record)` — 从 defect_type 推断位置状态
- `format_current_record` / `format_recent_record` / `format_history_record` / `format_statistics_record` — 各接口的格式化函数

### 3.2 ml_detection.py 路由（前缀 `/api/ml`）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/ml/detect` | 上传图片→YOLO推理→入库→返回结果→WebSocket广播 |
| GET | `/api/ml/status` | ML服务状态（模型是否加载） |
| POST | `/api/ml/reload` | 重新加载模型 |

**ML检测流程**：
1. 校验文件格式（jpg/jpeg/png）
2. 保存到 `static/uploads/`
3. 懒加载 `EnergyLabelDetector`（按优先级查找模型：DPFD Student > CWD Student > Teacher），使用 `threading.Lock` 保证线程安全；从配置读取 `sensitivity` 映射为 `conf_threshold`（低→0.45、中→0.25、高→0.15）和 `positionTolerance`；模型不存在时返回 503 并附带训练引导命令
4. 一次性读取配置（`load_config()` 仅调用一次），从中提取 `lightCompensation`、预设型号等
5. 执行推理 `detector.detect(file_path, brightness_offset=...)` 进行光照补偿预处理
6. 转换为后端格式 `detector.to_backend_format(output, device_id, batch_id)`（支持可选 `device_id`/`batch_id` 查询参数）
7. 从配置读取预设型号写入 `preset_model`，OCR 文本写入 `ocr_text`，创建数据库记录
8. 构建前端响应（含 detections 数组、OCR 信息等）
9. WebSocket 广播检测结果（直接 await，失败时记录日志不影响主流程）

### 3.3 export.py 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/export/csv` | 导出CSV（带BOM，支持Excel中文） |
| GET | `/api/export/summary` | 导出统计摘要JSON（SQL聚合，不全量加载记录） |

### 3.4 WebSocket

- 端点：`/ws/detection`
- 心跳：客户端发 `"ping"`，服务端回 `"pong"`
- 广播消息格式：`{"type":"detection_result","status":"OK/NG","defect_type":"...","position_status":"...","confidence":0.95,"timestamp":"...","image_url":"..."}`

---

## 四、前端详解（Web）

### 4.1 技术配置

- Vue 3 + Composition API (`<script setup>`)
- Vue Router (history mode)
- Vite 开发服务器 port 5173
- API 代理：`/api` → `http://localhost:8000`，`/static` → `http://localhost:8000`，`/ws` → `ws://localhost:8000`（启用 WebSocket 代理）
- 无 UI 框架，纯手写 CSS（暗色主题，glass-morphism 风格）
- 统一 API 封装层 `src/api.js`（15 秒超时、自动错误提取、`ApiError` 类），各页面可通过 `import { api } from '../api.js'` 使用
- 无状态管理库（各页面独立 fetch）

### 4.2 全局样式体系（App.vue）

CSS 变量：
- 背景色：`--bg-0` (#080a12) ~ `--bg-4` (#222738)
- 文字色：`--text-1` (白) / `--text-2` (灰) / `--text-3` (暗灰)
- 强调色：`--accent` (#6366f1 靛蓝) / `--purple` / `--pink` / `--green` / `--red` / `--orange` / `--cyan`
- 圆角：`--radius` (12px) / `--radius-lg` (16px) / `--radius-xl` (20px)

公共组件类：
- `.glass-card` — 毛玻璃卡片（hover 发光效果）
- `.btn-primary` — 渐变主按钮（涟漪+光泽动画）
- `.btn-ghost` — 幽灵按钮
- `.input-field` — 输入框
- `.badge-ok` / `.badge-ng` — 状态徽章
- `.page-header` / `.page-body` — 页面布局
- `.section-head` / `.section-icon` — 区块标题
- `.grid-2` — 两列网格
- `.skeleton` — 骨架屏加载

### 4.3 路由

| 路径 | 组件 | 说明 |
|------|------|------|
| `/` | Home.vue | 首页（无侧边栏） |
| `/monitor` | Monitor.vue | 实时监控 |
| `/history` | History.vue | 历史记录 |
| `/statistic` | Statistic.vue | 统计报表 |
| `/setup` | Setup.vue | 系统配置 |

侧边栏在 `path !== '/'` 时显示，底部有后端连接状态指示器（通过 `/api/config` 检测）。

### 4.4 各页面功能

**Home.vue**：
- 项目介绍着陆页，canvas 星空背景动画（`onUnmounted` 时正确清理 resize 监听器，避免内存泄漏）
- 数字计数器动画（识别准确率 99.2%、推理延迟 <50ms 等）
- 系统架构流程图（图像采集→AI推理→OCR识别→综合判定→数据分析）
- 五维检测能力展示
- 功能入口快捷卡片
- 技术栈标签

**Monitor.vue**：
- ML 服务状态指示器（调用 `/api/ml/status`）
- 图片上传区域（点击/拖拽，支持预览）
- 点击"开始检测"→POST `/api/ml/detect`
- 检测结果展示：状态条（OK绿/NG红）、标签识别（图片+OCR文本+置信度+匹配结果）、缺陷检测（5种类型网格）、位置检测（3×3宫格可视化）
- 最近记录表格（调用 `/api/recent`）
- WebSocket 实时接收新检测结果；WebSocket 连接成功后自动停止轮询，断开后恢复 5 秒轮询作为降级
- Toast 通知

**History.vue**：
- 日期范围筛选 + 状态筛选（ALL/OK/NG）
- 卡片式记录展示（缩略图+型号+标签+缺陷+位置），含错误提示和加载状态
- 分页器
- CSV 导出按钮（调用 `/api/export/csv`）

**Statistic.vue**：
- 最近7天检测趋势柱状图（总数 vs 缺陷数，仅通过 `hasDefect` 布尔值判断缺陷）
- 缺陷类型分布（水平条形图，动态收集，`"无"` 归入 `"正常"`，支持逗号分隔多缺陷拆分）
- 位置缺陷分布（水平条形图，动态收集后端返回的位置状态，不硬编码）
- 各型号合格率（进度条）
- 数据来源：`/api/statistic?startDate=...&endDate=...`

**Setup.vue**：
- 预设产品型号管理（添加/删除/启用禁用，至少保留一个型号）
- 检测参数：位置偏移容忍度（滑块 0-20%）、缺陷检测灵敏度（低/中/高）、光照补偿（-5~+5）
- 相机参数：曝光（-3~+3）、分辨率（640×480/1280×720/1920×1080）
- 保存/恢复默认（保存配置后自动调用 `/api/ml/reload` 重载检测器，使灵敏度等参数立即生效）
- 数据来源：GET/POST `/api/config`

---

## 五、ML 引擎详解

### 5.1 推理服务 `inference_service.py`

**EnergyLabelDetector 类**：
- 构造参数：`model_path`、`conf_threshold`(0.25)、`iou_threshold`(0.45)、`position_tolerance`(0.1)、`device`("cpu")
- 模型查找优先级：DPFD Student → CWD Student → Teacher
- 标准标签位置：默认 `(cx=0.5, cy=0.5)` 归一化坐标

**类别定义**（5类）：

| class_id | 英文名 | 中文名 | 是否缺陷 |
|----------|--------|--------|----------|
| 0 | label_normal | 正常 | 否 |
| 1 | label_offset | 偏移 | 是 |
| 2 | label_scratch | 划痕 | 是 |
| 3 | label_stain | 污渍 | 是 |
| 4 | label_wrinkle | 褶皱 | 是 |

**detect(image_path, brightness_offset) 流程**：
1. 光照补偿预处理：若 `brightness_offset != 0`，使用 OpenCV 调整亮度（`beta = offset * 25`），写入临时文件供推理使用，推理后自动清理
2. 可选 OCR 识别（调用 ocr_service，使用经过光照补偿的图片）
3. YOLO 推理 `model.predict()`（使用经过光照补偿的图片）
4. 遍历检测框：计算归一化坐标、判断是否缺陷、检查位置偏移
5. 综合判定：无缺陷 + 位置正常 + 有检测到标签 = 合格
6. 返回 `InferenceOutput` 数据类

**to_backend_format(output, device_id, batch_id) 转换**：
- `device_id` / `batch_id` 支持外部传入，默认 `"cam_01"` / `"default_batch"`
- `energy_level` 从 OCR 提取，默认 1.0
- `defect_type` 逗号拼接缺陷类型
- `position_x`/`position_y` 优先取 class_id=0（正常标签）的框坐标，无正常标签时降级取最高置信度框
- `confidence` 取最高置信度检测框

### 5.2 OCR 服务 `ocr_service.py`

- 依赖 PaddleOCR（可选，未安装时静默降级）
- `recognize(image_path)` → `OCRResult` 数据类
- 提取信息：能效等级(1-5级)、能效标识(A++~C)、产品型号、年耗电量、容积、品牌
- 正则匹配模式识别
- 支持中文数字（一/二/三...）

### 5.3 训练流程

- `train_teacher.py` — 训练教师模型 (yolo11m)
- `train_student_dpfd.py` — DPFD 知识蒸馏训练学生模型 (yolo11n)
- `prepare_dataset.py` — 数据集准备（YOLO格式）
- `generate_synthetic_data.py` — 合成数据增强
- `merge_datasets.py` — 合并真实+合成数据集
- `evaluate_models.py` — 模型评估对比
- `export_model.py` — 模型导出（ONNX等）
- `train_all.sh` — 一键训练
- `run_pipeline.sh` — 完整流水线

### 5.4 模型权重路径

```
yolo-distiller/runs/
├── teacher/yolo11m_energy_label/weights/best.pt
└── student/
    ├── yolo11n_dpfd_energy_label/weights/best.pt  (优先)
    └── yolov8n_cwd_energy_label/weights/best.pt
```

---

## 六、数据流

### 6.1 ML 检测完整流程

```
用户上传图片 (Monitor.vue)
  → POST /api/ml/detect (FormData)
    → 保存文件到 static/uploads/
    → 读取配置: sensitivity→conf_threshold, lightCompensation→brightness_offset
    → EnergyLabelDetector.detect(image_path, brightness_offset)
      → 光照补偿预处理 (OpenCV, 写临时文件)
      → PaddleOCR 识别文字 (可选)
      → YOLO 推理检测标签 (使用补偿后图片)
      → 综合判定 (缺陷+位置+能效)
      → 清理临时文件
    → to_backend_format() 转换
    → 从配置读取 preset_model, 写入 ocr_text
    → crud.create_detection_record() 入库
    → WebSocket 广播结果
    → 返回 JSON 响应
  ← 前端更新 UI + Toast 通知
```

### 6.2 普通接口流程（无 ML）

```
POST /api/v1/detect/record (JSON body)
  → crud.create_detection_record()
    → judge_qualified() 判定
    → 写入 SQLite
  ← 返回 DetectionRecordOut
```

---

## 七、测试

### 7.1 运行测试

```bash
cd Service-Outsourcing/backend
pip install -r requirements.txt
python -m pytest tests/ -v
```

### 7.2 测试覆盖

| 文件 | 用例数 | 说明 |
|------|--------|------|
| `tests/test_utils.py` | 8 | 工具函数：判定逻辑、缺陷类型标准化、OCR 文本生成 |
| `tests/test_api.py` | 7 | API 端点：配置读写、ML 状态、历史、统计、CSV 导出、摘要导出 |

---

## 八、下一步计划

### 阶段〇：训练前审查（必须先完成）

训练前必须完成以下审查，防止训练过程中出现框架错误、loss 不收敛、训练中断等问题。

#### 0.1 环境准备

使用 conda 环境 `yolo_distiller_lmc`，所有操作在该环境中执行：

```bash
conda activate yolo_distiller_lmc
```

检查依赖是否齐全：

```bash
conda run -n yolo_distiller_lmc python -c "
import numpy, torch, cv2, yaml, matplotlib, pandas, tqdm, psutil
print(f'numpy={numpy.__version__}, torch={torch.__version__}, CUDA={torch.cuda.is_available()}')
if torch.cuda.is_available(): print(f'GPU: {torch.cuda.get_device_name(0)}')
print('All dependencies OK')
"
```

如有缺失，在 conda 环境中安装：

```bash
conda run -n yolo_distiller_lmc pip install numpy torch torchvision opencv-python-headless matplotlib pandas seaborn tqdm psutil py-cpuinfo pyyaml
```

#### 0.2 验证 ultralytics 导入

```bash
cd yolo-distiller
conda run -n yolo_distiller_lmc python -c "
import sys; sys.path.insert(0, '.')
from ultralytics import YOLO
print('ultralytics import OK')
"
```

#### 0.3 验证数据集路径解析

```bash
conda run -n yolo_distiller_lmc python -c "
import sys; sys.path.insert(0, '.')
from pathlib import Path
import yaml
from ultralytics.data.utils import check_det_dataset

yaml_path = 'datasets/energy_label_merged.yaml'
with open(yaml_path) as f:
    data = yaml.safe_load(f)
print(f'YAML: nc={data[\"nc\"]}, names={data[\"names\"]}')

resolved = check_det_dataset(yaml_path)
print(f'Resolved: train={resolved[\"train\"]}, val={resolved[\"val\"]}')
print('Dataset resolution OK')
"
```

#### 0.4 验证数据集完整性

```bash
# 检查图片和标签数量是否匹配
echo "Train images: $(ls datasets/energy_label_merged/images/train/ | wc -l)"
echo "Train labels: $(ls datasets/energy_label_merged/labels/train/ | wc -l)"
echo "Val images:   $(ls datasets/energy_label_merged/images/val/ | wc -l)"
echo "Val labels:   $(ls datasets/energy_label_merged/labels/val/ | wc -l)"
# 预期：train 1441, val 361，图片和标签数量一一对应

# 抽查标签格式（应为 YOLO 格式：class_id cx cy w h）
head -1 datasets/energy_label_merged/labels/train/$(ls datasets/energy_label_merged/labels/train/ | head -1)
```

#### 0.5 已修复的框架 Bug

审查中发现并已修复 `trainer.py` 中的蒸馏损失权重 bug：

- **问题**：`DistillationLoss` 的 `self.distiller` 存储原始字符串 `"dpfdLoss"`，但 `get_loss()` 中检查 `self.distiller not in ('cwd', 'dpfd')`，导致 DPFD 蒸馏损失被错误地乘以 0.3 衰减系数
- **修复**：`self.distiller = distiller[:3].lower()` 统一为 `'cwd'`/`'mgd'`/`'dpf'`，检查条件改为 `not in ('cwd', 'dpf')`
- **影响**：如果不修复，DPFD 蒸馏效果会大打折扣，学生模型精度下降

#### 0.6 Dry-Run 测试（1 epoch 快速验证）

用 1 个 epoch 跑通完整训练流程，验证不会报错：

```bash
cd yolo-distiller
conda run -n yolo_distiller_lmc python -c "
import sys; sys.path.insert(0, '.')
from ultralytics import YOLO

model = YOLO('yolo11m.pt')
model.train(
    data='datasets/energy_label_merged.yaml',
    epochs=1, batch=4, imgsz=640,
    project='runs/test_dryrun', name='teacher_test',
    exist_ok=True, device='cpu',
    workers=0, verbose=True
)
print('Teacher dry-run OK')
"
```

如果 dry-run 通过，删除测试输出：

```bash
rm -rf yolo-distiller/runs/test_dryrun
```

#### 0.7 审查检查清单

| 检查项 | 状态 | 说明 |
|--------|------|------|
| conda 环境依赖齐全 | ✅ | numpy=2.0.2, torch=2.8.0+cu128, opencv, pandas, tqdm, psutil 等已安装 |
| ultralytics 可导入 | ✅ | `from ultralytics import YOLO` 成功 |
| 数据集路径解析正确 | ✅ | 已修复 `datasets_dir` → `yolo-distiller/datasets/`，`check_det_dataset()` 无报错 |
| 数据集完整性 | ✅ | 1441 train + 361 val，标签匹配，YOLO 格式正确 |
| trainer.py 蒸馏 bug | ✅ | distiller 字符串已统一为 3 字符小写（`cwd`/`dpf`），逻辑正确 |
| Teacher dry-run 1 epoch | ✅ | 训练循环无报错，mAP50=0.707，2分钟完成 |
| GPU 可用性 | ✅ | NVIDIA GeForce RTX 4080 SUPER (32GB)，CUDA=True |

全部 ✅，可进入阶段一正式训练。

---

### 阶段一：模型训练

所有命令在 `conda activate yolo_distiller_lmc` 环境下执行，工作目录为 `yolo-distiller/`。

#### 1.1 训练教师模型

```bash
cd yolo-distiller
conda run -n yolo_distiller_lmc python scripts/train_teacher.py
```

**训练参数**（`train_teacher.py`）：

| 参数 | 值 | 说明 |
|------|------|------|
| 模型 | yolo11m.pt | 预训练权重，20.1M 参数，68.5 GFLOPs |
| epochs | 200 | 最大训练轮数 |
| batch | 16 | 批大小（RTX 4080 SUPER 32GB 足够） |
| imgsz | 640 | 输入图片尺寸 |
| patience | 40 | 早停耐心值（40 轮无提升则停止） |
| optimizer | AdamW | 优化器 |
| lr0 | 0.001 | 初始学习率 |
| lrf | 0.01 | 最终学习率系数（lr0 × lrf） |
| cos_lr | True | 余弦退火学习率调度 |
| warmup_epochs | 5 | 预热轮数 |
| save_period | 10 | 每 10 轮保存 checkpoint |
| device | 自动检测 | GPU 可用时用 GPU，否则 CPU |

**数据增强策略**：mosaic=1.0, mixup=0.15, copy_paste=0.1, degrees=10°, shear=2°, close_mosaic=15

**预期输出**：
- 权重：`runs/teacher/yolo11m_energy_label/weights/best.pt`
- 训练曲线：`runs/teacher/yolo11m_energy_label/results.png`
- 预计耗时：GPU 约 1-2 小时（RTX 4080 SUPER），CPU 约 24+ 小时
- 训练中断可通过 `resume=True` 恢复

**实际训练结果**：
- mAP@50 = 0.994, mAP@50-95 = 0.989
- 训练耗时约 1.5 小时（RTX 4080 SUPER）
- 模型大小 38.6MB, 参数量 20.1M, FPS=150（GPU）

**验收标准**：mAP@50 > 0.85 ✅ 远超预期

#### 1.2 知识蒸馏训练学生模型

```bash
conda run -n yolo_distiller_lmc python scripts/train_student_dpfd.py
```

**前置条件**：教师模型 `runs/teacher/yolo11m_energy_label/weights/best.pt` 必须存在

**训练参数**（`train_student_dpfd.py`）：

| 参数 | 值 | 说明 |
|------|------|------|
| 学生模型 | yolo11n.pt | 轻量模型，2.6M 参数，6.6 GFLOPs |
| 教师模型 | Teacher best.pt | 步骤 1.1 的输出 |
| epochs | 250 | 蒸馏需要更多轮数 |
| batch | 32 | 学生模型更小，可用更大 batch |
| patience | 50 | 蒸馏训练波动较大，耐心值更高 |
| lr0 | 0.002 | 学生模型学习率略高 |
| distillation_loss | dpfdLoss | DPFD 蒸馏方法（双路径特征蒸馏） |
| close_mosaic | 20 | 蒸馏后期关闭 mosaic 的时机 |

**DPFD 蒸馏原理**：
- 双路径融合：CWD（通道级语义分布，擅长"看什么"）+ MGD（空间级掩码生成，擅长"在哪看"）
- 自适应门控网络动态平衡两条路径权重
- 压缩比：7.7x 参数压缩，10.4x 计算量加速

**实际训练结果**：
- mAP@50 = 0.992, mAP@50-95 = 0.986（与 Teacher 仅差 0.2%）
- 训练 250 epochs，耗时约 16 小时（workers=0，Docker shm 4GB 限制）
- 模型大小 5.3MB（压缩 86%），参数量 2.6M（压缩 7.7x），FPS=166（GPU）
- 各类别 AP@50：normal=0.994, offset=0.995, scratch=0.995, stain=0.983, wrinkle=0.995
- 导出格式：ONNX (10.1MB), TorchScript (10.4MB)

**训练中修复的 Bug**：
1. `initial_lr` KeyError：蒸馏模块的 param group 在 LambdaLR 调度器创建后添加，缺少 `initial_lr` 字段
2. `ConnectionResetError`：Docker 容器 shm 仅 4GB，多 worker dataloader 通信崩溃，设置 workers=0 解决

**预期输出**：
- 权重：`runs/student/yolo11n_dpfd_energy_label/weights/best.pt` ✅
- 目标：mAP@50 接近教师模型（差距 < 3%）✅ 实际差距仅 0.2%

#### 1.3 评估模型效果

```bash
conda run -n yolo_distiller_lmc python scripts/evaluate_models.py --device 0
```

**评估内容**：
- 自动查找所有已训练模型（Teacher / Student CWD / Student DPFD）
- 默认使用 `datasets/energy_label_merged.yaml` 验证集
- 输出对比表格：mAP@50、mAP@50-95、FPS、模型大小、参数量
- 各类别 AP@50 详细对比
- Teacher vs Student 压缩比和精度差距分析

**注意**：建议加 `--device 0` 使用 GPU 测速，否则默认 CPU 速度不具参考性

#### 1.4 导出模型（可选）

```bash
conda run -n yolo_distiller_lmc python scripts/export_model.py
```

**导出格式**：
- ONNX（opset=12, simplified）— 通用部署格式，支持 OpenCV DNN / ONNX Runtime / OpenHarmony NNRT
- TorchScript — PyTorch 原生部署

**模型选择优先级**：DPFD Student > CWD Student > Teacher

#### 1.5 一键训练（可选）

如果希望一次性完成 Teacher + Student 训练：

```bash
cd yolo-distiller
nohup bash scripts/train_all.sh &
tail -f train_all.log
```

`train_all.sh` 会依次执行 `train_teacher.py` → `train_student_dpfd.py`，日志写入 `train_all.log`。使用 `nohup` 可防止 SSH 断开导致训练中断。

训练完成后模型权重保存在 `yolo-distiller/runs/` 下，后端 `ml_detection.py` 会按优先级自动检测并加载。

---

### 阶段一完成总结

| 指标 | Teacher (YOLO11m) | Student DPFD (YOLO11n) | 压缩效果 |
|------|-------------------|------------------------|----------|
| mAP@50 | 0.994 | 0.992 | -0.2% |
| mAP@50-95 | 0.989 | 0.986 | -0.3% |
| FPS (GPU) | 150 | 166 | 1.1x |
| 模型大小 | 38.6 MB | 5.3 MB | 86% 缩减 |
| 参数量 | 20.1M | 2.6M | 7.7x 压缩 |
| ONNX 大小 | - | 10.1 MB | 适合部署 |

结论：DPFD 蒸馏效果极好，精度几乎无损，模型体积大幅压缩，完全满足边缘端部署需求。

---

### 阶段二：端到端验证

模型训练完成后，进行完整功能验证。

#### 2.1 启动后端

```bash
cd Service-Outsourcing/backend
pip install -r requirements.txt
pip install -r requirements-ml.txt  # ML 依赖（YOLO + PaddleOCR）
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**验证后端启动成功**：
- 访问 `http://localhost:8000/docs` 查看 Swagger API 文档
- 调用 `GET /api/ml/status` 确认模型已加载（返回 `model_loaded: true`）
- 如果模型未加载，检查 `runs/` 目录下是否有 `best.pt` 文件

#### 2.2 启动前端开发服务器

```bash
cd Service-Outsourcing/frontend/web
npm install
npm run dev
```

访问 `http://localhost:5173`

#### 2.3 前端页面手动验证指南（操作参考）

以下为浏览器中手动验证前端 UI 的操作指南。API 层面已通过 curl 和单元测试验证通过，前端 UI 交互需在浏览器中确认。

| 页面 | 验证项 | 预期结果 | API 验证 | UI 验证 |
|------|--------|----------|----------|---------|
| Monitor | 上传能效标签图片 → 点击"开始检测" | 返回检测结果：状态(OK/NG)、OCR文本、缺陷类型、位置状态、置信度 | ✅ curl 测试通过 | 待手动确认 |
| Monitor | WebSocket 实时推送 | 检测完成后，页面自动更新最近记录表格 | ✅ 广播逻辑已实现 | 待手动确认 |
| Monitor | ML 服务状态指示器 | 显示绿色"在线"状态 | ✅ /api/ml/status 返回 available:true | 待手动确认 |
| History | 日期筛选 + 状态筛选 | 正确过滤记录，分页正常 | ✅ /api/history 返回正确 | 待手动确认 |
| History | CSV 导出 | 下载的 CSV 文件包含所有记录，Excel 打开中文不乱码 | ✅ /api/export/csv 可用 | 待手动确认 |
| Statistic | 检测趋势图 | 柱状图显示最近 7 天数据 | ✅ /api/statistic 返回正确 | 待手动确认 |
| Statistic | 缺陷分布 + 位置分布 | 水平条形图正确展示各类型数量 | ✅ 同上 | 待手动确认 |
| Statistic | 型号合格率 | 进度条显示各型号合格百分比 | ✅ 同上 | 待手动确认 |
| Setup | 修改灵敏度 → 重新检测 | 灵敏度调高后，更多缺陷被检出 | ✅ /api/config + /api/ml/reload 可用 | 待手动确认 |
| Setup | 修改光照补偿 → 重新检测 | 暗图补偿后检测效果改善 | ✅ lightCompensation 参数已实现 | 待手动确认 |
| Setup | 添加/删除预设型号 | 配置保存成功，检测结果中型号正确 | ✅ /api/config POST 测试通过 | 待手动确认 |

> 启动后端 `uvicorn main:app --port 8000`，访问 `http://localhost:8000` 即可在浏览器中逐项验证。

#### 2.4 API 接口验证

```bash
# ML 检测
curl -X POST http://localhost:8000/api/ml/detect -F "file=@test_image.jpg"

# 最新结果
curl http://localhost:8000/api/current

# 历史记录
curl "http://localhost:8000/api/history?page=1&pageSize=10"

# 统计数据
curl "http://localhost:8000/api/statistic?startDate=2026-01-01&endDate=2026-12-31"

# 配置读写
curl http://localhost:8000/api/config
curl -X POST http://localhost:8000/api/config -H "Content-Type: application/json" -d '{"sensitivity":"高"}'

# CSV 导出
curl -o export.csv http://localhost:8000/api/export/csv

# 摘要导出
curl http://localhost:8000/api/export/summary
```

#### 2.5 后端单元测试

```bash
cd Service-Outsourcing/backend
python -m pytest tests/ -v
```

预期：15 个测试全部通过（8 个 test_utils + 7 个 test_api）

---

### 阶段二完成总结

#### 修复的问题

1. **ml_detection.py 模型路径错误**：`Path(__file__).resolve().parent` 层数不够，从 `backend/app/routers/` 到 `LMC/` 需要 5 层 parent（routers → app → backend → Service-Outsourcing → LMC），原代码只有 4 层，导致路径解析到 `Service-Outsourcing/yolo-distiller`（不存在）。已修复。

2. **端口占用**：Docker 容器中无 `lsof` 命令，改用 `ps aux | grep uvicorn` + `kill` 管理进程。

#### 验证结果

| # | 任务 | 状态 | 实际结果 |
|---|------|------|----------|
| 1 | 后端启动 + 模型自动加载 | ✅ | Student DPFD 模型加载成功，OCR (PaddleOCR) 可用 |
| 2 | `/api/ml/status` | ✅ | `available: true, conf_threshold: 0.25, ocr_available: true` |
| 3 | `/api/ml/detect` 缺陷图 | ✅ | 褶皱图 → NG，defect_type="褶皱"，confidence=0.9615，position_status="偏移" |
| 4 | `/api/ml/detect` 正常图 | ✅ | 正常图 → OK，defect_type="无"，confidence=0.8706，position_status="正常" |
| 5 | OCR 识别 | ✅ | 两张图均识别出 "1级能效"，ocr_available=true |
| 6 | `/api/history` | ✅ | total=2, records=2，分页正常 |
| 7 | `/api/statistic` | ✅ | 返回 2 条统计记录 |
| 8 | `/api/config` | ✅ | sensitivity=中, models=1 |
| 9 | `/api/current` | ✅ | status=OK, defect=无（最新一条记录） |
| 10 | 单元测试 | ✅ | 15/15 通过（8 test_utils + 7 test_api），耗时 2.3s |
| 11 | 前端构建 | ✅ | `npm run build` 成功，产物 134KB JS + 43KB CSS |
| 12 | 单端口部署 | ✅ | `http://localhost:8000/` 返回前端 HTML，API 同端口可用 |

#### 推理性能（CPU 模式）

| 指标 | 首次推理 | 后续推理 |
|------|----------|----------|
| 推理耗时 | 8173ms（含模型加载） | 84ms |
| 模型 | Student DPFD (YOLO11n) | - |
| 设备 | CPU (AMD EPYC 9V74) | - |

注：首次推理包含模型加载时间，后续推理仅 84ms，满足实时检测需求。GPU 模式下会更快。

---

### 阶段三：移动端完善

#### 3.0 当前代码状态分析

**uni-app 小程序端（`frontend/front/`）**：
- 5 个页面已搭建：index（监控）、history（历史）、statistic（统计）、setup（设置）、home（首页）
- TabBar 已配置 4 个入口（监控/历史/统计/设置）
- index.vue 已有 `uni.request` 调用 `/api/current` 和 `/api/recent`，但 URL 是相对路径，缺少 baseURL 配置
- history.vue 已对接 `/api/history`，支持状态筛选和分页加载
- statistic.vue 和 setup.vue 需要检查是否已对接
- 问题：`uni.request` 的 URL 没有 baseURL 前缀，在真机/模拟器上无法访问后端

**鸿蒙端（`frontend/front-homo/`）**：
- 单页面应用，只有 `Index.ets`（401 行）
- 已实现：顶部标题栏 + ML 状态指示 + 检测结果展示（标签识别/缺陷检测/位置检测）+ 最近记录表格
- 已有 HTTP API 调用：`/api/ml/status`、`/api/current`、`/api/recent`
- baseUrl 已配置为 `http://192.168.1.100:8000`（需改为实际地址）
- 缺失：图片上传检测功能、历史记录页面、统计页面、设置页面、TabBar 导航、WebSocket

#### 3.1 uni-app 小程序端（`frontend/front/`）

##### 3.1.1 创建 API 封装层（P0，预计 0.5h）

创建 `utils/api.js`：
- 可配置 `BASE_URL`（开发环境 `http://localhost:8000`，生产环境从配置读取）
- 封装 `request(url, options)` 函数，自动拼接 baseURL
- 统一错误处理（网络错误 toast 提示）
- 封装 `uploadFile(url, filePath)` 函数（用于图片上传检测）

##### 3.1.2 改造 index.vue 监控页（P0，预计 1h）

当前问题：
- `uni.request` URL 缺少 baseURL
- 没有图片上传检测功能（只展示结果，不能主动检测）

改造内容：
- 引入 API 封装层，替换硬编码 URL
- 添加图片上传区域（`uni.chooseImage` 选择图片 / `uni.chooseMedia` 拍照）
- 添加"开始检测"按钮，调用 `/api/ml/detect` 上传图片
- 添加 ML 服务状态指示器
- 添加检测中 loading 状态

##### 3.1.3 改造 history.vue 历史页（P1，预计 0.5h）

当前状态：已基本完成，有状态筛选和分页。

改造内容：
- 引入 API 封装层，替换硬编码 URL
- 添加日期范围筛选（`uni-datetime-picker` 或原生 picker）
- 添加 CSV 导出按钮（调用 `/api/export/csv`，`uni.downloadFile` 保存）

##### 3.1.4 改造 statistic.vue 统计页（P1，预计 1.5h）

改造内容：
- 引入 API 封装层
- 对接 `/api/statistic?startDate=...&endDate=...`
- 实现检测趋势展示（最近 7 天，用 uni-app 兼容的图表方案：`ucharts` 或纯 CSS 条形图）
- 实现缺陷类型分布展示
- 实现型号合格率展示

##### 3.1.5 改造 setup.vue 设置页（P2，预计 1h）

改造内容：
- 引入 API 封装层
- 对接 GET/POST `/api/config`
- 实现灵敏度选择（低/中/高）
- 实现位置容忍度滑块
- 实现光照补偿滑块
- 实现预设型号管理（添加/删除）
- 保存后调用 `/api/ml/reload`

##### 3.1.6 H5 适配验证（P2，预计 0.5h）

- `npm run dev:h5` 启动 H5 开发服务器
- 验证所有页面在浏览器中正常工作
- 检查 API 代理配置（vite.config.js 中添加 proxy）

#### 3.2 鸿蒙端（`frontend/front-homo/`）— 比赛核心要求

##### 3.2.1 多页面框架搭建（P0，预计 1h）

当前只有单页面 `Index.ets`，需要拆分为多页面 + TabBar 导航。

页面规划：
- `pages/Monitor.ets` — 实时监控（从 Index.ets 拆出，增加图片上传）
- `pages/History.ets` — 历史记录
- `pages/Statistics.ets` — 统计报表
- `pages/Settings.ets` — 系统设置

实现方式：
- 使用 `Tabs` + `TabContent` 组件实现底部 TabBar
- 将现有 Index.ets 的内容迁移到 Monitor.ets
- 更新 `main_pages.json` 注册新页面

##### 3.2.2 API 封装层（P0，预计 0.5h）

创建 `common/ApiService.ets`：
- 封装 `@ohos.net.http` 请求
- 可配置 baseUrl
- 统一错误处理
- 封装 GET/POST/上传文件方法
- 使用 Promise 替代回调（当前代码用回调风格，不够优雅）

##### 3.2.3 Monitor 页面增强（P0，预计 1.5h）

在现有 Index.ets 基础上增加：
- 图片选择功能（`@ohos.file.picker` 的 `PhotoViewPicker`）
- 图片上传检测（`@ohos.net.http` 的 multipart/form-data 上传）
- 检测中 loading 动画
- 检测结果动画过渡
- 图片预览（显示上传的图片）

##### 3.2.4 History 页面（P1，预计 1.5h）

- 调用 `/api/history?page=1&pageSize=20&statusFilter=ALL`
- 状态筛选（全部/合格/不合格）
- 卡片式记录展示（时间、型号、状态、缺陷、位置）
- 下拉刷新 + 上拉加载更多
- 空状态提示

##### 3.2.5 Statistics 页面（P2，预计 2h）

- 调用 `/api/statistic?startDate=...&endDate=...`
- 检测趋势展示（最近 7 天，用 ArkTS Canvas 或 Stack+Column 模拟柱状图）
- 缺陷类型分布（水平条形图）
- 型号合格率（进度条）
- 日期范围选择

##### 3.2.6 Settings 页面（P1，预计 1h）

- 对接 GET/POST `/api/config`
- 灵敏度选择（Slider 或 Radio）
- 位置容忍度（Slider）
- 光照补偿（Slider）
- 预设型号管理
- 后端地址配置（允许用户修改 baseUrl）
- 保存后调用 `/api/ml/reload`

##### 3.2.7 WebSocket 实时推送（P1，预计 1h）

- 使用 `@ohos.net.webSocket` 连接 `ws://host:8000/ws/detection`
- 接收检测结果实时更新 Monitor 页面
- 心跳保活（定时发送 ping）
- 断线重连机制

##### 3.2.8 UI 打磨（P1，预计 1h）

- 统一暗色主题配色（与 Web 端一致）
- 适配不同屏幕尺寸
- 添加页面过渡动画
- 错误状态和空状态的友好提示
- 加载骨架屏

#### 3.3 执行顺序建议

按优先级和依赖关系排序：

```
第一批（P0 核心功能，预计 4h）：
  1. uni-app: 创建 API 封装层 (3.1.1)
  2. uni-app: 改造 index.vue 添加图片上传检测 (3.1.2)
  3. 鸿蒙: API 封装层 (3.2.2)
  4. 鸿蒙: 多页面框架搭建 (3.2.1)
  5. 鸿蒙: Monitor 页面增强（图片上传检测）(3.2.3)

第二批（P1 完善功能，预计 5h）：
  6. uni-app: 改造 history.vue (3.1.3)
  7. 鸿蒙: History 页面 (3.2.4)
  8. 鸿蒙: Settings 页面 (3.2.6)
  9. 鸿蒙: WebSocket 实时推送 (3.2.7)
  10. 鸿蒙: UI 打磨 (3.2.8)

第三批（P2 锦上添花，预计 5h）：
  11. uni-app: 改造 statistic.vue (3.1.4)
  12. uni-app: 改造 setup.vue (3.1.5)
  13. uni-app: H5 适配验证 (3.1.6)
  14. 鸿蒙: Statistics 页面 (3.2.5)
```

总预计工时：约 14h

---

### 阶段四：部署与集成

#### 4.1 已完成

- ✅ Web 前端生产包构建（134KB JS + 43KB CSS）
- ✅ 单端口部署验证（后端托管前端静态文件，localhost:8000）

#### 4.2 Docker 化部署（P1，预计 2h）

创建 `Service-Outsourcing/Dockerfile`：
- 基础镜像：`python:3.9-slim`
- 安装后端依赖 + ML 依赖
- 复制前端构建产物到 `backend/` 可访问路径
- 复制模型权重（或通过 volume 挂载）
- 暴露端口 8000
- 启动命令：`uvicorn main:app --host 0.0.0.0 --port 8000`

创建 `docker-compose.yml`：
- 服务：`backend`（FastAPI + ML）
- Volume：模型权重、SQLite 数据库、上传图片
- 环境变量：`DATABASE_URL`、`CORS_ORIGINS`
- 端口映射：`8000:8000`

#### 4.3 清理训练中间文件（P1，预计 0.5h）

```bash
# 删除中间 checkpoint（保留 best.pt 和 last.pt）
find yolo-distiller/runs/ -name "epoch*.pt" -delete
# 预计释放约 2.8GB 空间
```

#### 4.4 生产环境配置（P2，预计 0.5h）

创建 `Service-Outsourcing/backend/.env`：
- `DATABASE_URL=sqlite:///./detection.db`
- `CORS_ORIGINS=http://your-domain.com`
- `LOG_LEVEL=info`

#### 4.5 Nginx 反向代理（P2，预计 1h，仅公网部署需要）

- Nginx 配置：代理 `/` → `localhost:8000`
- WebSocket 代理：`/ws/` → `ws://localhost:8000`
- HTTPS：Let's Encrypt 证书
- 静态文件缓存策略

| # | 任务 | 优先级 | 状态 | 预计工时 |
|---|------|--------|------|----------|
| 1 | 构建 Web 前端生产包 | P0 | ✅ | - |
| 2 | 单端口部署验证 | P0 | ✅ | - |
| 3 | Dockerfile + docker-compose | P1 | ⬜ | 2h |
| 4 | 清理训练中间文件 | P1 | ⬜ | 0.5h |
| 5 | 生产环境 .env 配置 | P2 | ⬜ | 0.5h |
| 6 | Nginx + HTTPS | P2 | ⬜ | 1h |

---

### 阶段五：比赛材料准备

#### 5.1 系统架构图（P0，预计 1h）

使用 draw.io 或 Mermaid 绘制：
- 整体架构：用户端（Web/小程序/鸿蒙）→ FastAPI 后端 → ML 引擎（YOLO + OCR）→ SQLite
- ML 训练流程：数据准备 → Teacher 训练 → DPFD 蒸馏 → 模型导出
- 知识蒸馏架构：Teacher(YOLO11m) → DPFD(CWD+MGD+Gate) → Student(YOLO11n)
- 数据流图：图片上传 → 光照补偿 → YOLO 推理 → OCR 识别 → 综合判定 → 入库 → WebSocket 广播

#### 5.2 知识蒸馏技术方案文档（P0，预计 2h）

内容大纲：
1. 问题背景：边缘端部署需要轻量模型，但直接训练小模型精度不够
2. 技术方案：DPFD（Dual-Path Feature Distillation）
   - CWD 路径：通道级语义分布对齐，擅长"看什么"
   - MGD 路径：空间级掩码生成蒸馏，擅长"在哪看"
   - 自适应门控网络：动态平衡两条路径权重
3. 实验结果：Teacher vs Student 对比表（已有数据）
4. 创新点总结：双路径融合、自适应门控、精度几乎无损（0.3%差距）
5. 部署方案：ONNX 导出 → OpenHarmony NNRT / ONNX Runtime

#### 5.3 性能指标数据表（P0，✅ 已完成）

`evaluate_models.py` 输出的对比表格已在 DEV_DOC.md 阶段一完成总结中记录。

#### 5.4 系统演示视频（P0，预计 2h）

录屏内容：
1. 后端启动 + 模型自动加载（终端）
2. Web 端完整检测流程：上传图片 → 检测结果 → 历史记录 → 统计报表 → 配置修改
3. 鸿蒙端演示（模拟器或真机）
4. 知识蒸馏效果对比：Teacher vs Student 精度/速度/体积
5. 多端协同：Web 检测 → 鸿蒙端实时接收结果

#### 5.5 答辩 PPT（P0，预计 3h）

PPT 大纲（约 15-20 页）：
1. 封面（项目名称、团队、赛题编号）
2. 项目背景（能效标签检测痛点）
3. 系统架构总览
4. 技术亮点一：DPFD 知识蒸馏（压缩 86%，精度差 0.3%）
5. 技术亮点二：多端协同（Web + 小程序 + OpenHarmony）
6. 技术亮点三：端到端自动化（图片→推理→OCR→判定→入库→推送）
7. 系统演示截图（各页面）
8. 性能指标对比表
9. 创新点总结
10. 未来展望

#### 5.6 项目 README（P1，预计 1h）

内容：
- 项目简介 + 技术栈
- 快速开始（3 步启动）
- 系统截图（Web 端 5 个页面）
- 模型性能指标
- 项目结构说明
- API 文档链接（Swagger）
- 许可证

| # | 任务 | 优先级 | 状态 | 预计工时 |
|---|------|--------|------|----------|
| 1 | 系统架构图 | P0 | ⬜ | 1h |
| 2 | 知识蒸馏技术方案文档 | P0 | ⬜ | 2h |
| 3 | 性能指标数据表 | P0 | ✅ | - |
| 4 | 系统演示视频 | P0 | ⬜ | 2h |
| 5 | 答辩 PPT | P0 | ⬜ | 3h |
| 6 | 项目 README | P1 | ⬜ | 1h |

---

### 整体进度总览

| 阶段 | 状态 | 完成度 | 剩余工时 |
|------|------|--------|----------|
| 阶段〇：训练前审查 | ✅ 完成 | 100% | 0h |
| 阶段一：模型训练 | ✅ 完成 | 100% | 0h |
| 阶段二：端到端验证 | ✅ 完成 | 100% | 0h |
| 阶段三：移动端完善 | ⬜ 待开始 | 0% | ~14h |
| 阶段四：部署与集成 | 🔄 进行中 | 30% | ~4h |
| 阶段五：比赛材料 | 🔄 进行中 | 15% | ~9h |

**总剩余工时估算：约 27h**

**建议执行顺序**：

```
Week 1（核心功能，~10h）：
  ├─ 阶段三 第一批 P0：uni-app API层 + 图片上传 + 鸿蒙多页面框架 + Monitor增强 (4h)
  ├─ 阶段三 第二批 P1：History + Settings + WebSocket + UI打磨 (5h)
  └─ 阶段五 5.1：系统架构图 (1h)

Week 2（完善+材料，~10h）：
  ├─ 阶段三 第三批 P2：Statistic + Setup + H5适配 (5h)
  ├─ 阶段五 5.2：知识蒸馏技术文档 (2h)
  └─ 阶段五 5.5：答辩PPT (3h)

Week 3（部署+收尾，~7h）：
  ├─ 阶段四 4.2-4.5：Docker + 清理 + 配置 (4h)
  ├─ 阶段五 5.4：演示视频 (2h)
  └─ 阶段五 5.6：README (1h)
```

**已完成的关键里程碑**：
- 模型训练：Teacher mAP50-95=0.989, Student DPFD mAP50-95=0.986（压缩86%，精度差0.3%）
- 端到端验证：后端+前端+ML推理+OCR 全链路打通
- 单端口部署：localhost:8000 同时托管前端和 API

---

## 九、启动方式

### 后端

```bash
cd Service-Outsourcing/backend
pip install -r requirements.txt
# 如需 ML 检测功能（YOLO + OCR），额外安装：
pip install -r requirements-ml.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 前端（开发）

```bash
cd Service-Outsourcing/frontend/web
npm install
npm run dev
# 访问 http://localhost:5173
```

### 前端（构建）

```bash
cd Service-Outsourcing/frontend/web
npm run build
# 产物在 dist/，后端会自动托管
```

### ML 训练

```bash
cd yolo-distiller
bash scripts/train_all.sh
```

### ML 推理测试

```bash
cd yolo-distiller
python scripts/inference_service.py --image path/to/image.jpg
```
