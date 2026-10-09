#!/usr/bin/env python3
"""Build the Sweet Suites: Valet Jam static site. Standard library only.

    python3 build.py            # writes *.html, sitemap.xml, robots.txt, CNAME
    python3 tools/make_images.py  # (re)writes og.png, favicon.png, icon.png, assets/icon-512.png

Page bodies live in _src/<page>.html. This script wraps each one in the shared
<head>, nav and footer, and fills the {{TOKENS}} used for the inline SVG
illustrations, which are generated below from the brand palette.

Placeholders left in the output on purpose (replace before publishing):
    __DOMAIN__        the site's domain, e.g. example.com (no scheme, no slash)
    __APPSTORE_URL__  the App Store product URL
Pages link to each other with relative *.html paths, so the site also works
opened straight from disk (file://) and on GitHub Pages.
"""
import math
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_src")
DOMAIN = "sweetsuitesgame.com"
BASE = "https://" + DOMAIN
APPSTORE = "https://apps.apple.com/app/id6820528894"
EMAIL = "hello@" + DOMAIN
PRIVACY_EMAIL = "privacy@" + DOMAIN
COMPANY = "ELAQ Limited"
EFFECTIVE = "10 October 2026"
YEAR = "2026"
NAME = "Sweet Suites: Valet Jam"

# ------------------------------------------------------------------ palette
# name: (base, light, dark, symbol, symbol ink) from BrandPalette.swift
VEH = {
    "cherry":    ("#F2364D", "#F78A98", "#B12A47", "heart", "#FFFFFF"),
    "sky":       ("#2F8CFF", "#86BCFF", "#2967C3", "circle", "#2B1D5C"),
    "lemon":     ("#FFCF2E", "#FFE386", "#BA9531", "star", "#2B1D5C"),
    "lime":      ("#5BCB3A", "#A0E18D", "#479339", "leaf", "#2B1D5C"),
    "grape":     ("#8A4DFF", "#BB98FF", "#683AC3", "moon", "#FFFFFF"),
    "tangerine": ("#FF8A1F", "#FFBB7D", "#BA6527", "triangle", "#2B1D5C"),
    "bubblegum": ("#FF6FC8", "#FFABDF", "#BA529D", "diamond", "#2B1D5C"),
    "mint":      ("#19C9B4", "#7AE0D4", "#19918F", "drop", "#2B1D5C"),
    "cocoa":     ("#8B5A3C", "#BC9F8E", "#69443B", "square", "#FFFFFF"),
}
INK = "#2B1D5C"
CELL = "#D9D4E6"
ASPHALT = "#4A4E6E"
LOTLINE = "#F4F1FF"

# Roof symbols (24-unit viewBox), same shapes as the brand sheet.
SYMBOLS = {
    "heart": '<path d="M12 21s-7.5-4.6-9.6-9.3C.9 8.3 3 4.5 6.6 4.5c2.2 0 3.6 1.2 4.4 2.6.8-1.4 2.2-2.6 4.4-2.6 3.6 0 5.7 3.8 4.2 7.2C19.5 16.4 12 21 12 21z"/>',
    "circle": '<circle cx="12" cy="12" r="8.5"/>',
    "star": '<path d="M12 2.5l2.9 6.1 6.6.8-4.9 4.6 1.3 6.6L12 17.3l-5.9 3.3 1.3-6.6-4.9-4.6 6.6-.8z"/>',
    "leaf": '<path d="M20.5 3.5C9 3.5 3.5 9 3.5 16c0 1.6.4 3 .9 4.1C6 13.6 10 10 15 8c-4 2.6-7.2 6.4-8.6 12.3 1 .4 2.1.6 3.3.6 7.2 0 10.8-6.9 10.8-17.4z"/>',
    "moon": '<path d="M14.5 3a9 9 0 1 0 6.5 13.4A7.5 7.5 0 0 1 14.5 3z"/>',
    "triangle": '<path d="M12 3.5l9.5 16.5h-19z"/>',
    "diamond": '<path d="M12 2l8 10-8 10-8-10z"/>',
    "drop": '<path d="M12 2.5s-7 7.6-7 12.3a7 7 0 0 0 14 0C19 10.1 12 2.5 12 2.5z"/>',
    "square": '<rect x="4" y="4" width="16" height="16" rx="3"/>',
}


def sprite():
    """Hidden SVG holding the roof symbols and shared gradients, once per page."""
    syms = "".join('<symbol id="sym-%s" viewBox="0 0 24 24">%s</symbol>' % (k, v) for k, v in SYMBOLS.items())
    grads = "".join(
        '<linearGradient id="g-%s" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="%s"/>'
        '<stop offset=".55" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>' % (n, l, b, d)
        for n, (b, l, d, _, _) in VEH.items())
    return ('<svg class="sr" width="0" height="0" aria-hidden="true" focusable="false"><defs>%s%s</defs></svg>'
            % (syms, grads))


def car(x, y, w, h, color, extra=""):
    """A top-down candy vehicle: rounded body, glossy top, ink outline, roof symbol."""
    b, l, d, sym, ink = VEH[color]
    r = min(w, h) * 0.3
    s = min(w, h) * 0.56
    return (
        '<g%s>'
        '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f" fill="%s"/>'
        '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f" fill="url(#g-%s)" stroke="%s" stroke-width="2"/>'
        '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="2" fill="#fff" opacity=".7"/>'
        '<use href="#sym-%s" x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
        '</g>' % (extra, x, y + 3, w, h, r, d, x, y, w, h, r, color, INK,
                  x + w * 0.16, y + h * 0.14, max(4, w * 0.22), 3,
                  sym, x + w / 2 - s / 2, y + h / 2 - s / 2, s, s, ink))


# ------------------------------------------------------------------ step 1: the lot
def svg_lot():
    C, ox, oy = 30, 30, 26  # cell size, lot origin
    cols, rows = 6, 4
    W, H = 240, 180
    out = ['<svg viewBox="0 0 %d %d" role="img" aria-labelledby="lot-t">' % (W, H),
           '<title id="lot-t">A jammed valet lot seen from above. A cherry-red car with a heart on its roof '
           'slides right and drives out through the matching red gate.</title>']
    # lot surface and kerb
    out.append('<rect x="%d" y="%d" width="%d" height="%d" rx="18" fill="%s" stroke="%s" stroke-width="3"/>'
               % (ox - 12, oy - 12, cols * C + 24, rows * C + 24, ASPHALT, INK))
    # bay markings
    for c in range(1, cols):
        out.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="1.5" stroke-dasharray="4 5" opacity=".35"/>'
                   % (ox + c * C, oy, ox + c * C, oy + rows * C, LOTLINE))
    for r in range(1, rows):
        out.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="1.5" stroke-dasharray="4 5" opacity=".35"/>'
                   % (ox, oy + r * C, ox + cols * C, oy + r * C, LOTLINE))
    # gates: matching colour bars on the lot edge
    gy = oy + 1 * C
    out.append('<rect class="gate-glow" x="%d" y="%d" width="22" height="%d" rx="8" fill="#FF3E86" opacity="0"/>'
               % (ox + cols * C + 2, gy - 4, C + 8))
    out.append('<rect x="%d" y="%d" width="10" height="%d" rx="4" fill="%s" stroke="%s" stroke-width="2"/>'
               % (ox + cols * C + 6, gy + 2, C - 4, VEH["cherry"][0], INK))
    out.append('<use href="#sym-heart" x="%d" y="%d" width="10" height="10" fill="#fff"/>' % (ox + cols * C + 6, gy + C / 2 - 5))
    out.append('<rect x="%d" y="%d" width="%d" height="10" rx="4" fill="%s" stroke="%s" stroke-width="2"/>'
               % (ox + 3 * C + 2, oy - 16, C - 4, VEH["sky"][0], INK))
    out.append('<rect x="%d" y="%d" width="10" height="%d" rx="4" fill="%s" stroke="%s" stroke-width="2"/>'
               % (ox - 16, oy + 3 * C + 2, C - 4, VEH["lemon"][0], INK))

    def v(col, row, length, horiz, color, extra=""):
        p = 3
        if horiz:
            return car(ox + col * C + p, oy + row * C + p, length * C - 2 * p, C - 2 * p - 3, color, extra)
        return car(ox + col * C + p, oy + row * C + p, C - 2 * p, length * C - 2 * p - 3, color, extra)

    out.append(v(1, 0, 2, False, "sky"))
    out.append(v(3, 0, 2, True, "grape"))
    out.append(v(0, 1, 2, False, "mint"))
    out.append(v(5, 0, 1, True, "cocoa"))
    out.append(v(4, 2, 2, False, "lime"))
    out.append(v(0, 3, 3, True, "lemon"))
    out.append(v(5, 2, 1, True, "tangerine"))
    out.append(v(2, 2, 2, True, "bubblegum"))
    # the car that leaves, animated
    out.append('<g class="car-exit">%s</g>' % v(2, 1, 2, True, "cherry"))
    # "Sweet!" pop when it leaves
    out.append('<g class="pop"><rect x="148" y="58" width="72" height="26" rx="13" fill="#FFC93C" stroke="#fff" stroke-width="3"/>'
               '<text x="184" y="76" text-anchor="middle" font-family="ui-rounded,Arial Rounded MT Bold,system-ui,sans-serif" '
               'font-weight="900" font-size="14" fill="%s">Sweet!</text></g>' % INK)
    out.append('</svg>')
    return "".join(out)


# ------------------------------------------------------------------ step 2: paint the picture
SOFA = [
    "..BBBBBBBB..",
    ".BBBBBBBBBB.",
    ".BYYBBBBYYB.",
    "BBYYBBBBYYBB",
    "BBBBBBBBBBBB",
    "BBBBBBBBBBBB",
    ".BBBBBBBBBB.",
    ".C........C.",
]


def svg_paint():
    W, H = 240, 180
    pitch, cell = 13, 11.5
    gw = len(SOFA[0]) * pitch
    x0, y0 = (W - gw) / 2, 10
    colors = {"B": "sky", "Y": "lemon", "C": "cocoa"}
    out = ['<svg viewBox="0 0 %d %d" role="img" aria-labelledby="paint-t">' % (W, H),
           '<title id="paint-t">A pixel-art sofa drawn as a grid of cells. Blue cells fill in one after another '
           'as paint flows across the picture. Below it, a paint tray with five slots, two holding leftover paint.</title>',
           '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="12" fill="#fff" stroke="%s" stroke-width="2"/>'
           % (x0 - 8, y0 - 6, gw + 14, len(SOFA) * pitch + 12, "#EDE8F7")]
    order = []
    for key in "BYC":  # paint flows colour by colour, in reading order
        for r, row in enumerate(SOFA):
            for c, ch in enumerate(row):
                if ch == key:
                    order.append((r, c, ch))
    n = len(order)
    for i, (r, c, ch) in enumerate(order):
        base = VEH[colors[ch]][0]
        delay = 0.15 + i * (2.6 / n)
        # static fallback (reduced motion): painted, except the last few cells
        static = base if i < n - 6 else CELL
        out.append('<rect class="pc" style="--c:%s;--d:%.2fs" x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="3" fill="%s"/>'
                   % (base, delay, x0 + c * pitch, y0 + r * pitch, cell, cell, static))
    # paint tray: 5 slots
    ty = y0 + len(SOFA) * pitch + 22
    out.append('<text x="%d" y="%d" font-family="ui-rounded,Arial Rounded MT Bold,system-ui,sans-serif" font-weight="800" '
               'font-size="10" fill="%s" letter-spacing="1">PAINT TRAY</text>' % (30, ty - 5, "#5E5585"))
    slots = ["sky", "lemon", None, None, None]
    sw = 30
    sx0 = (W - (5 * sw + 4 * 6)) / 2
    for k, s in enumerate(slots):
        x = sx0 + k * (sw + 6)
        out.append('<rect x="%.1f" y="%d" width="%d" height="26" rx="8" fill="#EDE8F7" stroke="%s" stroke-width="2"/>'
                   % (x, ty, sw, INK))
        if s:
            b, l, d, sym, ink = VEH[s]
            out.append('<rect x="%.1f" y="%d" width="%d" height="18" rx="6" fill="url(#g-%s)"/>' % (x + 4, ty + 4, sw - 8, s))
            out.append('<use href="#sym-%s" x="%.1f" y="%d" width="10" height="10" fill="%s"/>' % (sym, x + sw / 2 - 5, ty + 8, ink))
    out.append('</svg>')
    return "".join(out)


# ------------------------------------------------------------------ step 3: the hotel room (isometric)
def iso(x, y, z):
    return 120 + (x - y) * 8.66, 66 + (x + y) * 5 - z * 10


def poly(pts, fill, stroke=INK, sw=1.4, extra=""):
    return '<polygon points="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"%s/>' % (
        " ".join("%.1f,%.1f" % iso(*p) for p in pts), fill, stroke, sw, extra)


def box(x0, y0, z0, x1, y1, z1, top, right, left):
    return (poly([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], top)
            + poly([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], right)
            + poly([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], left))


def svg_room():
    sky = VEH["sky"]
    lemon = VEH["lemon"]
    out = ['<svg viewBox="0 0 240 180" role="img" aria-labelledby="room-t">',
           '<title id="room-t">An isometric hotel lounge: pastel walls, a window, a framed pixel heart, a wooden floor and rug, '
           'a potted plant, and the blue sofa from the painted picture dropping into place. Three gold stars sparkle above.</title>']
    # walls and floor
    out.append(poly([(0, 0, 0), (0, 10, 0), (0, 10, 6.2), (0, 0, 6.2)], "#FFE1EF"))
    out.append(poly([(0, 0, 0), (10, 0, 0), (10, 0, 6.2), (0, 0, 6.2)], "#E6E0FF"))
    out.append(poly([(0, 0, 0), (10, 0, 0), (10, 10, 0), (0, 10, 0)], "#FFD9A8"))
    for k in range(1, 10, 2):  # floorboards
        a, b = iso(k, 0, 0), iso(k, 10, 0)
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#F0C188" stroke-width="1"/>' % (a + b))
    # skirting
    out.append(poly([(0, 0, 0), (0, 10, 0), (0, 10, .35), (0, 0, .35)], "#fff", sw=1))
    out.append(poly([(0, 0, 0), (10, 0, 0), (10, 0, .35), (0, 0, .35)], "#fff", sw=1))
    # window on the right wall
    out.append(poly([(3.6, 0, 3.0), (7.6, 0, 3.0), (7.6, 0, 5.4), (3.6, 0, 5.4)], "#fff", sw=1.4))
    out.append(poly([(3.9, 0, 3.25), (7.3, 0, 3.25), (7.3, 0, 5.15), (3.9, 0, 5.15)], "#9EE7FF", sw=1))
    a, b = iso(5.6, 0, 3.25), iso(5.6, 0, 5.15)
    out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#fff" stroke-width="2"/>' % (a + b))
    # framed pixel heart on the left wall
    out.append(poly([(0, 2.6, 2.6), (0, 6.4, 2.6), (0, 6.4, 5.4), (0, 2.6, 5.4)], "#FFC93C"))
    out.append(poly([(0, 2.9, 2.85), (0, 6.1, 2.85), (0, 6.1, 5.15), (0, 2.9, 5.15)], "#fff", sw=1))
    heart = [".XX.XX.", "XXXXXXX", "XXXXXXX", ".XXXXX.", "..XXX..", "...X..."]
    for r, row in enumerate(heart):
        for c, ch in enumerate(row):
            if ch == "X":
                y0, z0 = 3.15 + c * 0.4, 4.85 - r * 0.32
                out.append(poly([(0, y0, z0), (0, y0 + .36, z0), (0, y0 + .36, z0 - .28), (0, y0, z0 - .28)],
                                VEH["cherry"][0], sw=0))
    # rug
    out.append(poly([(2.8, 3.6, .02), (8.4, 3.6, .02), (8.4, 8.6, .02), (2.8, 8.6, .02)], "#FF8FC8", sw=1.2))
    out.append(poly([(3.4, 4.2, .03), (7.8, 4.2, .03), (7.8, 8.0, .03), (3.4, 8.0, .03)], "none", stroke="#fff", sw=1.2,
                    extra=' stroke-dasharray="3 3"'))
    # plant (back left corner area)
    out.append(box(1.0, 7.0, 0, 2.2, 8.2, 1.4, "#BC9F8E", "#8B5A3C", "#69443B"))
    px, py = iso(1.6, 7.6, 2.4)
    for dx, dy, rr, col in [(-7, 2, 7, "#479339"), (6, 1, 7, "#479339"), (0, -6, 8, "#5BCB3A"), (-4, -1, 6, "#A0E18D")]:
        out.append('<circle cx="%.1f" cy="%.1f" r="%d" fill="%s" stroke="%s" stroke-width="1.4"/>' % (px + dx, py + dy, rr, col, INK))
    # sofa (the painted picture, now furniture), dropping in
    s = ['<g class="reveal">']
    s.append('<ellipse cx="%.1f" cy="%.1f" rx="44" ry="12" fill="%s" opacity=".18"/>' % (iso(5.5, 1.9, 0) + (INK,)))
    s.append(box(3.0, 0.3, 0.3, 8.0, 1.2, 3.0, sky[1], sky[0], sky[2]))       # back
    s.append(box(3.0, 1.2, 0.3, 8.0, 3.2, 1.5, sky[1], sky[0], sky[2]))       # seat
    s.append(box(3.6, 1.0, 1.5, 5.4, 1.6, 2.7, lemon[1], lemon[0], lemon[2]))  # cushions
    s.append(box(5.6, 1.0, 1.5, 7.4, 1.6, 2.7, lemon[1], lemon[0], lemon[2]))
    s.append(box(3.0, 1.2, 1.5, 3.6, 3.2, 2.2, sky[1], sky[0], sky[2]))       # arms
    s.append(box(7.4, 1.2, 1.5, 8.0, 3.2, 2.2, sky[1], sky[0], sky[2]))
    for lx, ly in [(3.2, 2.9), (7.7, 2.9)]:
        s.append(box(lx, ly, 0, lx + .25, ly + .25, .3, "#8B5A3C", "#69443B", "#69443B"))
    s.append('</g>')
    out.append("".join(s))
    # hotel rating badge
    out.append('<rect x="160" y="6" width="72" height="24" rx="12" fill="#fff" stroke="%s" stroke-width="1.6"/>' % INK)
    for k in range(3):
        out.append('<use class="sparkle" href="#sym-star" x="%d" y="9" width="18" height="18" fill="#FFC93C" stroke="%s" stroke-width="1.4"/>'
                   % (166 + k * 21, INK))
    out.append('</svg>')
    return "".join(out)


def fleet():
    items = []
    for n, (b, l, d, sym, ink) in VEH.items():
        items.append('<li><span class="chip" style="--b:%s;--l:%s;--d:%s"><svg viewBox="0 0 24 24" aria-hidden="true" '
                     'style="fill:%s"><use href="#sym-%s"/></svg></span>%s<span class="sr"> car, %s symbol</span></li>'
                     % (b, l, d, ink, sym, n, sym))
    return '<ul class="fleet" id="fleet" aria-label="The nine car colours and their roof symbols">%s</ul>' % "".join(items)


def svg_lost():
    out = ['<svg viewBox="0 0 340 170" role="img" aria-labelledby="lost-t">',
           '<title id="lost-t">An empty parking bay with dashed lines. A red car is driving off the edge of the lot.</title>',
           '<rect x="10" y="20" width="320" height="130" rx="22" fill="%s" stroke="%s" stroke-width="3"/>' % (ASPHALT, INK)]
    for x in (90, 170, 250):
        out.append('<line x1="%d" y1="34" x2="%d" y2="136" stroke="%s" stroke-width="2" stroke-dasharray="6 7" opacity=".4"/>' % (x, x, LOTLINE))
    out.append('<text x="130" y="100" text-anchor="middle" font-family="ui-rounded,Arial Rounded MT Bold,system-ui,sans-serif" '
               'font-weight="900" font-size="40" fill="%s" opacity=".55">404</text>' % LOTLINE)
    out.append('<g class="car-exit">%s</g>' % car(220, 66, 66, 34, "cherry"))
    out.append('</svg>')
    return "".join(out)


# ------------------------------------------------------------------ chrome
BADGE = ('<a class="badge" href="%s" aria-label="Download Sweet Suites: Valet Jam on the App Store">'
         '<svg viewBox="0 0 24 24" aria-hidden="true" fill="#fff"><path d="M12 3a1.2 1.2 0 0 1 1.2 1.2v8.9l3-3a1.2 1.2 0 1 1 1.7 1.7l-5 5a1.2 1.2 0 0 1-1.7 0l-5-5a1.2 1.2 0 1 1 1.7-1.7l3 3V4.2A1.2 1.2 0 0 1 12 3zM4.2 18.6h15.6a1.2 1.2 0 1 1 0 2.4H4.2a1.2 1.2 0 1 1 0-2.4z"/></svg>'
         '<span><small>Download on the</small><b>App Store</b></span></a>' % APPSTORE)

NAV = """<a class="skip" href="#main">Skip to content</a>
<header class="nav" id="nav">
  <div class="wrap nav-in">
    <a class="brand" href="{root}index.html"><img src="{root}icon.png" alt="" width="36" height="36"><span>Sweet Suites</span></a>
    <nav class="links" aria-label="Sections">
      <a href="{root}index.html#how">How it works</a>
      <a href="{root}index.html#features">Features</a>
      <a href="{root}index.html#fair-play">Fair play</a>
      <a href="{root}support.html">Support</a>
    </nav>
    <a class="pill small" href="{appstore}">Get the game</a>
  </div>
</header>"""

FOOT = """<footer class="foot">
  <div class="wrap foot-grid">
    <div class="foot-brand">
      <a class="brand" href="{root}index.html"><img src="{root}icon.png" alt="" width="36" height="36"><span>Sweet Suites: Valet Jam</span></a>
      <p>Clear the jammed valet lot, paint pixel-art pictures and renovate a sweet hotel, one room at a time. For iPhone.</p>
    </div>
    <nav aria-label="Game"><h2>Game</h2><a href="{root}index.html#how">How it works</a><a href="{root}index.html#features">Features</a><a href="{root}support.html">Support &amp; FAQ</a><a href="mailto:{email}">{email}</a></nav>
    <nav aria-label="Legal"><h2>Legal</h2><a href="{root}privacy.html">Privacy policy</a><a href="{root}terms.html">Terms of use</a><a href="https://www.apple.com/legal/internet-services/itunes/dev/stdeula/">Apple Standard EULA</a></nav>
  </div>
  <div class="wrap foot-base"><p>© {year} {company}. Free to play, with optional in-app purchases. No third-party ads and no tracking.</p><p>This website uses no cookies and no analytics.</p></div>
</footer>"""

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
{base}<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">{robots}
<meta name="color-scheme" content="light">
<meta name="theme-color" content="#4FD6FF">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{name}">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{base_url}/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="The Sweet Suites app icon, a pink car leaving a trail of paint that fills a pixel heart, beside the words Sweet Suites, Valet Jam in candy-pink pixel letters.">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{base_url}/og.png">
<link rel="icon" href="{root}favicon.png" type="image/png">
<link rel="apple-touch-icon" href="{root}icon.png">
<link rel="stylesheet" href="{root}assets/site.css?v=1">
<script src="{root}assets/site.js?v=1" defer></script>{extra_head}
</head>
<body>
"""

PAGES = [
    # file, path for canonical, title, description
    ("index", "/", NAME + " · Car jam puzzle & hotel decor",
     "Slide candy-coloured cars out of a jammed valet lot, watch each one paint a pixel-art picture, "
     "and renovate a sweet hotel room by room. Free to play on iPhone."),
    ("support", "/support", "Support & FAQ · " + NAME,
     "Help with Sweet Suites: Valet Jam: restoring purchases, in-game promotions and Remove Ads, ad-skip tickets, lives, "
     "lost progress, and how to contact us."),
    ("privacy", "/privacy", "Privacy policy · " + NAME,
     "How Sweet Suites: Valet Jam handles data: no account and no server, your save stays on your iPhone, "
     "no third-party ads and no tracking, payments through Apple."),
    ("terms", "/terms", "Terms of use · " + NAME,
     "Terms of use for Sweet Suites: Valet Jam: virtual currency, in-app purchases through Apple, and "
     "in-game promotions."),
    ("404", "/404", "Page not found · " + NAME, "This page drove off the lot."),
]

LD_JSON = """
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"MobileApplication","name":"%s","operatingSystem":"iOS 17.0 or later",
"applicationCategory":"GameApplication","url":"%s/","image":"%s/icon.png","installUrl":"%s",
"offers":{"@type":"Offer","price":"0","priceCurrency":"USD"},
"publisher":{"@type":"Organization","name":"%s","email":"%s"}}
</script>""" % (NAME, BASE, BASE, APPSTORE, COMPANY, EMAIL)

# 404 is served by GitHub Pages at any missing path, possibly nested, so on
# http(s) its relative links must resolve from the site root. On file:// they
# stay relative so the page can be checked straight from disk.
BASE_404 = "<script>if(location.protocol!=='file:')document.write('<base href=\"/\">')</script>\n"


def esc(s):
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


def render(name, path, title, desc):
    with open(os.path.join(SRC, name + ".html"), encoding="utf-8") as f:
        body = f.read()
    tokens = {
        "SPRITE": sprite(), "LOT": svg_lot(), "PAINT": svg_paint(), "ROOM": svg_room(),
        "FLEET": fleet(), "LOST": svg_lost(), "BADGE": BADGE, "APPSTORE": APPSTORE,
        "EMAIL": EMAIL, "PRIVACY_EMAIL": PRIVACY_EMAIL, "COMPANY": COMPANY, "EFFECTIVE": EFFECTIVE, "DOMAIN": DOMAIN, "NAME": NAME,
    }
    body = re.sub(r"\{\{(\w+)\}\}", lambda m: tokens[m.group(1)], body)
    if not body.lstrip().startswith("<svg class=\"sr\""):
        body = tokens["SPRITE"] + "\n" + body
    root = ""
    head = HEAD.format(
        base=BASE_404 if name == "404" else "", title=esc(title), desc=esc(desc),
        url=BASE + path, robots='\n<meta name="robots" content="noindex">' if name == "404" else "",
        name=esc(NAME), base_url=BASE, root=root, extra_head=LD_JSON if name == "index" else "")
    html = (head + NAV.format(root=root, appstore=APPSTORE) + "\n<main id=\"main\">\n" + body.strip()
            + "\n</main>\n" + FOOT.format(root=root, email=EMAIL, year=YEAR, company=COMPANY) + "\n</body>\n</html>\n")
    with open(os.path.join(HERE, name + ".html"), "w", encoding="utf-8") as f:
        f.write(html)
    return html


def main():
    for p in PAGES:
        render(*p)
    urls = [p[1] for p in PAGES if p[0] != "404"]
    with open(os.path.join(HERE, "sitemap.xml"), "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for u in urls:
            f.write("  <url><loc>%s%s</loc><lastmod>2026-10-08</lastmod></url>\n" % (BASE, u))
        f.write("</urlset>\n")
    with open(os.path.join(HERE, "robots.txt"), "w") as f:
        f.write("User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % BASE)
    with open(os.path.join(HERE, "CNAME"), "w") as f:
        f.write(DOMAIN + "\n")
    print("built", ", ".join(p[0] + ".html" for p in PAGES))


if __name__ == "__main__":
    main()
