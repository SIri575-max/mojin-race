from PIL import Image
from pathlib import Path

for p in sorted(Path(r"c:/Users/Lenovo/CodeBuddy/20260807025758/example").glob("测试*.jpeg")):
    img = Image.open(p)
    print(f"{p.name}  size={img.size}")
