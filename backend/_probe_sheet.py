"""让 AI 逐格描述图鉴图标特征，建立 特征关键词→图标名 映射"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vision_api as va
import json

# 用图鉴拼图让 AI 描述每个图标
sheet = va.build_icon_sheet(force=True)
icons = va.load_icons()
names = list(icons.keys())
print("图标:", names, flush=True)

PROMPT_DESC = (
    "这是《第五人格》娱乐赛的【异象图标图鉴】，共 %d 个格子，每个格子左上角有 #编号，下方有名称和分值。\n"
    "请逐个仔细查看每个图标（编号 #1 到 #%d），用简洁中文描述图标外观，"
    "必须包含：主要颜色、形状、人物/物品类型、最显著特征（如手持物品、衣着、颜色差异）。\n"
    "只输出 JSON 数组：[{\"id\": 1, \"desc\": \"图标外观描述\"}, ...]，不要输出其他内容。"
) % (len(names), len(names))

try:
    content = va._call_kills_once(sheet, prompt=PROMPT_DESC, temperature=0.0)
    print(content, flush=True)
    data = json.loads(content)
    items = data if isinstance(data, list) else data.get("icons", [])
    mapping = {}
    for it in items:
        iid = int(it.get("id", 0))
        if 1 <= iid <= len(names):
            mapping[names[iid - 1]] = it.get("desc", "")
    print("\n=== 特征映射 ===", flush=True)
    for n in names:
        print(f"  {n}: {mapping.get(n, '??')}", flush=True)
    with open("_tmp/sheet_desc.json", "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
except Exception as e:
    print("ERR", e, flush=True)
