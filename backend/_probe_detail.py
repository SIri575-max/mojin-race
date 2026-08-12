"""精确识别：裁剪图标区放大，逐格描述（第几行第几列），多次采样"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vision_api as va
from PIL import Image

ex = Path(r"c:/Users/Lenovo/CodeBuddy/20260807025758/example")

DETAIL_PROMPT = (
    "这是一张《第五人格》娱乐赛结算截图的【底部区域】放大图。\n"
    "请找到「击败异象」图标栏（由多个小图标卡片组成，每个卡片上有图标和右下角的数字）。\n"
    "【极其重要】请先确认图标栏共有几行、每行几个图标，然后严格【逐行逐列】扫描：\n"
    "对每个图标输出：\n"
    '- row：第几行（1开始）\n'
    '- col：第几列（1开始，从左到右）\n'
    '- name：图标名称（参考：叹息球、异色叹息球、贪婪的盗匪、异色贪婪的盗匪、盗匪、'
    '缄默的绅士、失职的看守、异色失职的看守、镜中回忆、厄运替身、旗杆阴兵、号角阴兵、故纸堆）\n'
    '- appearance：图标外观（颜色+形状+特征，例如“灰色身体、戴帽子”“蓝色镜子”）\n'
    '- count：图标右下角的数字（若无数字则填1）\n'
    "只输出 JSON 数组：[{\"row\":1,\"col\":1,\"name\":\"...\",\"appearance\":\"...\",\"count\":1}, ...]"
    "，不要输出任何其他内容。"
)


def run(fname, box):
    img = Image.open(ex / fname).convert("RGB")
    crop = img.crop(box)
    big = crop.resize((crop.size[0] * 2, crop.size[1] * 2), Image.LANCZOS)
    print(f"########## {fname} box={box} ##########", flush=True)
    for i, temp in enumerate([0.0, 0.3]):
        try:
            c = va._call_kills_once(big, prompt=DETAIL_PROMPT, temperature=temp)
            print(f"--- 采样#{i+1} temp={temp} ---", flush=True)
            print(c, flush=True)
        except Exception as e:
            print(f"[采样#{i+1}] ERR {e}", flush=True)


for fname in ["测试2（八种异象，分数为38.5）.jpeg", "测试3（6种异象，分数52）.jpeg", "测试4（7种异象，分数43.5）.jpeg"]:
    run(fname, (0, 540, 1920, 845))
    print("", flush=True)
