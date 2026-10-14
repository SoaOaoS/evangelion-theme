#!/usr/bin/env python3
"""Build the fastfetch portrait shipped with every theme (<theme>/fastfetch.png).

    python3 tools/generate-fastfetch.py [THEME ...]            # <theme>/fastfetch.png
    python3 tools/generate-fastfetch.py --preview [THEME ...]  # docs/fastfetch-<theme>.png

Each portrait is cropped from one of the theme's own wallpapers, framed with
the theme's border gradient and labelled like an Evangelion unit plate.
"""
import os
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from palettes import THEMES  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
JP = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"

# wallpaper, crop box as fractions (left, top, size relative to height), plate text
PORTRAITS = {
    "evangelion": ("backgrounds/1-tokyo-3-sunset.webp", (0.17, 0.0, 0.86), "EVA-01", "初号機"),
    "evangelion-unit-02": ("backgrounds/1-unit-02-launch.webp", (0.27, 0.0, 0.84), "EVA-02", "弐号機"),
    "evangelion-rei": ("backgrounds/3-rei-in-the-hangar.webp", (0.36, 0.0, 0.84), "EVA-00", "零号機"),
    "evangelion-eoe": ("backgrounds/1-end-of-evangelion.webp", (0.40, 0.23, 0.70), "LILITH", "第二使徒"),
}

SIZE = 720
BORDER = 10
RADIUS = 36


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def gradient(size, a, b):
    """Diagonal two-stop gradient, like the Hyprland active border."""
    ramp = Image.new("L", (size, size))
    ramp.putdata([(x + y) * 255 // (2 * size - 2) for y in range(size) for x in range(size)])
    return Image.composite(Image.new("RGB", (size, size), b), Image.new("RGB", (size, size), a), ramp)


def portrait(name):
    spec = THEMES[name]
    c = spec["colors"]
    src, (fx, fy, fs), plate, jp = PORTRAITS[name]
    img = Image.open(os.path.join(ROOT, spec["dir"], src)).convert("RGB")
    side = int(img.height * fs)
    left, top = int(img.width * fx), int(img.height * fy)
    art = img.crop((left, top, left + side, top + side)).resize((SIZE, SIZE), Image.LANCZOS).convert("RGBA")

    # plate: a dark band fading up from the bottom with the unit designation
    band = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    shade = rgb(c["darker_background"]) if spec["mode"] == "dark" else rgb(c["bright_foreground"])
    for y in range(SIZE - 190, SIZE):
        t = (y - (SIZE - 190)) / 190
        bd.line([(0, y), (SIZE, y)], fill=shade + (int(235 * min(1, t * 1.6)),))
    art.alpha_composite(band)
    d = ImageDraw.Draw(art)
    alert = rgb(c[spec["alert"]])
    text = rgb(c["bright_foreground"]) if spec["mode"] == "dark" else rgb(c["background"])
    d.rectangle([BORDER + 34, SIZE - 112, BORDER + 42, SIZE - 50], fill=alert)
    d.text((BORDER + 60, SIZE - 118), plate, font=ImageFont.truetype(MONO_B, 50), fill=text)
    jf = ImageFont.truetype(JP, 50)
    d.text((SIZE - BORDER - 40 - d.textlength(jp, font=jf), SIZE - 112), jp, font=jf, fill=alert)

    # frame: theme border gradient, rounded, transparent outside the corners
    a, b = (rgb(c[r]) for r in spec["border"])
    frame = gradient(SIZE, a, b).convert("RGBA")
    inner = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(inner).rounded_rectangle([BORDER, BORDER, SIZE - BORDER - 1, SIZE - BORDER - 1], RADIUS - BORDER, fill=255)
    frame.paste(art, (0, 0), inner)
    outer = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(outer).rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], RADIUS, fill=255)
    frame.putalpha(ImageChops.multiply(outer, frame.getchannel("A")))
    out = os.path.join(ROOT, spec["dir"], "fastfetch.png")
    frame.save(out, optimize=True)
    return out


# ---------------------------------------------------------------------------
# Preview: a mock foot window showing the template rendered with sample values.

NERD = os.environ.get("NERD_FONT_DIR", "/tmp/nf")
SAMPLE = {
    "title": "shinji{#90}@{#0}tokyo-3",
    "host": "Framework Laptop 13 (AMD Ryzen 7040)",
    "os": "Omarchy 4.0 · Arch Linux x86_64",
    "kernel": "6.17.2-arch1-1",
    "uptime": "3 hours, 12 mins",
    "wm": "Hyprland 0.52.1 (Wayland)",
    "terminal": "foot 1.24.0",
    "shell": "bash 5.3.3",
    "terminalfont": "JetBrainsMono Nerd Font (11pt)",
    "packages": "1184 (pacman), 12 (flatpak)",
    "cpu": "AMD Ryzen 7 7840U (16) @ 5.13 GHz",
    "gpu": "AMD Radeon 780M Graphics",
    "memory": "6.21 GiB / 30.60 GiB (20%)",
    "disk": "212.40 GiB / 931.51 GiB (23%) - btrfs",
    "battery": "87% [Discharging]",
}
ANSI = ["background", "red", "green", "yellow", "blue", "magenta", "cyan", "foreground",
        "muted", "bright_red", "bright_green", "bright_yellow", "bright_blue", "bright_magenta",
        "bright_cyan", "bright_foreground"]


def spans(fmt, state):
    """Split a fastfetch format string on {#...} colour codes into (text, style) runs."""
    import re
    out = []
    for part in re.split(r"(\{#[0-9;]*\})", fmt):
        m = re.fullmatch(r"\{#([0-9;]*)\}", part)
        if m:
            for code in (m.group(1) or "0").split(";"):
                code = int(code or 0)
                if code == 0:
                    state.update(fg=None, bold=False, italic=False)
                elif code == 1:
                    state["bold"] = True
                elif code == 3:
                    state["italic"] = True
                elif 30 <= code <= 37:
                    state["fg"] = code - 30
                elif 90 <= code <= 97:
                    state["fg"] = code - 90 + 8
        elif part:
            out.append((part, dict(state)))
    return out


def lines_for(name):
    import json
    import re
    text = open(os.path.join(ROOT, "extras/fastfetch/evangelion.template.jsonc")).read()
    cfg = json.loads(re.sub(r"^//.*$", "", text, flags=re.M))
    width = cfg["display"]["key"]["width"]
    theme_title = re.sub(r"(^|-)([a-z])", lambda m: m.group(1) + m.group(2).upper(), name).replace("-", " ")
    lines = []
    for mod in cfg["modules"]:
        if mod == "break":
            lines.append([])
            continue
        kind = mod["type"]
        if kind == "custom":
            lines.append(spans(mod["format"], {"fg": None, "bold": False, "italic": False}))
        elif kind == "colors":
            row = [(" " * mod.get("paddingLeft", 0), {"fg": None, "bold": False, "italic": False})]
            for i in range(8):
                row.append(("● ", {"fg": i, "bold": False, "italic": False}))
            lines.append(row)
        else:
            key = spans(mod["key"], {"fg": None, "bold": True, "italic": False})
            value = SAMPLE.get(kind)
            if kind == "command":
                value = theme_title + "  " + "".join("{#%d}●" % c for c in (35, 32, 33, 31, 36, 34))
            elif kind == "title":
                value = SAMPLE["title"]
            lines.append(key + [("\t%d" % width, {})] + spans(value, {"fg": None, "bold": False, "italic": False}))
    return lines


def preview(name):
    spec = THEMES[name]
    c = {k: rgb(v) for k, v in spec["colors"].items()}
    pal = [c[k] for k in ANSI]
    fonts = {
        (False, False): ImageFont.truetype(f"{NERD}/JetBrainsMonoNerdFont-Regular.ttf", 22),
        (True, False): ImageFont.truetype(f"{NERD}/JetBrainsMonoNerdFont-Bold.ttf", 22),
        (False, True): ImageFont.truetype(f"{NERD}/JetBrainsMonoNerdFont-Italic.ttf", 22),
        (True, True): ImageFont.truetype(f"{NERD}/JetBrainsMonoNerdFont-Bold.ttf", 22),
    }
    cw = int(round(fonts[(False, False)].getlength("M")))
    ch = 30
    lines = lines_for(name)
    logo_w, pad_l, pad_r, pad_t = 42, 2, 4, 1
    cols = pad_l + logo_w + pad_r + 62
    rows = max(len(lines), pad_t + logo_w * cw // ch + 1) + 2
    margin = 28
    W, H = cols * cw + margin * 2, rows * ch + margin * 2
    img = Image.new("RGBA", (W, H), c["background"] + (255,))
    d = ImageDraw.Draw(img)

    logo = Image.open(os.path.join(ROOT, spec["dir"], "fastfetch.png")).convert("RGBA")
    size = logo_w * cw
    img.alpha_composite(logo.resize((size, size), Image.LANCZOS), (margin + pad_l * cw, margin + (pad_t + 1) * ch))

    x0 = margin + (pad_l + logo_w + pad_r) * cw
    for row, line in enumerate(lines):
        x, y = x0, margin + (row + 1) * ch
        for text, st in line:
            if text.startswith("\t"):
                x = x0 + int(text[1:]) * cw
                continue
            colour = c["foreground"] if st.get("fg") is None else pal[st["fg"]]
            font = fonts[(st.get("bold", False), st.get("italic", False))]
            for chx in text:
                d.text((x, y), chx, font=font, fill=colour)
                x += cw

    # window chrome: the theme's Hyprland border gradient
    a, b = (rgb(spec["colors"][r]) for r in spec["border"])
    frame = gradient(max(W, H), a, b).resize((W, H))
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rectangle([0, 0, W - 1, H - 1], outline=255, width=4)
    img.paste(frame, (0, 0), mask)
    os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
    out = os.path.join(ROOT, "docs", f"fastfetch-{name}.png")
    img.convert("RGB").save(out, optimize=True)
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    make = preview if args[:1] == ["--preview"] else portrait
    for name in [a for a in args if a != "--preview"] or list(PORTRAITS):
        print("wrote", make(name))
