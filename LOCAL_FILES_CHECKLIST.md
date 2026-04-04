# 本地需要保存的文件清单

> 以下文件被 `.gitignore` 排除，不会随 `git clone` 获取。
> 换机器 / 重新克隆后需要手动恢复这些文件，否则项目无法正常运行。
>
> 按**重要程度**排序，标注了文件大小和存放路径。

---

## 一、模型权重（必须保存，核心资产）

| 文件 | 存放路径 | 大小 | 说明 |
|------|----------|------|------|
| Student DPFD 模型（推理用） | `yolo-distiller/runs/student/yolo11n_dpfd_energy_label/weights/best.pt` | 5.3 MB | **最重要**，后端推理依赖此文件，没有它 `/api/ml/detect` 返回 503 |
| Student DPFD ONNX | `yolo-distiller/runs/student/yolo11n_dpfd_energy_label/weights/best.onnx` | 11 MB | 导出的 ONNX 格式，用于边缘部署 |
| Student TorchScript | `yolo-distiller/runs/student/yolo11n_dpfd_energy_label/weights/best.torchscript` | — | 导出的 TorchScript 格式 |
| Teacher 模型 | `yolo-distiller/runs/teacher/yolo11m_energy_label/weights/best.pt` | 39 MB | 教师模型，蒸馏训练时需要，推理不需要 |
| YOLO11m 预训练权重 | `yolo-distiller/yolo11m.pt` | 39 MB | 官方预训练权重，训练教师模型时需要 |
| YOLO11n 预训练权重 | `yolo-distiller/yolo11n.pt` | 5.4 MB | 官方预训练权重，训练学生模型时需要 |

## 二、训练数据集（训练时需要，仅推理可不保存）

| 文件/目录 | 存放路径 | 大小 | 说明 |
|-----------|----------|------|------|
| 原始数据集 | `yolo-distiller/datasets/energy_label/` | ~793 MB（整个 datasets 目录） | 包含 images/train、images/val、labels/train、labels/val |
| 原始数据集配置 | `yolo-distiller/datasets/energy_label.yaml` | <1 KB | 数据集路径和类别定义 |
| 合并数据集 | `yolo-distiller/datasets/energy_label_merged/` | 包含在上面 793MB 中 | 真实+合成数据合并后的数据集 |
| 合并数据集配置 | `yolo-distiller/datasets/energy_label_merged.yaml` | <1 KB | 合并数据集的配置 |

## 三、训练日志和可视化（答辩/文书可能用到）

以下文件在 `yolo-distiller/runs/` 下，被 gitignore 排除：

**Student 训练产物** — `yolo-distiller/runs/student/yolo11n_dpfd_energy_label/`

| 文件 | 说明 |
|------|------|
| `results.csv` | 训练过程指标数据（loss、mAP 等） |
| `results.png` | 训练曲线图 |
| `confusion_matrix.png` | 混淆矩阵 |
| `confusion_matrix_normalized.png` | 归一化混淆矩阵 |
| `PR_curve.png` | Precision-Recall 曲线 |
| `P_curve.png` | Precision 曲线 |
| `R_curve.png` | Recall 曲线 |
| `F1_curve.png` | F1 曲线 |
| `labels.jpg` / `labels_correlogram.jpg` | 标签分布 |
| `val_batch*_labels.jpg` / `val_batch*_pred.jpg` | 验证集预测对比图 |
| `train_batch*.jpg` | 训练样本可视化 |
| `args.yaml` | 训练参数记录 |

**Teacher 训练产物** — `yolo-distiller/runs/teacher/yolo11m_energy_label/`

同上结构，文件类型一致。

**推理测试产物** — `yolo-distiller/runs/detect/predict/` 和 `predict2/`

| 文件 | 说明 |
|------|------|
| `bus.jpg` | 推理测试输出图片（不重要，可不保存） |

## 四、运行时生成文件（可不保存，会自动重建）

| 文件 | 存放路径 | 大小 | 说明 |
|------|----------|------|------|
| SQLite 数据库 | `Service-Outsourcing/backend/detection.db` | 28 KB | 检测记录数据库，删除后重启后端自动重建空库 |
| 上传图片 | `Service-Outsourcing/backend/static/uploads/*.jpg` | ~716 KB | 用户上传的检测图片，运行时生成 |
| 环境变量文件 | `Service-Outsourcing/backend/.env` | — | 当前不存在，按需从 `.env.example` 复制创建 |

## 五、前端构建产物和依赖（可通过命令重建）

| 文件/目录 | 存放路径 | 大小 | 重建命令 |
|-----------|----------|------|----------|
| Web 前端 node_modules | `Service-Outsourcing/frontend/web/node_modules/` | 39 MB | `cd Service-Outsourcing/frontend/web && npm install` |
| Web 前端构建产物 | `Service-Outsourcing/frontend/web/dist/` | <1 MB | `cd Service-Outsourcing/frontend/web && npm run build` |
| uni-app node_modules | `Service-Outsourcing/frontend/front/node_modules/` | 273 MB | `cd Service-Outsourcing/frontend/front && npm install` |
| uni-app 编译产物 | `Service-Outsourcing/frontend/front/dist/` | — | HBuilderX 或 `npm run dev:h5` 生成 |

---

## 快速恢复指南

克隆代码后，按以下顺序恢复：

```bash
# 1. 克隆仓库
git clone https://github.com/Stardep-lmc/EnergyLabel-Detection-System.git
cd EnergyLabel-Detection-System

# 2. 【必须】放入 Student 模型权重（从网盘/备份获取）
mkdir -p yolo-distiller/runs/student/yolo11n_dpfd_energy_label/weights/
cp /你的备份路径/best.pt yolo-distiller/runs/student/yolo11n_dpfd_energy_label/weights/best.pt

# 3. 【可选】放入 Teacher 模型权重
mkdir -p yolo-distiller/runs/teacher/yolo11m_energy_label/weights/
cp /你的备份路径/teacher_best.pt yolo-distiller/runs/teacher/yolo11m_energy_label/weights/best.pt

# 4. 【可选】放入预训练权重（训练时需要）
cp /你的备份路径/yolo11m.pt yolo-distiller/yolo11m.pt
cp /你的备份路径/yolo11n.pt yolo-distiller/yolo11n.pt

# 5. 【可选】放入数据集（训练时需要）
# 将 datasets 目录整体复制到 yolo-distiller/datasets/

# 6. 安装后端依赖并启动
cd Service-Outsourcing/backend
pip install -r requirements.txt
pip install -r requirements-ml.txt
uvicorn main:app --host 0.0.0.0 --port 8000

# 7. 安装前端依赖并构建
cd ../frontend/web
npm install
npm run build
```

---

## 备份建议

实际需要备份的是 **4 个文件/目录**（总计约 900 MB），全部位于 `yolo-distiller/` 下：

| 序号 | 文件/目录 | 路径 | 大小 | 说明 |
|------|-----------|------|------|------|
| 1 | datasets | `yolo-distiller/datasets/` | ~793 MB | 训练数据集（images + labels + yaml 配置） |
| 2 | runs | `yolo-distiller/runs/` | ~60 MB | 训练产物（student + teacher 的权重、日志、曲线图） |
| 3 | yolo11m.pt | `yolo-distiller/yolo11m.pt` | 39 MB | YOLO11m 官方预训练权重（训练教师模型用） |
| 4 | yolo11n.pt | `yolo-distiller/yolo11n.pt` | 5.4 MB | YOLO11n 官方预训练权重（训练学生模型用） |

其中 `runs/` 目录包含：
- `runs/student/yolo11n_dpfd_energy_label/weights/best.pt` — **推理必需**，没有它后端检测接口返回 503
- `runs/student/yolo11n_dpfd_energy_label/weights/best.onnx` — ONNX 导出格式
- `runs/student/yolo11n_dpfd_energy_label/results.csv` + `*.png` — 学生模型训练日志和曲线图
- `runs/teacher/yolo11m_energy_label/weights/best.pt` — 教师模型权重
- `runs/teacher/yolo11m_energy_label/results.csv` + `*.png` — 教师模型训练日志和曲线图

**最小备份**：如果只需要推理功能，只需 `runs/student/yolo11n_dpfd_energy_label/weights/best.pt`（5.3 MB）。
