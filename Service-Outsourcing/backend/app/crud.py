from __future__ import annotations
from datetime import datetime, date, time, timedelta, timezone
from typing import Optional, Dict, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, case, Integer

from . import models, schemas
from .utils import judge_qualified


def create_detection_record(db: Session, record: schemas.DetectionRecordCreate):
    # ML路径直接传入推理判定结果，普通接口留None走judge_qualified
    if record.is_qualified is not None:
        qualified = record.is_qualified
    else:
        qualified = judge_qualified(
            record.energy_level,
            defect_type=record.defect_type,
            position_status=record.position_status,
        )

    db_record = models.DetectionRecord(
        device_id=record.device_id,
        batch_id=record.batch_id,
        image_path=record.image_path,
        energy_level=record.energy_level,
        defect_type=record.defect_type,
        confidence=record.confidence,
        is_qualified=qualified,
        preset_model=record.preset_model,
        position_status=record.position_status,
        position_x=record.position_x,
        position_y=record.position_y,
        ocr_text=record.ocr_text,
    )
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record


# =========================
# 原有接口：历史 + 统计
# =========================
def get_history_with_stats(db: Session, skip=0, limit=100, device_id=None, batch_id=None):
    query = db.query(models.DetectionRecord)

    if device_id:
        query = query.filter(models.DetectionRecord.device_id == device_id)
    if batch_id:
        query = query.filter(models.DetectionRecord.batch_id == batch_id)

    total = query.count()
    items = query.order_by(models.DetectionRecord.created_at.desc()).offset(skip).limit(limit).all()

    # Use SQL aggregation instead of loading all records into memory
    from sqlalchemy import func, Integer
    stats_query = query.with_entities(
        func.count().label('total'),
        func.sum(func.cast(models.DetectionRecord.is_qualified == False, Integer)).label('fail_count')
    ).first()
    total_scanned = stats_query.total or 0
    fail_count = stats_query.fail_count or 0
    pass_count = total_scanned - fail_count
    pass_rate = round(pass_count / total_scanned, 3) if total_scanned else 0.0

    return {
        "stats": {
            "total_scanned": total_scanned,
            "fail_count": fail_count,
            "pass_count": pass_count,
            "pass_rate": pass_rate
        },
        "records": items,
        "total": total
    }


# =========================
# 前端兼容接口：查询函数
# =========================
def get_latest_record(db: Session):
    return db.query(models.DetectionRecord).order_by(models.DetectionRecord.created_at.desc()).first()


def get_recent_records(db: Session, limit: int = 10):
    return (
        db.query(models.DetectionRecord)
        .order_by(models.DetectionRecord.created_at.desc())
        .limit(limit)
        .all()
    )


def build_filtered_query(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status_filter: str = "ALL"
):
    query = db.query(models.DetectionRecord)

    if start_date:
        # fix #39: 使用 aware datetime 与 UTC 存储保持一致
        start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        query = query.filter(models.DetectionRecord.created_at >= start_dt)

    if end_date:
        end_dt = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
        query = query.filter(models.DetectionRecord.created_at < end_dt)

    status_filter = (status_filter or "ALL").upper()

    if status_filter == "OK":
        query = query.filter(models.DetectionRecord.is_qualified.is_(True))
    elif status_filter == "NG":
        query = query.filter(models.DetectionRecord.is_qualified.is_(False))

    return query


def get_frontend_history(
    db: Session,
    page: int = 1,
    page_size: int = 25,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status_filter: str = "ALL"
):
    query = build_filtered_query(db, start_date, end_date, status_filter)

    total = query.count()
    records = (
        query.order_by(models.DetectionRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return total, records


def get_statistics_records(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """返回原始记录（兼容现有前端聚合逻辑）"""
    query = build_filtered_query(db, start_date, end_date, "ALL")
    return (
        query.order_by(models.DetectionRecord.created_at.asc())
        .all()
    )


def get_aggregated_statistics(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    fix #44: SQL 聚合统计，避免全量加载 ORM 对象。
    返回按日期分组的趋势、缺陷分布、型号合格率。
    """
    query = build_filtered_query(db, start_date, end_date, "ALL")
    M = models.DetectionRecord

    # 按日期分组的趋势
    daily = (
        query.with_entities(
            func.date(M.created_at).label("day"),
            func.count().label("total"),
            func.sum(case(
                (M.defect_type.notin_(["无", "", None]), 1),
                else_=0
            ).cast(Integer)).label("defects"),
        )
        .group_by(func.date(M.created_at))
        .order_by(func.date(M.created_at))
        .all()
    )

    # 缺陷类型分布
    defect_rows = (
        query.with_entities(M.defect_type, func.count().label("cnt"))
        .group_by(M.defect_type)
        .all()
    )

    # 型号合格率
    model_rows = (
        query.with_entities(
            M.preset_model,
            func.count().label("total"),
            func.sum(case((M.is_qualified == True, 1), else_=0).cast(Integer)).label("ok"),
        )
        .group_by(M.preset_model)
        .all()
    )

    return {
        "trend": [{"day": str(r.day), "total": r.total, "defects": r.defects} for r in daily],
        "defect_distribution": {(r.defect_type or "无"): r.cnt for r in defect_rows},
        "model_rates": [
            {"model": r.preset_model or "未知", "total": r.total, "ok": r.ok,
             "rate": round(r.ok / r.total * 100) if r.total else 0}
            for r in model_rows
        ],
    }
