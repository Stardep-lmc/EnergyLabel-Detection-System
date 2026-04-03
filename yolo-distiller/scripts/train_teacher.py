#!/usr/bin/env python3
"""
Step 1: 训练Teacher模型 (YOLO11m)
大模型，追求最高精度，作为知识蒸馏的教师

YOLO11m: 409层, 20.1M参数, 68.5 GFLOPs
相比YOLOv8m，YOLO11m引入了C3k2和C2PSA模块，精度更高
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ultralytics import YOLO


def train_teacher():
    # Teacher: YOLO11m (中大模型，精度高)
    model = YOLO("yolo11m.pt")

    results = model.train(
        data=str(PROJECT_ROOT / "datasets" / "energy_label_merged.yaml"),
        epochs=200,
        batch=16,
        imgsz=640,
        patience=40,
        optimizer="AdamW",
        lr0=0.001,
        lrf=0.01,
        weight_decay=0.0005,
        warmup_epochs=5,
        cos_lr=True,
        # 竞赛级增强策略
        mosaic=1.0,
        mixup=0.15,
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
        close_mosaic=15,
        # 输出
        project=str(PROJECT_ROOT / "runs" / "teacher"),
        name="yolo11m_energy_label",
        exist_ok=True,
        save=True,
        save_period=10,
        plots=True,
        verbose=True,
        device=0 if __import__('torch').cuda.is_available() else "cpu",
    )

    print(f"\nTeacher模型训练完成!")
    print(f"Best模型: {PROJECT_ROOT / 'runs' / 'teacher' / 'yolo11m_energy_label' / 'weights' / 'best.pt'}")
    return results


if __name__ == "__main__":
    train_teacher()