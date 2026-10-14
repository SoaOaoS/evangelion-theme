"""Generate the original Evangelion-style artwork for the theme."""
import math
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = sys.argv[1]

BG = (19, 14, 31)
DARKER = (8, 6, 14)
CREAM = (232, 221, 199)
BRIGHT = (247, 239, 220)
PURPLE = (155, 106, 214)
DPURPLE = (58, 42, 94)
GREEN = (143, 209, 79)
ORANGE = (255, 138, 30)
RED = (229, 54, 74)
YELLOW = (242, 193, 46)
MUTED = (91, 74, 125)

SERIF_B = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
JP = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
MONO_R = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def squashed_text(text, font_path, size, fill, xscale=0.62, bg=(0, 0, 0, 0)):
    """Render text then compress horizontally: the classic EVA title-card serif."""
    font = ImageFont.truetype(font_path, size)
    l, t, r, b = font.getbbox(text)
    img = Image.new("RGBA", (r - l + 4, b - t + 4), bg)
    ImageDraw.Draw(img).text((-l + 2, -t + 2), text, font=font, fill=fill)
    return img.resize((max(1, int(img.width * xscale)), img.height), Image.LANCZOS)


def hexagon(draw, cx, cy, r, outline=None, fill=None, width=2):
    pts = [(cx + r * math.cos(math.radians(60 * i)), cy + r * math.sin(math.radians(60 * i))) for i in range(6)]
    draw.polygon(pts, outline=outline, fill=fill, width=width)


def scanlines(img, alpha=26, step=4):
    over = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    for y in range(0, img.height, step):
        d.line([(0, y), (img.width, y)], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(img.convert("RGBA"), over)


def grain(img, amount=10):
    noise = Image.effect_noise(img.size, amount).convert("L")
    noise = Image.merge("RGBA", (noise, noise, noise, Image.new("L", img.size, 14)))
    return Image.alpha_composite(img.convert("RGBA"), noise)


# --------------------------------------------------------------------------
# 1. Episode title card
# --------------------------------------------------------------------------
def title_card(W=3840, H=2160):
    img = Image.new("RGBA", (W, H), DARKER + (255,))
    s = H / 2160

    def put(text, x, y, size, xscale=0.6, fill=BRIGHT, font=SERIF_B):
        t = squashed_text(text, font, int(size * s), fill, xscale)
        img.alpha_composite(t, (int(x * s), int(y * s)))
        return t

    put("EPISODE:01", 420, 360, 210, 0.55)
    put("THE", 420, 690, 420, 0.5)
    put("TERMINAL", 1000, 690, 420, 0.5)
    put("HAS", 420, 1110, 420, 0.5)
    put("AWAKENED", 1080, 1110, 420, 0.5)
    jp = squashed_text("第壱話　端末、覚醒", JP, int(120 * s), CREAM, 1.0)
    img.alpha_composite(jp, (int(420 * s), int(1640 * s)))

    d = ImageDraw.Draw(img)
    d.rectangle([int(420 * s), int(1580 * s), int(2900 * s), int(1586 * s)], fill=ORANGE)
    # small NERV-ish meta text, bottom right
    meta = ImageFont.truetype(MONO_R, int(34 * s))
    d.text((int(2950 * s), int(1880 * s)), "OMARCHY // TOKYO-3 // 2015", font=meta, fill=MUTED)
    return grain(img, 18)


# --------------------------------------------------------------------------
# 2. MAGI decision console
# --------------------------------------------------------------------------
def magi_console(W=3840, H=2160, approve=True):
    img = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(img)
    s = H / 2160

    # faint hex grid
    r = 70 * s
    hstep = 1.5 * r
    vstep = math.sqrt(3) * r
    col = 0
    x = 0
    while x < W + r:
        y = (vstep / 2) if col % 2 else 0
        while y < H + r:
            hexagon(d, x, y, r - 4 * s, outline=(34, 25, 56), width=max(1, int(2 * s)))
            y += vstep
        x += hstep
        col += 1

    # MAGI panels (Melchior top, Balthasar left, Casper right)
    cx, cy = W / 2, H / 2 + 60 * s
    pw, ph = 620 * s, 380 * s
    panels = [
        ("MELCHIOR·1", cx - pw / 2, cy - 640 * s),
        ("BALTHASAR·2", cx - pw - 260 * s, cy - 40 * s),
        ("CASPER·3", cx + 260 * s, cy - 40 * s),
    ]
    centers = [(x0 + pw / 2, y0 + ph / 2) for _, x0, y0 in panels]
    for a in range(3):
        for b in range(a + 1, 3):
            d.line([centers[a], centers[b]], fill=MUTED, width=int(6 * s))

    label_font = ImageFont.truetype(MONO, int(44 * s))
    verdict_font = ImageFont.truetype(JP, int(150 * s))
    verdicts = ["承認", "承認", "承認"] if approve else ["承認", "否決", "承認"]
    for (name, x0, y0), verdict in zip(panels, verdicts):
        ok = verdict == "承認"
        fill = GREEN if ok else RED
        d.rectangle([x0, y0, x0 + pw, y0 + ph], fill=fill + (255,))
        d.rectangle([x0, y0, x0 + pw, y0 + ph], outline=DARKER, width=int(10 * s))
        d.text((x0 + 30 * s, y0 + 24 * s), name, font=label_font, fill=DARKER)
        tw = d.textlength(verdict, font=verdict_font)
        d.text((x0 + (pw - tw) / 2, y0 + 130 * s), verdict, font=verdict_font, fill=DARKER)

    # central title
    title = squashed_text("MAGI SYSTEM", SERIF_B, int(150 * s), ORANGE, 0.6)
    img.alpha_composite(title, (int(cx - title.width / 2), int(cy + 470 * s)))
    sub = ImageFont.truetype(MONO_R, int(38 * s))
    msg = "CODE:473  //  EXTENSION 1170  //  SELF-DESTRUCT: DENIED"
    d.text((cx - d.textlength(msg, font=sub) / 2, cy + 680 * s), msg, font=sub, fill=CREAM)

    # warning stripes top & bottom
    stripe_h = int(54 * s)
    for band_y in (0, H - stripe_h):
        band = Image.new("RGBA", (W, stripe_h), ORANGE + (255,))
        bd = ImageDraw.Draw(band)
        step = int(110 * s)
        for i in range(-stripe_h, W + stripe_h, step):
            bd.polygon([(i, stripe_h), (i + step / 2, stripe_h), (i + step / 2 + stripe_h, 0), (i + stripe_h, 0)], fill=DARKER)
        img.alpha_composite(band, (0, band_y))

    corner = ImageFont.truetype(MONO, int(40 * s))
    d.text((80 * s, 110 * s), "NERV HQ  //  CENTRAL DOGMA", font=corner, fill=PURPLE)
    d.text((W - 80 * s - d.textlength("SYNC 41.3%", font=corner), 110 * s), "SYNC 41.3%", font=corner, fill=GREEN)
    return grain(scanlines(img), 8)


# --------------------------------------------------------------------------
# 3. EMERGENCY overlay frame (used for the intro video)
# --------------------------------------------------------------------------
def emergency(W=1920, H=1080, phase=0.0, text="EMERGENCY"):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = 46
    hstep, vstep = 1.5 * r, math.sqrt(3) * r
    col, x = 0, 0
    while x < W + r:
        y = (vstep / 2) if col % 2 else 0
        while y < H + r:
            # sweep of lit hexagons moving across the screen
            k = math.sin((x / W) * 6 - phase * 8 + (y / H) * 2)
            if k > 0.55:
                hexagon(d, x, y, r - 5, fill=ORANGE + (int(70 + 120 * (k - 0.55) / 0.45),), outline=RED + (255,), width=2)
            else:
                hexagon(d, x, y, r - 5, outline=(80, 24, 30, 160), width=2)
            y += vstep
        x += hstep
        col += 1
    t = squashed_text(text, MONO, 190, RED + (255,), 0.85)
    box = Image.new("RGBA", (t.width + 120, t.height + 80), DARKER + (230,))
    box.alpha_composite(t, (60, 40))
    ImageDraw.Draw(box).rectangle([0, 0, box.width - 1, box.height - 1], outline=RED + (255,), width=6)
    img.alpha_composite(box, ((W - box.width) // 2, (H - box.height) // 2))
    return img


if __name__ == "__main__":
    what = sys.argv[2]
    if what == "card":
        title_card().convert("RGB").save(OUT, quality=90)
    elif what == "magi":
        magi_console().convert("RGB").save(OUT, quality=90)
    elif what == "intro":
        import os
        still = Image.open(sys.argv[3]).convert("RGBA").resize((1920, 1080), Image.LANCZOS)
        black = Image.new("RGBA", (1920, 1080), DARKER + (255,))
        fps, total = 30, 6 * 30
        os.makedirs(OUT, exist_ok=True)
        for f in range(total):
            t = f / fps
            if t < 3.6:
                frame = black.copy()
                blink = 1.0 if int(t * 4) % 2 == 0 else 0.55
                over = emergency(phase=t, text="EMERGENCY" if t < 1.8 else "PATTERN BLUE")
                over.putalpha(over.getchannel("A").point(lambda a: int(a * blink)))
                frame.alpha_composite(over)
            else:
                k = min(1.0, (t - 3.6) / 1.6)
                k = k * k * (3 - 2 * k)
                frame = Image.blend(black, still, k)
                if k < 1:
                    over = emergency(phase=t)
                    over.putalpha(over.getchannel("A").point(lambda a: int(a * (1 - k))))
                    frame.alpha_composite(over)
            frame.convert("RGB").save(f"{OUT}/{f:04d}.png")
