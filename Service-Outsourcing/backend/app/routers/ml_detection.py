"""
ML检测路由 - 将YOLO推理服务集成到后端API
提供图片上传→模型推理→结果入库→返回前端的完整流程
"""
import os
import sys
import shutil
import logging
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db
from ..utils import generate_filename, load_config

logger = logging.getLogger("ml_detection")

router = APIRouter(prefix="/api/ml", tags=["ML Detection"])

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ============ 推理服务懒加载 ============
_detector = None

# 推理服务路径（yolo-distiller/scripts/inference_service.py）
YOLO_DISTILLER_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "yolo-distiller"
INFERENCE_MODULE_PATH = YOLO_DISTILLER_ROOT / "scripts"


def get_detector():
    """懒加载检测器，避免启动时就加载模型"""
    global _detector
    if _detector is not None:
        return _detector

    # 将推理模块路径加入sys.path
    if str(INFERENCE_MODULE_PATH) not in sys.path:
        sys.path.insert(0, str(INFERENCE_MODULE_PATH))

    try:
        from inference_service import EnergyLabelDetector

        # 按优先级查找模型：DPFD Student > CWD Student > Teacher
        model_candidates = [
            ("Student DPFD", YOLO_DISTILLER_ROOT / "runs" / "student"
             / "yolo11n_dpfd_energy_label" / "weights" / "best.pt"),
            ("Student CWD", YOLO_DISTILLER_ROOT / "runs" / "student"
             / "yolov8n_cwd_energy_label" / "weights" / "best.pt"),
            ("Teacher", YOLO_DISTILLER_ROOT / "runs" / "teacher"
             / "yolo11m_energy_label" / "weights" / "best.pt"),
        ]

        model_path = None
        for label, path in model_candidates:
            if path.exists():
                model_path = str(path)
                logger.info(f"加载{label}模型: {model_path}")
                break

        if model_path is None:
            logger.warning("未找到训练好的模型，ML检测功能不可用")
            return None

        # 从配置读取参数
        config = load_config()
        position_tolerance = config.get("positionTolerance", 10) / 100.0

        _detector = EnergyLabelDetector(
            model_path=model_path,
            conf_threshold=0.25,
            iou_threshold=0.45,
            position_tolerance=position_tolerance,
            device="cpu",
        )
        return _detector

    except Exception as e:
        logger.error(f"加载检测器失败: {e}")
        return None


# ============ API接口 ============

@router.post("/detect")
async def ml_detect(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    上传图片 → YOLO推理 → 结果入库 → 返回检测结果
    这是核心的ML检测接口
    """
    # 1. 校验文件格式
    ALLOWED_EXT = {".jpg", ".jpeg", ".png"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"不支持的图片格式: {ext}")

    # 2. 保存上传文件
    filename = generate_filename(file.filename)
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 3. 获取检测器
    detector = get_detector()
    if detector is None:
        raise HTTPException(
            status_code=503,
            detail="ML检测服务不可用，请确认模型已训练完成"
        )

    # 4. 执行推理
    try:
        output = detector.detect(file_path)
    except Exception as e:
        logger.error(f"推理失败: {e}")
        raise HTTPException(status_code=500, detail=f"推理失败: {str(e)}")

    # 5. 转换为后端格式并入库
    backend_data = detector.to_backend_format(output)
    backend_data["image_path"] = f"static/uploads/{filename}"

    record_create = schemas.DetectionRecordCreate(
        device_id=backend_data["device_id"],
        batch_id=backend_data["batch_id"],
        image_path=backend_data["image_path"],
        energy_level=backend_data["energy_level"],
        defect_type=backend_data["defect_type"],
        confidence=backend_data["confidence"],
    )
    db_record = crud.create_detection_record(db, record_create)

    # 6. 构建返回结果
    base_url = str(request.base_url).rstrip("/")
    image_url = f"{base_url}/static/uploads/{filename}"

    return {
        "success": True,
        "record_id": db_record.id,
        "status": "OK" if output.is_qualified else "NG",
        "is_qualified": output.is_qualified,
        "defect_type": backend_data["defect_type"],
        "position_status": output.position_status,
        "confidence": backend_data["confidence"],
        "inference_time_ms": output.inference_time_ms,
        "total_labels": output.total_labels,
        "image_url": image_url,
        "detections": [
            {
                "class_name": d.class_cn,
                "confidence": d.confidence,
                "bbox": d.bbox,
                "is_defect": d.is_defect,
                "position_ok": d.position_ok,
            }
            for d in output.detections
        ],
        "timestamp": output.timestamp,
    }


@router.get("/status")
async def ml_status():
    """检查ML服务状态"""
    detector = get_detector()
    if detector is None:
        return {
            "available": False,
            "message": "模型未加载，请先训练模型",
        }
    return {
        "available": True,
        "model_path": str(detector.model.ckpt_path) if hasattr(detector.model, 'ckpt_path') else "loaded",
        "device": detector.device,
        "conf_threshold": detector.conf_threshold,
    }


@router.post("/reload")
async def ml_reload():
    """重新加载模型（配置变更后调用）"""
    global _detector
    _detector = None
    detector = get_detector()
    if detector is None:
        raise HTTPException(status_code=503, detail="模型重新加载失败")
    return {"success": True, "message": "模型已重新加载"}