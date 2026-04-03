#!/usr/bin/env python3
"""
合并两个数据集：
1. 修正大数据集(datasets_new_aug)的标签（根据文件名推断类别）
2. 与小数据集(energy_label)合并
3. 重新80/20分割train/val
4. 更新yaml配置

类别定义（5类）：
  0: label_normal    - 正常能效标签
  1: label_offset    - 标签位置偏移
  2: label_scratch   - 标签划痕/破损
  3: label_stain     - 标签污渍
  4: label_wrinkle   - 标签褶皱
"""
import os
import shutil
import random
from pathlib import Path

random.seed(42)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SMALL_DS = PROJECT_ROOT / "datasets" / "energy_label"
BIG_DS = PROJECT_ROOT / "datasets_new_aug" / "datasets_new_aug_1"
OUTPUT = PROJECT_ROOT / "datasets" / "energy_label_merged"

# 文件名关键词 → 类别ID
FILENAME_TO_CLASS = {
    "_offset": 1,
    "_scratch": 2,
    "_stain": 3,
    "_wrinkle": 4,
}


def infer_class_from_filename(filename):
    """根据文件名推断类别，默认为0(normal)"""
    fname_lower = filename.lower()
    for keyword, cls_id in FILENAME_TO_CLASS.items():
        if keyword in fname_lower:
            return cls_id
    return 0  # orig, trad等都算normal


def fix_label_file(src_label, dst_label, new_class_id):
    """修正标签文件的类别ID"""
    lines = []
    with open(src_label, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 5:
                # 替换类别ID，保留bbox
                parts[0] = str(new_class_id)
                lines.append(' '.join(parts))
    with open(dst_label, 'w') as f:
        f.write('\n'.join(lines) + '\n' if lines else '')


def collect_small_dataset():
    """收集小数据集的所有图片和标签"""
    pairs = []
    for split in ['train', 'val']:
        img_dir = SMALL_DS / "images" / split
        lbl_dir = SMALL_DS / "labels" / split
        if not img_dir.exists():
            continue
        for img_file in sorted(img_dir.glob("*")):
            if img_file.suffix.lower() not in {'.jpg', '.jpeg', '.png'}:
                continue
            lbl_file = lbl_dir / (img_file.stem + '.txt')
            if lbl_file.exists():
                pairs.append((img_file, lbl_file, None))  # None = 不需要修正
    return pairs


def collect_big_dataset():
    """收集大数据集，根据文件名修正类别"""
    pairs = []
    img_dir = BIG_DS / "images"
    lbl_dir = BIG_DS / "labels"
    if not img_dir.exists():
        return pairs
    for img_file in sorted(img_dir.glob("*")):
        if img_file.suffix.lower() not in {'.jpg', '.jpeg', '.png'}:
            continue
        lbl_file = lbl_dir / (img_file.stem + '.txt')
        if lbl_file.exists():
            new_cls = infer_class_from_filename(img_file.name)
            pairs.append((img_file, lbl_file, new_cls))
    return pairs


def main():
    print("=" * 60)
    print("合并数据集")
    print("=" * 60)

    # 收集
    small_pairs = collect_small_dataset()
    big_pairs = collect_big_dataset()
    print(f"小数据集: {len(small_pairs)} 张")
    print(f"大数据集: {len(big_pairs)} 张")

    # 统计大数据集修正后的类别分布
    big_class_dist = {}
    for _, _, cls_id in big_pairs:
        big_class_dist[cls_id] = big_class_dist.get(cls_id, 0) + 1
    print(f"大数据集修正后类别分布: {big_class_dist}")

    all_pairs = small_pairs + big_pairs
    print(f"合并总计: {len(all_pairs)} 张")

    # 打乱并分割 80/20
    random.shuffle(all_pairs)
    split_idx = int(len(all_pairs) * 0.8)
    train_pairs = all_pairs[:split_idx]
    val_pairs = all_pairs[split_idx:]
    print(f"Train: {len(train_pairs)}, Val: {len(val_pairs)}")

    # 创建输出目录
    for split in ['train', 'val']:
        (OUTPUT / "images" / split).mkdir(parents=True, exist_ok=True)
        (OUTPUT / "labels" / split).mkdir(parents=True, exist_ok=True)

    # 复制文件
    name_counter = {}

    def unique_name(stem, suffix):
        """处理文件名冲突"""
        key = stem + suffix
        if key not in name_counter:
            name_counter[key] = 0
            return stem + suffix
        name_counter[key] += 1
        return f"{stem}_{name_counter[key]}{suffix}"

    for split, pairs in [('train', train_pairs), ('val', val_pairs)]:
        for img_file, lbl_file, fix_cls in pairs:
            # 生成唯一文件名（避免两个数据集文件名冲突）
            new_name = unique_name(img_file.stem, img_file.suffix)
            new_lbl_name = unique_name(img_file.stem, '.txt')
            # 这里stem可能已经被修改了，用同一个base
            base = new_name.rsplit('.', 1)[0]

            dst_img = OUTPUT / "images" / split / new_name
            dst_lbl = OUTPUT / "labels" / split / (base + '.txt')

            shutil.copy2(img_file, dst_img)

            if fix_cls is not None:
                fix_label_file(lbl_file, dst_lbl, fix_cls)
            else:
                shutil.copy2(lbl_file, dst_lbl)

    # 统计最终类别分布
    final_dist = {}
    for split in ['train', 'val']:
        lbl_dir = OUTPUT / "labels" / split
        for lbl_file in lbl_dir.glob("*.txt"):
            with open(lbl_file) as f:
                for line in f:
                    parts = line.strip().split()
                    if parts:
                        cls = parts[0]
                        final_dist[cls] = final_dist.get(cls, 0) + 1

    print(f"\n最终类别分布: {dict(sorted(final_dist.items()))}")
    print(f"Train images: {len(list((OUTPUT / 'images' / 'train').glob('*')))}")
    print(f"Val images: {len(list((OUTPUT / 'images' / 'val').glob('*')))}")
    print(f"\n输出目录: {OUTPUT}")


if __name__ == "__main__":
    main()