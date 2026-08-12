"""实验：测试2 下半部(50%-100%)分成两个水平条带，各放大2x识别后合并"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _probe_zoom import call_once, score
from vision_api import load_icons
from PIL import Image

ex = Path(r"c:/Users/Lenovo/CodeBuddy/20260807025758/example")
fname = "测试2（八种异象，分数为38.5）.jpeg"
img = Image.open(ex / fname).convert("RGB")
w, h = img.size

# 下半部 50%-100%
bot = img.crop((0, h // 2, w, h))
bh = bot.size[1]
# 两行图标各一条带
strips = [
    ("条带1(50-75%)", bot.crop((0, 0, w, bh // 2))),
    ("条带2(75-100%)", bot.crop((0, bh // 2, w, bh))),
]
merged = {}
for label, s in strips:
    big = s.resize((s.size[0] * 2, s.size[1] * 2), Image.LANCZOS)
    r = call_once(big)
    print(f"{label}: {score(r)} {r}")
    for n, c in r.items():
        merged[n] = merged.get(n, 0) + c
print("合并:", score(merged), merged)
