"""Community colour chart: visitors vote for a colour through a GitHub issue.

    python scripts/colors.py render   # regenerate assets/colors/*.svg from data/colors.json
    python scripts/colors.py vote     # apply the vote in $VOTE_TITLE ("color|<id>") by $VOTE_USER

The vote command writes the reply posted on the issue to $GITHUB_OUTPUT (key: reply).
"""
import base64
import io
import json
import os
import sys
from urllib.parse import quote
from xml.sax.saxutils import escape

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

REPO = "PlacideLinkpehoun/Placidelinkpehoun"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DATA = os.path.join(ROOT, "data", "colors.json")
OUT = os.path.join(ROOT, "assets", "colors")
FONTS = {"Orbitron": "Orbitron-Medium.ttf", "NotoTaiLe": "NotoSansTaiLe.ttf"}

STEP, MAX = 5, 100
SLOT_TOP, SLOT_BOTTOM, TRACK, TEXT = "#494949", "#2B2B2B", "#1E1E1E", "#EDEDED"  # same greys as the skill slots
THEMES = {"dark": ("#E6EDF3", "#9198A1"), "light": ("#1F2328", "#59636E")}


# ------------------------------------------------------------------ helpers
def font_face(family, text):
    tt = TTFont(os.path.join(HERE, "fonts", FONTS[family]))
    opts = Options()
    opts.flavor = "woff2"
    sub = Subsetter(opts)
    sub.populate(text=text + " ")
    sub.subset(tt)
    buf = io.BytesIO()
    tt.save(buf)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"@font-face{{font-family:'{family}';src:url(data:font/woff2;base64,{b64}) format('woff2');}}"


def svg(w, h, body, fonts, title):
    css = "".join(font_face(f, t) for f, t in fonts.items())
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">'
            f'<title>{escape(title)}</title><style>{css}</style>{body}</svg>')


def write(name, content):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(content)


def load():
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


def save(data):
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def vote_url(c):
    title = quote(f"color|{c['id']}")
    body = quote(f"Just click **Create** to give **{c['name']}** +{STEP} 🎨\n\n(The issue closes itself once the chart is updated.)")
    return f"https://github.com/{REPO}/issues/new?title={title}&body={body}"


# ------------------------------------------------------------------ rendering
def render_header(data, theme):
    fg, muted = THEMES[theme]
    votes = data["total_votes"]
    last = data["last"][-1] if data["last"] else None
    sub = f"Click a color to give it +{STEP} (opens an issue)  ·  {votes} vote{'s' if votes != 1 else ''}"
    if last:
        sub += f"  ·  last: @{last['user']} → {last['color']}"
    title = "PICK YOUR COLOR"
    body = (f'<text x="2" y="52" font-family="Orbitron, sans-serif" font-size="24" letter-spacing="0.06em" fill="{fg}">{title}</text>'
            f'<text x="2" y="82" font-family="NotoTaiLe, sans-serif" font-size="17" fill="{muted}">{escape(sub)}</text>')
    return svg(998, 96, body, {"Orbitron": title, "NotoTaiLe": sub}, f"Pick your color - {sub}")


def render_row(c):
    W, H = 998, 46
    v = c["value"]
    full = v >= MAX
    tx, tw = 210, 600
    fw = tw * min(v, MAX) / MAX
    label = "MAX" if full else str(v)
    btn = "MAX" if full else f"+{STEP}"
    body = (
        f'<defs><linearGradient id="slot" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{SLOT_TOP}"/>'
        f'<stop offset="1" stop-color="{SLOT_BOTTOM}"/></linearGradient></defs>'
        f'<rect x="0" y="0" width="{W}" height="{H}" rx="10" fill="url(#slot)"/>'
        f'<circle cx="26" cy="{H / 2}" r="9" fill="{c["hex"]}"/>'
        f'<text x="46" y="{H / 2 + 6}" font-family="NotoTaiLe, sans-serif" font-size="18" fill="{TEXT}">{escape(c["name"])}</text>'
        f'<rect x="{tx}" y="{H / 2 - 7}" width="{tw}" height="14" rx="7" fill="{TRACK}"/>'
        + (f'<rect x="{tx}" y="{H / 2 - 7}" width="{fw:.1f}" height="14" rx="7" fill="{c["hex"]}">'
           f'<animate attributeName="width" from="0" to="{fw:.1f}" dur="0.9s" calcMode="spline" keySplines="0.2 0.8 0.3 1" keyTimes="0;1" fill="freeze"/></rect>'
           if v > 0 else "")
        + f'<text x="{tx + tw + 60}" y="{H / 2 + 6}" text-anchor="end" font-family="Orbitron, sans-serif" font-size="16" fill="{TEXT}">{label}</text>'
        f'<rect x="{W - 104}" y="8" width="94" height="{H - 16}" rx="8" fill="{c["hex"]}" opacity="{0.35 if full else 1}"/>'
        f'<text x="{W - 57}" y="{H / 2 + 6}" text-anchor="middle" font-family="Orbitron, sans-serif" font-size="16" fill="#0D1117">{btn}</text>'
    )
    return svg(W, H, body, {"NotoTaiLe": c["name"], "Orbitron": f"0123456789MAX+{label}"}, f"{c['name']}: {v} / {MAX}")


def render(data):
    for theme in THEMES:
        write(f"header-{theme}.svg", render_header(data, theme))
    for c in data["colors"]:
        write(f"{c['id']}.svg", render_row(c))


def readme_section(data):
    """Markdown block to paste in README.md (links never change)."""
    rows = "\n".join(f'<a href="{vote_url(c)}"><img alt="Vote for {c["name"]}" src="assets/colors/{c["id"]}.svg" width="100%"></a>'
                     for c in data["colors"])
    return ('<picture>\n  <source media="(prefers-color-scheme: dark)" srcset="assets/colors/header-dark.svg">\n'
            '  <source media="(prefers-color-scheme: light)" srcset="assets/colors/header-light.svg">\n'
            '  <img alt="Pick your color" src="assets/colors/header-dark.svg" width="100%">\n</picture>\n\n'
            f'<p>\n{rows}\n</p>')


# ------------------------------------------------------------------ voting
def vote(data):
    title = os.environ.get("VOTE_TITLE", "").strip().lower()
    user = os.environ.get("VOTE_USER", "someone")
    cid = title.split("|", 1)[1].strip() if "|" in title else ""
    c = next((c for c in data["colors"] if c["id"] == cid), None)
    if c is None:
        return False, "Hmm, I don't know this color 🤔 Use one of the bars on the profile to vote."
    if c["value"] >= MAX:
        return False, f"**{c['name']}** is already at its maximum ({MAX}) 👑 Try another color!"
    c["value"] = min(c["value"] + STEP, MAX)
    data["total_votes"] += 1
    data["last"] = (data["last"] + [{"user": user, "color": c["name"]}])[-5:]
    msg = f"Thanks @{user}! **{c['name']}** is now at **{c['value']}** / {MAX} 🎨"
    if c["value"] >= MAX:
        msg += " — it just reached the maximum 👑"
    return True, msg


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    data = load()
    if cmd == "vote":
        changed, reply = vote(data)
        if changed:
            save(data)
            render(data)
        print(reply)
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
                f.write(f"changed={'true' if changed else 'false'}\nreply<<EOF\n{reply}\nEOF\n")
    elif cmd == "readme":
        print(readme_section(data))
    else:
        render(data)
