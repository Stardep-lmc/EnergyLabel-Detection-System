#!/usr/bin/env python3
"""
Step 3: 模型导出
将训练好的模型导出为多种格式，用于不同部署场景：
- ONNX: 通用推理框架（OpenCV DNN, ONNX Runtime, OpenHarmony NNRT）
- TorchScript: PyTorch原生部署
- NCNN: 移动端/嵌入式部署
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ultralytics import YOLO


def export_model():
    # 优先导出DPFD蒸馏Student模型
    student_dpfd = PROJECT_ROOT / "runs" / "student" / "yolo11n_dpfd_energy_label" / "weights" / "best.pt"
    # 回退到CWD Student
    student_cwd = PROJECT_ROOT / "runs" / "student" / "yolov8n_cwd_energy_label" / "weights" / "best.pt"
    # 回退到Teacher
    teacher_path = PROJECT_ROOT / "runs" / "teacher" / "yolo11m_energy_label" / "weights" / "best.pt"

    model_path = None
    for p in [student_dpfd, student_cwd, teacher_path]:
        if p.exists():
            model_path = p
            break

    if model_path is None:
        print("错误: 未找到任何训练好的模型")
        return

    print(f"导出模型: {model_path}")
    model = YOLO(str(model_path))

    # ONNX导出（主要部署格式）
    print("\n[1/2] 导出ONNX...")
    model.export(
        format="onnx",
        imgsz=640,
        simplify=True,
        opset=12,
        dynamic=False,
    )

    # TorchScript导出
    print("\n[2/2] 导出TorchScript...")
    model.export(
        format="torchscript",
        imgsz=640,
    )

    export_dir = model_path.parent
    print(f"\n导出完成! 文件位于: {export_dir}")
    for f in export_dir.iterdir():
        if f.suffix in ('.onnx', '.torchscript', '.pt'):
            size_mb = f.stat().st_size / 1024 / 1024
            print(f"  {f.name}: {size_mb:.1f} MB")


if __name__ == "__main__":
    export_model()