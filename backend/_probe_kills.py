"""临时探针：跑一遍当前异象识别，看新测试图的识别效果"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vision_api import analyze_kills_icons, load_icons

icons = load_icons()
print("图标库:")
for name, (score, _) in sorted(icons.items(), key=lambda kv: kv[1][0]):
    print(f"  {name} = {score}")
print()

for p in sorted(Path(__file__).resolve().parent.parent.glob("example/测试*.jpeg")):
    print(f"===== {p.name} =====")
    for sample in (1, 2):
        r = analyze_kills_icons(str(p), samples=sample)
        detail = r["kills_detail"]
        total = r["kills_score"]
        cnt = r["kills_total"]
        print(f"  采样{sample}次 -> 总分={total} 个数={cnt}")
        for d in detail:
            print(f"    {d['name']} x{d['count']} = {d['sub']}")
    print()
