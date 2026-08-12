"""实验：图鉴对照检索（图鉴+截图同图/同请求，AI 对照编号）"""
import sys
import json
import os
import base64
import io
from pathlib import Path

import requests
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vision_api as va
from PIL import Image

ex = Path(r"c:/Users/Lenovo/CodeBuddy/20260807025758/example")

REF_PROMPT = (
    "第一张图是【异象图鉴】，共13个图标，每个格子左上角有 #编号（#1~#13），下方有名称和分值。\n"
    "第二张图是《第五人格》娱乐赛结算截图。请找到截图中的「击败异象」图标栏"
    "（通常在截图左中下部，可能有1行、2行甚至3行图标）。\n"
    "【重要】先观察图标栏共有几行、每行几个图标，然后逐行从左到右扫描，绝不能遗漏任何一行或图标。\n"
    "将截图中每个异象图标与图鉴对照，输出对应图鉴编号和数量：\n"
    '只输出 JSON 数组：[{"id": 3, "count": 4}, {"id": 7, "count": 1}, ...]。\n'
    "若某个图标在图鉴中找不到对应，就输出 {\"id\": 0, \"count\": 1} 标记为未知。\n"
    "不要输出任何其他内容。"
)


def call_ref(path_or_img, band_box=None, temperature=0.0):
    """把图鉴 + 截图(可选条带) 一起发给 AI"""
    base_url = os.environ.get("VISION_BASE_URL", "").rstrip("/")
    model = os.environ.get("VISION_MODEL", "")
    key = os.environ.get("VISION_API_KEY", "")

    sheet = va.build_icon_sheet()
    images = []
    # 图鉴
    buf = io.BytesIO()
    Image.open(sheet).convert("RGB").save(buf, format="JPEG", quality=92)
    images.append("data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode())
    # 截图
    if hasattr(path_or_img, "save"):
        buf2 = io.BytesIO()
        path_or_img.save(buf2, format="PNG")
        images.append("data:image/png;base64," + base64.b64encode(buf2.getvalue()).decode())
    else:
        img = Image.open(path_or_img).convert("RGB")
        if band_box:
            w, h = img.size
            img = img.crop(band_box)
            img = img.resize((img.size[0] * 2, img.size[1] * 2), Image.LANCZOS)
        buf2 = io.BytesIO()
        img.save(buf2, format="PNG")
        images.append("data:image/png;base64," + base64.b64encode(buf2.getvalue()).decode())

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是严格的 JSON 输出助手。"},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": REF_PROMPT},
                    *[{"type": "image_url", "image_url": {"url": u}} for u in images],
                ],
            },
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    resp = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"接口错误({resp.status_code}): {resp.text[:200]}")
    content = resp.json()["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.startswith("json"):
            content = content[4:]
    return content


os.environ.setdefault("VISION_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
os.environ.setdefault("VISION_MODEL", "glm-4v-flash")

icons = va.load_icons()
names = list(icons.keys())
id2name = {i + 1: n for i, n in enumerate(names)}

for fname, expect in [
    ("测试2（八种异象，分数为38.5）.jpeg", 38.5),
    ("测试3（6种异象，分数52）.jpeg", 52),
    ("测试4（7种异象，分数43.5）.jpeg", 43.5),
]:
    path = str(ex / fname)
    print(f"\n########## {fname} 期望={expect} ##########", flush=True)
    # 三种输入：整图 / 底部放大 / 底部
    inputs = [
        ("整图", None),
        ("底部0.6-1.0", (0, int(864 * 0.60), 1920, 864)),
    ]
    for tag, box in inputs:
        try:
            content = call_ref(path, box, temperature=0.0)
            print(f"[{tag}] {content}", flush=True)
        except Exception as e:
            print(f"[{tag}] ERR {e}", flush=True)
