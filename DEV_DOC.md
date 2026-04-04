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

## 八、已完成里程碑

| 指标 | Teacher (YOLO11m) | Student DPFD (YOLO11n) | 压缩效果 |
|------|-------------------|------------------------|----------|
| mAP@50 | 0.994 | 0.992 | -0.2% |
| mAP@50-95 | 0.989 | 0.986 | -0.3% |
| FPS (GPU) | 150 | 166 | 1.1x |
| 模型大小 | 38.6 MB | 5.3 MB | 86% 缩减 |
| 参数量 | 20.1M | 2.6M | 7.7x 压缩 |
| ONNX 大小 | - | 10.1 MB | 适合部署 |

| 阶段 | 状态 | 关键成果 |
|------|------|----------|
| 阶段〇 训练前审查 | ✅ | 环境验证、数据集校验、trainer.py 蒸馏 bug 修复 |
| 阶段一 模型训练 | ✅ | Teacher mAP50=0.994, Student DPFD mAP50=0.992, ONNX 导出 |
| 阶段二 端到端验证 | ✅ | 后端+Web+ML+OCR 全链路打通, 15/15 测试通过, 单端口部署 |
| 阶段三 移动端完善 | ✅ | uni-app 5页面 + 鸿蒙4页面 + WebSocket + 图片上传 |
| 阶段四 部署（部分） | ✅ | Dockerfile + docker-compose + .env.example + .dockerignore |

---

## 九、待完成计划

### 9.1 技术任务

| # | 任务 | 优先级 | 状态 |
|---|------|--------|------|
| 1 | uni-app H5 适配验证 | P1 | 待验证（需 HBuilderX 或 uni-app CLI） |
| 2 | 清理训练中间文件 | P1 | ✅ 已完成（epoch*.pt 无残留，last.pt 已删除） |
| 3 | Nginx + HTTPS（可选，仅公网部署） | P2 | 可选 |

### 文书任务

| # | 任务 | 优先级 | 状态 |
|---|------|--------|------|
| 1 | 系统架构图（draw.io/Mermaid） | P0 | 待完成 |
| 2 | 知识蒸馏技术方案文档 | P0 | 待完成 |
| 3 | 系统演示视频 | P0 | 待完成 |
| 4 | 答辩 PPT（15-20页） | P0 | 待完成 |
| 5 | 项目 README | P1 | ✅ 已完成（根目录 DEPLOY_GUIDE.md + DEV_DOC.md） |

---

## 十、启动方式

### 后端

```bash
cd Service-Outsourcing/backend
pip install -r requirements.txt
pip install -r requirements-ml.txt  # ML 依赖（可选）
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
