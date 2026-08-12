# -*- coding: utf-8 -*-
"""验证图标库加载与 /api/icons/list 返回结构"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import vision_api as va

icons = va.load_icons()
print(f"共 {len(icons)} 种图标：")
for n, (score, _p) in sorted(icons.items(), key=lambda kv: kv[1][0]):
    print(f"  {n}: {score}")
