# -*- coding: utf-8 -*-
"""更细致分析 ui/ 素材：九宫格分块颜色、中间区域、是否存在大面积色块（按钮/图标）"""
import os, glob
from PIL import Image

d = r"c:/Users/Lenovo/CodeBuddy/20260807025758/ui"
for f in sorted(glob.glob(os.path.join(d, "*.jpg")) + glob.glob(os.path.join(d, "*.png"))):
    im = Image.open(f).convert("RGB")
    w, h = im.size
    print("=" * 40)
    print(os.path.basename(f), f"{w}x{h}")
    # 3x3 分块平均色
    g = 3
    for r in range(g):
        row = []
        for c in range(g):
            box = (c * w // g, r * h // g, (c + 1) * w // g, (r + 1) * h // g)
            crop = im.crop(box).resize((20, 20))
            px = list(crop.getdata())
            avg = tuple(sum(p[i] for p in px) // len(px) for i in range(3))
            row.append(f"({avg[0]:>3},{avg[1]:>3},{avg[2]:>3})")
        print("  ", " ".join(row))
