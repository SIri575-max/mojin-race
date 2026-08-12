# -*- coding: utf-8 -*-
"""生成 ZUL蓝宝石杯 透明文字 logo（金色渐变 + 蓝宝石蓝点缀）"""
from PIL import Image, ImageDraw, ImageFont
import os, math

OUT = os.path.join(os.path.dirname(__file__), "..", "frontend", "logo_web.png")

def find_font(*names, size=100):
    for n in names:
        p = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", n)
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

W, H = 1200, 360
img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

font_en = find_font("georgia.ttf", "Georgia.ttf", "arialbd.ttf", "timesbd.ttf", size=170)
font_cn = find_font("msyhbd.ttc", "msyh.ttc", "simhei.ttf", "simsun.ttc", size=150)

def gold_gradient_text(draw, xy, text, font, fill_top=(247, 231, 168), fill_bottom=(212, 175, 55)):
    """沿文字包围盒垂直渐变填充"""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tmp = Image.new("RGBA", (tw + 8, th + 8), (0, 0, 0, 0))
    td = ImageDraw.Draw(tmp)
    td.text((4 - bbox[0], 4 - bbox[1]), text, font=font, fill=(255, 255, 255, 255))
    px = tmp.load()
    for y in range(tmp.size[1]):
        t = y / max(th, 1)
        r = int(fill_top[0] + (fill_bottom[0] - fill_top[0]) * t)
        g = int(fill_top[1] + (fill_bottom[1] - fill_top[1]) * t)
        b = int(fill_top[2] + (fill_bottom[2] - fill_top[2]) * t)
        for x in range(tmp.size[0]):
            a = px[x, y][3]
            if a:
                px[x, y] = (r, g, b, a)
    img.paste(tmp, (xy[0] + 0, xy[1] + 0), tmp)

def draw_text_with_outline(draw, xy, text, font, fill, stroke_fill=(20, 16, 40, 255), stroke=3):
    draw.text(xy, text, font=font, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)

# —— 布局：ZUL（左，英文金色）+ 蓝宝石杯（右，中文蓝白）——
gold_top, gold_bottom = (250, 225, 160), (208, 170, 50)
# ZUL
gold_gradient_text(draw, (40, 60), "ZUL", font_en, gold_top, gold_bottom)
# 小装饰线（分隔符）
draw.line((40, 300, 400, 300), fill=(212, 175, 55, 200), width=3)
# 蓝宝石杯：蓝渐变 + 白描边
cn_text = "蓝宝石杯"
bbox = draw.textbbox((0, 0), cn_text, font=font_cn)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
# 蓝色渐变文本
tmp = Image.new("RGBA", (tw + 8, th + 8), (0, 0, 0, 0))
td = ImageDraw.Draw(tmp)
td.text((4 - bbox[0], 4 - bbox[1]), cn_text, font=font_cn, fill=(255, 255, 255, 255))
px = tmp.load()
for y in range(tmp.size[1]):
    t = y / max(th, 1)
    r = int(140 + (60 - 140) * t)
    g = int(190 + (130 - 190) * t)
    b = int(255 + (210 - 255) * t)
    for x in range(tmp.size[0]):
        a = px[x, y][3]
        if a:
            px[x, y] = (r, g, b, a)
img.paste(tmp, (440, 50), tmp)

# 顶部细金字副标
sub = "SAPPHIRE CUP · 第五人格摸金娱乐赛"
font_sub = find_font("georgia.ttf", "Georgia.ttf", "arial.ttf", size=34)
sub_bbox = draw.textbbox((0, 0), sub, font=font_sub)
sub_w = sub_bbox[2] - sub_bbox[0]
draw.text(((W - sub_w) // 2, 8), sub, font=font_sub, fill=(180, 170, 210, 220))

img.save(OUT)
print("saved:", OUT, img.size)

# 预览检查：非透明像素占比
import collections
c = collections.Counter()
a = img.getchannel("A")
hist = a.histogram()
total = W * H
op = sum(hist[128:])
print(f"透明像素比例={100 - op/total*100:.1f}% 有效内容={op/total*100:.1f}%")
