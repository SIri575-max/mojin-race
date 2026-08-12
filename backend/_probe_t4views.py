"""查看测试4 每个视角的解析计数"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vision_api as va
from PIL import Image

path = str(Path(r"c:/Users/Lenovo/CodeBuddy/20260807025758/example") / "测试4（7种异象，分数43.5）.jpeg")
print("[整图#1]", va._parse_kills_once(va._call_kills_once(path, temperature=0.0)), flush=True)
print("[整图#2]", va._parse_kills_once(va._call_kills_once(path, temperature=0.3)), flush=True)
img = Image.open(path).convert("RGB")
w, h = img.size
region = img.crop((0, int(h * 0.55), w, h))
region = region.resize((region.size[0] * 2, region.size[1] * 2), Image.LANCZOS)
print("[逐格#1]", va._parse_kills_once(va._call_kills_once(region, prompt=va.DETAIL_KILLS_PROMPT, temperature=0.0)), flush=True)
print("[逐格#2]", va._parse_kills_once(va._call_kills_once(region, prompt=va.DETAIL_KILLS_PROMPT, temperature=0.3)), flush=True)
for j, band in enumerate(va._crop_bands(path)):
    print(f"[条带#{j+1}]", va._parse_kills_once(va._call_kills_once(band, temperature=0.0)), flush=True)
