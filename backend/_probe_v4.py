"""查看测试4各视角详情"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from vision_api import (_call_kills_once, _parse_kills_once, _crop_bands)

ex = Path(r"c:/Users/Lenovo/CodeBuddy/20260807025758/example")
fname = "测试4（7种异象，分数43.5）.jpeg"
path = str(ex / fname)

for i in range(2):
    c = _call_kills_once(path, temperature=0.3 if i % 2 else 0.0)
    print(f"整图#{i+1}: {_parse_kills_once(c)}")
for j, band in enumerate(_crop_bands(path)):
    c = _call_kills_once(band, temperature=0.0)
    print(f"条带#{j+1}: {_parse_kills_once(c)}")
