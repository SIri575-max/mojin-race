# -*- coding: utf-8 -*-
"""检查透明 logo：非透明像素占比 + ASCII 预览"""
from PIL import Image
import numpy as np

im = Image.open(r"c:/Users/Lenovo/CodeBuddy/20260807025758/frontend/logo_web.png").convert("RGBA")
a = np.array(im)
alpha = a[..., 3]
non_transparent = (alpha > 30).mean()
print(f"尺寸 {im.size}  非透明像素占比 {non_transparent:.1%}")
chars = " .:-=+*#%@"
g = a[..., :3].mean(axis=2)
w, h = im.size
gw, gh = 60, max(1, int(h * 60 / w / 2))
small = np.array(im.resize((gw, gh)))
ga = small[..., :3].mean(axis=2)
al = small[..., 3]
for r in range(gh):
    row = ""
    for c in range(gw):
        if al[r, c] < 40:
            row += " "
        else:
            p = int(ga[r, c])
            row += chars[min(9, p * 10 // 256)]
    print(row)
