#!/usr/bin/env python3
"""Original Evangelion-style artwork, drawn from the theme palettes.

    python3 tools/generate-artwork.py THEME KIND OUT [STILL]

KIND is one of: card, magi, atfield, hazard, impact, plugsuit, intro.
`intro` writes PNG frames into the OUT directory, ending on STILL (two
optional extra arguments replace the flashing texts); pipe them
through ffmpeg (see README). Requires Pillow.
"""
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from palettes import THEMES  # noqa: E402

SERIF_B = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
JP = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

W, H = 3840, 2160

# Per-theme copy for the title cards, the MAGI console and the intros.
COPY = {
    "evangelion": {
        "card": ["EPISODE:01", ["THE", "TERMINAL"], ["HAS", "AWAKENED"]],
        "card_jp": "第壱話　端末、覚醒",
        "magi": ["承認", "承認", "承認"],
        "magi_msg": "CODE:473  //  EXTENSION 1170  //  SELF-DESTRUCT: DENIED",
        "intro": ["EMERGENCY", "PATTERN BLUE"],
    },
    "evangelion-unit-02": {
        "card": ["EPISODE:02", ["THE BEAST"], ["IN", "RED"]],
        "card_jp": "第弐話　紅い獣",
        "magi": ["承認", "否決", "承認"],
        "magi_msg": "UNIT-02  //  BEAST MODE  //  LIMITER RELEASE: 2 OF 3",
        "intro": ["WARNING", "SYNC 400%"],
    },
    "evangelion-rei": {
        "card": ["EPISODE:00", ["A WHITE"], ["SILENCE"]],
        "card_jp": "第零話　白い沈黙",
        "magi": ["承認", "承認", "承認"],
        "magi_msg": "UNIT-00  //  REACTIVATION TEST  //  PILOT: AYANAMI",
        "intro": ["ACTIVATION", "UNIT-00"],
    },
    "evangelion-eoe": {
        "card": ["EPISODE:26'", ["ONE MORE"], ["FINAL:"], ["I NEED YOU."]],
        "card_jp": "最終話　まごころを、君に",
        "magi": ["否決", "否決", "否決"],
        "magi_msg": "OPERATION 2  //  JSSDF INTRUSION  //  MAGI: HACKED",
        "intro": ["THIRD IMPACT", "AIR"],
    },
}


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


class P:
    """Palette accessor: P(theme).red -> (r, g, b)."""

    def __init__(self, theme):
        self.__dict__.update({k: rgb(v) for k, v in THEMES[theme]["colors"].items()})
        self.dark = THEMES[theme]["mode"] == "dark"
        self.spec = THEMES[theme]


def font(path, size):
    return ImageFont.truetype(path, int(size))


def squashed(text, path, size, fill, xscale=0.55):
    """Tall, horizontally compressed serif: the Evangelion title-card look."""
    f = font(path, size)
    l, t, r, b = f.getbbox(text)
    img = Image.new("RGBA", (r - l + 8, b - t + 8), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((-l + 4, -t + 4), text, font=f, fill=fill)
    return img.resize((max(1, int(img.width * xscale)), img.height), Image.LANCZOS)


def hexagon(d, cx, cy, r, **kw):
    pts = [(cx + r * math.cos(math.radians(60 * i)), cy + r * math.sin(math.radians(60 * i))) for i in range(6)]
    d.polygon(pts, **kw)


def hex_grid(r):
    hstep, vstep = 1.5 * r, math.sqrt(3) * r
    col, x = 0, 0.0
    while x < W + r:
        y = vstep / 2 if col % 2 else 0.0
        while y < H + r:
            yield x, y
            y += vstep
        x += hstep
        col += 1


def grain(img, amount=16, alpha=14):
    noise = Image.effect_noise(img.size, amount).convert("L")
    layer = Image.merge("RGBA", (noise, noise, noise, Image.new("L", img.size, alpha)))
    return Image.alpha_composite(img.convert("RGBA"), layer)


def scanlines(img, alpha=24, step=4):
    over = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    for y in range(0, img.height, step):
        d.line([(0, y), (img.width, y)], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(img.convert("RGBA"), over)


def vignette(img, strength=0.55):
    mask = Image.new("L", (W // 8, H // 8), 0)
    d = ImageDraw.Draw(mask)
    for i in range(60):
        t = i / 60
        d.ellipse([-W / 16 * (1 - t) - 40 + t * 120, -H / 16 * (1 - t) - 40 + t * 70,
                   W / 8 + W / 16 * (1 - t) + 40 - t * 120, H / 8 + H / 16 * (1 - t) + 40 - t * 70],
                  fill=int(255 * t))
    mask = mask.resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(40))
    dark = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    dark.putalpha(mask.point(lambda v: int((255 - v) * strength)))
    return Image.alpha_composite(img.convert("RGBA"), dark)


def stripes(width, height, a, b, step=110):
    band = Image.new("RGBA", (width, height), a + (255,))
    d = ImageDraw.Draw(band)
    for i in range(-height, width + height, step):
        d.polygon([(i, height), (i + step / 2, height), (i + step / 2 + height, 0), (i + height, 0)], fill=b + (255,))
    return band


# ----------------------------------------------------------------------------
def card(theme):
    p, copy = P(theme), COPY[theme]
    bg = p.darker_background if p.dark else p.background
    ink = p.bright_foreground
    head, *rows = copy["card"]
    # lay the words out on a tall scratch canvas, then fit it to the frame
    scratch = Image.new("RGBA", (W * 2, 900 + 860 * len(rows)), (0, 0, 0, 0))
    scratch.alpha_composite(squashed(head, SERIF_B, 420, ink, 0.55), (0, 0))
    y, right = 620, 0
    for row in rows:
        x = 0
        for word in row:
            t = squashed(word, SERIF_B, 840, ink, 0.5)
            scratch.alpha_composite(t, (x, y))
            x += t.width + 120
        right = max(right, x - 120)
        y += 860
    content = scratch.crop((0, 0, right, y - 100))
    scale = min(1.0, (W - 1100) / content.width, (H - 760) / content.height)
    content = content.resize((int(content.width * scale), int(content.height * scale)), Image.LANCZOS)

    img = Image.new("RGBA", (W, H), bg + (255,))
    top = (H - content.height - 260) // 2
    img.alpha_composite(content, (420, top))
    d = ImageDraw.Draw(img)
    ly = top + content.height + 70
    d.rectangle([420, ly, 2900, ly + 6], fill=p.orange if theme == "evangelion" else p.accent)
    img.alpha_composite(squashed(copy["card_jp"], JP, 120, p.foreground, 1.0), (420, ly + 60))
    d.text((W - 900, H - 220), f"OMARCHY // {theme.upper()}", font=font(MONO, 34), fill=p.muted)
    return grain(img, 18)


def magi(theme):
    p, copy = P(theme), COPY[theme]
    img = Image.new("RGBA", (W, H), p.background + (255,))
    d = ImageDraw.Draw(img)
    grid = tuple(int(a * 0.82 + b * 0.18) for a, b in zip(p.background, p.muted))
    for x, y in hex_grid(70):
        hexagon(d, x, y, 66, outline=grid, width=2)

    cx, cy = W / 2, H / 2 + 60
    pw, ph = 620, 380
    panels = [("MELCHIOR·1", cx - pw / 2, cy - 640), ("BALTHASAR·2", cx - pw - 260, cy - 40), ("CASPER·3", cx + 260, cy - 40)]
    centers = [(x0 + pw / 2, y0 + ph / 2) for _, x0, y0 in panels]
    for a in range(3):
        for b in range(a + 1, 3):
            d.line([centers[a], centers[b]], fill=p.muted, width=6)
    ink = p.darker_background if p.dark else p.bright_foreground
    for (name, x0, y0), verdict in zip(panels, copy["magi"]):
        fill = p.green if verdict == "承認" else p.red
        d.rectangle([x0, y0, x0 + pw, y0 + ph], fill=fill)
        d.rectangle([x0, y0, x0 + pw, y0 + ph], outline=ink, width=10)
        d.text((x0 + 30, y0 + 24), name, font=font(MONO_B, 44), fill=ink)
        vf = font(JP, 150)
        d.text((x0 + (pw - d.textlength(verdict, font=vf)) / 2, y0 + 130), verdict, font=vf, fill=ink)

    title = squashed("MAGI SYSTEM", SERIF_B, 150, p.orange, 0.6)
    img.alpha_composite(title, (int(cx - title.width / 2), int(cy + 470)))
    sub = font(MONO, 38)
    d.text((cx - d.textlength(copy["magi_msg"], font=sub) / 2, cy + 680), copy["magi_msg"], font=sub, fill=p.foreground)
    band = stripes(W, 54, p.orange, p.darker_background if p.dark else p.foreground)
    img.alpha_composite(band, (0, 0))
    img.alpha_composite(band, (0, H - 54))
    corner = font(MONO_B, 40)
    d.text((80, 110), "NERV HQ  //  CENTRAL DOGMA", font=corner, fill=p.magenta)
    d.text((W - 80 - d.textlength("SYNC 41.3%", font=corner), 110), "SYNC 41.3%", font=corner, fill=p.green)
    return grain(scanlines(img) if p.dark else img, 8)


def atfield(theme, seed=3):
    """Concentric octagonal A.T. Field ripples over a hex lattice."""
    p = P(theme)
    rnd = random.Random(seed)
    img = Image.new("RGBA", (W, H), p.darker_background + (255,))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy = W * 0.62, H * 0.52
    a, b = (rgb(THEMES[theme]["colors"][r]) for r in THEMES[theme]["border"])
    for i in range(22):
        r = 120 + i * 95
        t = i / 21
        col = tuple(int(a[k] + (b[k] - a[k]) * t) for k in range(3))
        pts = [(cx + r * math.cos(math.radians(22.5 + 45 * j)), cy + r * math.sin(math.radians(22.5 + 45 * j))) for j in range(8)]
        gd.polygon(pts, outline=col + (int(230 * (1 - t) + 25),), width=max(2, int(14 * (1 - t))))
    blur = glow.filter(ImageFilter.GaussianBlur(28))
    img.alpha_composite(blur)
    img.alpha_composite(blur)
    img.alpha_composite(glow)

    lattice = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lattice)
    for x, y in hex_grid(54):
        dist = math.hypot(x - cx, y - cy)
        k = max(0.0, 1 - dist / 2600)
        if rnd.random() < 0.04 * k:
            hexagon(ld, x, y, 50, fill=a + (int(90 * k),))
        hexagon(ld, x, y, 50, outline=b + (int(40 * k) + 8,), width=2)
    img.alpha_composite(lattice)

    d = ImageDraw.Draw(img)
    d.text((140, H - 300), "ABSOLUTE TERROR FIELD", font=font(MONO_B, 60), fill=p.foreground)
    d.text((140, H - 220), "PHASE SPACE INVERSION  //  NEUTRALISING", font=font(MONO, 40), fill=p.dark_foreground)
    d.text((140, 160), "A.T.フィールド全開", font=font(JP, 96), fill=b)
    return grain(vignette(img), 14)


def hazard(theme):
    """Unit-02 style hazard panel with a giant stencilled 02."""
    p = P(theme)
    img = Image.new("RGBA", (W, H), p.background + (255,))
    d = ImageDraw.Draw(img)
    # angled armour plates
    d.polygon([(0, 0), (W * 0.58, 0), (W * 0.40, H), (0, H)], fill=p.red)
    d.polygon([(W * 0.58, 0), (W * 0.62, 0), (W * 0.44, H), (W * 0.40, H)], fill=p.orange)
    num = squashed("02", SERIF_B, 2300, p.darker_background, 0.62)
    img.alpha_composite(num, (160, (H - num.height) // 2))
    band = stripes(int(W * 0.5), 160, p.yellow, p.darker_background, 180).rotate(-12, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(band, (int(W * 0.47), int(H * 0.62)))
    d = ImageDraw.Draw(img)
    x = int(W * 0.62)
    d.text((x, 360), "EVANGELION", font=font(MONO_B, 120), fill=p.bright_foreground)
    d.text((x, 500), "PRODUCTION MODEL", font=font(MONO_B, 120), fill=p.bright_foreground)
    d.text((x, 680), "エヴァンゲリオン弐号機", font=font(JP, 110), fill=p.orange)
    for i, line in enumerate(["PILOT ........ SORYU A. LANGLEY", "SYNC RATIO ... 78.4 %", "S² ENGINE .... OFFLINE",
                              "UMBILICAL .... CONNECTED", "LIMITER ...... ENGAGED"]):
        d.text((x, 900 + i * 70), line, font=font(MONO, 48), fill=p.light_foreground)
    return grain(scanlines(img), 14)


def impact(theme):
    """Third Impact: red LCL sea under a black sky, a white moon-face and crosses."""
    p = P(theme)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    d = ImageDraw.Draw(img)
    horizon = int(H * 0.64)
    for y in range(horizon):
        t = y / horizon
        col = tuple(int(p.darker_background[k] * (1 - t) + p.selection[k] * t * 0.9) for k in range(3))
        d.line([(0, y), (W, y)], fill=col)
    for y in range(horizon, H):
        t = (y - horizon) / (H - horizon)
        col = tuple(int(p.red[k] * (1 - t * 0.55)) for k in range(3))
        d.line([(0, y), (W, y)], fill=col)
    # the great white moon
    moon = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    md = ImageDraw.Draw(moon)
    mx, my, mr = W * 0.5, horizon - 80, 760
    md.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=p.bright_foreground + (255,))
    md.rectangle([0, horizon, W, H], fill=(0, 0, 0, 0))
    halo = moon.filter(ImageFilter.GaussianBlur(60))
    img.alpha_composite(halo)
    img.alpha_composite(moon)
    # blood band across the moon (the scar)
    d = ImageDraw.Draw(img)
    d.rectangle([mx - mr, my - 30, mx + mr, my + 30], fill=p.red)
    # reflection
    refl = moon.crop((0, horizon - mr * 2, W, horizon)).transpose(Image.FLIP_TOP_BOTTOM)
    refl.putalpha(refl.getchannel("A").point(lambda v: int(v * 0.25)))
    img.alpha_composite(refl.filter(ImageFilter.GaussianBlur(12)), (0, horizon))
    # crosses on the horizon
    rnd = random.Random(26)
    placed = []
    for _ in range(400):
        if len(placed) == 6:
            break
        cx = rnd.randint(180, W - 180)
        if abs(cx - mx) < mr + 120 or any(abs(cx - o) < 220 for o in placed):
            continue
        placed.append(cx)
        h = rnd.randint(160, 460)
        w = max(8, h // 14)
        arm = h // 4
        d.rectangle([cx - w, horizon - h, cx + w, horizon], fill=(0, 0, 0))
        d.rectangle([cx - arm, horizon - h * 0.75 - w, cx + arm, horizon - h * 0.75 + w], fill=(0, 0, 0))
    # horizon line
    d.line([(0, horizon), (W, horizon)], fill=p.bright_red, width=4)
    d.text((140, 140), "THIRD IMPACT", font=font(MONO_B, 64), fill=p.foreground)
    d.text((140, 220), "HUMAN INSTRUMENTALITY PROJECT", font=font(MONO, 40), fill=p.dark_foreground)
    jp = squashed("気持ち悪い", JP, 90, p.bright_foreground, 1.0)
    img.alpha_composite(jp, (W - jp.width - 160, H - jp.height - 140))
    return grain(img, 20, 16)


def plugsuit(theme):
    """Light, minimal plugsuit panel lines for the Rei variant."""
    p = P(theme)
    img = Image.new("RGBA", (W, H), p.background + (255,))
    d = ImageDraw.Draw(img)
    # sweeping suit seams
    for i, col in enumerate([p.darker_background, p.blue, p.darker_background, p.red]):
        off = i * 120
        d.line([(W * 0.55 + off, 0), (W * 0.40 + off, H * 0.45), (W * 0.62 + off, H)], fill=col, width=40 if col == p.darker_background else 18, joint="curve")
    # chest interface clips (Rei's A10 nerve clips)
    for cy in (H * 0.3, H * 0.62):
        d.rounded_rectangle([W * 0.18, cy - 80, W * 0.18 + 260, cy + 80], radius=40, fill=p.bright_foreground)
        d.rounded_rectangle([W * 0.18 + 30, cy - 50, W * 0.18 + 230, cy + 50], radius=24, fill=p.blue)
    d.ellipse([W * 0.78 - 110, H * 0.24 - 110, W * 0.78 + 110, H * 0.24 + 110], fill=p.red)
    d.text((W * 0.7, H * 0.78), "PILOT 00", font=font(MONO_B, 90), fill=p.foreground)
    d.text((W * 0.7, H * 0.78 + 120), "AYANAMI REI  //  FIRST CHILDREN", font=font(MONO, 40), fill=p.dark_foreground)
    jp = squashed("綾波レイ", JP, 220, p.foreground, 1.0)
    img.alpha_composite(jp, (int(W * 0.7), int(H * 0.56)))
    return grain(img, 12, 10)


# ----------------------------------------------------------------------------
def emergency_overlay(theme, phase, text, w=1920, h=1080):
    p = P(theme)
    hot = {"evangelion-rei": p.accent, "evangelion-eoe": p.red}.get(theme, p.orange)
    edge = p.bright_foreground if theme == "evangelion-eoe" else p.red
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = 46
    hstep, vstep = 1.5 * r, math.sqrt(3) * r
    col, x = 0, 0.0
    while x < w + r:
        y = vstep / 2 if col % 2 else 0.0
        while y < h + r:
            k = math.sin((x / w) * 6 - phase * 8 + (y / h) * 2)
            if k > 0.55:
                hexagon(d, x, y, r - 5, fill=hot + (int(70 + 120 * (k - 0.55) / 0.45),), outline=edge + (255,), width=2)
            else:
                hexagon(d, x, y, r - 5, outline=edge + (110,), width=2)
            y += vstep
        x += hstep
        col += 1
    t = squashed(text, MONO_B, 170, edge + (255,), 0.85)
    box_bg = p.darker_background if p.dark else p.bright_foreground
    box = Image.new("RGBA", (t.width + 120, t.height + 80), box_bg + (235,))
    box.alpha_composite(t, (60, 40))
    ImageDraw.Draw(box).rectangle([0, 0, box.width - 1, box.height - 1], outline=edge + (255,), width=6)
    img.alpha_composite(box, ((w - box.width) // 2, (h - box.height) // 2))
    return img


def intro(theme, out, still_path, texts=None, seconds=6, fps=30):
    p = P(theme)
    texts = texts or COPY[theme]["intro"]
    still = Image.open(still_path).convert("RGBA").resize((1920, 1080), Image.LANCZOS)
    base = Image.new("RGBA", (1920, 1080), (p.darker_background if p.dark else p.foreground) + (255,))
    os.makedirs(out, exist_ok=True)
    for f in range(seconds * fps):
        t = f / fps
        if t < 3.6:
            frame = base.copy()
            blink = 1.0 if int(t * 4) % 2 == 0 else 0.55
            over = emergency_overlay(theme, t, texts[0] if t < 1.8 else texts[1])
            over.putalpha(over.getchannel("A").point(lambda a: int(a * blink)))
            frame.alpha_composite(over)
        else:
            k = min(1.0, (t - 3.6) / 1.6)
            k = k * k * (3 - 2 * k)
            frame = Image.blend(base, still, k)
            if k < 1:
                over = emergency_overlay(theme, t, texts[1])
                over.putalpha(over.getchannel("A").point(lambda a: int(a * (1 - k))))
                frame.alpha_composite(over)
        frame.convert("RGB").save(f"{out}/{f:04d}.png")


KINDS = {"card": card, "magi": magi, "atfield": atfield, "hazard": hazard, "impact": impact, "plugsuit": plugsuit}

if __name__ == "__main__":
    theme, kind, out = sys.argv[1:4]
    if kind == "intro":
        intro(theme, out, sys.argv[4], sys.argv[5:7] or None)
    else:
        KINDS[kind](theme).convert("RGB").save(out, quality=90)
