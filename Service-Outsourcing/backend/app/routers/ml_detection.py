"""
ML检测路由 - 将YOLO推理服务集成到后端API
提供图片上传→模型推理→结果入库→返回前端的完整流程
"""
import os
import sys
import shutil
import logging
import asyncio
import threading
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db
from ..utils import generate_filename, load_config

logger = logging.getLogger("ml_detection")

router = APIRouter(prefix="/api/ml", tags=["ML Detection"])

# 以 backend/ 目录为基准，不依赖启动目录
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = str(BACKEND_DIR / "static" / "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ============ 推理服务懒加载 ============
_detector = None
_detector_lock = threading.Lock()

# 推理服务路径（yolo-distiller/scripts/inference_service.py）
YOLO_DISTILLER_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "yolo-distiller"
INFERENCE_MODULE_PATH = YOLO_DISTILLER_ROOT / "scripts"

# 模型候选路径（模块级，供 get_detector 和 /status 共用）
MODEL_CANDIDATES = [
    ("Student DPFD", YOLO_DISTILLER_ROOT / "runs" / "student"
     / "yolo11n_dpfd_energy_label" / "weights" / "best.pt"),
    ("Student CWD", YOLO_DISTILLER_ROOT / "runs" / "student"
     / "yolov8n_cwd_energy_label" / "weights" / "best.pt"),
    ("Teacher", YOLO_DISTILLER_ROOT / "runs" / "teacher"
     / "yolo11m_energy_label" / "weights" / "best.pt"),
]


def get_detector():
    """懒加载检测器，避免启动时就加载模型（线程安全）"""
    global _detector

    # 快速路径：已初始化时直接返回（读取引用是原子的）
    det = _detector
    if det is not None:
        return det

    with _detector_lock:
        # 双重检查：获取锁后再次确认，避免重复初始化
        if _detector is not None:
            return _detector

        # 将推理模块路径加入sys.path
        if str(INFERENCE_MODULE_PATH) not in sys.path:
            sys.path.insert(0, str(INFERENCE_MODULE_PATH))

        try:
            from inference_service import EnergyLabelDetector

            model_path = None
            for label, path in MODEL_CANDIDATES:
                if path.exists():
                    model_path = str(path)
                    logger.info(f"加载{label}模型: {model_path}")
                    break

            if model_path is None:
                logger.warning("未找到训练好的模型，ML检测功能不可用")
                return None

            # 从配置读取参数，将灵敏度映射为置信度阈值
            config = load_config()
            position_tolerance = config.get("positionTolerance", 10) / 100.0
            sensitivity = config.get("sensitivity", "中")
            conf_map = {"低": 0.45, "中": 0.25, "高": 0.15}
            conf_threshold = conf_map.get(sensitivity, 0.25)

            _detector = EnergyLabelDetector(
                model_path=model_path,
                conf_threshold=conf_threshold,
                iou_threshold=0.45,
                position_tolerance=position_tolerance,
                device="cpu",
            )
            logger.info(f"检测器参数: sensitivity={sensitivity}, conf={conf_threshold}, pos_tol={position_tolerance}")
            return _detector

        except Exception as e:
            logger.error(f"加载检测器失败: {e}")
            return None


# ============ API接口 ============

@router.post("/detect")
async def ml_detect(
    request: Request,
    file: UploadFile = File(...),
    device_id: str = "cam_01",
    batch_id: str = "default_batch",
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
            detail="ML检测服务不可用，请先训练模型: cd yolo-distiller && bash scripts/train_all.sh"
        )

    # 4. 读取配置（一次性读取，避免重复IO）
    config = load_config()

    # 5. 执行推理（放到线程池，不阻塞事件循环 — fix #38）
    try:
        brightness_offset = float(config.get("lightCompensation", 0))
        output = await asyncio.to_thread(
            detector.detect, file_path, brightness_offset=brightness_offset
        )
    except Exception as e:
        logger.error(f"推理失败: {e}")
        raise HTTPException(status_code=500, detail=f"推理失败: {str(e)}")

    # 6. 转换为后端格式并入库
    backend_data = detector.to_backend_format(output, device_id=device_id, batch_id=batch_id)
    backend_data["image_path"] = f"static/uploads/{filename}"

    # 从配置读取预设型号
    preset_model_str = "未配置"
    if config.get("models"):
        enabled = [m for m in config["models"] if m.get("enabled", True)]
        if enabled:
            preset_model_str = f"{enabled[0].get('name', '')} {enabled[0].get('model', '')}".strip() or "未配置"

    record_create = schemas.DetectionRecordCreate(
        device_id=backend_data["device_id"],
        batch_id=backend_data["batch_id"],
        image_path=backend_data["image_path"],
        energy_level=backend_data["energy_level"],
        defect_type=backend_data["defect_type"],
        confidence=backend_data["confidence"],
        position_status=output.position_status,
        preset_model=preset_model_str,
        ocr_text=backend_data.get("ocr_text", ""),
        position_x=backend_data.get("position_x", 0.5),
        position_y=backend_data.get("position_y", 0.5),
        is_qualified=output.is_qualified,  # 直接使用推理侧判定结果，避免与judge_qualified冲突
    )
    db_record = crud.create_detection_record(db, record_create)

    # 6. 构建返回结果
    base_url = str(request.base_url).rstrip("/")
    image_url = f"{base_url}/static/uploads/{filename}"

    result = {
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
        "ocr_text": backend_data.get("ocr_text") or (f"{int(backend_data['energy_level'])}级能效" if backend_data['energy_level'] else ""),
        "preset_model": preset_model_str,
        "position_x": backend_data.get("position_x", 0.5),
        "position_y": backend_data.get("position_y", 0.5),
        "product_model": backend_data.get("product_model") or preset_model_str,
        "ocr_available": backend_data.get("ocr_available", False),
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

    # 7. WebSocket广播检测结果
    try:
        ws_mgr = request.app.state.ws_manager
        await ws_mgr.broadcast({
            "type": "detection_result",
            "status": result["status"],
            "defect_type": result["defect_type"],
            "position_status": result["position_status"],
            "confidence": result["confidence"],
            "timestamp": result["timestamp"],
            "image_url": image_url,
        })
    except Exception as e:
        logger.warning(f"WebSocket广播失败: {e}")

    return result


@router.get("/status")
async def ml_status():
    """检查ML服务状态"""
    detector = get_detector()
    if detector is None:
        return {
            "available": False,
            "message": "模型未加载，请先训练模型",
            "train_guide": "cd yolo-distiller && bash scripts/train_all.sh",
            "model_paths": [str(p) for _, p in MODEL_CANDIDATES],
        }
    # 获取OCR可用状态
    ocr_available = False
    try:
        from inference_service import _ocr_available
        ocr_available = _ocr_available
    except ImportError:
        pass

    return {
        "available": True,
        "model_path": str(detector.model.ckpt_path) if hasattr(detector.model, 'ckpt_path') else "loaded",
        "device": detector.device,
        "conf_threshold": detector.conf_threshold,
        "ocr_available": ocr_available,
    }


@router.post("/reload")
async def ml_reload():
    """重新加载模型（配置变更后调用），在锁内完成清除+重建，避免竞态"""
    global _detector
    with _detector_lock:
        _detector = None

    detector = get_detector()
    if detector is None:
        raise HTTPException(status_code=503, detail="模型重新加载失败")
    return {"success": True, "message": "模型已重新加载"}
