from datetime import date
from typing import Optional, List

import os
import shutil

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, Request
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db
from ..utils import (
    generate_filename,
    build_ocr_text,
    normalize_defect_type,
    load_config,
    save_config
)

router = APIRouter()

# 以 backend/ 目录为基准，不依赖启动目录
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(BACKEND_DIR, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# =========================
# 工具函数：前端字段适配
# =========================
def build_image_url(request: Request, image_path: str) -> str:
    if not image_path:
        return ""

    if image_path.startswith("http://") or image_path.startswith("https://"):
        return image_path

    base_url = str(request.base_url).rstrip("/")
    return f"{base_url}/{image_path.lstrip('/')}"


def pick_preset_model(record) -> str:
    """
    从数据库 preset_model 字段读取，若为空则从配置文件读取第一个启用型号作为降级
    """
    if getattr(record, 'preset_model', None):
        return record.preset_model
    # 降级：从配置读取
    try:
        config = load_config()
        if config.get("models"):
            enabled = [m for m in config["models"] if m.get("enabled", True)]
            if enabled:
                return f"{enabled[0].get('name', '')} {enabled[0].get('model', '')}".strip() or "未配置"
    except Exception:
        pass
    return "未配置"


def to_status(record) -> str:
    return "OK" if record.is_qualified else "NG"


def to_position_status(record) -> str:
    """
    从缺陷类型推断位置状态：
    如果 defect_type 包含"偏移"则位置异常，否则正常
    """
    dt = normalize_defect_type(record.defect_type)
    if "偏移" in dt or "offset" in dt.lower():
        return "偏移"
    return "正常"


def format_current_record(record, request: Request):
    return {
        "status": to_status(record),
        "ocrText": getattr(record, 'ocr_text', '') or build_ocr_text(record.energy_level),
        "presetModel": getattr(record, 'preset_model', '') or pick_preset_model(record),
        "isMatch": bool(record.is_qualified),
        "defectType": normalize_defect_type(record.defect_type),
        "positionStatus": getattr(record, 'position_status', '') or to_position_status(record),
        "positionX": int((getattr(record, 'position_x', None) or 0.5) * 100),
        "positionY": int((getattr(record, 'position_y', None) or 0.5) * 100),
        "timestamp": record.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "imageUrl": build_image_url(request, record.image_path),
    }


def format_recent_record(record):
    return {
        "timestamp": record.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "presetModel": getattr(record, 'preset_model', '') or pick_preset_model(record),
        "ocrText": getattr(record, 'ocr_text', '') or build_ocr_text(record.energy_level),
        "status": to_status(record),
        "defectType": normalize_defect_type(record.defect_type),
        "positionStatus": getattr(record, 'position_status', '') or to_position_status(record),
    }


def format_history_record(record, request: Request):
    return {
        "timestamp": record.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "presetModel": getattr(record, 'preset_model', '') or pick_preset_model(record),
        "ocrText": getattr(record, 'ocr_text', '') or build_ocr_text(record.energy_level),
        "status": to_status(record),
        "defectType": normalize_defect_type(record.defect_type),
        "positionStatus": getattr(record, 'position_status', '') or to_position_status(record),
        "imageUrl": build_image_url(request, record.image_path),
    }


def format_statistics_record(record):
    defect_type = normalize_defect_type(record.defect_type)

    return {
        "timestamp": record.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "presetModel": getattr(record, 'preset_model', '') or pick_preset_model(record),
        "status": to_status(record),
        "hasDefect": defect_type != "无",
        "defectType": defect_type,
        "positionStatus": getattr(record, 'position_status', '') or to_position_status(record),
    }


# =========================
# 你原有接口（保留，别动前面的联调）
# =========================
@router.post("/api/v1/detect/upload_image")
async def upload_image(file: UploadFile = File(...)):
    ALLOWED_EXT = {".jpg", ".jpeg", ".png"}
    ext = os.path.splitext(file.filename)[1].lower()

    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"Invalid image format: {ext}")

    filename = generate_filename(file.filename)
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "image_name": filename,
        "image_url": f"/static/uploads/{filename}"
    }


@router.post("/api/v1/detect/record", response_model=schemas.DetectionRecordOut)
def create_record(record: schemas.DetectionRecordCreate, db: Session = Depends(get_db)):
    return crud.create_detection_record(db, record)


@router.get("/api/v1/detect/history", response_model=schemas.HistoryResponse)
def get_legacy_history(
    page: int = 1,
    size: int = 10,
    device_id: str = None,
    batch_id: str = None,
    db: Session = Depends(get_db)
):
    skip = (page - 1) * size
    return crud.get_history_with_stats(db, skip, size, device_id, batch_id)


# =========================
# 前端新要求接口
# =========================

# 1. 获取当前检测结果
@router.get("/api/current", response_model=schemas.CurrentResultResponse)
def get_current(request: Request, db: Session = Depends(get_db)):
    record = crud.get_latest_record(db)
    if not record:
        raise HTTPException(status_code=404, detail="No detection record found")
    return format_current_record(record, request)


# 2. 获取最近10条记录
@router.get("/api/recent", response_model=List[schemas.RecentRecordResponse])
def get_recent(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    records = crud.get_recent_records(db, limit=limit)
    return [format_recent_record(r) for r in records]


# 3. 历史分页
@router.get("/api/history", response_model=schemas.FrontendHistoryResponse)
def get_history(
    request: Request,
    page: int = Query(1, ge=1),
    pageSize: int = Query(25, ge=1, le=100),
    startDate: Optional[date] = Query(None),
    endDate: Optional[date] = Query(None),
    statusFilter: str = Query("ALL"),
    db: Session = Depends(get_db)
):
    total, records = crud.get_frontend_history(
        db=db,
        page=page,
        page_size=pageSize,
        start_date=startDate,
        end_date=endDate,
        status_filter=statusFilter
    )

    return {
        "total": total,
        "records": [format_history_record(r, request) for r in records]
    }


# 4. 获取配置
@router.get("/api/config", response_model=schemas.ConfigResponse)
def get_config():
    return load_config()


# 5. 保存配置
@router.post("/api/config", response_model=schemas.SaveConfigResponse)
def post_config(config: schemas.ConfigResponse):
    save_config(config.model_dump())
    # 不再在此处重置检测器，由前端调用 /api/ml/reload 触发（fix #40）
    return {
        "success": True,
        "message": "配置保存成功"
    }


# 6. 获取统计数据（兼容前端 /api/statistic 和 /api/statistics）
@router.get("/api/statistic", response_model=List[schemas.StatisticsItemResponse])
@router.get("/api/statistics", response_model=List[schemas.StatisticsItemResponse])
def get_statistics(
    startDate: Optional[date] = Query(None),
    endDate: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    records = crud.get_statistics_records(
        db=db,
        start_date=startDate,
        end_date=endDate
    )
    return [format_statistics_record(r) for r in records]