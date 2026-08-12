"""裁剪候选图标区域放大保存 + 让 AI 描述区域内容"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vision_api as va
from PIL import Image

ex = Path(r"c:/Users/Lenovo/CodeBuddy/20260807025758/example")
tmp = Path(r"c:/Users/Lenovo/CodeBuddy/20260807025758/_tmp")
tmp.mkdir(exist_ok=True)

regions = [
    ("测试2（八种异象，分数为38.5）.jpeg", (0, 540, 1920, 840), "底部0.63-0.97"),
    ("测试3（6种异象，分数52）.jpeg", (0, 540, 1920, 840), "底部0.63-0.97"),
    ("测试4（7种异象，分数43.5）.jpeg", (0, 540, 1920, 840), "底部0.63-0.97"),
]

for fname, box, tag in regions:
    img = Image.open(ex / fname).convert("RGB")
    print(f"########## {fname} [{tag}] ##########", flush=True)
    crop = img.crop(box)
    big = crop.resize((crop.size[0] * 2, crop.size[1] * 2), Image.LANCZOS)
    out = tmp / f"bottom_{fname.split('（')[0]}.png"
    big.save(out)
    print(f"  保存 {out} size={big.size}", flush=True)
    try:
        content = va._call_kills_once(big, prompt=None, temperature=0.0)
        print(f"  AI: {content}", flush=True)
    except Exception as e:
        print(f"  ERR {e}", flush=True)
