#!/usr/bin/env python3
"""
合成能效标签训练数据生成器

在没有真实标注数据的情况下，生成模拟的能效标签图片用于训练。
生成的图片包含：
- 不同能效等级的标签（1-5级）
- 不同缺陷类型（正常/偏移/划痕/污渍/褶皱）
- 不同位置和角度
- YOLO格式的标注文件

用法：
    python generate_synthetic_data.py --output ../datasets/energy_label --num 500
"""
import os
import random
import argparse
import math
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("需要安装Pillow: pip install Pillow")

import numpy as np


# 类别定义（与inference_service.py一致）
CLASSES = {
    0: "label_normal",
    1: "label_offset",
    2: "label_scratch",
    3: "label_stain",
    4: "label_wrinkle",
}

# 能效等级颜色
ENERGY_COLORS = {
    1: (0, 150, 0),      # 深绿
    2: (100, 180, 0),     # 浅绿
    3: (220, 200, 0),     # 黄色
    4: (230, 130, 0),     # 橙色
    5: (220, 30, 0),      # 红色
}

# 能效等级对应的标识
ENERGY_GRADES = {1: 'A++', 2: 'A+', 3: 'A', 4: 'B', 5: 'C'}


def create_energy_label(width=200, height=280, energy_level=1):
    """创建一个模拟的能效标签图片"""
    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # 标题区域
    draw.rectangle([0, 0, width, 35], fill=(0, 80, 160))
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        font_text = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    except (OSError, IOError):
        font_title = ImageFont.load_default()
        font_text = font_title
        font_big = font_title

    draw.text((10, 8), "ENERGY LABEL", fill=(255, 255, 255), font=font_title)

    # 能效等级条
    bar_y = 45
    for level in range(1, 6):
        color = ENERGY_COLORS[level]
        bar_width = width - 40 - (level - 1) * 20
        draw.rectangle([20, bar_y, 20 + bar_width, bar_y + 18], fill=color)
        grade = ENERGY_GRADES[level]
        draw.text((25, bar_y + 2), grade, fill=(255, 255, 255), font=font_text)

        # 当前等级指示箭头
        if level == energy_level:
            arrow_x = 20 + bar_width + 5
            draw.polygon([(arrow_x, bar_y + 3), (arrow_x + 15, bar_y + 9), (arrow_x, bar_y + 15)],
                         fill=color)

        bar_y += 22

    # 大数字显示能效等级
    big_y = bar_y + 10
    draw.text((width // 2 - 20, big_y), str(energy_level), fill=ENERGY_COLORS[energy_level], font=font_big)
    draw.text((width // 2 + 10, big_y + 8), "级", fill=(50, 50, 50), font=font_text)

    # 参数区域
    param_y = big_y + 50
    params = [
        ("年耗电量", f"{random.randint(200, 600)} kWh"),
        ("容积", f"{random.randint(100, 600)} L"),
        ("噪声", f"{random.randint(30, 50)} dB"),
    ]
    for label, value in params:
        draw.text((20, param_y), label, fill=(100, 100, 100), font=font_text)
        draw.text((width - 80, param_y), value, fill=(30, 30, 30), font=font_text)
        param_y += 18

    # 底部型号
    draw.line([(10, height - 30), (width - 10, height - 30)], fill=(200, 200, 200))
    model_str = f"BCD-{random.randint(100, 999)}W"
    draw.text((20, height - 25), model_str, fill=(120, 120, 120), font=font_text)

    return img


def apply_defect(img, defect_type):
    """对标签图片应用缺陷效果"""
    if defect_type == 0:  # normal
        return img

    w, h = img.size
    draw = ImageDraw.Draw(img)

    if defect_type == 2:  # scratch - 划痕
        for _ in range(random.randint(1, 3)):
            x1 = random.randint(0, w)
            y1 = random.randint(0, h)
            x2 = x1 + random.randint(-60, 60)
            y2 = y1 + random.randint(-60, 60)
            draw.line([(x1, y1), (x2, y2)], fill=(80, 80, 80), width=random.randint(1, 3))

    elif defect_type == 3:  # stain - 污渍
        for _ in range(random.randint(1, 4)):
            cx = random.randint(20, w - 20)
            cy = random.randint(20, h - 20)
            r = random.randint(8, 25)
            color = (
                random.randint(100, 180),
                random.randint(80, 150),
                random.randint(50, 120),
            )
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)

    elif defect_type == 4:  # wrinkle - 褶皱
        # 模拟褶皱：添加波浪形变形效果
        arr = np.array(img)
        for y in range(h):
            shift = int(3 * math.sin(y / 8.0))
            arr[y] = np.roll(arr[y], shift, axis=0)
        img = Image.fromarray(arr)

    return img


def generate_sample(img_size=640, defect_prob=0.3, offset_prob=0.15):
    """
    生成一个训练样本：背景 + 能效标签 + 标注

    Returns:
        img: PIL Image
        annotations: list of (class_id, cx, cy, w, h) 归一化坐标
    """
    # 背景：模拟家电表面
    bg_color = (
        random.randint(200, 245),
        random.randint(200, 245),
        random.randint(200, 245),
    )
    img = Image.new('RGB', (img_size, img_size), bg_color)

    # 添加一些背景纹理
    draw = ImageDraw.Draw(img)
    for _ in range(random.randint(0, 5)):
        x = random.randint(0, img_size)
        y = random.randint(0, img_size)
        r = random.randint(50, 200)
        shade = random.randint(-15, 15)
        c = tuple(max(0, min(255, bg_color[i] + shade)) for i in range(3))
        draw.ellipse([x - r, y - r, x + r, y + r], fill=c)

    # 决定缺陷类型
    rand = random.random()
    if rand < offset_prob:
        defect_class = 1  # offset
    elif rand < offset_prob + defect_prob:
        defect_class = random.choice([2, 3, 4])  # scratch/stain/wrinkle
    else:
        defect_class = 0  # normal

    # 创建能效标签
    energy_level = random.randint(1, 5)
    label_w = random.randint(140, 220)
    label_h = int(label_w * random.uniform(1.2, 1.5))
    label_img = create_energy_label(label_w, label_h, energy_level)

    # 应用缺陷
    if defect_class in (2, 3, 4):
        label_img = apply_defect(label_img, defect_class)

    # 随机旋转（小角度）
    angle = random.uniform(-8, 8)
    label_img = label_img.rotate(angle, expand=True, fillcolor=bg_color)

    # 确定粘贴位置
    lw, lh = label_img.size
    if defect_class == 1:  # offset - 偏移
        # 偏移到边缘位置
        side = random.choice(['left', 'right', 'top', 'bottom'])
        if side == 'left':
            px = random.randint(-lw // 4, img_size // 6)
        elif side == 'right':
            px = random.randint(img_size * 2 // 3, img_size - lw // 2)
        elif side == 'top':
            px = random.randint(img_size // 4, img_size * 3 // 4 - lw)
        else:
            px = random.randint(img_size // 4, img_size * 3 // 4 - lw)

        if side in ('left', 'right'):
            py = random.randint(img_size // 4, img_size * 3 // 4 - lh)
        elif side == 'top':
            py = random.randint(-lh // 4, img_size // 6)
        else:
            py = random.randint(img_size * 2 // 3, img_size - lh // 2)
    else:
        # 正常位置：大致居中，有小偏移
        cx = img_size // 2 + random.randint(-40, 40)
        cy = img_size // 2 + random.randint(-40, 40)
        px = cx - lw // 2
        py = cy - lh // 2

    # 粘贴标签
    img.paste(label_img, (px, py))

    # 添加一些全局噪声和光照变化
    arr = np.array(img).astype(np.float32)
    # 亮度变化
    brightness = random.uniform(0.7, 1.3)
    arr = arr * brightness
    # 高斯噪声
    noise = np.random.normal(0, random.uniform(2, 8), arr.shape)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)

    # 偶尔模糊
    if random.random() < 0.2:
        img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.5, 1.5)))

    # 计算YOLO格式标注（归一化坐标）
    # 标签的实际可见区域
    vis_x1 = max(0, px)
    vis_y1 = max(0, py)
    vis_x2 = min(img_size, px + lw)
    vis_y2 = min(img_size, py + lh)

    if vis_x2 - vis_x1 < 20 or vis_y2 - vis_y1 < 20:
        # 标签几乎不可见，跳过
        return img, []

    cx_norm = ((vis_x1 + vis_x2) / 2) / img_size
    cy_norm = ((vis_y1 + vis_y2) / 2) / img_size
    w_norm = (vis_x2 - vis_x1) / img_size
    h_norm = (vis_y2 - vis_y1) / img_size

    annotations = [(defect_class, cx_norm, cy_norm, w_norm, h_norm)]

    return img, annotations


def generate_dataset(output_dir, num_train=400, num_val=100):
    """生成完整的训练数据集"""
    output_dir = Path(output_dir)

    for split, count in [('train', num_train), ('val', num_val)]:
        img_dir = output_dir / 'images' / split
        lbl_dir = output_dir / 'labels' / split
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        print(f"生成 {split} 集: {count} 张图片...")

        for i in range(count):
            img, annotations = generate_sample()

            # 保存图片
            img_path = img_dir / f"{split}_{i:05d}.jpg"
            img.save(str(img_path), quality=90)

            # 保存标注
            lbl_path = lbl_dir / f"{split}_{i:05d}.txt"
            with open(lbl_path, 'w') as f:
                for cls_id, cx, cy, w, h in annotations:
                    f.write(f"{cls_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")

            if (i + 1) % 50 == 0:
                print(f"  [{i + 1}/{count}]")

    # 生成dataset yaml
    yaml_path = output_dir / 'energy_label.yaml'
    yaml_content = f"""# 能效标签检测数据集（合成数据）
# 自动生成，用于模型训练和验证

path: {output_dir.resolve()}
train: images/train
val: images/val

nc: 5
names:
  0: label_normal
  1: label_offset
  2: label_scratch
  3: label_stain
  4: label_wrinkle
"""
    with open(yaml_path, 'w') as f:
        f.write(yaml_content)

    print(f"\n数据集生成完成:")
    print(f"  训练集: {num_train} 张")
    print(f"  验证集: {num_val} 张")
    print(f"  YAML: {yaml_path}")
    print(f"  类别: {list(CLASSES.values())}")

    return str(yaml_path)


def main():
    parser = argparse.ArgumentParser(description="生成合成能效标签训练数据")
    parser.add_argument("--output", type=str, default="../datasets/energy_label",
                        help="输出目录")
    parser.add_argument("--num-train", type=int, default=400,
                        help="训练集数量")
    parser.add_argument("--num-val", type=int, default=100,
                        help="验证集数量")
    args = parser.parse_args()

    if not HAS_PIL:
        print("错误: 需要安装Pillow库")
        print("  pip install Pillow")
        return

    generate_dataset(args.output, args.num_train, args.num_val)


if __name__ == "__main__":
    main()