"""通用视觉大模型识别模块（OpenAI 兼容接口）

支持服务商（只需设置环境变量）：
  VISION_API_KEY   - API Key
  VISION_BASE_URL  - OpenAI 兼容 base_url
  VISION_MODEL     - 模型名

各家推荐配置示例：
  智谱AI（免费 glm-4v-flash）:
    VISION_BASE_URL=https://open.bigmodel.cn/api/paas/v4
    VISION_MODEL=glm-4v-flash
  阿里百炼 qwen-vl-plus:
    VISION_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
    VISION_MODEL=qwen-vl-plus
  硅基流动 Qwen2.5-VL-7B（免费）:
    VISION_BASE_URL=https://api.siliconflow.cn/v1
    VISION_MODEL=Qwen/Qwen2.5-VL-7B-Instruct
  火山豆包:
    VISION_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
    VISION_MODEL=你的接入点ID
  OpenAI:
    VISION_BASE_URL=https://api.openai.com/v1
    VISION_MODEL=gpt-4o-mini
"""
import base64
import io
import json
import math
import os
import re
from collections import defaultdict
from pathlib import Path

import requests


def _load_dotenv():
    """启动时自动加载 backend/.env，保证任何方式启动后端都能使用视觉 AI 配置"""
    env_file = Path(__file__).resolve().parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if not os.environ.get(key):
            os.environ[key] = value


_load_dotenv()

PROMPT = (
    "你是一名赛事成绩录入助手。用户会给你一张《第五人格·摸金搜打撤》娱乐赛的战绩截图。\n"
    "请仔细查看图片，找出并读取以下三个数值（每个数值必须紧挨着对应标签，不要读取距离标签较远的数字）：\n"
    "1. 探索价值：标注「探索价值」的数值（本局总价值，通常较大）\n"
    "2. 带出价值：标注「带出价值」的数值\n"
    "3. 击败异象：标注「击败异象」的数值，它是带\"个\"字的小整数（写法如\"12个\"），"
    "位置在该标签旁或下方；请务必完整读出这个数字，不要遗漏\n"
    "若页面是战绩列表/汇总页（一屏出现多场战绩，无法找到单场的「带出价值」「击败异象」）："
    "explore_value 取列表中最新一场（通常在最上方）的「探索价值」，takeout_value 和 kills 输出 null。\n"
    "请严格只输出一个 JSON 对象："
    '{"explore_value": 数字, "takeout_value": 数字, "kills": 整数}。'
    "找不到的字段输出 null。不要输出任何其他内容。"
)


def is_configured() -> bool:
    return bool(os.environ.get("VISION_API_KEY") and os.environ.get("VISION_MODEL"))


def _encode_image(path: str) -> str:
    ext = Path(path).suffix.lower().lstrip(".") or "png"
    if ext == "jpg":
        ext = "jpeg"
    return f"data:image/{ext};base64,{base64.b64encode(Path(path).read_bytes()).decode()}"


def _post_chat(payload: dict, timeout: int = 60) -> str:
    """发送 chat/completions 请求并返回清洗后的文本内容。

    任何网络异常 / 非 200 / 响应结构异常统一抛 RuntimeError，
    由上层回退处理，避免裸 500 崩溃。
    """
    base_url = os.environ["VISION_BASE_URL"].rstrip("/")
    key = os.environ["VISION_API_KEY"]
    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
            timeout=timeout,
        )
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"视觉AI请求失败: {e}")
    if resp.status_code != 200:
        raise RuntimeError(f"视觉AI接口错误({resp.status_code}): {resp.text[:200]}")
    try:
        content = resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        raise RuntimeError(f"视觉AI返回格式异常: {e}")
    if content is None:
        raise RuntimeError("视觉AI返回内容为空")
    if not isinstance(content, str):
        content = str(content)
    content = content.strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.startswith("json"):
            content = content[4:]
    return content


def analyze_image(path: str) -> dict:
    """调用视觉大模型识别战绩图，返回结构化字段。

    失败时抛出 RuntimeError。
    """
    if not is_configured():
        raise RuntimeError("未配置视觉 AI（缺少 VISION_API_KEY / VISION_MODEL）")

    model = os.environ["VISION_MODEL"]

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是严格的 JSON 输出助手。"},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url", "image_url": {"url": _encode_image(path)}},
                ],
            },
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    content = _post_chat(payload, timeout=60)
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, ValueError):
        raise RuntimeError(f"视觉AI返回无法解析: {content[:200]}")

    def num(v):
        if v is None or v == "":
            return None
        try:
            return float(str(v).replace(",", "").replace("，", ""))
        except (ValueError, TypeError):
            return None

    return {
        "explore_value": num(data.get("explore_value")),
        "takeout_value": num(data.get("takeout_value")),
        "kills": num(data.get("kills")),
        "raw_text": f"[视觉AI识别] {content}",
    }


LIST_PROMPT = (
    "你是一名赛事成绩录入助手。用户会给你一张《第五人格·摸金搜打撤》娱乐赛的【战绩列表截图】，"
    "即一屏展示多场战绩记录。\n"
    "请逐场识别，输出 JSON 对象：\n"
    '{"matches": [{"time": "08/08 00:22", "explore_value": 468000}, ...]}，\n'
    "其中 time 为该场战绩的日期时间（格式：月/日 时:分，如 \"08/08 00:22\"，注意月/日/时请补零为两位），"
    "explore_value 为该场探索价值（纯数字，去掉千分位逗号）。\n"
    "请只列出有探索价值的场次，忽略无法读取数值的条目；只输出这一个 JSON，不要输出任何其他内容。"
)


def analyze_list(path: str) -> list:
    """调用视觉大模型识别战绩列表截图，返回每场战绩列表。

    返回: [{"time": "08/08 00:22", "explore_value": 468000}, ...]
    失败时抛出 RuntimeError。
    """
    if not is_configured():
        raise RuntimeError("未配置视觉 AI（缺少 VISION_API_KEY / VISION_MODEL）")

    model = os.environ["VISION_MODEL"]

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是严格的 JSON 输出助手。"},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": LIST_PROMPT},
                    {"type": "image_url", "image_url": {"url": _encode_image(path)}},
                ],
            },
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    content = _post_chat(payload, timeout=90)
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, ValueError):
        raise RuntimeError(f"视觉AI返回无法解析: {content[:200]}")

    matches = data.get("matches", []) if isinstance(data, dict) else data
    result = []
    if isinstance(matches, list):
        for m in matches:
            if not isinstance(m, dict):
                continue
            time_str = str(m.get("time", "")).strip()
            v = m.get("explore_value")
            try:
                value = float(str(v).replace(",", "").replace("，", "").strip())
            except (ValueError, TypeError):
                value = None
            if time_str and value is not None:
                result.append({"time": time_str, "explore_value": value})
    return result


# ============================================================
# 击败异象：图标种类识别 + 分值累加
# ============================================================

_ICON_RE = re.compile(r"^(.*?)_(\d+(?:\.\d+)?)\.jpg$")


def load_icons() -> "dict[str, tuple[float, Path]]":
    """从 example 目录读取异象图标库：{名称: (分值, 图片路径)}。

    文件命名规则：名字_分值.jpg，例如 盗匪_1.jpg、叹息球_1.5.jpg。
    """
    example_dir = Path(__file__).resolve().parent.parent / "example"
    icons: dict[str, tuple[float, Path]] = {}
    for p in sorted(example_dir.glob("*.jpg")):
        m = _ICON_RE.match(p.name)
        if not m:
            continue
        name = m.group(1).strip()
        try:
            score = float(m.group(2))
        except ValueError:
            continue
        if "测试" in name:
            continue
        icons[name] = (score, p)
    return icons


def _sheet_cache_path() -> Path:
    return Path(__file__).resolve().parent / "icon_sheet.jpg"


def build_icon_sheet(force: bool = False) -> Path:
    """把 13 张异象图标拼成一张带编号的图鉴图，用于视觉AI对照识别。

    若 example 目录图标有更新（目录 mtime 晚于缓存），自动重建。
    返回拼图文件路径。
    """
    from PIL import Image, ImageDraw, ImageFont

    icons = load_icons()
    if not icons:
        raise RuntimeError("example 目录未找到异象图标（需按 名字_分值.jpg 命名）")

    sheet_path = _sheet_cache_path()
    if not force and sheet_path.exists():
        example_dir = icons[next(iter(icons))][1].parent
        if sheet_path.stat().st_mtime >= example_dir.stat().st_mtime:
            return sheet_path

    cell_w, cell_h = 168, 210
    cols = 7
    rows = math.ceil(len(icons) / cols)
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), (18, 16, 24))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 24)
        font_num = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20)
    except OSError:
        font = font_num = ImageFont.load_default()

    for i, (name, (score, img_path)) in enumerate(icons.items()):
        col, row = i % cols, i // cols
        x, y = col * cell_w, row * cell_h
        # 编号
        draw.text((x + 10, y + 6), f"#{i + 1}", fill=(212, 175, 55), font=font_num)
        # 名称+分值
        label = f"{name} {score}分"
        draw.text((x + 10, y + cell_h - 28), label, fill=(230, 224, 240), font=font_num)
        img = Image.open(img_path).convert("RGBA")
        img.thumbnail((cell_w - 24, cell_h - 70))
        sheet.paste(
            img,
            (x + (cell_w - img.width) // 2, y + 36),
            img if img.mode == "RGBA" else None,
        )
    sheet.save(sheet_path, quality=92)
    return sheet_path


# 逐格扫描 prompt：强制 AI 按“第几行第几列”逐格输出，能显著减少漏行/漏图标
DETAIL_KILLS_PROMPT = (
    "这是一张《第五人格》娱乐赛结算截图的【图标区放大图】。\n"
    "请找到「击败异象」图标栏（由多个小图标卡片组成，每个卡片上有图标，右下角/旁边有数字表示数量）。\n"
    "【极其重要】请先确认图标栏共有几行、每行几个图标，然后严格【逐行逐列】扫描，绝不遗漏任何一格。\n"
    "对每个图标输出：\n"
    '- row：第几行（从1开始）\n'
    '- col：第几列（从1开始，从左到右）\n'
    '- name：图标名称（参考：叹息球、异色叹息球、贪婪的盗匪、异色贪婪的盗匪、盗匪、'
    '缄默的绅士、失职的看守、异色失职的看守、镜中回忆、厄运替身、旗杆阴兵、号角阴兵、故纸堆）\n'
    '- appearance：图标外观（颜色+形状+特征，例如“灰色身体戴帽子”“蓝色镜子”）\n'
    '- count：图标右下角/旁边的数字（若看不到数字则填1）\n'
    "只输出 JSON 数组：[{\"row\":1,\"col\":1,\"name\":\"...\",\"appearance\":\"...\",\"count\":1}, ...]"
    "，不要输出任何其他内容。"
)


KILLS_PROMPT_TEMPLATE = (
    "你是一名赛事成绩录入助手。用户给你一张《第五人格》娱乐赛的【单场结算截图】。\n"
    "请找到「击败异象」栏（通常在左侧“本局记录”下方）。该栏会陈列若干个异象图标，"
    "每个图标右下角或旁边有一个数字（可能写成 x7、×7、x1 或直接是数字），表示该异象的数量。\n"
    "【非常重要】异象图标可能排成【一行、两行甚至三行】！请先仔细观察：这栏里共有几行图标、"
    "每行有几个图标。然后严格【逐行、从左到右】扫描——先完整读出第一行的所有图标，"
    "再完整读出第二行、第三行的所有图标，确保整栏中每一个图标都被读到，绝对不能遗漏任何一行，"
    "也不能遗漏行内的任何一个图标。\n"
    "该栏图标来自以下图鉴（输出 name 时请优先使用这些标准名称）：\n"
    "叹息球、异色叹息球、贪婪的盗匪、异色贪婪的盗匪、盗匪、缄默的绅士、"
    "失职的看守、异色失职的看守、镜中回忆、厄运替身、旗杆阴兵、号角阴兵、故纸堆。\n"
    "请逐个列出每个图标：\n"
    "- name：优先使用上面的标准图鉴名称；若确实不属于上述名称，再根据外观给出一个贴切的中文名称"
    "（例如“戴面具的角色”“红色气球”“绿色衣服的老妇人”）；\n"
    "- appearance：用简洁中文描述图标外观，务必包含颜色和形状（例如“红色圆形气球”“穿黑色衣服的角色”）；\n"
    "- count：读取图标右下角/旁边的数字作为数量，请反复确认该数字，千万不要读错或漏读。\n"
    "注意：颜色或衣着不同的图标即使形状相似，也要分成多个条目，不要合并。\n"
    "只输出一个 JSON 数组：[{\"name\": \"红色气球\", \"appearance\": \"红色圆形气球\", \"count\": 7}, ...]，"
    "不要输出任何其他内容。"
)


_ICON_COLOR_RULES = [
    ("异色叹息球", ["红色", "粉红", "粉红色", "红球", "红色球"]),
    ("异色贪婪的盗匪", ["黑色", "黑衣", "暗色", "深色", "异色", "白色", "白衣", "白发", "灰白"]),
    ("异色失职的看守", ["黑色", "黑衣", "暗色", "深色", "异色", "白色", "白衣", "白发", "灰白"]),
]

# 外观关键词 → 图鉴名（按顺序命中，越靠前优先级越高）。
# 用于把 AI 描述中的模糊说法（如“灰衣老人”“蓝光宝箱”）转正为图鉴标准名。
_ICON_APPEARANCE_RULES = [
    ("镜中回忆", ["镜子", "镜中", "倒影", "光晕", "蓝色镜子"]),
    ("缄默的绅士", ["西装", "礼帽", "绅士", "燕尾服", "领结", "拄拐"]),
    ("故纸堆", ["书", "羊皮纸", "纸张", "卷轴", "卷宗", "文件", "书本"]),
    ("厄运替身", ["骷髅", "白骨", "人偶", "木偶", "娃娃", "破旧衣服"]),
    ("旗杆阴兵", ["旗帜", "旗杆", "扛旗", "持旗", "挥旗", "拿旗"]),
    ("号角阴兵", ["号角", "喇叭", "吹号", "拿号角"]),
    ("叹息球", ["球形", "球体", "圆球", "地球仪", "灰色球"]),
    ("异色叹息球", ["粉色球", "粉球", "粉红球", "红色球", "红球"]),
    ("失职的看守", ["幽灵", "守墓", "守墓人", "灰衣老人", "灰袍", "白袍", "白发老人", "白头发", "蓝甲", "蓝色盔甲", "蓝色幽灵", "蓝色身体", "盔甲", "头盔"]),
    ("异色失职的看守", ["蓝光", "蓝色发光", "发光宝箱", "绿甲", "绿色盔甲", "兜帽"]),
    ("贪婪的盗匪", ["骷髅面具", "骷髅头面具", "绿裤子", "绿背心", "绿色背心", "绿色裤子"]),
    ("异色贪婪的盗匪", ["绿衣", "绿色衣服", "绿色皮肤", "绿色身体", "绿色头发", "绿发", "绿色上衣"]),
    ("盗匪", ["木棍", "棍棒", "黄面具", "黄色面具", "棕色身体", "棕色面具", "棕面具", "戴帽子", "褐色"]),
]


def _best_icon_match(name: str, appearance: str, icons: dict) -> "str | None":
    """根据 AI 给出的 name + appearance，匹配图鉴中最合适的图标名。"""
    if not name and not appearance:
        return None
    text = f"{name} {appearance}"
    # 0) 颜色变体优先：出现颜色词且对应基础名也在文本中
    for variant, colors in _ICON_COLOR_RULES:
        if any(c in text for c in colors):
            base_of_variant = variant.replace("红色", "").replace("异色", "")
            if base_of_variant in text:
                return variant
    # 1) 完整图鉴名出现在 name/appearance 中（按名称长度降序，取最具体者）
    cand = [n for n in icons if n in text]
    if cand:
        best = max(cand, key=len)
        # 1.5) 颜色纠偏：AI 常按外观颜色叫错变体。
        # 贪婪的盗匪是绿/黑衣着；若外观是棕/黄色调，实际是普通盗匪。
        if best == "贪婪的盗匪" and any(
            c in appearance for c in ("棕色", "褐色", "黄色", "棕身", "黄身")
        ):
            return "盗匪"
        # 盗匪若为黑色/深色调，实为贪婪的盗匪或异色贪婪的盗匪
        if best == "盗匪" and any(c in appearance for c in ("黑色", "黑色身体", "黑衣", "深色")):
            return "贪婪的盗匪"
        return best
    # 2) 名称 alias 匹配
    matched = _match_icon_name(name, icons)
    if matched:
        return matched
    # 3) 外观关键词转正（把 AI 的模糊描述映射到图鉴标准名）
    for icon_name, keywords in _ICON_APPEARANCE_RULES:
        if any(k in text for k in keywords):
            return icon_name
    return None


def _match_icon_name(name: str, icons: dict) -> "str | None":
    """名称匹配：精确 → 包含（icon 名在 name 中或 name 在 icon 名中）"""
    if not name:
        return None
    if name in icons:
        return name
    for icon_name in icons:
        if icon_name in name or name in icon_name:
            return icon_name
    # 去除常见误加/误减字再匹配
    for alias in (name.replace("的", ""), name.replace("笨拙的", ""), name.replace("普通", "")):
        if alias and alias in icons:
            return alias
    return None


def _call_kills_once(pil_image, prompt: str = None, temperature: float = 0.0) -> str:
    """单次调用视觉大模型，返回模型原始文本（自动解析 ```json 包裹）。"""
    model = os.environ["VISION_MODEL"]

    # 图片编码：PIL Image 直接转 PNG base64
    if hasattr(pil_image, "save"):
        buf = io.BytesIO()
        pil_image.save(buf, format="PNG")
        url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    else:
        url = _encode_image(str(pil_image))

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是严格的 JSON 输出助手。"},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt or KILLS_PROMPT_TEMPLATE},
                    {"type": "image_url", "image_url": {"url": url}},
                ],
            },
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    return _post_chat(payload, timeout=120)


def _parse_kills_once(content: str) -> dict:
    """解析模型返回的 JSON，匹配图鉴，返回 {名称: 数量} 计数字典。"""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise RuntimeError(f"视觉AI返回无法解析: {content[:200]}")

    icons = load_icons()
    raw_items = data.get("icons", []) if isinstance(data, dict) else data
    if not isinstance(raw_items, list):
        raw_items = []
    counts: dict[str, int] = {}
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        appearance = str(item.get("appearance", "")).strip()
        matched = _best_icon_match(name, appearance, icons)
        if not matched:
            continue
        try:
            count = int(float(str(item.get("count", 0))))
        except (TypeError, ValueError):
            count = 0
        if count <= 0:
            continue
        counts[matched] = counts.get(matched, 0) + count
    return counts


def _analyze_kills_once(path: str, temperature: float = 0.0) -> dict:
    """单次调用视觉大模型识别【击败异象】图标栏，返回标准结构。"""
    content = _call_kills_once(path, temperature=temperature)
    counts = _parse_kills_once(content)
    detail = []
    total = 0.0
    _icons = load_icons()
    for matched, count in counts.items():
        info = _icons.get(matched)
        if not info:
            continue
        score = info[0]
        sub = round(score * count, 2)
        detail.append({"name": matched, "count": count, "score": score, "sub": sub})
        total += sub
    return {
        "kills_score": round(total, 2),
        "kills_total": sum(counts.values()),
        "kills_detail": detail,
        "raw_text": f"[视觉AI识别] {content}",
    }


# 同一图标在 AI 描述中可能被叫成不同名称（如“盗匪” vs “贪婪的盗匪”），
# 需要归并到同一族内做一致性判断
_KILL_FAMILIES: list[tuple[str, ...]] = [
    ("盗匪", "贪婪的盗匪", "异色贪婪的盗匪"),
    ("失职的看守", "异色失职的看守"),
    ("叹息球", "异色叹息球"),
]


def _robust_max(counts: list) -> int:
    """多视角计数稳健合并：
    - 单视角：直接采用（补漏优先，条带放大常能识别整图漏掉的图标）；
    - 多视角：取最大（多个独立视角都识别到同一图标，说明真实存在；
      数量本身模型就常低估，取上限最接近真实值）。
    不再做“尖峰抑制”：它会把真实的多数量图标（如 x4）误当幻觉压成 1。
    """
    if not counts:
        return 0
    return max(counts)


def _merge_kills_counts(views: list[dict]) -> dict:
    """多视角合并：
    - 对同一族内（基础名相同）的图标：若某视角同时出现多个变体 → 全部保留（真实共存）；
      否则视为命名漂移，取出现频次最高的那个变体。
    - 族外图标取各视角稳健最大计数。
    """
    if not views:
        return {}
    fam_of = {}
    for fam in _KILL_FAMILIES:
        for m in fam:
            fam_of[m] = fam

    fam_presence: dict[tuple, list[set]] = {fam: [set() for _ in views] for fam in _KILL_FAMILIES}
    for vi, v in enumerate(views):
        for name in v:
            fam = fam_of.get(name)
            if fam:
                fam_presence[fam][vi].add(name)

    merged: dict[str, int] = {}
    handled = set()
    for fam in _KILL_FAMILIES:
        # 是否某视角同时看到该族多个变体（真实共存）
        coexist = any(len(s) >= 2 for s in fam_presence[fam])
        if coexist:
            # 共存：保留族内所有被识别出的变体
            for m in fam:
                cnts = [v[m] for v in views if m in v]
                if cnts:
                    merged[m] = _robust_max(cnts)
                    handled.add(m)
        else:
            # 漂移：族内只保留一个变体（其余变体视为同一图标的命名漂移）
            best = max(fam, key=lambda m: sum(1 for v in views if m in v))
            cnts = [v[best] for v in views if best in v]
            if cnts:
                merged[best] = _robust_max(cnts)
            # 族内【所有】变体都标记已处理，防止在族外循环里被重复计分
            for m in fam:
                handled.add(m)
    # 族外图标：取稳健最大计数
    for vi, v in enumerate(views):
        for name, cnt in v.items():
            if name not in handled:
                merged[name] = max(merged.get(name, 0), _robust_max([v[name] for v in views if name in v]))
    return merged


def _crop_bands(path: str) -> list:
    """把结算截图从底部向上切成若干条带（图标栏通常在下半部，且常排两行），
    返回已放大的 PIL Image 列表。"""
    from PIL import Image

    img = Image.open(path).convert("RGB")
    w, h = img.size
    # 图标栏位置因截图布局而异：横向大图约在 45%-81%，竖版约在 62%-97%。
    # 上半部(45%-62%)常混入“本局收获/战利品”列表（金色鱼形物品、书页等），
    # 会被误当成异象，因此条带只从 62% 起切，避开战利品区。
    bands = []
    for (y0, y1) in [(0.62, 0.85), (0.72, 1.0)]:
        band = img.crop((0, int(h * y0), w, int(h * y1)))
        if band.size[0] > 400:
            band = band.resize((band.size[0] * 2, band.size[1] * 2), Image.LANCZOS)
        bands.append(band)
    return bands


def analyze_kills_icons(path: str, samples: int = 2, multi_view: bool = True) -> dict:
    """调用视觉大模型识别结算图的【击败异象】图标栏。

    视觉大模型存在随机性，且误差多为“低估”（漏识别/合并/把高分局认成低分）。
    因此：
    1. 整图采样 samples 次（取总分最大的一次）；
    2. 若 multi_view，再对底部条带放大各识别 1 次；
    3. 全部视角做“族去抖 + 取最大计数”合并，最大限度补漏且避免命名漂移重复计分。

    返回: {
        "kills_score": float,      # 异象总分 Σ(分值×数量)
        "kills_total": int,        # 异象总个数 Σ数量
        "kills_detail": [{"name","count","score","sub"}],  # 图标明细
        "raw_text": str,
    }
    失败时抛出 RuntimeError。
    """
    if not is_configured():
        raise RuntimeError("未配置视觉 AI（缺少 VISION_API_KEY / VISION_MODEL）")

    views: list[dict] = []
    raw_texts = []
    last_err = None
    # 1) 整图采样（小温度扰动增加多样性，尽量覆盖不同漏读组合）
    _TEMPS = (0.0, 0.3, 0.7)
    for i in range(max(1, samples)):
        try:
            content = _call_kills_once(path, temperature=_TEMPS[i % len(_TEMPS)])
            views.append(_parse_kills_once(content))
            raw_texts.append(f"[整图#{i+1}] {content}")
        except Exception as e:
            last_err = e
            continue
    # 2) 图标区放大 + 逐格扫描（强制 row/col，对“两行”布局补漏最有效）
    if multi_view:
        try:
            from PIL import Image as _PILImage

            _img = _PILImage.open(path).convert("RGB")
            _w, _h = _img.size
            region = _img.crop((0, int(_h * 0.55), _w, _h))
            if region.size[0] > 400:
                region = region.resize((region.size[0] * 2, region.size[1] * 2), _PILImage.LANCZOS)
            for i in range(2):
                try:
                    content = _call_kills_once(region, prompt=DETAIL_KILLS_PROMPT, temperature=_TEMPS[i % len(_TEMPS)])
                    views.append(_parse_kills_once(content))
                    raw_texts.append(f"[逐格#{i+1}] {content}")
                except Exception as e:
                    last_err = e
                    continue
        except Exception as e:
            last_err = RuntimeError(f"裁剪图标区失败: {e}")
        # 3) 底部条带放大（覆盖不同纵向范围）
        try:
            for j, band in enumerate(_crop_bands(path)):
                try:
                    content = _call_kills_once(band, temperature=0.0)
                    views.append(_parse_kills_once(content))
                    raw_texts.append(f"[条带#{j+1}] {content}")
                except Exception as e:
                    last_err = e
                    continue
        except Exception as e:
            last_err = RuntimeError(f"裁剪条带失败: {e}")

    if not views:
        raise RuntimeError(f"视觉AI识别击败异象失败: {last_err}")

    merged = _merge_kills_counts(views)
    icons = load_icons()
    detail = []
    total = 0.0
    for matched, count in merged.items():
        info = icons.get(matched)
        if not info:
            continue
        score = info[0]
        sub = round(score * count, 2)
        detail.append({"name": matched, "count": count, "score": score, "sub": sub})
        total += sub
    return {
        "kills_score": round(total, 2),
        "kills_total": sum(merged.values()),
        "kills_detail": detail,
        "raw_text": "\n".join(raw_texts),
    }
