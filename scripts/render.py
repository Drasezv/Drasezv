#!/usr/bin/env python3
"""Draw the neofetch-style profile card as two SVGs (dark and light).

Static lines live in LINES, the logo in art.txt (made once from the avatar).
Live numbers come from the public GitHub API.
"""
import json
import os
import urllib.request
from datetime import datetime, timezone
from html import escape
from pathlib import Path

USER = "Drasezv"
ROOT = Path(__file__).resolve().parent.parent

THEMES = {
    "dark": {"bg": "#0d1117", "border": "#30363d", "text": "#c9d1d9", "key": "#58a6ff",
             "dim": "#484f58", "art": "#e6dccb", "ok": "#3fb950"},
    "light": {"bg": "#ffffff", "border": "#d0d7de", "text": "#24292f", "key": "#0969da",
              "dim": "#afb8c1", "art": "#24292f", "ok": "#1a7f37"},
}

LINES = [
    ("role", "infrastructure / self-hosted"),
    ("stack", "Linux, Docker, Python, Bash, Ansible, MQTT"),
    ("shipping", "cctab, homewatch"),
]

FONT = "ui-monospace,SFMono-Regular,Consolas,'Liberation Mono',Menlo,monospace"
CHAR_W, LINE_H, SIZE = 8.9, 20, 14


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}",
                                 headers={"Accept": "application/vnd.github+json"})
    if os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def uptime(since):
    now = datetime.now(timezone.utc)
    months = (now.year - since.year) * 12 + now.month - since.month
    if now.day < since.day:
        months -= 1
    years, months = divmod(months, 12)
    parts = [f"{years} year{'s' * (years != 1)}"] if years else []
    parts.append(f"{months} month{'s' * (months != 1)}")
    return ", ".join(parts)


def stats():
    user = api(f"/users/{USER}")
    repos = api(f"/users/{USER}/repos?per_page=100&type=owner")
    own = [r for r in repos if not r["fork"]]
    last = max((r["pushed_at"] for r in own if r["name"] != USER), default=user["created_at"])
    return [
        ("on github", user["created_at"][:10]),
        ("repos", f"{len(own)} public"),
        ("last push", last[:10]),
    ]


def card(theme, rows):
    t = THEMES[theme]
    art = (ROOT / "scripts" / "art.txt").read_text(encoding="utf-8").rstrip("\n").split("\n")
    art_cols = max(len(a) for a in art)
    pad = 28
    art_w = art_cols * CHAR_W
    tx = pad + art_w + 32
    key_w = 11
    rows_all = list(LINES) + list(rows)
    total = max(24, max(key_w + 2 + len(v) for _, v in rows_all) + 2)
    head = f"{USER.lower()}@root"
    body = [("head", head), ("rule", "-" * len(head))]
    body += [("kv", k, v) for k, v in LINES]
    body += [("gap",), ("sub", "github")]
    body += [("kv", k, v) for k, v in rows]

    h = pad * 2 + max(len(art), len(body)) * LINE_H
    w = int(tx + total * CHAR_W + pad)
    css = ("<style>"
           "@keyframes in{from{opacity:0;transform:translateX(-6px)}to{opacity:1;transform:translateX(0)}}"
           "text{opacity:0;animation:in .45s ease-out forwards}"
           "@media (prefers-reduced-motion:reduce){text{animation-duration:.01s}}"
           "</style>")
    grad = (f'<linearGradient id="sheen" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{art_w}" y2="{h}">'
            f'<stop offset="0" stop-color="{t["art"]}"/>'
            f'<stop offset="0.42" stop-color="{t["art"]}"/>'
            f'<stop offset="0.5" stop-color="{t["key"]}"/>'
            f'<stop offset="0.58" stop-color="{t["art"]}"/>'
            f'<stop offset="1" stop-color="{t["art"]}"/>'
            f'<animateTransform attributeName="gradientTransform" type="translate" '
            f'from="{-art_w * 1.2} 0" to="{art_w * 1.2} 0" dur="3.2s" begin="1s" '
            f'repeatCount="indefinite"/></linearGradient>')
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
           f'viewBox="0 0 {w} {h}" font-family="{FONT}" font-size="{SIZE}">',
           css, f'<defs>{grad}</defs>',
           f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="10" '
           f'fill="{t["bg"]}" stroke="{t["border"]}"/>',
           '<g xml:space="preserve">']

    def fit(n):
        return f'textLength="{n * CHAR_W:.1f}" lengthAdjust="spacingAndGlyphs"'

    # every run of non-space chars gets its own x, so no renderer eats the gaps
    art_y = pad + (h - pad * 2 - len(art) * LINE_H) / 2
    for i, line in enumerate(art):
        y = art_y + (i + 0.75) * LINE_H
        for word in line.split():
            start = line.index(word)
            line = line[:start] + " " * len(word) + line[start + len(word):]
            out.append(f'<text x="{pad + start * CHAR_W:.1f}" y="{y:.1f}" {fit(len(word))} '
                       f'fill="url(#sheen)" style="animation-delay:{i * 0.04:.2f}s">'
                       f'{escape(word)}</text>')

    body_y = pad + (h - pad * 2 - len(body) * LINE_H) / 2
    for i, line in enumerate(body):
        y = body_y + (i + 0.75) * LINE_H
        delay = f' style="animation-delay:{0.35 + i * 0.07:.2f}s"'
        kind = line[0]
        if kind == "head":
            out.append(f'<text x="{tx}" y="{y}" {fit(len(line[1]))} fill="{t["key"]}" '
                       f'font-weight="700"{delay}>{escape(line[1])}</text>')
        elif kind == "rule":
            out.append(f'<text x="{tx}" y="{y}" {fit(len(line[1]))} fill="{t["dim"]}"{delay}>{line[1]}</text>')
        elif kind == "sub":
            label = f"-- {line[1]} " + "-" * (total - len(line[1]) - 4)
            out.append(f'<text x="{tx}" y="{y}" {fit(len(label))} fill="{t["dim"]}"{delay}>{label}</text>')
        elif kind == "kv":
            k, v = line[1], line[2]
            dots = "." * max(2, key_w - len(k))
            n = len(k) + len(dots) + 2 + len(v)
            out.append(f'<text x="{tx}" y="{y}" {fit(n)}{delay}><tspan fill="{t["key"]}">{escape(k)}</tspan>'
                       f'<tspan fill="{t["dim"]}"> {dots} </tspan>'
                       f'<tspan fill="{t["text"]}">{escape(v)}</tspan></text>')
    out += ["</g>", "</svg>"]
    return "\n".join(out) + "\n"


def main():
    rows = stats()
    (ROOT / "assets").mkdir(exist_ok=True)
    for theme in THEMES:
        (ROOT / "assets" / f"card-{theme}.svg").write_text(card(theme, rows), encoding="utf-8")


if __name__ == "__main__":
    main()
