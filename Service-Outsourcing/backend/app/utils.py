import uuid
import os
import json
import tempfile
from copy import deepcopy

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config_store.json")

DEFAULT_CONFIG = {
    "models": [
        {
            "name": "冰箱",
            "model": "BCD-520W",
            "standardLabel": "A++",
            "enabled": True
        }
    ],
    "positionTolerance": 10,
    "sensitivity": "中",
    "lightCompensation": 0,
    "camera": {
        "exposure": 0,
        "resolution": "1280x720"
    }
}


def generate_filename(filename: str) -> str:
    ext = os.path.splitext(filename)[1]
    return f"{uuid.uuid4().hex}{ext}"


def get_max_energy_level() -> float:
    """从配置获取允许的最大能效等级数值，默认3.0（即1-3级合格）"""
    try:
        config = load_config()
        grade_map = {"A++": 1.0, "A+": 1.5, "A": 2.0, "B": 3.0, "C": 4.0}
        models = config.get("models", [])
        enabled = [m for m in models if m.get("enabled", True)]
        if enabled:
            grade = enabled[0].get("standardLabel", "A")
            return grade_map.get(grade, 3.0)
    except Exception:
        pass
    return 3.0


def judge_qualified(energy_level: float, defect_type: str = "无", position_status: str = "正常") -> bool:
    """
    综合判定是否合格：
    1. 能效等级不超过配置中标准能效等级对应的阈值
    2. 无缺陷
    3. 位置正常
    """
    max_level = get_max_energy_level()
    energy_ok = energy_level <= max_level
    defect_ok = defect_type in (None, "", "无", "none", "normal", "ok", "正常")
    position_ok = position_status in (None, "", "正常", "normal")
    return energy_ok and defect_ok and position_ok


def normalize_defect_type(defect_type: str) -> str:
    if defect_type is None:
        return "无"

    value = str(defect_type).strip().lower()
    if value in {"", "none", "normal", "ok", "无", "正常"}:
        return "无"

    return defect_type


def build_ocr_text(energy_level: float) -> str:
    """
    临时兼容：
    现在没有真实 OCR 文本，就先用 energy_level 映射成 "x级能效"
    后续 ML 接入后再换成真实 OCR 结果
    """
    try:
        val = float(energy_level)
        if val.is_integer():
            return f"{int(val)}级能效"
        return f"{val}级能效"
    except Exception:
        return "未知"


def load_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return deepcopy(DEFAULT_CONFIG)

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(data: dict):
    """原子写入：先写临时文件，再 rename，避免并发写入导致文件损坏"""
    dir_name = os.path.dirname(CONFIG_FILE)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, CONFIG_FILE)
    except Exception:
        os.unlink(tmp_path)
        raise
