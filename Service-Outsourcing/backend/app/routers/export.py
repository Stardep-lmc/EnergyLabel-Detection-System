"""
数据导出路由 - 支持CSV格式导出检测记录
"""
import io
import csv
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, case, Integer
from sqlalchemy.orm import Session

from ..database import get_db
from .. import crud

router = APIRouter()


@router.get("/api/export/csv")
def export_csv(
    startDate: Optional[date] = Query(None),
    endDate: Optional[date] = Query(None),
    statusFilter: str = Query("ALL"),
    db: Session = Depends(get_db)
):
    """导出检测记录为CSV文件"""
    query = crud.build_filtered_query(db, startDate, endDate, statusFilter)
    query = query.order_by(crud.models.DetectionRecord.created_at.desc())

    def generate():
        # BOM + 表头（fix #43: 流式输出，不全量加载到内存）
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "序号", "设备ID", "批次ID", "能效等级", "缺陷类型",
            "置信度", "是否合格", "图片路径", "检测时间"
        ])
        yield '\ufeff' + buf.getvalue()

        for i, r in enumerate(query.yield_per(500), 1):
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow([
                i,
                r.device_id,
                r.batch_id,
                r.energy_level,
                r.defect_type or "无",
                f"{r.confidence:.4f}",
                "合格" if r.is_qualified else "不合格",
                r.image_path,
                r.created_at.strftime("%Y-%m-%d %H:%M:%S")
            ])
            yield buf.getvalue()

    return StreamingResponse(
        generate(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=detection_records.csv"
        }
    )


@router.get("/api/export/summary")
def export_summary(
    startDate: Optional[date] = Query(None),
    endDate: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    """导出统计摘要 — 使用 SQL 聚合，避免全量加载到内存"""
    query = crud.build_filtered_query(db, startDate, endDate, "ALL")

    # 总量 & 合格数 — SQL 聚合
    stats = query.with_entities(
        func.count().label("total"),
        func.sum(case(
            (crud.models.DetectionRecord.is_qualified == True, 1),
            else_=0
        ).cast(Integer)).label("pass_count"),
    ).first()
    total = stats.total or 0
    pass_count = stats.pass_count or 0
    fail_count = total - pass_count

    # 缺陷类型分布 — SQL GROUP BY
    defect_rows = (
        query.with_entities(
            crud.models.DetectionRecord.defect_type,
            func.count().label("cnt"),
        )
        .group_by(crud.models.DetectionRecord.defect_type)
        .all()
    )
    defect_stats = {(r.defect_type or "无"): r.cnt for r in defect_rows}

    # 设备统计 — SQL GROUP BY
    device_rows = (
        query.with_entities(
            crud.models.DetectionRecord.device_id,
            func.count().label("total"),
            func.sum(case(
                (crud.models.DetectionRecord.is_qualified == True, 1),
                else_=0
            ).cast(Integer)).label("pass_cnt"),
        )
        .group_by(crud.models.DetectionRecord.device_id)
        .all()
    )
    device_stats = {
        r.device_id: {
            "total": r.total,
            "pass": r.pass_cnt,
            "pass_rate": round(r.pass_cnt / r.total, 4) if r.total else 0,
        }
        for r in device_rows
    }

    return {
        "total": total,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "pass_rate": round(pass_count / total, 4) if total else 0,
        "defect_distribution": defect_stats,
        "device_stats": device_stats,
    }
