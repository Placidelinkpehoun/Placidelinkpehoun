"""Generates assets/about-{dark,light}.svg: bio text + "Most Used Languages" card.

Language stats come from the GitHub API (public, non-fork repos of USER), so the
card stays up to date when this runs in the scheduled GitHub Action.

    python scripts/about.py            # needs: pip install fonttools brotli
"""
import base64
import io
import json
import os
import urllib.request
from xml.sax.saxutils import escape

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

USER = "PlacideLinkpehoun"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets")
FONT = os.path.join(HERE, "fonts", "NotoSansTaiLe.ttf")

BIO = ["I enjoy working on creative", "projects that draw on both my", "coding and design skills. I'm",
       "interested in video game", "development and build various", "projects in my free time."]
THEMES = {"dark": "#E6EDF3", "light": "#1F2328"}  # bio text colour

# "tokyonight" look of github-readme-stats
CARD_BG, CARD_TITLE, CARD_TEXT = "#1A1B27", "#70A5FD", "#38BDAE"
TOP_N = 8
FALLBACK_COLORS = {"Python": "#3572A5", "HTML": "#e34c26", "TypeScript": "#3178c6", "CSS": "#663399",
                   "C#": "#178600", "JavaScript": "#f1e05a", "ShaderLab": "#222c37", "GDScript": "#355570"}


def api(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": USER})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def languages():
    totals = {}
    for repo in api(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner"):
        if repo["fork"]:
            continue
        for lang, size in api(repo["languages_url"]).items():
            totals[lang] = totals.get(lang, 0) + size
    total = sum(totals.values()) or 1
    top = sorted(totals.items(), key=lambda kv: -kv[1])[:TOP_N]
    return [(lang, size * 100 / total) for lang, size in top]


def colors():
    try:
        with urllib.request.urlopen("https://raw.githubusercontent.com/ozh/github-colors/master/colors.json", timeout=30) as r:
            data = json.load(r)
        return {k: v["color"] for k, v in data.items() if v.get("color")}
    except Exception:
        return FALLBACK_COLORS


def font_face(text):
    tt = TTFont(FONT)
    opts = Options()
    opts.flavor = "woff2"
    sub = Subsetter(opts)
    sub.populate(text=text + " ")
    sub.subset(tt)
    buf = io.BytesIO()
    tt.save(buf)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"@font-face{{font-family:'NotoTaiLe';src:url(data:font/woff2;base64,{b64}) format('woff2');}}"


def text_width(text, size):
    tt = TTFont(FONT)
    cmap, hmtx = tt.getBestCmap(), tt["hmtx"]
    return sum(hmtx[cmap[ord(c)]][0] for c in text if ord(c) in cmap) * size / tt["head"].unitsPerEm


def lang_card(langs, cols, bx, by, bw, bh):
    """389x246 card, same layout as github-readme-stats 'Most Used Languages'."""
    s = f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="6" fill="{CARD_BG}"/>'
    s += (f'<text x="{bx + 27}" y="{by + 48}" font-family="NotoTaiLe, sans-serif" font-size="21" '
          f'font-weight="bold" fill="{CARD_TITLE}">Most Used Languages</text>')
    barx, bary, barw, barh = bx + 27, by + 70, bw - 54, 9
    s += f'<clipPath id="bar"><rect x="{barx}" y="{bary}" width="{barw}" height="{barh}" rx="4"/></clipPath><g clip-path="url(#bar)">'
    x = barx
    for lang, pct in langs:
        w = barw * pct / 100
        s += f'<rect x="{x:.2f}" y="{bary}" width="{w + 0.5:.2f}" height="{barh}" fill="{cols.get(lang, "#858585")}"/>'
        x += w
    s += "</g>"
    half = (len(langs) + 1) // 2
    for i, (lang, pct) in enumerate(langs):
        col, row = divmod(i, half)
        lx = bx + 31 + col * 180
        ly = by + 121 + row * 33
        s += f'<circle cx="{lx}" cy="{ly - 4.5}" r="6.5" fill="{cols.get(lang, "#858585")}"/>'
        s += (f'<text x="{lx + 15}" y="{ly}" font-family="NotoTaiLe, sans-serif" font-size="15" '
              f'fill="{CARD_TEXT}">{escape(lang)} {pct:.2f}%</text>')
    return s


def build(theme, langs, cols):
    W, H = 404, 616
    size = 22 * 303 / text_width(BIO[0], 22)  # first line ~303 px wide, as in the mockup
    bio = "".join(f'<text x="15" y="{107 + i * 36}" font-family="NotoTaiLe, sans-serif" font-size="{size:.2f}" '
                  f'fill="{THEMES[theme]}">{escape(l)}</text>' for i, l in enumerate(BIO))
    card = lang_card(langs, cols, 15, 325, 389, 246)
    used = "".join(BIO) + "Most Used Languages" + "".join(f"{l} {p:.2f}%" for l, p in langs)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img">'
            f'<title>{escape(" ".join(BIO))}</title><style>{font_face(used)}</style>{bio}{card}</svg>')


if __name__ == "__main__":
    langs, cols = languages(), colors()
    print(", ".join(f"{l} {p:.2f}%" for l, p in langs))
    os.makedirs(OUT, exist_ok=True)
    for theme in THEMES:
        with open(os.path.join(OUT, f"about-{theme}.svg"), "w", encoding="utf-8") as f:
            f.write(build(theme, langs, cols))
