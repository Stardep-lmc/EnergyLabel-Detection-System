#!/usr/bin/env python3
"""
OCR服务模块
使用PaddleOCR识别能效标签上的文字信息

功能：
1. 识别能效等级（1-5级）
2. 识别产品型号
3. 识别能效标签上的关键数据（年耗电量、容积等）
4. 结构化输出OCR结果
"""
import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

logger = logging.getLogger("ocr_service")

# 尝试导入PaddleOCR，不可用时降级
_paddle_available = False
_ocr_instance = None

try:
    from paddleocr import PaddleOCR
    _paddle_available = True
except ImportError:
    logger.warning("PaddleOCR未安装，OCR功能将使用降级模式。安装: pip install paddleocr paddlepaddle")


@dataclass
class OCRResult:
    """OCR识别结果"""
    raw_texts: List[str] = field(default_factory=list)
    energy_level: Optional[str] = None       # 能效等级: "1级", "2级", ...
    energy_grade: Optional[str] = None       # 能效标识: "A++", "A+", "A", "B", "C"
    product_model: Optional[str] = None      # 产品型号
    annual_consumption: Optional[str] = None  # 年耗电量
    volume: Optional[str] = None             # 容积
    brand: Optional[str] = None              # 品牌
    confidence: float = 0.0


def get_ocr():
    """懒加载PaddleOCR实例"""
    global _ocr_instance
    if _ocr_instance is not None:
        return _ocr_instance

    if not _paddle_available:
        return None

    try:
        _ocr_instance = PaddleOCR(
            use_angle_cls=True,
            lang='ch',
            show_log=False,
            use_gpu=False,
        )
        logger.info("PaddleOCR初始化成功")
        return _ocr_instance
    except Exception as e:
        logger.error(f"PaddleOCR初始化失败: {e}")
        return None


# 能效等级匹配模式
ENERGY_LEVEL_PATTERNS = [
    (r'[1一壹]\s*级', '1级'),
    (r'[2二贰]\s*级', '2级'),
    (r'[3三叁]\s*级', '3级'),
    (r'[4四肆]\s*级', '4级'),
    (r'[5五伍]\s*级', '5级'),
]

ENERGY_GRADE_PATTERNS = [
    (r'A\+\+', 'A++'),
    (r'A\+', 'A+'),
    (r'(?<!\+)A(?!\+)', 'A'),
    (r'(?<![A-Z])B(?![A-Z])', 'B'),
    (r'(?<![A-Z])C(?![A-Z])', 'C'),
]

# 产品型号模式（常见家电型号格式）
MODEL_PATTERNS = [
    r'[A-Z]{2,4}[-/]?\d{3,4}[A-Z]?\w*',  # BCD-520W, KFR-35GW
    r'\d{2,3}[A-Z]{1,3}\d{2,4}',           # 50T680
]

# 年耗电量
CONSUMPTION_PATTERN = r'(\d+\.?\d*)\s*[kK][wW][hH·•]?/?[年年]?'
CONSUMPTION_PATTERN2 = r'年?\s*耗电[量]?\s*[:：]?\s*(\d+\.?\d*)'

# 容积
VOLUME_PATTERN = r'(\d+\.?\d*)\s*[升LlⅬ]'
VOLUME_PATTERN2 = r'容积\s*[:：]?\s*(\d+\.?\d*)'


def extract_energy_info(texts: List[str]) -> OCRResult:
    """从OCR文本中提取能效标签信息"""
    result = OCRResult(raw_texts=texts)
    full_text = ' '.join(texts)

    # 提取能效等级
    for pattern, level in ENERGY_LEVEL_PATTERNS:
        if re.search(pattern, full_text):
            result.energy_level = level
            break

    # 提取能效标识
    for pattern, grade in ENERGY_GRADE_PATTERNS:
        if re.search(pattern, full_text):
            result.energy_grade = grade
            break

    # 提取产品型号
    for pattern in MODEL_PATTERNS:
        match = re.search(pattern, full_text)
        if match:
            result.product_model = match.group(0)
            break

    # 提取年耗电量
    match = re.search(CONSUMPTION_PATTERN, full_text)
    if not match:
        match = re.search(CONSUMPTION_PATTERN2, full_text)
    if match:
        result.annual_consumption = f"{match.group(1)} kWh/年"

    # 提取容积
    match = re.search(VOLUME_PATTERN, full_text)
    if not match:
        match = re.search(VOLUME_PATTERN2, full_text)
    if match:
        result.volume = f"{match.group(1)} L"

    # 品牌识别（常见家电品牌）
    brands = ['海尔', 'Haier', '美的', 'Midea', '格力', 'Gree', '海信', 'Hisense',
              '西门子', 'Siemens', '松下', 'Panasonic', 'TCL', '容声', 'Ronshen',
              '美菱', 'Meiling', '奥克斯', 'AUX', '长虹', 'Changhong']
    for brand in brands:
        if brand.lower() in full_text.lower():
            result.brand = brand
            break

    return result


def recognize(image_path: str) -> OCRResult:
    """
    对图片进行OCR识别，提取能效标签信息

    Args:
        image_path: 图片路径

    Returns:
        OCRResult: 结构化的OCR结果
    """
    ocr = get_ocr()

    if ocr is None:
        # 降级模式：返回空结果
        logger.warning("OCR不可用，返回空结果")
        return OCRResult(confidence=0.0)

    try:
        results = ocr.ocr(image_path, cls=True)

        if not results or not results[0]:
            return OCRResult(confidence=0.0)

        texts = []
        total_conf = 0.0
        count = 0

        for line in results[0]:
            if line and len(line) >= 2:
                text = line[1][0]
                conf = line[1][1]
                texts.append(text)
                total_conf += conf
                count += 1

        avg_conf = total_conf / count if count > 0 else 0.0

        result = extract_energy_info(texts)
        result.confidence = round(avg_conf, 4)

        logger.info(f"OCR识别完成: {len(texts)}个文本块, 平均置信度={avg_conf:.3f}")
        if result.energy_level:
            logger.info(f"  能效等级: {result.energy_level}")
        if result.energy_grade:
            logger.info(f"  能效标识: {result.energy_grade}")
        if result.product_model:
            logger.info(f"  产品型号: {result.product_model}")

        return result

    except Exception as e:
        logger.error(f"OCR识别失败: {e}")
        return OCRResult(confidence=0.0)


def is_available() -> bool:
    """检查OCR服务是否可用"""
    return _paddle_available


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python ocr_service.py <图片路径>")
        sys.exit(1)

    result = recognize(sys.argv[1])
    print(f"原始文本: {result.raw_texts}")
    print(f"能效等级: {result.energy_level}")
    print(f"能效标识: {result.energy_grade}")
    print(f"产品型号: {result.product_model}")
    print(f"年耗电量: {result.annual_consumption}")
    print(f"容积: {result.volume}")
    print(f"品牌: {result.brand}")
    print(f"置信度: {result.confidence}")