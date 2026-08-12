"""实验：全部测试图，整图 + 两行区域放大 + 多温度采样，合并"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _probe_zoom import call_once, score
from PIL import Image

ex = Path(r"c:/Users/Lenovo/CodeBuddy/20260807025758/example")
cases = [
    ("测试2（八种异象，分数为38.5）.jpeg", 38.5),
    ("测试3（6种异象，分数52）.jpeg", 52),
    ("测试4（7种异象，分数43.5）.jpeg", 43.5),
]

for fname, expect in cases:
    img = Image.open(ex / fname).convert("RGB")
    w, h = img.size
    print(f"===== {fname} 期望={expect} =====")
    merged = {}
    views = []
    # 整图 temp 0 / 0.7
    for t in (0, 0.7):
        views.append(("整图", call_once(img, t)))
    # 两行区域放大
    row1 = img.crop((0, int(h * 0.60), w, int(h * 0.82)))
    row2 = img.crop((0, int(h * 0.78), w, h))
    for label, band in (("行1", row1), ("行2", row2)):
        for scale in (2,):
            big = band.resize((band.size[0] * scale, band.size[1] * scale), Image.LANCZOS)
            for t in (0, 0.7):
                views.append((f"{label}{scale}x", call_once(big, t)))
    for label, r in views:
        print(f"  {label}: {score(r)} {r}")
        for n, c in r.items():
            merged[n] = max(merged.get(n, 0), c)
    print(f"  ==> 合并(max)总分={score(merged)} {merged}")
    print()
