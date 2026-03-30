#!/bin/bash
# ============================================================
# 产品能效标签与缺陷检测系统 - 完整训练流水线
# YOLO11 Teacher-Student + DPFD (Dual-Path Feature Distillation)
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "============================================"
echo "  能效标签检测系统 - DPFD蒸馏训练流水线"
echo "  Teacher: YOLO11m | Student: YOLO11n"
echo "  蒸馏方法: DPFD (CWD + MGD 自适应融合)"
echo "  项目根目录: $PROJECT_ROOT"
echo "============================================"

# Step 0: 检查Python环境
echo ""
echo "[Step 0] 检查Python环境..."
python3 -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')" 2>/dev/null || {
    echo "错误: 请先安装PyTorch"
    exit 1
}

# Step 1: 准备数据集
echo ""
echo "[Step 1] 准备数据集（5类重标注 + train/val划分）..."
cd "$PROJECT_ROOT"
python3 scripts/prepare_dataset.py

TRAIN_COUNT=$(find datasets/energy_label/images/train -name "*.jpg" 2>/dev/null | wc -l)
VAL_COUNT=$(find datasets/energy_label/images/val -name "*.jpg" 2>/dev/null | wc -l)
echo "  训练集: ${TRAIN_COUNT} 张, 验证集: ${VAL_COUNT} 张"

if [ "$TRAIN_COUNT" -eq 0 ]; then
    echo "错误: 数据集准备失败"
    exit 1
fi

# Step 2: 训练Teacher模型
echo ""
echo "[Step 2] 训练Teacher模型 (YOLO11m, 200 epochs)..."
python3 scripts/train_teacher.py

TEACHER_PATH="$PROJECT_ROOT/runs/teacher/yolo11m_energy_label/weights/best.pt"
if [ ! -f "$TEACHER_PATH" ]; then
    echo "错误: Teacher模型训练失败"
    exit 1
fi
echo "  Teacher模型: $TEACHER_PATH"

# Step 3: DPFD蒸馏训练Student模型
echo ""
echo "[Step 3] DPFD蒸馏训练Student模型 (YOLO11n, 250 epochs)..."
python3 scripts/train_student_dpfd.py

STUDENT_PATH="$PROJECT_ROOT/runs/student/yolo11n_dpfd_energy_label/weights/best.pt"
if [ ! -f "$STUDENT_PATH" ]; then
    echo "错误: Student模型训练失败"
    exit 1
fi
echo "  Student模型: $STUDENT_PATH"

# Step 4: 导出模型
echo ""
echo "[Step 4] 导出模型 (ONNX + TorchScript)..."
python3 scripts/export_model.py

# Step 5: 验证推理
echo ""
echo "[Step 5] 验证推理..."
TEST_IMG=$(find datasets/energy_label/images/val -name "*.jpg" | head -1)
if [ -n "$TEST_IMG" ]; then
    python3 scripts/inference_service.py --image "$TEST_IMG" --device cpu
fi

echo ""
echo "============================================"
echo "  DPFD蒸馏训练流水线完成!"
echo "  Teacher (YOLO11m): $TEACHER_PATH"
echo "  Student (YOLO11n): $STUDENT_PATH"
echo "============================================"
echo ""
echo "下一步: 启动后端服务"
echo "  cd ../Service-Outsourcing/backend && python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"