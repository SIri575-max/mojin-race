# -*- coding: utf-8 -*-
"""ASCII 预览 logo_web.png 布局"""
from PIL import Image
import os
p = os.path.join(os.path.dirname(__file__), "..", "frontend", "logo_web.png")
im = Image.open(p).convert("RGBA")
im2 = im.resize((110, 26))
for y in range(im2.size[1]):
    row = ""
    for x in range(im2.size[0]):
        r, g, b, a = im2.getpixel((x, y))
        if a < 32:
            row += " "
        else:
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            row += "@" if lum > 180 else ("#" if lum > 120 else "+")
    print(row)
