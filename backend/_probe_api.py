# -*- coding: utf-8 -*-
"""验证 /api/icons/list 接口（直接调用 FastAPI 函数）"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from main import icon_list

r = icon_list()
icons = r.get("icons", [])
print(f"接口返回 {len(icons)} 种图标")
for ic in icons[:4]:
    print(f"  {ic['name']}: {ic['score']}")
