# -*- coding: utf-8 -*-
"""OCR 识别 ui/logo.png 的文字内容"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image
from rapidocr_onnxruntime import RapidOCR

engine = RapidOCR()
im = Image.open(os.path.join(os.path.dirname(__file__), "..", "ui", "logo.png")).convert("RGB")
# 原图识别
result, _ = engine(im)
print("=== 原图 OCR ===")
if result:
    for box, text, score in result:
        print(f"  {text!r}  (score={score:.2f})")
else:
    print("  (无文字)")

# 二值化增强后再识别
import numpy as np
arr = np.array(im.convert("L"))
bw = np.where(arr < 140, 0, 255).astype("uint8")
im2 = Image.fromarray(bw)
result2, _ = engine(im2)
print("=== 二值化后 OCR ===")
if result2:
    for box, text, score in result2:
        print(f"  {text!r}  (score={score:.2f})")
else:
    print("  (无文字)")
