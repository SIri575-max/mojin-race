# -*- coding: utf-8 -*-
"""将 ui/ 图片转成 ASCII 灰度预览，辅助判断内容布局"""
import os, glob
from PIL import Image

d = r"c:/Users/Lenovo/CodeBuddy/20260807025758/ui"
chars = " .:-=+*#%@"
for f in sorted(glob.glob(os.path.join(d, "*.jpg")) + glob.glob(os.path.join(d, "*.png"))):
    im = Image.open(f).convert("L")
    # 缩到 60 宽，保留宽高比（2:1 字符宽高比修正）
    w = 60
    h = max(1, int(im.size[1] * w / im.size[0] / 2))
    small = im.resize((w, h))
    px = list(small.getdata())
    print("=" * 66)
    print(os.path.basename(f), f"{im.size[0]}x{im.size[1]}")
    for r in range(h):
        row = "".join(chars[min(9, p * 10 // 256)] for p in px[r * w:(r + 1) * w])
        print(row)
