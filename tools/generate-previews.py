#!/usr/bin/env python3
"""Render preview.png (desktop mock-up) and preview-unlock.png for a theme.

    python3 tools/generate-previews.py [THEME ...]     # default: every theme
"""
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from palettes import THEMES  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROLES = dict(bg="background", dbg="dark_background", lbg="lighter_background", fg="foreground",
             dfg="dark_foreground", bfg="bright_foreground", sel="selection", muted="muted", red="red",
             yellow="yellow", orange="orange", green="green", cyan="cyan", blue="blue", magenta="magenta",
             brown="brown", accent="accent")
PILOTS = {
    "evangelion": ("Ikari Shinji", "Evangelion Unit-01", "Tokyo-3"),
    "evangelion-unit-02": ("Soryu Asuka Langley", "Evangelion Unit-02", "Berlin"),
    "evangelion-rei": ("Ayanami Rei", "Evangelion Unit-00", "Terminal Dogma"),
    "evangelion-eoe": ("Ikari Gendo", "Lilith", "Geofront"),
}
C = {}
THEME = NAME = SPEC = None


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def use(name):
    global THEME, NAME, SPEC
    NAME, SPEC = name, THEMES[name]
    THEME = os.path.join(ROOT, SPEC["dir"])
    C.clear()
    C.update({k: hexrgb(SPEC["colors"][v]) for k, v in ROLES.items()})
    C["border_a"], C["border_b"] = (hexrgb(SPEC["colors"][r]) for r in SPEC["border"])
    C["alert"] = hexrgb(SPEC["colors"][SPEC["alert"]])
    C["glow"] = hexrgb(SPEC["colors"][SPEC["glow"]])
    C["logo"] = hexrgb(SPEC["colors"][SPEC["logo"]])
    C["brights"] = [hexrgb(SPEC["colors"][k]) for k in
                    ("muted", "bright_red", "bright_green", "bright_yellow", "bright_blue", "bright_magenta", "bright_cyan", "bright_foreground")]


def default_background():
    d = os.path.join(THEME, "backgrounds")
    files = [f for f in os.listdir(d) if f.endswith(".webp")]
    return os.path.join(d, sorted(files, key=lambda f: int(re.match(r"(\d+)", f).group(1)))[0])

MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
JP = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
W, H = 2560, 1440
F = ImageFont.truetype(MONO, 22)
FB = ImageFont.truetype(MONO_B, 22)
LH = 30


def gradient_border(img, box, width=3):
    x0, y0, x1, y1 = box
    a, b = C["border_a"], C["border_b"]
    grad = Image.new("RGB", (x1 - x0, y1 - y0))
    gd = ImageDraw.Draw(grad)
    n = (x1 - x0) + (y1 - y0)
    for i in range(n):
        t = i / n
        col = tuple(int(a[k] + (b[k] - a[k]) * t) for k in range(3))
        gd.line([(i, 0), (i - (y1 - y0), y1 - y0)], fill=col, width=2)
    mask = Image.new("L", grad.size, 0)
    md = ImageDraw.Draw(mask)
    md.rectangle([0, 0, grad.width - 1, grad.height - 1], outline=255, width=width)
    img.paste(grad, (x0, y0), mask)


def window(img, box, alpha=245, glow=False):
    if glow:
        halo = Image.new("RGBA", img.size, (0, 0, 0, 0))
        x0, y0, x1, y1 = box
        ImageDraw.Draw(halo).rectangle([x0 - 4, y0 - 4, x1 + 4, y1 + 4], outline=C["glow"] + (170,), width=14)
        halo = halo.filter(ImageFilter.GaussianBlur(14))
        img.alpha_composite(halo)
    over = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(over).rectangle(box, fill=C["bg"] + (alpha,))
    img.alpha_composite(over)
    gradient_border(img, box)


def spans(d, x, y, parts):
    for text, col, *bold in parts:
        font = FB if bold else F
        d.text((x, y), text, font=font, fill=C[col])
        x += d.textlength(text, font=font)


def desktop():
    wall = Image.open(default_background()).convert("RGBA").resize((W, H), Image.LANCZOS)
    img = wall.copy()
    d = ImageDraw.Draw(img)

    # top bar
    d.rectangle([0, 0, W, 40], fill=C["bg"])
    x = 20
    for i in range(1, 6):
        d.text((x, 8), str(i), font=FB if i == 1 else F, fill=C["accent"] if i == 1 else C["dfg"])
        x += 34
    clock = "Wednesday 14:15"
    d.text(((W - d.textlength(clock, font=F)) / 2, 8), clock, font=F, fill=C["fg"])
    status = "SYNC 41.3%   ◢ AT-FIELD   ▮▮▮ 87%"
    d.text((W - 20 - d.textlength(status, font=F), 8), status, font=F, fill=C["fg"])

    g = 14
    top = 40 + g
    mid_x, mid_y = W // 2, top + (H - top) * 56 // 100
    boxes = {
        "nvim": (g, top, mid_x - g // 2, mid_y - g // 2),
        "btop": (mid_x + g // 2, top, W - g, mid_y - g // 2),
        "term": (g, mid_y + g // 2, mid_x - g // 2, H - g),
        "fetch": (mid_x + g // 2, mid_y + g // 2, W - g, H - g),
    }
    for key, b in boxes.items():
        window(img, b, glow=key == "nvim")
    d = ImageDraw.Draw(img)

    # --- nvim -----------------------------------------------------------
    x0, y0, x1, y1 = boxes["nvim"]
    code = [
        [("-- NERV // human instrumentality bootstrap", "muted")],
        [("local ", "magenta"), ("magi", "fg"), (" = ", "cyan"), ("require", "blue"), ('("magi.system")', "green")],
        [],
        [("local ", "magenta"), ("units", "fg"), (" = { ", "cyan"), ('"Unit-00"', "green"), (", ", "fg"), ('"Unit-01"', "green"), (", ", "fg"), ('"Unit-02"', "green"), (" }", "cyan")],
        [],
        [("function ", "magenta"), ("M.", "fg"), ("launch", "blue"), ("(unit, pilot)", "fg")],
        [("  if ", "magenta"), ("pilot.sync_ratio", "fg"), (" < ", "cyan"), ("40", "orange"), (" then", "magenta")],
        [("    return ", "magenta"), ("nil", "orange"), (", ", "fg"), ('"sync ratio too low"', "green")],
        [("  end", "magenta")],
        [("  local ", "magenta"), ("vote", "fg"), (" = ", "cyan"), ("magi", "fg"), (".", "fg"), ("decide", "blue"), ("({", "fg")],
        [("    melchior ", "fg"), ("= ", "cyan"), ("true", "orange"), (", balthasar ", "fg"), ("= ", "cyan"), ("true", "orange"), (",", "fg")],
        [("    casper   ", "fg"), ("= ", "cyan"), ("pilot.name ", "fg"), ("~= ", "cyan"), ('"Gendo"', "green")],
        [("  })", "fg")],
        [("  ", "fg"), ("assert", "red"), ("(vote, ", "fg"), ('"PATTERN BLUE: ANGEL"', "yellow"), (")", "fg")],
        [("  return ", "magenta"), ("unit", "fg"), (":", "fg"), ("eject_plug", "blue"), ("(", "fg"), ("false", "orange"), (")", "fg")],
        [("end", "magenta")],
        [],
        [("return ", "magenta"), ("M", "fg")],
    ]
    y = y0 + 20
    for n, line in enumerate(code, 1):
        sel = n == 7
        if sel:
            d.rectangle([x0 + 3, y - 2, x1 - 3, y + LH - 4], fill=C["lbg"])
        d.text((x0 + 20, y), f"{n:>3}", font=F, fill=C["alert"] if sel else C["muted"])
        spans(d, x0 + 90, y, line)
        y += LH
    # statusline
    sy = y1 - 46
    d.rectangle([x0 + 3, sy, x1 - 3, sy + 34], fill=C["dbg"])
    d.rectangle([x0 + 3, sy, x0 + 120, sy + 34], fill=C["green"])
    d.text((x0 + 18, sy + 5), "NORMAL", font=FB, fill=C["dbg"])
    spans(d, x0 + 140, sy + 5, [("  main ", "magenta"), (" lua/nerv/launch.lua", "fg"), ("   7:23", "dfg")])

    # --- btop-ish ---------------------------------------------------------
    x0, y0, x1, y1 = boxes["btop"]
    d.text((x0 + 24, y0 + 16), "┌ cpu ┐", font=FB, fill=C["alert"])
    d.text((x1 - 260, y0 + 16), "MAGI-01  2.4 GHz", font=F, fill=C["fg"])
    names = ["MELCHIOR", "BALTHASAR", "CASPER", "LCL-PUMP", "S2-ENGINE", "AT-FIELD", "UMBILICAL", "DUMMY-SYS"]
    vals = [0.42, 0.67, 0.21, 0.88, 0.55, 0.95, 0.33, 0.12]
    y = y0 + 64
    barw = x1 - x0 - 420
    for name, v in zip(names, vals):
        d.text((x0 + 24, y), f"{name:<10}", font=F, fill=C["fg"])
        bx = x0 + 200
        for i in range(int(barw * v) // 12):
            t = i * 12 / barw
            col = C["green"] if t < 0.5 else C["yellow"] if t < 0.8 else C["red"]
            d.rectangle([bx + i * 12, y + 4, bx + i * 12 + 8, y + 22], fill=col)
        for i in range(int(barw * v) // 12, barw // 12):
            d.rectangle([bx + i * 12, y + 4, bx + i * 12 + 8, y + 22], fill=C["sel"])
        d.text((x1 - 190, y), f"{int(v * 100):>3}%  {38 + int(v * 30)}°C", font=F, fill=C["cyan"])
        y += 40
    y += 10
    d.text((x0 + 24, y), "┌ mem ┐", font=FB, fill=C["alert"])
    y += 40
    for label, v, col in [("Used", 0.62, "red"), ("Cached", 0.24, "cyan"), ("Free", 0.14, "magenta")]:
        d.text((x0 + 24, y), f"{label:<8}", font=F, fill=C["fg"])
        d.rectangle([x0 + 200, y + 6, x0 + 200 + barw, y + 20], fill=C["sel"])
        d.rectangle([x0 + 200, y + 6, x0 + 200 + int(barw * v), y + 20], fill=C[col])
        d.text((x1 - 190, y), f"{v * 64:5.1f} GiB", font=F, fill=C["dfg"])
        y += 36

    # --- terminal -----------------------------------------------------------
    x0, y0, x1, y1 = boxes["term"]
    rows = [
        [("drwxr-xr-x", "dfg"), ("  shinji ", "yellow"), ("  ", "fg"), ("backgrounds/", "blue", 1)],
        [(".rw-r--r--", "dfg"), ("  shinji ", "yellow"), ("  ", "fg"), ("btop.theme", "fg")],
        [(".rw-r--r--", "dfg"), ("  shinji ", "yellow"), ("  ", "fg"), ("colors.toml", "fg")],
        [(".rw-r--r--", "dfg"), ("  shinji ", "yellow"), ("  ", "fg"), ("shell.menu.toml", "fg")],
        [(".rw-r--r--", "dfg"), ("  shinji ", "yellow"), ("  ", "fg"), ("unlock.png", "magenta")],
        [],
        [(PILOTS[NAME][2] + " ", "magenta", 1), ("~/eva ", "cyan"), ("on ", "fg"), (" main ", "green"), ("❯ ", "orange", 1), ("omarchy theme set " + NAME, "fg")],
        [("  ✓ ", "green"), ("Synchronisation complete. ", "fg"), ("Ratio: ", "dfg"), ("400%", "red", 1)],
        [],
        [(PILOTS[NAME][2] + " ", "magenta", 1), ("~/eva ", "cyan"), ("❯ ", "orange", 1), ("█", "bfg")],
    ]
    y = y0 + 24
    for line in rows:
        spans(d, x0 + 24, y, line)
        y += LH + 4

    # --- fetch + palette ---------------------------------------------------
    x0, y0, x1, y1 = boxes["fetch"]
    jp = ImageFont.truetype(JP, 58)
    d.text((x0 + 40, y0 + 34), "新世紀", font=jp, fill=C["red"])
    d.text((x0 + 40, y0 + 96), "エヴァンゲリオン", font=jp, fill=C["bfg"])
    info = [
        ("pilot", PILOTS[NAME][0]), ("unit", PILOTS[NAME][1]), ("os", "Omarchy 4 // Arch"),
        ("theme", NAME), ("sync", "41.3%"),
    ]
    y = y0 + 186
    for k, v in info:
        spans(d, x0 + 44, y, [(f"{k:<7}", "green", 1), (v, "fg")])
        y += LH + 2
    sw = (x1 - x0 - 88) // 8
    names = ["bg", "red", "green", "yellow", "blue", "magenta", "cyan", "fg"]
    brights = C["brights"]
    for i, n in enumerate(names):
        bx = x0 + 44 + i * sw
        d.rectangle([bx, y1 - 150, bx + sw - 8, y1 - 100], fill=C[n] if n != "bg" else C["dbg"], outline=C["muted"] if n == "bg" else None)
        d.rectangle([bx, y1 - 92, bx + sw - 8, y1 - 42], fill=brights[i])
    d.rectangle([x0 + 44, y1 - 150 - 64, x0 + 44 + 8 * sw - 8, y1 - 150 - 16], fill=C["alert"])
    d.text((x0 + 60, y1 - 150 - 56), "NERV  //  God's in his heaven. All's right with the world.", font=FB, fill=C["dbg"])

    img.convert("RGB").save(f"{THEME}/preview.png", optimize=True)


def unlock_preview():
    img = Image.new("RGB", (1920, 1080), C["bg"])
    logo = Image.open(f"{THEME}/unlock.png").convert("RGBA")
    img.paste(logo, ((1920 - logo.width) // 2, 450), logo)
    d = ImageDraw.Draw(img)
    bx, by = 818, 674
    d.rectangle([bx, by, bx + 284, by + 44], outline=C["fg"], width=2)
    d.text((bx + 16, by + 4), "••••", font=ImageFont.truetype(MONO, 26), fill=C["fg"])
    # padlock glyph
    d.rounded_rectangle([768, 686, 800, 712], radius=4, fill=C["fg"])
    d.arc([772, 668, 796, 696], 180, 360, fill=C["fg"], width=4)
    img.save(f"{THEME}/preview-unlock.png", optimize=True)


def swatches():
    """docs/palette-<theme>.png: a labelled strip of the palette for the README."""
    keys = ["background", "foreground", "accent", "red", "orange", "yellow", "green", "cyan", "blue", "magenta"]
    w, h = 1600, 230
    img = Image.new("RGB", (w, h), C["bg"])
    d = ImageDraw.Draw(img)
    sw = (w - 40) // len(keys)
    small = ImageFont.truetype(MONO, 17)
    for i, k in enumerate(keys):
        x = 20 + i * sw
        col = hexrgb(SPEC["colors"][k])
        d.rectangle([x, 20, x + sw - 10, 150], fill=col, outline=C["muted"] if k == "background" else None)
        d.text((x, 162), k, font=small, fill=C["fg"])
        d.text((x, 188), SPEC["colors"][k], font=small, fill=C["dfg"])
    os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
    img.save(os.path.join(ROOT, "docs", f"palette-{NAME}.png"), optimize=True)


if __name__ == "__main__":
    for name in sys.argv[1:] or list(THEMES):
        use(name)
        desktop()
        unlock_preview()
        swatches()
        print("preview", name)
