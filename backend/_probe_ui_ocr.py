# -*- coding: utf-8 -*-
"""OCR 识别 ui/ 图片中的文字，辅助判断素材内容"""
import os, glob
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ocr_service import get_engine

engine = get_engine()
d = r"c:/Users/Lenovo/CodeBuddy/20260807025758/ui"
for f in sorted(glob.glob(os.path.join(d, "*.jpg")) + glob.glob(os.path.join(d, "*.png"))):
    print("=" * 40)
    print(os.path.basename(f))
    try:
        result, _ = engine(f)
        if not result:
            print("  (无文字)")
        for item in result or []:
            print("  ", item[1], f"conf={item[2]:.2f}" if len(item) > 2 else "")
    except Exception as e:
        print("  ERR", e)
