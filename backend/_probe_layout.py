"""分析测试图底部图标栏布局：用行/列标准差检测图标卡片边界"""
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ex = Path(r"c:/Users/Lenovo/CodeBuddy/20260807025758/example")


def find_boundaries(values, thresh_ratio=0.35, min_run=3):
    """返回连续大于阈值的区间 [start, end) 列表"""
    med = float(np.median(values))
    mx = float(np.max(values))
    thr = med + (mx - med) * thresh_ratio
    active = values > thr
    segs = []
    i = 0
    n = len(values)
    while i < n:
        if active[i]:
            j = i
            while j < n and active[j]:
                j += 1
            if j - i >= min_run:
                segs.append((i, j))
            i = j
        else:
            i += 1
    return segs, thr


for f in os.listdir(ex):
    if "测试" not in f:
        continue
    img = Image.open(ex / f).convert("RGB")
    w, h = img.size
    # 分析区域：底部 40%~100%
    y0 = int(h * 0.4)
    band = np.array(img.crop((0, y0, w, h)))
    gray = cv2.cvtColor(band, cv2.COLOR_RGB2GRAY)
    print(f"===== {f} size={img.size} =====", flush=True)
    # 行标准差（内容复杂度）
    row_std = gray.std(axis=1)
    segs, thr = find_boundaries(row_std)
    print(f"row_std thr={thr:.1f} segments:", flush=True)
    for s0, s1 in segs:
        print(f"  行带 y={y0+s0}-{y0+s1-1} (绝对{y0+s0}~{y0+s1-1})", flush=True)
    # 对每个行带再检测列边界
    for s0, s1 in segs:
        sub = gray[s0:s1]
        col_std = sub.std(axis=0)
        csegs, cthr = find_boundaries(col_std, thresh_ratio=0.5, min_run=5)
        cols = [f"x={cs0}-{cs1-1}(宽{cs1-cs0})" for cs0, cs1 in csegs]
        print(f"  -> 列:{' | '.join(cols)}", flush=True)
