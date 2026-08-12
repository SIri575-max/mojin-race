"""实验：多视角识别（整图 + 水平条带放大）合并取max，三张测试图全量验证"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _probe_zoom import call_once, score
from vision_api import load_icons
from PIL import Image

ex = Path(r"c:/Users/Lenovo/CodeBuddy/20260807025758/example")
cases = [
    ("测试2（八种异象，分数为38.5）.jpeg", 38.5),
    ("测试3（6种异象，分数52）.jpeg", 52),
    ("测试4（7种异象，分数43.5）.jpeg", 43.5),
]

VIEWS = [(0.5, 1.0), (0.65, 1.0)]  # 底部累计裁切条带 (start, end)

for fname, expect in cases:
    img = Image.open(ex / fname).convert("RGB")
    w, h = img.size
    print(f"===== {fname} 期望={expect} =====")
    # 整图
    base = call_once(img)
    print(f"  整图: {score(base)} {base}")
    # 条带
    bands = []
    for (s0, s1) in VIEWS:
        band = img.crop((0, int(h * s0), w, int(h * s1)))
        big = band.resize((band.size[0] * 2, band.size[1] * 2), Image.LANCZOS)
        r = call_once(big)
        print(f"  条带[{int(s0*100)}%-{int(s1*100)}%]: {score(r)} {r}")
        bands.append(r)
    merged = {}
    for r in [base] + bands:
        for n, c in r.items():
            merged[n] = max(merged.get(n, 0), c)
    print(f"  ==> 合并总分={score(merged)} {merged}")
    print()
