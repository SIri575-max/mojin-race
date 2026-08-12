"""精确定位测试3 第二行图标：裁剪第二行区域，多采样识别"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vision_api as va
from PIL import Image

ex = Path(r"c:/Users/Lenovo/CodeBuddy/20260807025758/example")

P = (
    "这是两张并排的异象图标卡片（放大图）。请仔细描述这两张卡片的图标外观：\n"
    "- 颜色、形状、人物/物品类型、最显著特征\n"
    "- 卡片右下角的数字\n"
    "只输出 JSON 数组：[{\"col\":1,\"appearance\":\"...\",\"count\":1},{\"col\":2,\"appearance\":\"...\",\"count\":1}]"
)

for fname in ["测试3（6种异象，分数52）.jpeg", "测试4（7种异象，分数43.5）.jpeg"]:
    img = Image.open(ex / fname).convert("RGB")
    # 第二行区域（图标区 y 540-845 的下半）
    crop = img.crop((0, 660, 1920, 845))
    big = crop.resize((crop.size[0] * 2, crop.size[1] * 2), Image.LANCZOS)
    print(f"########## {fname} 第二行(660-845) ##########", flush=True)
    for i, temp in enumerate([0.0, 0.3, 0.7]):
        try:
            c = va._call_kills_once(big, prompt=P, temperature=temp)
            print(f"--- 采样#{i+1} temp={temp} ---", flush=True)
            print(c, flush=True)
        except Exception as e:
            print(f"[采样#{i+1}] ERR {e}", flush=True)
    print("", flush=True)
