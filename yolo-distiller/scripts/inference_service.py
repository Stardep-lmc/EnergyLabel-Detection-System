#!/usr/bin/env python3
"""
推理服务模块
提供能效标签检测的核心推理能力，供后端API调用

功能：
1. 标签检测与定位（YOLO目标检测）
2. 缺陷分类（正常/偏移/划痕/污渍/褶皱）
3. 位置偏移判断
4. 置信度评估
5. 检测结果结构化输出
"""
import sys
import time
import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ultralytics import YOLO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("inference_service")

# 类别映射
CLASS_NAMES = {
    0: "label_normal",
    1: "label_offset",
    2: "label_scratch",
    3: "label_stain",
    4: "label_wrinkle",
}

CLASS_CN = {
    0: "正常",
    1: "偏移",
    2: "划痕",
    3: "污渍",
    4: "褶皱",
}

# 缺陷类型（非正常的都算缺陷）
DEFECT_CLASSES = {1, 2, 3, 4}


@dataclass
class DetectionResult:
    """单个检测结果"""
    class_id: int
    class_name: str
    class_cn: str
    confidence: float
    bbox: List[float]       # [x1, y1, x2, y2] 像素坐标
    bbox_norm: List[float]  # [cx, cy, w, h] 归一化坐标
    is_defect: bool
    position_ok: bool       # 标签位置是否在规定范围内


@dataclass
class InferenceOutput:
    """完整推理输出"""
    image_path: str
    detections: List[DetectionResult]
    has_defect: bool
    is_qualified: bool
    defect_types: List[str]
    position_status: str
    total_labels: int
    inference_time_ms: float
    timestamp: str


class EnergyLabelDetector:
    """能效标签检测器"""

    def __init__(
        self,
        model_path: Optional[str] = None,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        position_tolerance: float = 0.1,  # 位置偏移容忍度（归一化）
        device: str = "cpu",
    ):
        if model_path is None:
            # 按优先级查找模型：DPFD Student > CWD Student > Teacher
            candidates = [
                PROJECT_ROOT / "runs" / "student" / "yolo11n_dpfd_energy_label" / "weights" / "best.pt",
                PROJECT_ROOT / "runs" / "student" / "yolov8n_cwd_energy_label" / "weights" / "best.pt",
                PROJECT_ROOT / "runs" / "teacher" / "yolo11m_energy_label" / "weights" / "best.pt",
            ]
            model_path = None
            for p in candidates:
                if p.exists():
                    model_path = str(p)
                    break
            if model_path is None:
                model_path = str(candidates[0])  # 会在下面的exists检查中报错

        if not Path(model_path).exists():
            raise FileNotFoundError(f"模型文件不存在: {model_path}")

        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.position_tolerance = position_tolerance
        self.device = device

        # 预设的标准标签位置（归一化坐标 cx, cy）
        # 实际使用时从配置中读取
        self.standard_position = {"cx": 0.5, "cy": 0.5}

        logger.info(f"检测器初始化完成: model={model_path}, device={device}")

    def set_standard_position(self, cx: float, cy: float):
        """设置标准标签位置"""
        self.standard_position = {"cx": cx, "cy": cy}

    def check_position(self, cx: float, cy: float) -> bool:
        """检查标签位置是否在容忍范围内"""
        dx = abs(cx - self.standard_position["cx"])
        dy = abs(cy - self.standard_position["cy"])
        return dx <= self.position_tolerance and dy <= self.position_tolerance

    def detect(self, image_path: str) -> InferenceOutput:
        """
        对单张图片进行检测
        返回结构化的检测结果
        """
        start_time = time.time()

        # YOLO推理
        results = self.model.predict(
            source=image_path,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            device=self.device,
            verbose=False,
        )

        detections = []
        has_defect = False
        defect_types = set()
        all_positions_ok = True

        if results and len(results) > 0:
            result = results[0]
            img_h, img_w = result.orig_shape

            for box in result.boxes:
                cls_id = int(box.cls.item())
                conf = float(box.conf.item())
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                # 归一化坐标
                cx = (x1 + x2) / 2 / img_w
                cy = (y1 + y2) / 2 / img_h
                w = (x2 - x1) / img_w
                h = (y2 - y1) / img_h

                is_defect = cls_id in DEFECT_CLASSES
                position_ok = self.check_position(cx, cy)

                if is_defect:
                    has_defect = True
                    defect_types.add(CLASS_CN.get(cls_id, "未知"))

                if not position_ok:
                    all_positions_ok = False

                det = DetectionResult(
                    class_id=cls_id,
                    class_name=CLASS_NAMES.get(cls_id, f"unknown_{cls_id}"),
                    class_cn=CLASS_CN.get(cls_id, "未知"),
                    confidence=round(conf, 4),
                    bbox=[round(v, 2) for v in [x1, y1, x2, y2]],
                    bbox_norm=[round(v, 4) for v in [cx, cy, w, h]],
                    is_defect=is_defect,
                    position_ok=position_ok,
                )
                detections.append(det)

        inference_time = (time.time() - start_time) * 1000

        # 综合判定
        is_qualified = not has_defect and all_positions_ok and len(detections) > 0

        if not all_positions_ok:
            position_status = "偏移"
        elif len(detections) == 0:
            position_status = "未检测到标签"
        else:
            position_status = "正常"

        output = InferenceOutput(
            image_path=image_path,
            detections=detections,
            has_defect=has_defect,
            is_qualified=is_qualified,
            defect_types=sorted(defect_types),
            position_status=position_status,
            total_labels=len(detections),
            inference_time_ms=round(inference_time, 2),
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

        return output

    def detect_batch(self, image_paths: List[str]) -> List[InferenceOutput]:
        """批量检测"""
        return [self.detect(p) for p in image_paths]

    def to_backend_format(self, output: InferenceOutput) -> dict:
        """
        将推理结果转换为后端API所需的格式
        对接 Service-Outsourcing/backend 的 DetectionRecordCreate schema
        """
        # 取最高置信度的检测结果
        best_det = None
        if output.detections:
            best_det = max(output.detections, key=lambda d: d.confidence)

        # 缺陷类型字符串
        if output.defect_types:
            defect_str = ",".join(output.defect_types)
        else:
            defect_str = "无"

        # 能效等级（从OCR或预设，这里暂用1.0占位）
        energy_level = 1.0

        return {
            "device_id": "cam_01",
            "batch_id": "default_batch",
            "image_path": output.image_path,
            "energy_level": energy_level,
            "defect_type": defect_str,
            "confidence": best_det.confidence if best_det else 0.0,
            "is_qualified": output.is_qualified,
            # 扩展字段（前端需要）
            "position_status": output.position_status,
            "position_x": best_det.bbox_norm[0] if best_det else 0,
            "position_y": best_det.bbox_norm[1] if best_det else 0,
            "inference_time_ms": output.inference_time_ms,
            "total_labels": output.total_labels,
        }


def main():
    """测试推理"""
    import argparse

    parser = argparse.ArgumentParser(description="能效标签检测推理")
    parser.add_argument("--image", type=str, required=True, help="图片路径")
    parser.add_argument("--model", type=str, default=None, help="模型路径")
    parser.add_argument("--conf", type=float, default=0.25, help="置信度阈值")
    parser.add_argument("--device", type=str, default="cpu", help="推理设备")
    args = parser.parse_args()

    detector = EnergyLabelDetector(
        model_path=args.model,
        conf_threshold=args.conf,
        device=args.device,
    )

    output = detector.detect(args.image)

    print(json.dumps(asdict(output), ensure_ascii=False, indent=2))
    print(f"\n后端格式:")
    print(json.dumps(detector.to_backend_format(output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()