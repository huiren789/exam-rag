"""生成 README 首屏演示图：终端风格的真实运行截图。
内容逐字取自 `python -m examrag -q "难度的定义是什么"` 的真实输出。
依赖：Pillow（仅本脚本用，不属于 ExamRAG 运行依赖）。
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "demo.png"

W, H = 1200, 675
BG = (13, 17, 23)
BAR = (32, 38, 48)
CARD = (22, 27, 35)
BORDER = (48, 56, 68)
WHITE = (232, 234, 238)
MUTED = (139, 148, 158)
GREEN = (86, 182, 131)
BLUE = (88, 166, 255)
AMBER = (240, 178, 74)
PURPLE = (163, 143, 231)
CYAN = (86, 204, 204)

F_MONO = "C:/Windows/Fonts/consola.ttf"
F_CJK = "C:/Windows/Fonts/msyh.ttc"


def f(size: int, mono: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(F_MONO if mono else F_CJK, size)


def main() -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # 顶部窗口栏
    d.rectangle([0, 0, W, 46], fill=BAR)
    for x, color in ((24, (255, 95, 86)), (48, (255, 189, 46)), (72, (39, 201, 63))):
        d.ellipse([x, 17, x + 13, 30], fill=color)
    d.text((96, 13), "examrag — 有据可依的课程复习搭档", font=f(16), fill=MUTED)
    d.text((W - 150, 13), "python 3.8+", font=f(14, mono=True), fill=MUTED)

    x0, y0 = 28, 66
    d.rounded_rectangle([x0, y0, W - 28, H - 28], radius=12, fill=CARD, outline=BORDER, width=1)

    px = x0 + 26
    y = y0 + 26

    # 命令（等宽字体不含中文，分段混排渲染）
    d.text((px, y), "$", font=f(20, mono=True), fill=GREEN)
    mono_prefix = 'python -m examrag -q "'
    cx = px + 24
    d.text((cx, y), mono_prefix, font=f(19, mono=True), fill=WHITE)
    cx += d.textlength(mono_prefix, font=f(19, mono=True))
    d.text((cx, y), "难度的定义是什么", font=f(19), fill=WHITE)
    cx += d.textlength("难度的定义是什么", font=f(19))
    d.text((cx, y), '"', font=f(19, mono=True), fill=WHITE)
    y += 42

    # 检索结果行
    d.text((px, y), "检索到", font=f(16), fill=MUTED)
    y += 30
    tags = [
        ("掌握", "难度的定义", GREEN),
        ("理解", "信度的定义", BLUE),
        ("理解", "效度的定义", BLUE),
    ]
    tx = px
    for level, name, color in tags:
        tw = d.textlength(f"{level}·{name}", font=f(17))
        d.rounded_rectangle([tx, y, tx + tw + 22, y + 32], radius=16, fill=(*color,))
        d.text((tx + 11, y + 6), f"{level}·{name}", font=f(17), fill=(13, 17, 23))
        tx += tw + 34
    y += 58

    # 依据句（高亮卖点）
    d.text((px, y), "依据句", font=f(16), fill=MUTED)
    y += 28
    d.rounded_rectangle([px, y, W - 80, y + 74], radius=8, fill=(26, 33, 43), outline=(*CYAN,), width=1)
    d.text((px + 16, y + 12), "掌握·难度的定义", font=f(16), fill=CYAN)
    d.text(
        (px + 16, y + 40),
        "在报告难度时应指明是哪种难度的计算方法……  重合度 3",
        font=f(15),
        fill=WHITE,
    )
    y += 100

    # 分隔线
    d.line([px, y, W - 80, y], fill=BORDER, width=1)
    y += 18

    # 回答
    d.text((px, y), "AI", font=f(16, mono=True), fill=PURPLE)
    y += 30
    answer = [
        "难度是衡量试题难易程度的指标，通常用通过率 P 表示，P=x(均分)/w，P 越大越容易。",
        "另一种写法是 q=1−P，q 越大越难。报告难度时应说明用的是哪一种。",
    ]
    for line in answer:
        d.text((px, y), line, font=f(17), fill=WHITE)
        y += 30
    y += 8
    d.text((px, y), "依据：【掌握·难度的定义】", font=f(16), fill=AMBER)
    y += 42

    # 底部卖点条
    d.line([px, y, W - 80, y], fill=BORDER, width=1)
    y += 16
    highlights = [
        ("本地检索", GREEN),
        ("逐句溯源", CYAN),
        ("核心零依赖", BLUE),
        ("在线可玩 Demo", PURPLE),
    ]
    hx = px
    for text, color in highlights:
        tw = d.textlength(text, font=f(15))
        d.text((hx, y), "●", font=f(15), fill=color)
        d.text((hx + 20, y), text, font=f(15), fill=WHITE)
        hx += tw + 62

    img.save(OUT, "PNG", optimize=True)
    print(f"saved: {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
