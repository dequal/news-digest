#!/usr/bin/env python3
"""generate_hero.py — 生成固定尺寸的每日头条 Hero 大图 (960x400 PNG)"""

from PIL import Image, ImageDraw, ImageFont
import os, sys, glob

WIDTH, HEIGHT = 960, 400

def _find_font(patterns):
    """按顺序查找第一个存在的字体文件"""
    for p in patterns:
        matches = glob.glob(p)
        if matches:
            return matches[0]
    return None

# macOS / Linux 通用字体路径
_FONT_PATTERNS_BOLD = [
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
]
_FONT_PATTERNS_LIGHT = [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/arphic/ukai.ttc",
]

def _load_font(path, size):
    """安全加载字体，失败返回默认字体"""
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def make_gradient(w, h):
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    colors = [(26, 35, 126), (26, 115, 232), (0, 135, 90), (197, 34, 31)]
    seg = w // (len(colors) - 1)
    for i in range(w):
        t = i / seg
        idx = min(int(t), len(colors) - 2)
        lt = t - idx
        c1, c2 = colors[idx], colors[idx + 1]
        fill = tuple(int(c1[j]+(c2[j]-c1[j])*lt) for j in range(3))
        draw.line([(i, 0), (i, h)], fill=fill)
    return img

def draw_wrapped(draw, text, x, y, max_w, font, fill):
    lines, cur = [], ""
    for ch in text:
        test = cur + ch
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_w:
            lines.append(cur); cur = ch
        else:
            cur = test
    if cur: lines.append(cur)
    for i, ln in enumerate(lines):
        draw.text((x, y + i * (font.size + 8)), ln, font=font, fill=fill)
    return len(lines) * (font.size + 8)

def generate(title, date_str, output_path):
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    img = make_gradient(WIDTH, HEIGHT).convert("RGBA")
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 60))
    img = Image.alpha_composite(img, overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    draw.line([(60, 80), (140, 80)], fill=(255, 255, 255), width=3)

    font_d = _load_font(
        _find_font(_FONT_PATTERNS_LIGHT) or _FONT_PATTERNS_LIGHT[0], 22)
    draw.text((60, 92), f"DAILY BRIEFING · {date_str}", font=font_d, fill=(255, 255, 255))

    font_t = _load_font(
        _find_font(_FONT_PATTERNS_BOLD) or _FONT_PATTERNS_BOLD[0], 40)
    draw_wrapped(draw, title, 60, 155, WIDTH - 120, font_t, (255, 255, 255))

    draw.line([(60, HEIGHT - 80), (WIDTH - 60, HEIGHT - 80)], fill=(255, 255, 255, 80), width=1)
    font_b = _load_font(
        _find_font(_FONT_PATTERNS_LIGHT) or _FONT_PATTERNS_LIGHT[0], 15)
    draw.text((60, HEIGHT - 58), "每日新闻精选 · GLOBAL NEWS NETWORK", font=font_b, fill=(255, 255, 255))
    draw.text((WIDTH - 320, HEIGHT - 58), "由 阿尔法的1号机器人 自动生成", font=font_b, fill=(255, 255, 255))
    draw.rectangle([(0, HEIGHT - 5), (WIDTH, HEIGHT)], fill=(255, 255, 255))

    img.save(output_path, "PNG", optimize=True)
    return output_path

if __name__ == "__main__":
    from datetime import datetime, timezone, timedelta
    TZ = timezone(timedelta(hours=8))
    now = datetime.now(TZ)
    date_str = now.strftime("%Y年%m月%d日")
    title = sys.argv[1] if len(sys.argv) > 1 else "每日新闻精选"
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "output", f"hero_{now.strftime('%Y%m%d')}.png")
    print(generate(title, date_str, out))
