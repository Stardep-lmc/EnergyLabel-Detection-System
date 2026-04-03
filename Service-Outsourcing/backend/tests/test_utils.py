"""单元测试：工具函数"""
import sys
import os

# 确保能导入 app 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.utils import judge_qualified, normalize_defect_type, build_ocr_text


def test_judge_qualified_normal():
    assert judge_qualified(1.0, "无", "正常") is True


def test_judge_qualified_defect():
    assert judge_qualified(1.0, "划痕", "正常") is False


def test_judge_qualified_position():
    assert judge_qualified(1.0, "无", "偏移") is False


def test_normalize_defect_type_none():
    assert normalize_defect_type(None) == "无"


def test_normalize_defect_type_none_str():
    assert normalize_defect_type("none") == "无"


def test_normalize_defect_type_normal():
    assert normalize_defect_type("划痕") == "划痕"


def test_build_ocr_text_int():
    assert build_ocr_text(1.0) == "1级能效"


def test_build_ocr_text_float():
    assert build_ocr_text(2.5) == "2.5级能效"