"""实验：整图 + 6段均匀窄条带放大识别，同图鉴名取max合并"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _probe_zoom import call_once, score
from vision_api import load_icons
from PIL import Image

ex = Path(r"c:/Users/Lenovo/CodeBuddy/20260807025758/example")

for fname, expect in [
    ("测试2（八种异象，分数为38.5）.jpeg", 38.5),
]:
    img = Image.open(ex / fname).convert("RGB")
    w, h = img.size
    print(f"===== {fname} 期望={expect} {w}x{h} =====")
    base = call_once(img)
    print(f"  整图: {score(base)} {base}")
    N = 6
    merged = {}
    for i in range(N):
        y0, y1 = int(h * i / N), int(h * (i + 1) / N)
        band = img.crop((0, y0, w, y1))
        big = band.resize((band.size[0] * 2, band.size[1] * 2), Image.LANCZOS)
        r = call_once(big)
        print(f"  段{i+1}[{i*100//N}%-{(i+1)*100//N}%]: {score(r)} {r}")
        for n, c in r.items():
            merged[n] = max(merged.get(n, 0), c)
    print(f"  ==> 整图+6段合并总分={score(merged)} {merged}")
