# -*- coding: utf-8 -*-
"""logo.png(白底深色内容) -> 金色透明 logo_web.png：抠白底 + 深色像素着色为金色渐变"""
from PIL import Image
import numpy as np

src = r"c:/Users/Lenovo/CodeBuddy/20260807025758/ui/logo.png"
dst = r"c:/Users/Lenovo/CodeBuddy/20260807025758/frontend/logo_web.png"

im = Image.open(src).convert("RGBA")
a = np.array(im).astype(np.int16)
r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]

# 白底判定
maxc = np.maximum(np.maximum(r, g), b)
minc = np.minimum(np.minimum(r, g), b)
is_bg = (maxc > 235) & ((maxc - minc) < 18)

alpha_new = al.copy()
alpha_new[is_bg] = 0
soft = (~is_bg) & (maxc > 215) & ((maxc - minc) < 30)
alpha_new[soft] = (alpha_new[soft] * 0.35).astype(np.int16)

# 内容像素着色：黑色(或深色) -> 金色渐变（上亮下暗，仿烫金）
h, w = alpha_new.shape
r_new, g_new, b_new = r.copy(), g.copy(), b.copy()
mask = alpha_new > 40
ys = np.arange(h)[:, None] * np.ones(w)[None, :]
t = (ys / max(1, h - 1))
g_top = np.array([247, 231, 168])
g_mid = np.array([212, 175, 55])
g_bot = np.array([143, 111, 28])
color = np.stack([
    (g_top[0] + (g_mid[0] - g_top[0]) * t) * (1 - t) + g_bot[0] * t,
    (g_top[1] + (g_mid[1] - g_top[1]) * t) * (1 - t) + g_bot[1] * t,
    (g_top[2] + (g_mid[2] - g_top[2]) * t) * (1 - t) + g_bot[2] * t,
], axis=2)
# 仅对内容区域着色，透明区域保持
r_new[mask] = color[..., 0][mask]
g_new[mask] = color[..., 1][mask]
b_new[mask] = color[..., 2][mask]

out = np.dstack([r_new, g_new, b_new, alpha_new]).clip(0, 255).astype(np.uint8)
im2 = Image.fromarray(out, "RGBA")

# 裁剪透明边并缩放到高 240
bbox = im2.getbbox()
if bbox:
    im2 = im2.crop(bbox)
tw, th = im2.size
nh = 240
nw = max(1, int(tw * nh / th))
im2 = im2.resize((nw, nh), Image.LANCZOS)
im2.save(dst)
print("输出:", dst, im2.size)

# ASCII 预览（透明部分显示为空格）
chars = " .:-=+*#%@"
w2, h2 = im2.size
gw2, gh2 = 64, max(1, int(h2 * 64 / w2 / 2))
sm = np.array(im2.resize((gw2, gh2)))
sa, sg = sm[..., 3], sm[..., :3].mean(axis=2)
for yy in range(gh2):
    line = ""
    for xx in range(gw2):
        if sa[yy, xx] < 40:
            line += " "
        else:
            line += chars[min(9, int(sg[yy, xx]) * 10 // 256)]
    print(line)
