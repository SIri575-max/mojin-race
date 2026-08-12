"""临时实验：方式B增强 + 多采样聚合（出现>=2次保留，count取最大值）"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vision_api import _encode_image, load_icons, _best_icon_match

import os, requests

base_url = os.environ["VISION_BASE_URL"].rstrip("/")
model = os.environ["VISION_MODEL"]
key = os.environ["VISION_API_KEY"]

PROMPT_B = (
    "你是一名赛事成绩录入助手。用户给你一张《第五人格》娱乐赛的【单场结算截图】。\n"
    "请找到「击败异象」栏（通常在左侧“本局记录”下方）。该栏会陈列若干个异象图标，"
    "每个图标右下角或旁边有一个数字（可能写成 x7、×7、x1 或直接是数字），表示该异象的数量。\n"
    "【重要】异象图标可能排成【一行或两行】！如果第一行图标下面还有一行，请务必也读取第二行。\n"
    "请严格【逐行、从左到右】扫描：先完整读出第一行的所有图标，再完整读出第二行的所有图标，"
    "确保整栏中每一个图标都被读到，绝对不能遗漏任何一行或任何一个图标。\n"
    "请逐个列出每个图标：\n"
    "- name：根据图标外观给出一个最贴切的中文名称；\n"
    "- appearance：用简洁中文描述图标外观，务必包含颜色和形状；\n"
    "- count：读取图标右下角/旁边的数字作为数量。请反复确认这个数字，"
    "例如 \"x3\" 就是3，“×12”就是12。\n"
    "注意：颜色或衣着不同的图标即使形状相似，也要分成多个条目，不要合并。\n"
    "只输出一个 JSON 数组：[{\"name\": \"红色气球\", \"appearance\": \"红色圆形气球\", \"count\": 7}, ...]，"
    "不要输出任何其他内容。"
)


def call_once(path):
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
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    resp = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"ERR {resp.status_code} {resp.text[:150]}")
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
        return []
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


def aggregate(trials):
    # trials: list of {name: count}
    votes = defaultdict(list)
    for t in trials:
        for name, cnt in t.items():
            votes[name].append(cnt)
    merged = {}
    for name, counts in votes.items():
        if len(counts) < 2:
            continue  # 过滤幻觉（只在1次出现）
        merged[name] = max(counts)
    return merged


if __name__ == "__main__":
    icons = load_icons()
    tests = [
        ("测试2（八种异象，分数为38.5）.jpeg", 38.5),
        ("测试3（6种异象，分数52）.jpeg", 52),
        ("测试4（7种异象，分数43.5）.jpeg", 43.5),
    ]
    N = 4
    for fname, expect in tests:
        fpath = Path(__file__).resolve().parent.parent / "example" / fname
        trials = []
        for i in range(N):
            try:
                content = call_once(fpath)
                trials.append(parse_once(content, icons))
                print(f"   {fname} 第{i+1}次: {trials[-1]}")
            except RuntimeError as e:
                print(f"   {fname} 第{i+1}次失败: {e}")
        merged = aggregate(trials)
        total = round(sum(icons[n][0] * c for n, c in merged.items()), 2)
        print(f"  == {fname} 期望={expect} 聚合总分={total} 明细={merged}")
        print()
