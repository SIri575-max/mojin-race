"""临时实验：对比方式B增强(两行强调) vs 方式A(带图鉴编号) 的异象识别效果"""
import base64
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vision_api import _encode_image, build_icon_sheet, load_icons, _best_icon_match

if not (os.environ.get("VISION_API_KEY") and os.environ.get("VISION_MODEL")):
    sys.exit("未配置视觉AI")

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
    "- name：根据图标外观给出一个最贴切的中文名称（例如“戴面具的角色”“红色气球”“绿色衣服的老妇人”）；\n"
    "- appearance：用简洁中文描述图标外观，务必包含颜色和形状（例如“红色圆形气球”“穿黑色衣服的角色”）；\n"
    "- count：读取图标右下角/旁边的数字作为数量。\n"
    "注意：颜色或衣着不同的图标即使形状相似，也要分成多个条目，不要合并；"
    "同一种图标如果重复出现也要分别列出或累加数量。\n"
    "只输出一个 JSON 数组：[{\"name\": \"红色气球\", \"appearance\": \"红色圆形气球\", \"count\": 7}, ...]，"
    "不要输出任何其他内容。"
)

PROMPT_A = (
    "你是一名赛事成绩录入助手。我会给你两张图：\n"
    "第一张是【异象图鉴】：上面陈列了所有可能的异象图标，每个图标左上角有编号（#1、#2...），"
    "下方有名称和分值。\n"
    "第二张是《第五人格》娱乐赛的【单场结算截图】：其中「击败异象」栏陈列了若干个异象图标，"
    "每个图标右下角或旁边有数字（x7、×7、x1 或直接数字）表示数量。\n"
    "请把结算图中的每个图标与【异象图鉴】逐一对照，找出它对应图鉴中的编号，并读取右下角的数量。\n"
    "【重要】异象图标可能排成【一行或两行】！请逐行从左到右扫描，先第一行再第二行，"
    "确保整栏中每一个图标都被读到，绝对不能遗漏。\n"
    "只输出一个 JSON 数组：[{\"id\": 1, \"count\": 7}, ...]，id 是图鉴编号（1开始）。"
    "不要输出任何其他内容。"
)


def _call(messages, image_paths):
    content = [{"type": "text", "text": messages}]
    for p in image_paths:
        content.append({"type": "image_url", "image_url": {"url": _encode_image(str(p))}})
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": "你是严格的 JSON 输出助手。"},
                     {"role": "user", "content": content}],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    import requests
    resp = requests.post(f"{base_url}/chat/completions",
                         headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                         json=payload, timeout=120)
    if resp.status_code != 200:
        return f"ERR {resp.status_code} {resp.text[:150]}"
    c = resp.json()["choices"][0]["message"]["content"].strip()
    if c.startswith("```"):
        c = c.strip("`")
        if c.startswith("json"):
            c = c[4:]
    return c


def parse_B(content, icons):
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return f"解析失败: {content[:120]}"
    items = data.get("icons", []) if isinstance(data, dict) else data
    detail, total = [], 0.0
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
        for d in detail:
            if d["name"] == matched:
                d["count"] += cnt
                d["sub"] = round(d["score"] * d["count"], 2)
                total += icons[matched][0] * cnt
                break
        else:
            sub = round(icons[matched][0] * cnt, 2)
            detail.append({"name": matched, "count": cnt, "score": icons[matched][0], "sub": sub})
            total += sub
    return f"总分={round(total,2)} 明细={detail}"


def parse_A(content, icons):
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return f"解析失败: {content[:120]}"
    items = data.get("icons", []) if isinstance(data, dict) else data
    names = sorted(icons)
    detail, total = [], 0.0
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict):
            continue
        try:
            iid = int(float(str(it.get("id", 0))))
            cnt = int(float(str(it.get("count", 0))))
        except (TypeError, ValueError):
            continue
        if not (1 <= iid <= len(names)) or cnt <= 0:
            continue
        matched = names[iid - 1]
        for d in detail:
            if d["name"] == matched:
                d["count"] += cnt
                d["sub"] = round(d["score"] * d["count"], 2)
                total += icons[matched][0] * cnt
                break
        else:
            sub = round(icons[matched][0] * cnt, 2)
            detail.append({"name": matched, "count": cnt, "score": icons[matched][0], "sub": sub})
            total += sub
    return f"总分={round(total,2)} 明细={detail}"


if __name__ == "__main__":
    icons = load_icons()
    sheet = build_icon_sheet()
    tests = [
        ("测试2（八种异象，分数为38.5）.jpeg", 38.5),
        ("测试3（6种异象，分数52）.jpeg", 52),
        ("测试4（7种异象，分数43.5）.jpeg", 43.5),
    ]
    for fname, expect in tests:
        fpath = Path(__file__).resolve().parent.parent / "example" / fname
        print(f"===== {fname} 期望={expect} =====")
        print(" [方式B-增强] ", parse_B(_call(PROMPT_B, [fpath]), icons))
        print(" [方式A-图鉴] ", parse_A(_call(PROMPT_A, [fpath, sheet]), icons))
        print()
