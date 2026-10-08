#!/usr/bin/env python3
"""Generate the site's raster images with the standard library only (zlib + struct).

    python3 tools/make_images.py

Reads the app icon from ../SweetSuites-brand (the brand kit) and writes:
    og.png              1200x630 social card
    favicon.png         64x64, rounded corners, transparent outside
    icon.png            180x180 apple-touch-icon
    assets/icon-512.png 512x512 hero icon

rsvg-convert and ImageMagick are not used on purpose (Intel-only on the build Mac).
The wordmark on the social card is drawn as candy-block pixel letters, the same
"painted cell" look as the picture in the icon, so no font rendering is needed.
"""
import math
import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
BRAND = os.path.join(os.path.dirname(SITE), "SweetSuites-brand")
ICON_SRC = os.path.join(BRAND, "AppIcon.appiconset", "AppIcon-1024.png")


def hx(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


SKY_TOP, SKY_BOT = hx("#4FD6FF"), hx("#5B4BFF")
PINK, PINK_LO = hx("#FF3E86"), hx("#C81E63")
INK, WHITE = hx("#2B1D5C"), (1.0, 1.0, 1.0)
GOLD, GOLD_LO = hx("#FFC93C"), hx("#E0961B")
VEHICLES = ["#F2364D", "#2F8CFF", "#FFCF2E", "#5BCB3A", "#8A4DFF",
            "#FF8A1F", "#FF6FC8", "#19C9B4", "#8B5A3C"]


# ------------------------------------------------------------------ PNG I/O
def read_png(path):
    """Decode an 8-bit, non-interlaced RGB or RGBA PNG. Returns (w, h, ch, rows)."""
    with open(path, "rb") as f:
        data = f.read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos, idat = 8, b""
    while pos < len(data):
        n = struct.unpack(">I", data[pos:pos + 4])[0]
        t = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + n]
        if t == b"IHDR":
            w, h, depth, ctype, _, _, inter = struct.unpack(">IIBBBBB", body)
            assert depth == 8 and ctype in (2, 6) and inter == 0, "unsupported PNG"
        elif t == b"IDAT":
            idat += body
        pos += 12 + n
    ch = 3 if ctype == 2 else 4
    raw = zlib.decompress(idat)
    stride = w * ch
    rows, prev = [], bytearray(stride)
    i = 0
    for _ in range(h):
        ft = raw[i]
        line = bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        for x in range(stride):
            a = line[x - ch] if x >= ch else 0
            b = prev[x]
            c = prev[x - ch] if x >= ch else 0
            if ft == 1:
                line[x] = (line[x] + a) & 255
            elif ft == 2:
                line[x] = (line[x] + b) & 255
            elif ft == 3:
                line[x] = (line[x] + ((a + b) >> 1)) & 255
            elif ft == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if pa <= pb and pa <= pc else b if pb <= pc else c
                line[x] = (line[x] + pr) & 255
        rows.append(line)
        prev = line
    return w, h, ch, rows


def write_png(path, w, h, pix, alpha=False):
    """pix: flat list of floats 0..1, 3 or 4 per pixel (straight alpha)."""
    ch = 4 if alpha else 3
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        base = y * w * ch
        raw += bytes(int(clamp(v) * 255 + 0.5) for v in pix[base:base + w * ch])

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6 if alpha else 2, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))


def icon_rgb():
    w, h, ch, rows = read_png(ICON_SRC)
    pix = []
    for r in rows:
        for x in range(w):
            pix += [r[x * ch] / 255, r[x * ch + 1] / 255, r[x * ch + 2] / 255]
    return w, pix


def resample(src, n_in, n_out):
    """Area-average downscale of a square RGB image."""
    scale = n_in / n_out
    taps = []
    for o in range(n_out):
        a, b = o * scale, (o + 1) * scale
        ws = []
        for s in range(int(a), min(n_in, int(math.ceil(b)))):
            ov = min(b, s + 1) - max(a, s)
            if ov > 0:
                ws.append((s, ov / scale))
        taps.append(ws)
    tmp = [0.0] * (n_in * n_out * 3)
    for y in range(n_in):
        rb = y * n_in * 3
        for ox, ws in enumerate(taps):
            r = g = b = 0.0
            for s, wt in ws:
                i = rb + s * 3
                r += src[i] * wt; g += src[i + 1] * wt; b += src[i + 2] * wt
            j = (y * n_out + ox) * 3
            tmp[j], tmp[j + 1], tmp[j + 2] = r, g, b
    out = [0.0] * (n_out * n_out * 3)
    for oy, ws in enumerate(taps):
        for x in range(n_out):
            r = g = b = 0.0
            for s, wt in ws:
                i = (s * n_out + x) * 3
                r += tmp[i] * wt; g += tmp[i + 1] * wt; b += tmp[i + 2] * wt
            j = (oy * n_out + x) * 3
            out[j], out[j + 1], out[j + 2] = r, g, b
    return out


# ------------------------------------------------------------------ drawing
def sd_rrect(cx, cy, hw, hh, r):
    def f(x, y):
        qx = abs(x - cx) - hw + r
        qy = abs(y - cy) - hh + r
        return math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - r
    return f


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = [0.0] * (w * h * 3)

    def fill(self, sdf, color, bbox, opacity=1.0, soft=1.0):
        w, h, px = self.w, self.h, self.px
        x0, y0 = max(0, int(bbox[0])), max(0, int(bbox[1]))
        x1, y1 = min(w, int(math.ceil(bbox[2]))), min(h, int(math.ceil(bbox[3])))
        const = not callable(color)
        half = soft / 2
        for y in range(y0, y1):
            fy = y + 0.5
            for x in range(x0, x1):
                fx = x + 0.5
                d = sdf(fx, fy)
                if d >= half:
                    continue
                a = (1.0 if d <= -half else 0.5 - d / soft) * opacity
                r, g, b = color if const else color(fx, fy)
                i = (y * w + x) * 3
                px[i] += (r - px[i]) * a
                px[i + 1] += (g - px[i + 1]) * a
                px[i + 2] += (b - px[i + 2]) * a


# 5x7 pixel letters for the wordmark.
GLYPHS = {
    "S": [".XXX.", "X...X", "X....", ".XXX.", "....X", "X...X", ".XXX."],
    "W": ["X...X", "X...X", "X...X", "X.X.X", "X.X.X", "XX.XX", "X...X"],
    "E": ["XXXXX", "X....", "X....", "XXXX.", "X....", "X....", "XXXXX"],
    "T": ["XXXXX", "..X..", "..X..", "..X..", "..X..", "..X..", "..X.."],
    "U": ["X...X", "X...X", "X...X", "X...X", "X...X", "X...X", ".XXX."],
    "I": ["XXX", ".X.", ".X.", ".X.", ".X.", ".X.", "XXX"],
    "V": ["X...X", "X...X", "X...X", "X...X", "X...X", ".X.X.", "..X.."],
    "A": [".XXX.", "X...X", "X...X", "XXXXX", "X...X", "X...X", "X...X"],
    "L": ["X....", "X....", "X....", "X....", "X....", "X....", "XXXXX"],
    "J": ["..XXX", "...X.", "...X.", "...X.", "...X.", "X..X.", ".XX.."],
    "M": ["X...X", "XX.XX", "X.X.X", "X.X.X", "X...X", "X...X", "X...X"],
    " ": ["..", "..", "..", "..", "..", "..", ".."],
}


def word_cells(text):
    cells, col = [], 0
    for k, chr_ in enumerate(text):
        g = GLYPHS[chr_]
        for r, row in enumerate(g):
            for c, v in enumerate(row):
                if v == "X":
                    cells.append((col + c, r))
        col += len(g[0]) + (1 if k < len(text) - 1 else 0)
    return cells, col


def candy_word(cv, text, x0, y0, pitch, body, edge, outline, drop):
    cells, _ = word_cells(text)
    cell = pitch * 0.99
    hw = cell / 2
    rad = cell * 0.2
    pad = pitch * 0.22  # white outline thickness
    centers = [(x0 + c * pitch + pitch / 2, y0 + r * pitch + pitch / 2) for c, r in cells]
    # 1. hard ink drop, 2. white outline (merges into a stroke), 3. candy body + gloss
    if drop:
        for cx, cy in centers:
            bb = (cx - hw - pad - 2, cy - hw, cx + hw + pad + 2, cy + hw + pad + drop + 2)
            cv.fill(sd_rrect(cx, cy + drop, hw + pad, hw + pad, rad + pad), INK, bb)
    if outline:
        for cx, cy in centers:
            bb = (cx - hw - pad - 2, cy - hw - pad - 2, cx + hw + pad + 2, cy + hw + pad + 2)
            cv.fill(sd_rrect(cx, cy, hw + pad, hw + pad, rad + pad), WHITE, bb)
    for cx, cy in centers:
        bb = (cx - hw - 2, cy - hw - 2, cx + hw + 2, cy + hw + 2)
        cv.fill(sd_rrect(cx, cy + cell * 0.08, hw, hw, rad), edge, bb)
        top, bot = cy - hw, cy + hw

        def grad(x, y, top=top, bot=bot):
            return mix(mix(body, WHITE, 0.28), body, clamp((y - top) / (bot - top)))
        cv.fill(sd_rrect(cx, cy - cell * 0.04, hw, hw * 0.94, rad), grad, bb)
        cv.fill(sd_rrect(cx - hw * 0.38, cy - hw * 0.46, hw * 0.30, hw * 0.15, hw * 0.15),
                WHITE, bb, opacity=0.8)


def make_og(icon_w, icon_pix):
    W, H = 1200, 630
    cv = Canvas(W, H)

    def bg(x, y):
        return mix(SKY_TOP, SKY_BOT, clamp((x * 0.55 + y) / (W * 0.55 + H)))
    cv.fill(lambda x, y: -1e9, bg, (0, 0, W, H))
    # soft glows
    cv.fill(lambda x, y: math.hypot(x - 300, y - 300) - 150, WHITE, (0, 0, W, H), opacity=0.22, soft=520)
    cv.fill(lambda x, y: math.hypot(x - 1050, y - 560) - 80, hx("#FF6FC8"), (500, 200, W, H), opacity=0.25, soft=420)

    # icon with drop shadow and rounded mask
    S, ix, iy = 380, 70, 125
    r = S * 0.225
    cv.fill(sd_rrect(ix + S / 2, iy + S / 2 + 22, S / 2, S / 2, r), INK,
            (ix - 60, iy - 30, ix + S + 60, iy + S + 90), opacity=0.35, soft=40)
    cv.fill(sd_rrect(ix + S / 2, iy + S / 2, S / 2 + 7, S / 2 + 7, r + 7), WHITE,
            (ix - 10, iy - 10, ix + S + 10, iy + S + 10))
    small = resample(icon_pix, icon_w, S)
    mask = sd_rrect(S / 2, S / 2, S / 2, S / 2, r)
    for y in range(S):
        for x in range(S):
            d = mask(x + 0.5, y + 0.5)
            if d >= 0.5:
                continue
            a = 1.0 if d <= -0.5 else 0.5 - d
            i = ((iy + y) * W + ix + x) * 3
            j = (y * S + x) * 3
            for k in range(3):
                cv.px[i + k] += (small[j + k] - cv.px[i + k]) * a

    # wordmark: SWEET / SUITES in candy pink cells, VALET JAM on a gold pill
    tx = 530
    pitch = 18.5
    candy_word(cv, "SWEET", tx, 112, pitch, PINK, PINK_LO, True, 9)
    candy_word(cv, "SUITES", tx, 112 + 7 * pitch + 30, pitch, PINK, PINK_LO, True, 9)

    p2 = 7.5
    _, cols = word_cells("VALET JAM")
    pw, ph = cols * p2 + 52, 7 * p2 + 36
    px0, py0 = tx + 2, 112 + 14 * pitch + 30 + 46
    cxp, cyp = px0 + pw / 2, py0 + ph / 2
    bb = (px0 - 12, py0 - 12, px0 + pw + 12, py0 + ph + 20)
    cv.fill(sd_rrect(cxp, cyp + 7, pw / 2 + 5, ph / 2 + 5, 22), INK, bb, opacity=0.25, soft=8)
    cv.fill(sd_rrect(cxp, cyp, pw / 2 + 5, ph / 2 + 5, 23), WHITE, bb)
    cv.fill(sd_rrect(cxp, cyp + 3, pw / 2, ph / 2, 18), GOLD_LO, bb)
    cv.fill(sd_rrect(cxp, cyp - 2, pw / 2, ph / 2 - 3, 18), GOLD, bb)
    candy_word(cv, "VALET JAM", px0 + 26, py0 + 16, p2, INK, INK, False, 0)

    # row of the nine vehicle colours
    y = py0 + ph + 44
    for k, c in enumerate(VEHICLES):
        cx = tx + 14 + k * 40
        col = hx(c)
        bbx = (cx - 20, y - 20, cx + 20, y + 24)
        cv.fill(sd_rrect(cx, y + 4, 14, 14, 5), mix(col, INK, 0.35), bbx)
        cv.fill(sd_rrect(cx, y, 14, 14, 5),
                lambda x, yy, col=col, y=y: mix(mix(col, WHITE, 0.3), col, clamp((yy - y + 14) / 28)), bbx)
        cv.fill(sd_rrect(cx - 5, y - 7, 4, 2, 2), WHITE, bbx, opacity=0.8)

    write_png(os.path.join(SITE, "og.png"), W, H, cv.px)


def rounded_rgba(pix, n, radius_frac=0.225):
    out = []
    m = sd_rrect(n / 2, n / 2, n / 2, n / 2, n * radius_frac)
    for y in range(n):
        for x in range(n):
            d = m(x + 0.5, y + 0.5)
            a = 0.0 if d >= 0.5 else 1.0 if d <= -0.5 else 0.5 - d
            j = (y * n + x) * 3
            out += [pix[j], pix[j + 1], pix[j + 2], a]
    return out


def main():
    os.makedirs(os.path.join(SITE, "assets"), exist_ok=True)
    w, pix = icon_rgb()
    print("icon decoded", w)
    p512 = resample(pix, w, 512)
    write_png(os.path.join(SITE, "assets", "icon-512.png"), 512, 512, p512)
    p180 = resample(p512, 512, 180)
    write_png(os.path.join(SITE, "icon.png"), 180, 180, p180)
    p64 = resample(p512, 512, 64)
    write_png(os.path.join(SITE, "favicon.png"), 64, 64, rounded_rgba(p64, 64), alpha=True)
    print("icons written")
    make_og(w, pix)
    print("og.png written")


if __name__ == "__main__":
    main()
