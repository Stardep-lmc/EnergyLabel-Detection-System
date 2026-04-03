from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from datetime import datetime, timezone
from .database import Base

class DetectionRecord(Base):
    __tablename__ = "detection_records"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(64), nullable=False, index=True)
    batch_id = Column(String(64), nullable=False, index=True)
    image_path = Column(String(255), nullable=False)
    energy_level = Column(Float, nullable=False)
    defect_type = Column(String(128), nullable=False)
    confidence = Column(Float, nullable=False)
    is_qualified = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    # 扩展字段：持久化 ML 检测产生的信息
    preset_model = Column(String(128), nullable=True, default="")
    position_status = Column(String(32), nullable=True, default="正常")
    position_x = Column(Float, nullable=True, default=0.5)
    position_y = Column(Float, nullable=True, default=0.5)
    ocr_text = Column(String(255), nullable=True, default="")
