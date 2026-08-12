import re
import os
import uuid
from pathlib import Path

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_engine = None


def get_engine():
    """懒加载 RapidOCR 引擎，避免导入即占用内存"""
    global _engine
    if _engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _engine = RapidOCR()
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"OCR 引擎加载失败: {e}")
    return _engine


def save_image(data: bytes, ext: str = ".png") -> str:
    fname = f"{uuid.uuid4().hex}{ext}"
    path = UPLOAD_DIR / fname
    path.write_bytes(data)
    return str(path)


def ocr_image(path: str) -> str:
    """识别图片，返回拼接的文本行列表文本"""
    engine = get_engine()
    try:
        result, _ = engine(path)
    except Exception as e:
        raise RuntimeError(f"图片无法识别（可能不是有效图片或已损坏）: {e}") from e
    if not result:
        return ""
    lines = [item[1] for item in result]
    return "\n".join(lines)


def _to_number(text: str):
    """把 OCR 文本转数字，容忍千分位/逗号"""
    text = text.replace(",", "").replace("，", "").replace(" ", "")
    try:
        return float(text)
    except ValueError:
        return None


def _matches_label(s: str, kind: str) -> bool:
    """判断一行文本是否包含对应标签关键词（容忍 OCR 个别字识别错）"""
    s = s.replace(" ", "").replace("\u3000", "")
    if kind == "explore":
        return any(k in s for k in ("探索价值", "探案价值", "探索位", "探亲价值", "探索"))
    if kind == "takeout":
        return any(k in s for k in ("带出价值", "帯出价值", "带出", "采出价值"))
    if kind == "kills":
        return any(k in s for k in ("击败异象", "击败异象", "击败异", "异象", "击败"))
    return False


_LABELS = {
    "explore": ("探索价值", "探索"),
    "takeout": ("带出价值", "带出"),
    "kills": ("击败异象", "异象", "击败"),
}

# 击败异象的行文单位（真实截图为 "12个"）
_KILLS_UNITS = ("个", "只", "名", "位")
# 一场对局击败异象数量上限（超出视为物品价值等干扰数字）
_KILLS_MAX = 500
# 探索价值下限（过滤战绩列表页中 "主页60"、"段位积分-5" 等干扰数字）
_EXPLORE_MIN = 1000


def extract_result(text: str) -> dict:
    """从 OCR 文本中提取探索价值 / 带出价值 / 击败异象

    兼容三种布局：
    - 标签和数字同行："探索价值  12345"
    - 标签与数字分行："探索价值" 下一行 "12345"
    - 击败异象带单位："击败异象" 下一行 "12个"
    """
    explore = None
    takeout = None
    kills = None
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    pending = None  # 最近出现的标签类型，用于"标签行 + 下一行数字"布局

    def try_set(kind, v):
        nonlocal explore, takeout, kills
        if v is None:
            return
        if kind == "explore" and explore is None and v >= _EXPLORE_MIN:
            explore = v
        elif kind == "takeout" and takeout is None:
            takeout = v
        elif kind == "kills" and kills is None and 0 <= v <= _KILLS_MAX:
            kills = int(v)

    for s in lines:
        # 先判断该行属于哪个标签
        cur_label = None
        for kind, kws in _LABELS.items():
            if any(k in s for k in kws):
                cur_label = kind
                break

        if cur_label:
            # 同行提取：标签后紧跟数字
            m = re.search(r"[\d][\d,，.\s]*", s)
            if m:
                label_end = max(s.find(k) + len(k) for k in _LABELS[cur_label] if s.find(k) >= 0)
                if 0 <= m.start() - label_end <= 8:
                    try_set(cur_label, _to_number(m.group(0)))
            pending = cur_label
            continue

        v = None
        # 纯数字行：归属到 pending 标签
        if re.fullmatch(r"[\d,，.\s]+", s):
            v = _to_number(s)
        elif pending == "kills":
            # "数字+单位"行（如 "12个"）：仅击败异象会带单位，且单位须匹配
            m = re.fullmatch(r"([\d,，]+)\s*([\u4e00-\u9fff]+)", s)
            if m and m.group(2) in _KILLS_UNITS:
                v = _to_number(m.group(1))

        if v is None:
            continue
        if pending == "takeout" and takeout is None:
            takeout = v
        elif pending == "kills" and kills is None:
            if 0 <= v <= _KILLS_MAX:
                kills = int(v)
        elif pending == "explore" and explore is None and v >= _EXPLORE_MIN:
            explore = v
        elif explore is None and takeout is None and kills is None and v >= _EXPLORE_MIN:
            explore = v

    return {
        "explore_value": explore,
        "takeout_value": takeout,
        "kills": kills,
        "raw_text": text,
    }


# ---- 战绩列表截图解析 ----

# 匹配 "08/08 00:22" 或 OCR 无空格形式 "08/0800:22"
_LIST_TIME_RE = re.compile(r"(\d{1,2})/(\d{1,2})\s*(\d{1,2}):(\d{2})")


def extract_list_result(text: str) -> list:
    """从战绩列表截图 OCR 文本中解析每场战绩：时间 + 探索价值

    列表截图每场结构（OCR 顺序）：
        08/08 00:22     <- 时间
        468000          <- 探索价值（纯数字，>= _EXPLORE_MIN 才认）
        +30             <- 段位积分变化（非纯数字行，忽略）
    返回: [{"time": "08/08 00:22", "explore_value": 468000}, ...]
    """
    matches = []
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    current_time = None
    for line in lines:
        m = _LIST_TIME_RE.search(line)
        if m:
            current_time = f"{int(m.group(1)):02d}/{int(m.group(2)):02d} {int(m.group(3)):02d}:{m.group(4)}"
            continue
        if current_time and re.fullmatch(r"[\d,，.\s]+", line):
            v = _to_number(line)
            if v is not None and v >= _EXPLORE_MIN:
                matches.append({"time": current_time, "explore_value": v})
                current_time = None  # 每场只取第一个符合条件的数值
    return matches


# ---- 击败异象图标识别（本地 OCR fallback） ----

# 图标名称（与 example 目录 名字_分值.jpg 对应），按名称长度降序匹配避免子串误命中
_ICON_NAMES_OCR = sorted(
    [
        "异色失职的看守", "异色贪婪的盗匪", "缄默的绅士", "镜中回忆", "旗杆阴兵",
        "红色叹息球", "厄运替身", "失职的看守", "号角阴兵", "贪婪的盗匪",
        "故纸堆", "叹息球", "盗匪",
    ],
    key=len, reverse=True,
)
_ICON_COUNT_RE = re.compile(r"[x×X]\s*(\d+(?:\.\d+)?)|\b(\d+)\s*(?:个|只|名)", re.IGNORECASE)


def extract_kills_icons(text: str) -> dict:
    """本地 OCR 识别击败异象图标：尽力匹配「图标名 + xN」文本行。

    真实结算图中图标下方通常只有小数字（如 x7），本地 OCR 无法把图标和数字可靠关联，
    因此主要作为辅助：识别到「图标名 xN」形式的行才计入。
    返回: {"kills_detail": [{"name","count"}], "kills_total": int, "note": str}
    """
    detail: "dict[str, int]" = {}
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for line in lines:
        m = _ICON_COUNT_RE.search(line)
        if not m:
            continue
        count_raw = m.group(1) or m.group(2)
        if not count_raw:
            continue
        try:
            count = int(float(count_raw))
        except ValueError:
            continue
        if count <= 0 or count > _KILLS_MAX:
            continue
        for name in _ICON_NAMES_OCR:
            if name in line:
                detail[name] = detail.get(name, 0) + count
                break
    if not detail:
        return {"kills_detail": [], "kills_total": None,
                "note": "本地OCR未能可靠关联图标，建议使用视觉AI识别"}
    return {
        "kills_detail": [{"name": k, "count": v} for k, v in detail.items()],
        "kills_total": sum(detail.values()),
        "note": "",
    }
