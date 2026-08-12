"""实验：对两行图标区域分别 3x 放大识别，多温度采样后合并"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _probe_zoom import call_once, score
from PIL import Image

ex = Path(r"c:/Users/Lenovo/CodeBuddy/20260807025758/example")
fname = "测试2（八种异象，分数为38.5）.jpeg"
img = Image.open(ex / fname).convert("RGB")
w, h = img.size

# 两行区域
row1 = img.crop((0, int(h * 0.60), w, int(h * 0.82)))  # 第一行
row2 = img.crop((0, int(h * 0.78), w, h))               # 第二行
merged = {}
for label, band in (("行1", row1), ("行2", row2)):
    for scale in (2, 3):
        big = band.resize((band.size[0] * scale, band.size[1] * scale), Image.LANCZOS)
        for temp in (0, 0.7):
            r = call_once(big, temp)
            print(f"{label} {scale}x temp={temp}: {score(r)} {r}")
            for n, c in r.items():
                merged[n] = max(merged.get(n, 0), c)
print("合并:", score(merged), merged)
