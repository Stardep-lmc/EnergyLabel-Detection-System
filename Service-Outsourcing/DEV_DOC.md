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

#### 2.3 逐页面功能验证

| 页面 | 验证项 | 预期结果 |
|------|--------|----------|
| Monitor | 上传能效标签图片 → 点击"开始检测" | 返回检测结果：状态(OK/NG)、OCR文本、缺陷类型、位置状态、置信度 |
| Monitor | WebSocket 实时推送 | 检测完成后，页面自动更新最近记录表格 |
| Monitor | ML 服务状态指示器 | 显示绿色"在线"状态 |
| History | 日期筛选 + 状态筛选 | 正确过滤记录，分页正常 |
| History | CSV 导出 | 下载的 CSV 文件包含所有记录，Excel 打开中文不乱码 |
| Statistic | 检测趋势图 | 柱状图显示最近 7 天数据 |
| Statistic | 缺陷分布 + 位置分布 | 水平条形图正确展示各类型数量 |
| Statistic | 型号合格率 | 进度条显示各型号合格百分比 |
| Setup | 修改灵敏度 → 重新检测 | 灵敏度调高后，更多缺陷被检出 |
| Setup | 修改光照补偿 → 重新检测 | 暗图补偿后检测效果改善 |
| Setup | 添加/删除预设型号 | 配置保存成功，检测结果中型号正确 |

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

### 阶段二待办清单

阶段二是当前最紧迫的工作，需要将训练好的模型接入后端并验证完整链路。

| # | 任务 | 优先级 | 状态 | 说明 |
|---|------|--------|------|------|
| 1 | 将 Student 模型权重复制/软链到后端可访问路径 | P0 | ⬜ | `ml_detection.py` 按优先级查找 `yolo-distiller/runs/` 下的权重 |
| 2 | 启动后端，验证 `/api/ml/status` 返回 `model_loaded: true` | P0 | ⬜ | 确认模型自动加载成功 |
| 3 | 用真实能效标签图片测试 `/api/ml/detect` | P0 | ⬜ | 验证推理结果正确（缺陷类型、置信度、位置） |
| 4 | 验证 OCR 功能（PaddleOCR 是否正常工作） | P1 | ⬜ | 如 PaddleOCR 未安装，确认降级逻辑正常 |
| 5 | 启动 Web 前端，Monitor 页面完整检测流程 | P0 | ⬜ | 上传→检测→结果展示→WebSocket 推送 |
| 6 | 验证 History / Statistic / Setup 页面 | P1 | ⬜ | 数据展示、筛选、导出、配置保存 |
| 7 | 运行后端单元测试 `pytest tests/ -v` | P1 | ⬜ | 15 个测试全部通过 |
| 8 | 构建 Web 前端生产包 `npm run build` | P1 | ⬜ | 验证单端口部署（后端托管前端静态文件） |

---

### 阶段三：移动端完善

#### 3.1 uni-app 小程序端（`frontend/front/`）

当前状态：基础页面框架已搭建（首页、历史、统计），但未对接后端 API。

| # | 任务 | 优先级 | 状态 |
|---|------|--------|------|
| 1 | 封装 API 请求层（baseURL 配置、错误处理） | P0 | ⬜ |
| 2 | 对接 `/api/ml/detect` 实现图片上传检测 | P0 | ⬜ |
| 3 | 对接 `/api/history` 展示历史记录 | P1 | ⬜ |
| 4 | 对接 `/api/statistic` 展示统计数据 | P1 | ⬜ |
| 5 | 对接 `/api/config` 实现配置管理 | P2 | ⬜ |
| 6 | 适配微信小程序运行环境 | P1 | ⬜ |
| 7 | 适配 H5 运行环境 | P2 | ⬜ |

#### 3.2 鸿蒙端（`frontend/front-homo/`）— 比赛核心要求

当前状态：空壳 OpenHarmony ArkTS 项目。这是诚迈科技命题的核心要求，必须完成。

| # | 任务 | 优先级 | 状态 |
|---|------|--------|------|
| 1 | 搭建 ArkTS 页面框架（TabBar + 路由） | P0 | ⬜ |
| 2 | 实现检测功能页面（图片选择/拍照 + 上传 + 结果展示） | P0 | ⬜ |
| 3 | 实现历史记录页面（列表 + 详情） | P1 | ⬜ |
| 4 | 实现统计页面（图表展示） | P2 | ⬜ |
| 5 | 对接后端 HTTP API | P0 | ⬜ |
| 6 | 对接 WebSocket 实时推送 | P1 | ⬜ |
| 7 | OpenHarmony NNRT 本地推理适配（用 ONNX 模型） | P2 | ⬜ |
| 8 | UI 适配 OpenHarmony 设计规范 | P1 | ⬜ |

---

### 阶段四：部署与集成

| # | 任务 | 优先级 | 状态 |
|---|------|--------|------|
| 1 | 构建 Web 前端生产包 | P0 | ⬜ |
| 2 | 单端口部署验证（后端托管前端） | P0 | ⬜ |
| 3 | Docker 化部署（Dockerfile + docker-compose） | P1 | ⬜ |
| 4 | 清理训练中间文件（epoch*.pt 占 2.8GB） | P1 | ⬜ |
| 5 | 配置 `.env` 生产环境变量 | P2 | ⬜ |
| 6 | Nginx 反向代理 + HTTPS（如需公网部署） | P2 | ⬜ |

---

### 阶段五：比赛材料准备

| # | 任务 | 优先级 | 状态 |
|---|------|--------|------|
| 1 | 系统架构图（前后端 + ML 引擎 + 多端） | P0 | ⬜ |
| 2 | 知识蒸馏技术方案文档（DPFD 创新点、压缩比、精度保持） | P0 | ⬜ |
| 3 | 性能指标数据表（evaluate_models.py 输出已有） | P0 | ✅ |
| 4 | 系统演示视频（完整检测流程录屏） | P0 | ⬜ |
| 5 | 答辩 PPT | P0 | ⬜ |
| 6 | 项目 README 完善（安装、运行、演示截图） | P1 | ⬜ |

---

### 整体进度总览

| 阶段 | 状态 | 完成度 |
|------|------|--------|
| 阶段〇：训练前审查 | ✅ 完成 | 100% |
| 阶段一：模型训练 | ✅ 完成 | 100% |
| 阶段二：端到端验证 | ⬜ 待开始 | 0% |
| 阶段三：移动端完善 | ⬜ 待开始 | 0% |
| 阶段四：部署与集成 | ⬜ 待开始 | 0% |
| 阶段五：比赛材料 | 🔄 进行中 | 20% |

**当前建议优先级**：阶段二（端到端验证）→ 阶段三（鸿蒙端，比赛核心）→ 阶段四（部署）→ 阶段五（材料）

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
