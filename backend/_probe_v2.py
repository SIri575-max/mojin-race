"""临时实验 v2：temperature>0 多采样 + 聚合(出现>=2次保留, count取max)"""
import json
import os
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vision_api import _encode_image, load_icons, _best_icon_match

base_url = os.environ["VISION_BASE_URL"].rstrip("/")
model = os.environ["VISION_MODEL"]
key = os.environ["VISION_API_KEY"]

PROMPT_B = (
    "你是一名赛事成绩录入助手。用户给你一张《第五人格》娱乐赛的【单场结算截图】。\n"
    "请找到「击败异象」栏（通常在左侧“本局记录”下方）。该栏会陈列若干个异象图标，"
    "每个图标右下角或旁边有一个数字（可能写成 x7、×7、x1 或直接是数字），表示该异象的数量。\n"
    "【重要】异象图标可能排成【一行、两行或三行】！请先仔细数一数：这栏里共有几行图标、"
    "每行各几个图标。然后严格【逐行、从左到右】扫描：先完整读出第一行的所有图标，"
    "再完整读出第二行、第三行的所有图标，确保整栏中每一个图标都被读到，绝对不能遗漏。\n"
    "请逐个列出每个图标：\n"
    "- name：根据图标外观给出一个最贴切的中文名称；\n"
    "- appearance：用简洁中文描述图标外观，务必包含颜色和形状；\n"
    "- count：读取图标右下角/旁边的数字作为数量。请反复确认这个数字，"
    "例如 \"x3\" 就是3，“×12”就是12，千万不要读错或漏读。\n"
    "注意：颜色或衣着不同的图标即使形状相似，也要分成多个条目，不要合并。\n"
    "只输出一个 JSON 数组：[{\"name\": \"红色气球\", \"appearance\": \"红色圆形气球\", \"count\": 7}, ...]，"
    "不要输出任何其他内容。"
)


def call_once(path, temp):
    content = [
        {"type": "text", "text": PROMPT_B},
        {"type": "image_url", "image_url": {"url": _encode_image(str(path))}},
    ]
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是严格的 JSON 输出助手。"},
            {"role": "user", "content": content},
        ],
        "temperature": temp,
        "response_format": {"type": "json_object"},
    }
    resp = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    if resp.status_code != 200:
        return None
    c = resp.json()["choices"][0]["message"]["content"].strip()
    if c.startswith("```"):
        c = c.strip("`")
        if c.startswith("json"):
            c = c[4:]
    return c


def parse_once(content, icons):
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return {}
    items = data.get("icons", []) if isinstance(data, dict) else data
    out = {}
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict):
            continue
        matched = _best_icon_match(str(it.get("name", "")), str(it.get("appearance", "")), icons)
        if not matched:
            continue
        try:
            cnt = int(float(str(it.get("count", 0))))
        except (TypeError, ValueError):
            cnt = 0
        if cnt <= 0:
            continue
        out[matched] = out.get(matched, 0) + cnt
    return out


def run_one(path, temp, n):
    trials = []
    def _one(_):
        for _ in range(1):
            c = call_once(path, temp)
            if c:
                return parse_once(c, icons)
        return {}
    with ThreadPoolExecutor(max_workers=n) as ex:
        trials = list(ex.map(_one, range(n)))
    return trials


if __name__ == "__main__":
    icons = load_icons()
    tests = [
        ("测试2（八种异象，分数为38.5）.jpeg", 38.5),
        ("测试3（6种异象，分数52）.jpeg", 52),
        ("测试4（7种异象，分数43.5）.jpeg", 43.5),
    ]
    for temp in (0.5, 1.0):
        print(f"########## temperature={temp} ##########")
        for fname, expect in tests:
            fpath = Path(r"c:/Users/Lenovo/CodeBuddy/20260807025758/example") / fname
            trials = run_one(fpath, temp, 4)
            votes = defaultdict(list)
            for t in trials:
                print(f"   trial: {t}")
                for name, cnt in t.items():
                    votes[name].append(cnt)
            merged = {name: max(cs) for name, cs in votes.items() if len(cs) >= 2}
            total = round(sum(icons[n][0] * c for n, c in merged.items()), 2)
            print(f"  == {fname} 期望={expect} 聚合总分={total} 明细={merged}")
            print()
