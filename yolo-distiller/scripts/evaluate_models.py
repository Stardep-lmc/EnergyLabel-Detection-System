#!/usr/bin/env python3
"""
模型评估对比脚本

对比Teacher、Student(CWD)、Student(DPFD)三个模型的性能指标：
- mAP@50, mAP@50-95
- 推理速度 (FPS)
- 模型大小
- 各类别AP

用法：
    python evaluate_models.py --data ../datasets/energy_label/energy_label.yaml
"""
import sys
import time
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import torch
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ultralytics import YOLO


@dataclass
class ModelMetrics:
    name: str
    model_path: str
    file_size_mb: float
    params_m: float
    flops_g: float
    map50: float
    map50_95: float
    fps: float
    per_class_ap: dict


def evaluate_model(model_path: str, data_yaml: str, name: str, device: str = "cpu") -> Optional[ModelMetrics]:
    """评估单个模型"""
    path = Path(model_path)
    if not path.exists():
        print(f"  ⚠ 模型不存在: {model_path}")
        return None

    print(f"\n{'='*60}")
    print(f"评估模型: {name}")
    print(f"路径: {model_path}")
    print(f"{'='*60}")

    # 模型大小
    file_size_mb = path.stat().st_size / (1024 * 1024)

    # 加载模型
    model = YOLO(model_path)

    # 参数量和FLOPs
    params = sum(p.numel() for p in model.model.parameters())
    params_m = params / 1e6

    # FLOPs估算（通过模型info）
    try:
        info = model.info(verbose=False)
        flops_g = info[1] if isinstance(info, (list, tuple)) and len(info) > 1 else 0
    except Exception:
        flops_g = 0

    # 验证集评估
    print("  运行验证...")
    try:
        results = model.val(
            data=data_yaml,
            device=device,
            verbose=False,
            plots=False,
        )

        map50 = results.box.map50
        map50_95 = results.box.map

        # 各类别AP
        per_class_ap = {}
        if hasattr(results.box, 'ap_class_index') and hasattr(results.box, 'ap50'):
            names = model.names
            for i, cls_idx in enumerate(results.box.ap_class_index):
                cls_name = names.get(int(cls_idx), f"class_{cls_idx}")
                per_class_ap[cls_name] = float(results.box.ap50[i])
    except Exception as e:
        print(f"  ⚠ 验证失败: {e}")
        map50 = 0
        map50_95 = 0
        per_class_ap = {}

    # 推理速度测试
    print("  测试推理速度...")
    try:
        dummy_img = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)

        # 预热
        for _ in range(3):
            model.predict(dummy_img, verbose=False, device=device)

        # 计时
        times = []
        for _ in range(20):
            t0 = time.time()
            model.predict(dummy_img, verbose=False, device=device)
            times.append(time.time() - t0)

        avg_time = np.mean(times)
        fps = 1.0 / avg_time if avg_time > 0 else 0
    except Exception as e:
        print(f"  ⚠ 速度测试失败: {e}")
        fps = 0

    metrics = ModelMetrics(
        name=name,
        model_path=model_path,
        file_size_mb=round(file_size_mb, 2),
        params_m=round(params_m, 2),
        flops_g=round(flops_g, 2),
        map50=round(map50, 4),
        map50_95=round(map50_95, 4),
        fps=round(fps, 1),
        per_class_ap=per_class_ap,
    )

    print(f"  ✓ mAP@50={metrics.map50:.4f}, mAP@50-95={metrics.map50_95:.4f}")
    print(f"  ✓ FPS={metrics.fps:.1f}, Size={metrics.file_size_mb:.1f}MB, Params={metrics.params_m:.1f}M")

    return metrics


def print_comparison(metrics_list):
    """打印对比表格"""
    valid = [m for m in metrics_list if m is not None]
    if not valid:
        print("\n没有可用的模型进行对比")
        return

    print(f"\n{'='*80}")
    print("模型性能对比")
    print(f"{'='*80}")

    # 表头
    header = f"{'模型':<20} {'mAP@50':>8} {'mAP@50-95':>10} {'FPS':>6} {'大小(MB)':>9} {'参数(M)':>8}"
    print(header)
    print("-" * 80)

    for m in valid:
        row = f"{m.name:<20} {m.map50:>8.4f} {m.map50_95:>10.4f} {m.fps:>6.1f} {m.file_size_mb:>9.1f} {m.params_m:>8.1f}"
        print(row)

    # 对比分析
    if len(valid) >= 2:
        print(f"\n{'='*80}")
        print("对比分析")
        print(f"{'='*80}")

        teacher = next((m for m in valid if 'teacher' in m.name.lower()), None)
        students = [m for m in valid if 'student' in m.name.lower()]

        if teacher and students:
            for s in students:
                map_diff = s.map50 - teacher.map50
                speed_ratio = s.fps / teacher.fps if teacher.fps > 0 else 0
                size_ratio = s.file_size_mb / teacher.file_size_mb if teacher.file_size_mb > 0 else 0

                print(f"\n{s.name} vs {teacher.name}:")
                print(f"  mAP@50 差距: {map_diff:+.4f} ({'↑' if map_diff >= 0 else '↓'})")
                print(f"  速度提升: {speed_ratio:.2f}x")
                print(f"  模型压缩: {size_ratio:.2f}x ({(1-size_ratio)*100:.0f}% 更小)")

        # DPFD vs CWD
        dpfd = next((m for m in valid if 'dpfd' in m.name.lower()), None)
        cwd = next((m for m in valid if 'cwd' in m.name.lower()), None)
        if dpfd and cwd:
            print(f"\nDPFD vs CWD:")
            print(f"  mAP@50: DPFD={dpfd.map50:.4f}, CWD={cwd.map50:.4f} (差距: {dpfd.map50-cwd.map50:+.4f})")
            print(f"  FPS: DPFD={dpfd.fps:.1f}, CWD={cwd.fps:.1f}")

    # 各类别AP
    print(f"\n{'='*80}")
    print("各类别 AP@50")
    print(f"{'='*80}")

    all_classes = set()
    for m in valid:
        all_classes.update(m.per_class_ap.keys())

    if all_classes:
        header = f"{'类别':<20}" + "".join(f"{m.name:>15}" for m in valid)
        print(header)
        print("-" * (20 + 15 * len(valid)))

        for cls in sorted(all_classes):
            row = f"{cls:<20}"
            for m in valid:
                ap = m.per_class_ap.get(cls, 0)
                row += f"{ap:>15.4f}"
            print(row)


def main():
    parser = argparse.ArgumentParser(description="模型评估对比")
    parser.add_argument("--data", type=str, default=None, help="数据集YAML路径")
    parser.add_argument("--device", type=str, default="cpu", help="推理设备")
    args = parser.parse_args()

    # 查找数据集
    if args.data is None:
        candidates = [
            PROJECT_ROOT / "datasets" / "energy_label_merged.yaml",
            PROJECT_ROOT / "datasets" / "energy_label" / "energy_label.yaml",
            PROJECT_ROOT / "datasets" / "energy_label.yaml",
        ]
        for c in candidates:
            if c.exists():
                args.data = str(c)
                break

    if args.data is None or not Path(args.data).exists():
        print("错误: 未找到数据集YAML文件")
        print("请先运行: python generate_synthetic_data.py")
        return

    # 查找模型
    model_candidates = [
        ("Teacher (YOLO11m)", PROJECT_ROOT / "runs" / "teacher" / "yolo11m_energy_label" / "weights" / "best.pt"),
        ("Student CWD (YOLOv8n)", PROJECT_ROOT / "runs" / "student" / "yolov8n_cwd_energy_label" / "weights" / "best.pt"),
        ("Student DPFD (YOLO11n)", PROJECT_ROOT / "runs" / "student" / "yolo11n_dpfd_energy_label" / "weights" / "best.pt"),
    ]

    print("查找模型...")
    for name, path in model_candidates:
        status = "✓" if path.exists() else "✗"
        print(f"  {status} {name}: {path}")

    # 评估
    metrics_list = []
    for name, path in model_candidates:
        if path.exists():
            m = evaluate_model(str(path), args.data, name, args.device)
            metrics_list.append(m)

    if not any(m is not None for m in metrics_list):
        print("\n没有找到已训练的模型。请先训练模型:")
        print("  bash scripts/run_pipeline.sh")
        return

    print_comparison(metrics_list)


if __name__ == "__main__":
    main()