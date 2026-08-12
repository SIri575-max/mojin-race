# -*- coding: utf-8 -*-
"""分析原始 logo.png 的颜色分布直方图，判断内容深浅"""
from PIL import Image
import numpy as np

im = Image.open(r"c:/Users/Lenovo/CodeBuddy/20260807025758/ui/logo.png").convert("RGB")
a = np.array(im).astype(np.int16)
gray = a.mean(axis=2)
# 亮度分桶
bins = np.arange(0, 256, 16)
hist, _ = np.histogram(gray, bins=bins)
print("亮度分布 (0-255, 每16一档):")
for i, c in enumerate(hist):
    bar = "#" * (c // max(1, int(hist.max() / 40)))
    print(f"  {bins[i]:>3}-{bins[i]+15:>3}: {c:>6} {bar}")
print("平均亮度:", gray.mean())
# 非白像素(亮度<240)占比
print("亮度<240:", (gray < 240).mean().round(3), " 亮度<200:", (gray < 200).mean().round(3))
# 中间区域 vs 边缘
mid = gray[400:1476, 600:1853]
print("中间区域平均亮度:", mid.mean(), " 中间<200占比:", (mid < 200).mean().round(3))
