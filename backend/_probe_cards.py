"""检测底部区域图标卡片矩形，确定行/列布局"""
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ex = Path(r"c:/Users/Lenovo/CodeBuddy/20260807025758/example")

for f in os.listdir(ex):
    if "测试" not in f:
        continue
    img = Image.open(ex / f).convert("RGB")
    w, h = img.size
    # 分析区域：底部 45%~95%
    y0, y1 = int(h * 0.45), int(h * 0.95)
    band = np.array(img.crop((0, y0, w, y1)))
    gray = cv2.cvtColor(band, cv2.COLOR_RGB2GRAY)
    # 边缘检测
    edges = cv2.Canny(gray, 60, 150)
    # 形态学闭运算连接卡片边框
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=3)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    print(f"===== {f} =====", flush=True)
    rects = []
    for c in contours:
        x, y, cw, ch = cv2.boundingRect(c)
        if cw > 80 and ch > 80 and cw < w * 0.4 and ch < (y1 - y0) * 0.8:
            rects.append((x, y + y0, cw, ch))
    # 按 y 聚类行，按 x 排序
    rects.sort(key=lambda r: r[1])
    rows = []
    for r in rects:
        placed = False
        for row in rows:
            if abs(row[0][1] - r[1]) < 40:
                row.append(r)
                placed = True
                break
        if not placed:
            rows.append([r])
    for row in rows:
        row.sort(key=lambda r: r[0])
        cells = [f"(x={x},y={y},w={cw},h={ch})" for x, y, cw, ch in row]
        print(f"  行 y={row[0][1]}-{max(r[1]+r[3] for r in row)}: {' | '.join(cells)}", flush=True)
