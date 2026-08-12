"""查看多视角中每个视角的解析结果，分析幻觉/漏读来源"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vision_api as va

ex = Path(r"c:/Users/Lenovo/CodeBuddy/20260807025758/example")
cases = [
    ("测试2（八种异象，分数为38.5）.jpeg", 38.5),
    ("测试3（6种异象，分数52）.jpeg", 52),
    ("测试4（7种异象，分数43.5）.jpeg", 43.5),
]

for fname, expect in cases:
    path = str(ex / fname)
    print(f"\n########## {fname} 期望={expect} ##########", flush=True)
    views = []
    for i in range(2):
        try:
            c = va._call_kills_once(path, temperature=0.3 if i % 2 else 0.0)
            views.append(va._parse_kills_once(c))
            print(f"[整图#{i+1} temp={0.3 if i % 2 else 0.0}] {c}", flush=True)
        except Exception as e:
            print(f"[整图#{i+1}] ERR {e}", flush=True)
    for j, band in enumerate(va._crop_bands(path)):
        try:
            c = va._call_kills_once(band, temperature=0.0)
            views.append(va._parse_kills_once(c))
            print(f"[条带#{j+1}] {c}", flush=True)
        except Exception as e:
            print(f"[条带#{j+1}] ERR {e}", flush=True)
    print(f"--- 合并结果 ---", flush=True)
    merged = va._merge_kills_counts(views)
    for k, v in sorted(merged.items(), key=lambda x: -x[1]):
        print(f"  {k} x{v} = {va.load_icons()[k][0]*v}", flush=True)
