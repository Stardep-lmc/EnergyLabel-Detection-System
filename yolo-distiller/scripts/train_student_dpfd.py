#!/usr/bin/env python3
"""
Step 2: DPFD蒸馏训练Student模型 (YOLO11n)
使用创新的Dual-Path Feature Distillation (DPFD)方法

DPFD创新点：
- 双路径融合：CWD（通道级语义分布）+ MGD（空间级掩码生成）
- 自适应门控：可学习的注意力网络动态平衡两条路径的权重
- CWD路径擅长类别识别（"看什么"），MGD路径擅长缺陷定位（"在哪看"）
- 相比单独CWD或MGD，DPFD在缺陷检测场景下能同时提升分类和定位精度

Teacher: YOLO11m (20.1M params, 68.5 GFLOPs)
Student: YOLO11n (2.6M params, 6.6 GFLOPs) → 7.7x压缩, 10.4x加速
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ultralytics import YOLO


def train_student_dpfd():
    # 加载Teacher模型
    teacher_path = PROJECT_ROOT / "runs" / "teacher" / "yolo11m_energy_label" / "weights" / "best.pt"
    if not teacher_path.exists():
        raise FileNotFoundError(
            f"Teacher模型不存在: {teacher_path}\n请先运行 train_teacher.py"
        )

    teacher_model = YOLO(str(teacher_path))
    print(f"Teacher模型已加载: {teacher_path}")

    # Student: YOLO11n (轻量模型)
    student_model = YOLO("yolo11n.pt")

    # DPFD蒸馏训练
    results = student_model.train(
        data=str(PROJECT_ROOT / "datasets" / "energy_label.yaml"),
        epochs=250,
        batch=32,
        imgsz=640,
        patience=50,
        optimizer="AdamW",
        lr0=0.002,
        lrf=0.01,
        weight_decay=0.0005,
        warmup_epochs=5,
        cos_lr=True,
        # 竞赛级增强策略
        mosaic=1.0,
        mixup=0.1,
        copy_paste=0.1,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=10.0,
        translate=0.1,
        scale=0.5,
        shear=2.0,
        fliplr=0.5,
        flipud=0.0,
        close_mosaic=20,
        # DPFD蒸馏参数
        teacher=teacher_model.model,
        distillation_loss="dpfdLoss",  # 前3字符 "dpf" 映射到 DPFDLoss
        # 输出
        project=str(PROJECT_ROOT / "runs" / "student"),
        name="yolo11n_dpfd_energy_label",
        exist_ok=True,
        save=True,
        save_period=10,
        plots=True,
        verbose=True,
        device=0,
    )

    print(f"\nStudent DPFD蒸馏训练完成!")
    print(f"Best模型: {PROJECT_ROOT / 'runs' / 'student' / 'yolo11n_dpfd_energy_label' / 'weights' / 'best.pt'}")
    return results


if __name__ == "__main__":
    train_student_dpfd()