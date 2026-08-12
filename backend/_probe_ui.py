# -*- coding: utf-8 -*-
"""分析 ui/ 素材：尺寸、主色调、是否为横幅/图标等特征"""
import os, glob
from PIL import Image

d = r"c:/Users/Lenovo/CodeBuddy/20260807025758/ui"
for f in sorted(glob.glob(os.path.join(d, "*"))):
    try:
        im = Image.open(f).convert("RGB")
        w, h = im.size
        # 缩略后统计主色调
        small = im.resize((50, 50))
        px = list(small.getdata())
        # 简单统计: 平均色 + 亮暗占比
        avg = tuple(sum(c[i] for c in px) // len(px) for i in range(3))
        dark = sum(1 for c in px if sum(c) < 200) / len(px)
        bright = sum(1 for c in px if sum(c) > 600) / len(px)
        # 边缘区域颜色（判断是否为边框/横幅）
        e = list(small.crop((0, 0, 50, 10)).getdata())
        edge = tuple(sum(c[i] for c in e) // len(e) for i in range(3))
        print(f"{os.path.basename(f):<12} {w}x{h}  avg={avg}  edge={edge}  dark%={dark:.0%} bright%={bright:.0%}")
    except Exception as ex:
        print(f, "ERR", ex)
