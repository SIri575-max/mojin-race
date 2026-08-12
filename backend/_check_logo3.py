# -*- coding: utf-8 -*-
"""检查 ui/logo.png 的 alpha 通道与内容，确认是否透明底文字 logo"""
from PIL import Image
import os

p = os.path.join(os.path.dirname(__file__), "..", "ui", "logo.png")
im = Image.open(p).convert("RGBA")
print("size:", im.size, "mode:", im.mode)

# 统计 alpha 分布
a = im.getchannel("A")
hist = a.histogram()
total = im.size[0] * im.size[1]
transparent = sum(hist[0:32])
opaque = sum(hist[224:256])
semi = total - transparent - opaque
print(f"total={total} 透明(alpha<32)={transparent}({transparent/total*100:.1f}%) 半透明={semi}({semi/total*100:.1f}%) 不透明(alpha>223)={opaque}({opaque/total*100:.1f}%)")

# 不透明像素的平均颜色
import collections
colors = collections.Counter()
for x in range(0, im.size[0], 4):
    for y in range(0, im.size[1], 4):
        r, g, b, al = im.getpixel((x, y))
        if al > 128:
            colors[(r // 32 * 32, g // 32 * 32, b // 32 * 32)] += 1
print("不透明像素主色(量化32):", colors.most_common(8))

# 保存一份缩略预览的 ASCII 观察 alpha 形状
im2 = im.resize((60, 20))
for y in range(im2.size[1]):
    row = ""
    for x in range(im2.size[0]):
        r, g, b, al = im2.getpixel((x, y))
        row += "#" if al > 128 else ("+" if al > 32 else " ")
    print(row)
