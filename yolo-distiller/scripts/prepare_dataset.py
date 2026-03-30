#!/usr/bin/env python3
"""
数据集准备脚本
功能：
1. 将原始2类标签（0=正常, 1=偏移）扩展为5类标签
   0: label_normal   (正常标签)
   1: label_offset   (标签偏移)
   2: label_scratch  (标签划痕/破损)
   3: label_stain    (标签污渍)
   4: label_wrinkle  (标签褶皱)
2. 修复Windows反斜杠路径
3. 去除重复条目
4. 按8:2比例划分train/val
5. 重命名文件去除空格（YOLO兼容）
"""

import os
import re
import shutil
import random
from pathlib import Path

# ============ 配置 ============
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SRC_DIR = PROJECT_ROOT / "datasets_new_aug" / "datasets_new_aug_1"
DST_DIR = PROJECT_ROOT / "datasets" / "energy_label"

TRAIN_RATIO = 0.8
RANDOM_SEED = 42

# 根据文件名后缀判断缺陷类型
# _orig / _trad* → 保持原始类别（正常=0）
# _offset* → 1 (偏移)
# _scratch* → 2 (划痕)
# _stain* → 3 (污渍)
# _wrinkle* → 4 (褶皱)
DEFECT_MAP = {
    "orig": None,       # 保持原始类别 0
    "trad": None,       # 传统增强，保持原始类别 0
    "offset": 1,
    "scratch": 2,
    "stain": 3,
    "wrinkle": 4,
}

CLASS_NAMES = {
    0: "label_normal",
    1: "label_offset",
    2: "label_scratch",
    3: "label_stain",
    4: "label_wrinkle",
}


def sanitize_filename(name: str) -> str:
    """去除文件名中的空格和括号，替换为下划线格式"""
    # "image (1)_orig.jpg" → "image_1_orig.jpg"
    name = name.replace(" (", "_").replace(")", "")
    name = name.replace(" ", "_")
    return name


def detect_defect_type(filename: str):
    """
    从文件名推断缺陷类型
    返回新的class_id，如果是orig/trad则返回None（保持原始class）
    """
    stem = Path(filename).stem  # e.g. "image (1)_scratch_0"

    # 提取最后的类型标识
    # 匹配模式: image (N)_<type>_<idx> 或 image (N)_<type><idx>
    for key in ["offset", "scratch", "stain", "wrinkle", "trad", "orig"]:
        if f"_{key}" in stem:
            return DEFECT_MAP[key]

    # 默认保持原始类别
    return None


def process_label_file(src_label: Path, new_class_id):
    """
    读取标签文件，根据需要替换class_id
    返回处理后的标签行列表
    """
    lines = []
    if not src_label.exists():
        return lines

    with open(src_label, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 5:
                continue

            # 原始class_id可能是浮点数如"0.0"，统一转为int
            orig_cls = int(float(parts[0]))

            if new_class_id is not None:
                # 替换class_id
                parts[0] = str(new_class_id)
            else:
                # orig/trad: 保持原始class（转为整数格式）
                parts[0] = str(orig_cls)

            lines.append(" ".join(parts))

    return lines


def main():
    random.seed(RANDOM_SEED)

    src_images = SRC_DIR / "images"
    src_labels = SRC_DIR / "labels"

    if not src_images.exists():
        print(f"错误: 源图片目录不存在: {src_images}")
        return

    # 创建目标目录
    for split in ["train", "val"]:
        (DST_DIR / "images" / split).mkdir(parents=True, exist_ok=True)
        (DST_DIR / "labels" / split).mkdir(parents=True, exist_ok=True)

    # 收集所有图片
    image_files = sorted([
        f for f in src_images.iterdir()
        if f.suffix.lower() in {".jpg", ".jpeg", ".png"}
    ])

    print(f"找到 {len(image_files)} 张图片")

    # 去重（train.txt中有重复条目）
    seen = set()
    unique_files = []
    for f in image_files:
        if f.name not in seen:
            seen.add(f.name)
            unique_files.append(f)

    print(f"去重后 {len(unique_files)} 张图片")

    # 按原始图片编号分组，确保同一张原图的所有增强版本在同一个split中
    # 避免数据泄露
    groups = {}
    for f in unique_files:
        # 提取图片编号: "image (1)_orig.jpg" → "1"
        match = re.search(r'image\s*\((\d+)\)', f.name)
        if match:
            img_id = match.group(1)
        else:
            img_id = f.stem
        if img_id not in groups:
            groups[img_id] = []
        groups[img_id].append(f)

    # 按组划分train/val
    group_ids = sorted(groups.keys(), key=lambda x: int(x) if x.isdigit() else x)
    random.shuffle(group_ids)

    split_idx = int(len(group_ids) * TRAIN_RATIO)
    train_ids = set(group_ids[:split_idx])
    val_ids = set(group_ids[split_idx:])

    print(f"训练集: {len(train_ids)} 组, 验证集: {len(val_ids)} 组")

    stats = {cls_name: 0 for cls_name in CLASS_NAMES.values()}
    train_count = 0
    val_count = 0

    for img_id, files in groups.items():
        split = "train" if img_id in train_ids else "val"

        for src_img in files:
            # 确定新的class_id
            new_class_id = detect_defect_type(src_img.name)

            # 对应的标签文件
            label_name = src_img.stem + ".txt"
            src_label = src_labels / label_name

            # 处理标签
            label_lines = process_label_file(src_label, new_class_id)
            if not label_lines:
                # 没有标签的图片跳过
                continue

            # 生成新文件名（去除空格）
            new_img_name = sanitize_filename(src_img.name)
            new_label_name = sanitize_filename(label_name)

            # 复制图片
            dst_img = DST_DIR / "images" / split / new_img_name
            shutil.copy2(src_img, dst_img)

            # 写入新标签
            dst_label = DST_DIR / "labels" / split / new_label_name
            with open(dst_label, "w") as f:
                f.write("\n".join(label_lines) + "\n")

            # 统计
            for line in label_lines:
                cls_id = int(float(line.split()[0]))
                cls_name = CLASS_NAMES.get(cls_id, f"unknown_{cls_id}")
                stats[cls_name] = stats.get(cls_name, 0) + 1

            if split == "train":
                train_count += 1
            else:
                val_count += 1

    print(f"\n数据集准备完成:")
    print(f"  训练集: {train_count} 张")
    print(f"  验证集: {val_count} 张")
    print(f"  输出目录: {DST_DIR}")
    print(f"\n类别统计:")
    for cls_name, count in stats.items():
        print(f"  {cls_name}: {count}")


if __name__ == "__main__":
    main()