"""实验 v3：验证新版 analyze_kills_icons 多视角合并"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from vision_api import analyze_kills_icons

ex = Path(r"c:/Users/Lenovo/CodeBuddy/20260807025758/example")
cases = [
    ("测试2（八种异象，分数为38.5）.jpeg", 38.5),
    ("测试3（6种异象，分数52）.jpeg", 52),
    ("测试4（7种异象，分数43.5）.jpeg", 43.5),
]
for fname, expect in cases:
    r = analyze_kills_icons(str(ex / fname), samples=2, multi_view=True)
    print(f"===== {fname} 期望={expect} =====")
    print(f"总分={r['kills_score']} 个数={r['kills_total']}")
    for d in r["kills_detail"]:
        print(f"  {d['name']} x{d['count']} = {d['sub']}")
    print()
