#!/usr/bin/env python3
"""
Gothic GitHub dashboard.

Generates two animated SVGs from live GitHub data:

    dragon.svg     contribution calendar, devoured by a pixel dragon
    dashboard.svg  streaks, languages, activity line, hour/day heatmap

Run locally:
    ACCESS_TOKEN=ghp_xxx python gothic.py
"""

import os
import sys
import datetime
import collections
import xml.sax.saxutils as su

import requests

USER = os.environ.get("GH_USER", "Hosein-Abdollahi")
API = "https://api.github.com/graphql"

# palette sampled from the reference art -------------------------------------
BG        = "#1b120d"   # dragon background
PANEL     = "#221610"
EMPTY     = "#2c1d16"   # unlit contribution cell
RAMP      = ["#4a1f22", "#7a3338", "#a84a4c", "#cd6063"]
DRAGON    = "#cd6063"
DRAGON_D  = "#7a3338"
CREAM     = "#dbb8a4"
CREAM_HI  = "#f0dcc6"
BLOOD     = "#470813"
IRON      = "#b4a59a"
MUTED     = "#8a6f62"

SERIF = "'Iowan Old Style','Palatino Linotype','Book Antiqua',Palatino,Georgia,serif"
MONO = "'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace"


# ---------------------------------------------------------------- graphql ---

def gql(query, variables=None):
    token = os.environ.get("ACCESS_TOKEN")
    if not token:
        sys.exit("ACCESS_TOKEN is not set (classic PAT with repo + read:user).")
    r = requests.post(API, json={"query": query, "variables": variables or {}},
                      headers={"Authorization": "bearer " + token}, timeout=40)
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def fetch_calendar():
    """Day-by-day contribution counts for the trailing year."""
    q = """
    query($login:String!){
      user(login:$login){
        contributionsCollection{
          contributionCalendar{
            totalContributions
            weeks{ contributionDays{ date weekday contributionCount } }
          }
        }
      }
    }"""
    cal = gql(q, {"login": USER})["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [[(d["date"], d["contributionCount"], d["weekday"])
              for d in w["contributionDays"]] for w in cal["weeks"]]
    return cal["totalContributions"], weeks


def fetch_profile():
    q = """
    query($login:String!, $cursor:String){
      user(login:$login){
        followers{ totalCount }
        repositories(first:100, after:$cursor, ownerAffiliations:OWNER, isFork:false){
          totalCount
          pageInfo{ hasNextPage endCursor }
          nodes{
            name stargazerCount
            languages(first:10, orderBy:{field:SIZE, direction:DESC}){
              edges{ size node{ name } }
            }
          }
        }
      }
    }"""
    cursor, repos, stars, langs = None, 0, 0, collections.Counter()
    followers = 0
    names = []
    while True:
        u = gql(q, {"login": USER, "cursor": cursor})["user"]
        followers = u["followers"]["totalCount"]
        block = u["repositories"]
        repos = block["totalCount"]
        for n in block["nodes"]:
            stars += n["stargazerCount"]
            names.append(n["name"])
            for e in n["languages"]["edges"]:
                langs[e["node"]["name"]] += e["size"]
        if not block["pageInfo"]["hasNextPage"]:
            break
        cursor = block["pageInfo"]["endCursor"]
    return {"repos": repos, "stars": stars, "followers": followers,
            "languages": langs, "names": names}


def fetch_punchcard(names, limit_per_repo=300):
    """Commit timestamps -> (weekday, hour) histogram."""
    uid = gql("query($l:String!){user(login:$l){id}}", {"l": USER})["user"]["id"]
    q = """
    query($owner:String!,$name:String!,$id:ID!,$cursor:String){
      repository(owner:$owner,name:$name){
        defaultBranchRef{ target{ ... on Commit{
          history(first:100, after:$cursor, author:{id:$id}){
            pageInfo{ hasNextPage endCursor }
            nodes{ committedDate }
          }}}}
      }}"""
    grid = collections.Counter()
    for name in names:
        cursor, got = None, 0
        while got < limit_per_repo:
            try:
                repo = gql(q, {"owner": USER, "name": name,
                               "id": uid, "cursor": cursor})["repository"]
            except RuntimeError:
                break
            ref = repo.get("defaultBranchRef")
            if not ref:
                break
            hist = ref["target"]["history"]
            for node in hist["nodes"]:
                ts = datetime.datetime.fromisoformat(
                    node["committedDate"].replace("Z", "+00:00"))
                grid[(ts.weekday(), ts.hour)] += 1
                got += 1
            if not hist["pageInfo"]["hasNextPage"]:
                break
            cursor = hist["pageInfo"]["endCursor"]
    return grid


# ----------------------------------------------------------------- helpers ---

def streaks(weeks):
    days = sorted((d for w in weeks for d in w), key=lambda x: x[0])
    longest = run = 0
    for _, count, _ in days:
        run = run + 1 if count > 0 else 0
        longest = max(longest, run)
    current = 0
    for _, count, _ in reversed(days):
        if count > 0:
            current += 1
        elif current == 0:
            continue          # today may simply not have landed yet
        else:
            break
    return current, longest


def level(count, ceiling):
    if count <= 0:
        return -1
    step = max(1.0, ceiling / 4.0)
    return min(3, int((count - 1) // step))


def ornament(x, y, flip_x=1, flip_y=1, color=None):
    """Small pixel flourish, echoing the wrought-iron corner pieces."""
    color = color or DRAGON_D
    cells = [
        (0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0),
        (0, 1), (1, 1), (2, 1),
        (0, 2), (1, 2), (4, 2), (5, 2),
        (0, 3), (1, 3), (3, 3), (4, 3),
        (0, 4), (2, 4), (3, 4),
        (0, 5), (2, 5),
        (0, 6), (1, 6),
    ]
    s = 3
    out = []
    for cx, cy in cells:
        px = x + flip_x * cx * s - (s if flip_x < 0 else 0)
        py = y + flip_y * cy * s - (s if flip_y < 0 else 0)
        out.append('<rect x="%.0f" y="%.0f" width="%d" height="%d" fill="%s"/>'
                   % (px, py, s, s, color))
    return "".join(out)


def frame(w, h, title):
    """Panel background, double border and corner flourishes."""
    out = ['<rect x="0" y="0" width="%d" height="%d" rx="8" fill="%s"/>' % (w, h, BG)]
    out.append('<rect x="6" y="6" width="%d" height="%d" fill="none" stroke="%s" '
               'stroke-width="3"/>' % (w - 12, h - 12, DRAGON_D))
    out.append('<rect x="12" y="12" width="%d" height="%d" fill="none" stroke="%s" '
               'stroke-width="1" opacity=".5"/>' % (w - 24, h - 24, IRON))
    out.append(ornament(14, 14, 1, 1))
    out.append(ornament(w - 14, 14, -1, 1))
    out.append(ornament(14, h - 14, 1, -1))
    out.append(ornament(w - 14, h - 14, -1, -1))
    if title:
        out.append('<text class="ttl" x="%d" y="42" text-anchor="middle">%s</text>'
                   % (w // 2, su.escape(title)))
    return "".join(out)


# ------------------------------------------------------------ dragon sprite ---
# D dark outline   R body   L cream highlight   . transparent

HEAD = [
    "..L...L..",
    "..LD.DL..",
    ".DDRRRDD.",
    "DRRRRRRRD",
    "DRRRRLRRD",
    "DRRRRRRRD",
    ".DRRRRRRD",
    "..DLLLLD.",
    "...DDDD..",
]

WING = [
    ".DDDD..",
    "DRRRRD.",
    "DRRRRRD",
    ".DRRRRD",
    "..DRRD.",
    "...DD..",
    "...D...",
]

BODY = [
    "..DDD..",
    ".DRRRD.",
    "DRRLRRD",
    "DRLRRLD",
    "DRRRRRD",
    ".DRRRD.",
    "..DDD..",
]

TAIL = [
    "..DDD..",
    ".DRRRD.",
    ".DRRRD.",
    "..DRD..",
    "..DRD..",
    "...DD..",
    "....D..",
]

SPRITE_COLORS = {"D": DRAGON_D, "R": DRAGON, "L": CREAM}


def sprite(rows, scale):
    """Pixel rows -> svg rect soup, centred on (0,0)."""
    h = len(rows)
    w = max(len(r) for r in rows)
    ox, oy = -w * scale / 2.0, -h * scale / 2.0
    out = []
    for y, row in enumerate(rows):
        x = 0
        while x < len(row):
            ch = row[x]
            if ch == ".":
                x += 1
                continue
            run = 1
            while x + run < len(row) and row[x + run] == ch:
                run += 1
            out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%d" fill="%s"/>'
                       % (ox + x * scale, oy + y * scale, run * scale, scale,
                          SPRITE_COLORS[ch]))
            x += run
    return "".join(out)


# ------------------------------------------------------------- dragon graph ---

CELL = 12
GAP = 3
PITCH = CELL + GAP
BUCKETS = 48          # quantised eat times -> keyframe blocks


def build_dragon_svg(weeks, total):
    cols = len(weeks)
    pad_l, pad_t = 40, 74
    grid_w = cols * PITCH
    grid_h = 7 * PITCH
    w = pad_l * 2 + grid_w
    h = pad_t + grid_h + 74

    ceiling = max((c for wk in weeks for _, c, _ in wk), default=1)

    # serpentine path over every cell, alternating direction per column
    path = []
    for ci in range(cols):
        rows = range(7) if ci % 2 == 0 else range(6, -1, -1)
        for ri in rows:
            path.append((ci, ri))

    step = 0.055                       # seconds per cell
    travel = len(path) * step
    cycle = travel + 3.0               # pause before the loop restarts

    index = {pos: i for i, pos in enumerate(path)}

    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'viewBox="0 0 %d %d" font-family=%s>' % (w, h, w, h, su.quoteattr(SERIF))]

    css = [
        ".ttl{fill:%s;font-size:19px;letter-spacing:5px;font-family:%s}" % (CREAM, SERIF),
        ".lbl{fill:%s;font-size:11px;font-family:%s}" % (MUTED, MONO),
        ".big{fill:%s;font-size:15px;font-family:%s}" % (CREAM_HI, MONO),
        "@keyframes wake{from{opacity:0}to{opacity:1}}",
        ".cell{animation:wake .5s ease-out backwards}",
    ]
    # one keyframe block per quantised eat time
    for b in range(BUCKETS):
        t = (b + 0.5) / BUCKETS * travel
        p1 = t / cycle * 100.0
        p2 = min(99.0, p1 + 0.45)
        css.append("@keyframes e%d{0%%,%.2f%%{opacity:1}%.2f%%,99%%{opacity:0}"
                   "100%%{opacity:1}}" % (b, p1, p2))
        css.append(".e%d{animation:wake .5s ease-out backwards,"
                   "e%d %.2fs linear infinite}" % (b, b, cycle))

    # the dragon's own march: one keyframe list, reused by every segment
    marks = []
    for i, (ci, ri) in enumerate(path):
        pct = (i * step) / cycle * 100.0
        x = pad_l + ci * PITCH + CELL / 2.0
        y = pad_t + ri * PITCH + CELL / 2.0
        marks.append("%.3f%%{transform:translate(%.1fpx,%.1fpx)}" % (pct, x, y))
    end_x = pad_l + grid_w + 30
    end_y = pad_t + grid_h / 2.0
    marks.append("%.3f%%,100%%{transform:translate(%.1fpx,%.1fpx)}"
                 % (travel / cycle * 100.0, end_x, end_y))
    css.append("@keyframes march{%s}" % "".join(marks))
    css.append(".seg{animation:march %.2fs steps(1,end) infinite}" % cycle)
    css.append("@keyframes flap{0%,100%{transform:scaleY(1)}50%{transform:scaleY(.55)}}")
    css.append(".wing{animation:flap .34s ease-in-out infinite;transform-origin:center}")

    out.append("<style>%s</style>" % "".join(css))
    out.append(frame(w, h, "CONTRIBUTION  GRIMOIRE"))

    # sprites live in defs so each segment is a cheap <use>
    out.append("<defs>")
    out.append('<g id="dh">%s</g>' % sprite(HEAD, 3))
    out.append('<g id="dw">%s</g>' % sprite(WING, 3))
    out.append('<g id="db">%s</g>' % sprite(BODY, 3))
    out.append('<g id="dt">%s</g>' % sprite(TAIL, 3))
    out.append("</defs>")

    # weekday gutter
    for ri, name in ((1, "M"), (3, "W"), (5, "F")):
        out.append('<text class="lbl" x="%d" y="%.1f">%s</text>'
                   % (pad_l - 18, pad_t + ri * PITCH + CELL - 2, name))

    # month ticks
    seen = set()
    for ci, wk in enumerate(weeks):
        d = datetime.date.fromisoformat(wk[0][0])
        if d.month not in seen and d.day <= 7:
            seen.add(d.month)
            out.append('<text class="lbl" x="%.1f" y="%d">%s</text>'
                       % (pad_l + ci * PITCH, pad_t - 8, d.strftime("%b")))

    # cells: dim base, lit overlay that the dragon snuffs out
    for ci, wk in enumerate(weeks):
        for date, count, weekday in wk:
            x = pad_l + ci * PITCH
            y = pad_t + weekday * PITCH
            out.append('<rect x="%.1f" y="%.1f" width="%d" height="%d" rx="2" '
                       'fill="%s"/>' % (x, y, CELL, CELL, EMPTY))
            lv = level(count, ceiling)
            if lv < 0:
                continue
            i = index[(ci, weekday)]
            bucket = min(BUCKETS - 1, int(i / max(1, len(path)) * BUCKETS))
            delay = 0.4 + i * 0.0016
            out.append('<rect class="cell e%d" x="%.1f" y="%.1f" width="%d" height="%d" '
                       'rx="2" fill="%s" style="animation-delay:%.2fs,0s"><title>%s: %d'
                       '</title></rect>'
                       % (bucket, x, y, CELL, CELL, RAMP[lv], delay, date, count))

    # dragon: tail first so the head overlaps it
    segs = [("dt", 5), ("db", 4), ("db", 3), ("db", 2), ("dw", 1), ("dh", 0)]
    for ref, lag in segs:
        inner = '<g class="wing"><use href="#%s"/></g>' % ref if ref == "dw" \
                else '<use href="#%s"/>' % ref
        out.append('<g class="seg" style="animation-delay:%.3fs">%s</g>'
                   % (lag * step, inner))

    # footer readout
    base = pad_t + grid_h + 30
    out.append('<text class="big" x="%d" y="%d">%s contributions this year</text>'
               % (pad_l, base, "{:,}".format(total)))
    lx = w - pad_l - 4 * PITCH - 66
    out.append('<text class="lbl" x="%d" y="%d">less</text>' % (lx - 30, base))
    for i, col in enumerate([EMPTY] + RAMP):
        out.append('<rect x="%.1f" y="%.1f" width="%d" height="%d" rx="2" fill="%s"/>'
                   % (lx + i * PITCH, base - 10, CELL, CELL, col))
    out.append('<text class="lbl" x="%.1f" y="%d">more</text>'
               % (lx + 5 * PITCH + 4, base))

    out.append("</svg>")
    return "\n".join(out)


# ---------------------------------------------------------------- dashboard ---

def build_dashboard_svg(stats, weeks, cur_streak, max_streak, total, punch):
    w, h = 860, 560
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'viewBox="0 0 %d %d" font-family=%s>' % (w, h, w, h, su.quoteattr(SERIF))]

    css = [
        ".ttl{fill:%s;font-size:19px;letter-spacing:5px}" % CREAM,
        ".h{fill:%s;font-size:12px;letter-spacing:3px;font-family:%s}" % (IRON, MONO),
        ".k{fill:%s;font-size:12px;font-family:%s}" % (MUTED, MONO),
        ".v{fill:%s;font-size:26px;font-family:%s}" % (CREAM_HI, MONO),
        ".s{fill:%s;font-size:11px;font-family:%s}" % (MUTED, MONO),
        "@keyframes rise{from{opacity:0;transform:translateY(9px)}"
        "to{opacity:1;transform:translateY(0)}}",
        ".r{animation:rise .55s ease-out backwards}",
        "@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}",
        ".bar{animation:grow .8s ease-out backwards;transform-origin:left center}",
        "@keyframes draw{to{stroke-dashoffset:0}}",
        ".line{stroke-dasharray:2600;stroke-dashoffset:2600;"
        "animation:draw 2.4s ease-out .3s forwards}",
        "@keyframes glow{0%,100%{opacity:.30}50%{opacity:.60}}",
        ".halo{animation:glow 3.4s ease-in-out infinite}",
    ]
    out.append("<style>%s</style>" % "".join(css))
    out.append(frame(w, h, "THE  LEDGER"))

    # ---- counters -----------------------------------------------------------
    figures = [
        ("{:,}".format(total), "CONTRIBUTIONS"),
        (str(cur_streak), "CURRENT STREAK"),
        (str(max_streak), "LONGEST STREAK"),
        (str(stats["repos"]), "REPOSITORIES"),
        (str(stats["stars"]), "STARS"),
        (str(stats["followers"]), "FOLLOWERS"),
    ]
    x0, y0, col_w = 46, 96, 137
    for i, (value, label) in enumerate(figures):
        cx = x0 + (i % 3) * col_w
        cy = y0 + (i // 3) * 64
        d = 0.15 + i * 0.08
        out.append('<text class="v r" x="%.0f" y="%.0f" style="animation-delay:%.2fs">%s'
                   '</text>' % (cx, cy, d, value))
        out.append('<text class="k r" x="%.0f" y="%.0f" style="animation-delay:%.2fs">%s'
                   '</text>' % (cx, cy + 17, d + 0.04, label))

    # ---- languages ----------------------------------------------------------
    lx, ly = 470, 76
    out.append('<text class="h" x="%d" y="%d">TOMES</text>' % (lx, ly))
    langs = stats["languages"].most_common(5)
    span = sum(v for _, v in langs) or 1
    for i, (name, size) in enumerate(langs):
        y = ly + 26 + i * 28
        frac = size / span
        out.append('<text class="k" x="%d" y="%d">%s</text>' % (lx, y, su.escape(name)))
        out.append('<text class="s" x="%d" y="%d" text-anchor="end">%.1f%%</text>'
                   % (w - 52, y, frac * 100))
        out.append('<rect x="%d" y="%d" width="%d" height="7" rx="3" fill="%s"/>'
                   % (lx, y + 6, 300, EMPTY))
        out.append('<rect class="bar" x="%d" y="%d" width="%.0f" height="7" rx="3" '
                   'fill="%s" style="animation-delay:%.2fs"/>'
                   % (lx, y + 6, max(4, 300 * frac), RAMP[3 - min(3, i)], 0.5 + i * 0.12))

    # ---- activity line ------------------------------------------------------
    ax, ay, aw, ah = 46, 268, w - 92, 118
    out.append('<text class="h" x="%d" y="%d">THE  TIDE</text>' % (ax, ay - 12))
    series = [sum(c for _, c, _ in wk) for wk in weeks]
    peak = max(series) or 1
    pts = []
    for i, v in enumerate(series):
        px = ax + (i / max(1, len(series) - 1)) * aw
        py = ay + ah - (v / peak) * ah
        pts.append((px, py))
    line = " ".join("%.1f,%.1f" % p for p in pts)
    area = "%.1f,%.1f " % (ax, ay + ah) + line + " %.1f,%.1f" % (ax + aw, ay + ah)
    out.append('<polygon class="halo" points="%s" fill="%s" opacity=".4"/>' % (area, BLOOD))
    out.append('<polyline class="line" points="%s" fill="none" stroke="%s" '
               'stroke-width="2.5" stroke-linejoin="round"/>' % (line, DRAGON))
    out.append('<line x1="%d" y1="%.0f" x2="%d" y2="%.0f" stroke="%s" stroke-width="1" '
               'opacity=".45"/>' % (ax, ay + ah, ax + aw, ay + ah, DRAGON_D))
    out.append('<text class="s" x="%d" y="%.0f">peak %d / week</text>'
               % (ax, ay - 12, peak))

    # ---- punch card ---------------------------------------------------------
    px0, py0 = 46, 430
    out.append('<text class="h" x="%d" y="%d">THE  WITCHING  HOURS</text>' % (px0, py0 - 12))
    cw, chh, cg = 28, 13, 2
    busiest = max(punch.values()) if punch else 1
    days = ["M", "T", "W", "T", "F", "S", "S"]
    for d in range(7):
        out.append('<text class="s" x="%d" y="%.0f">%s</text>'
                   % (px0 - 14, py0 + d * (chh + cg) + 10, days[d]))
        for hh in range(24):
            v = punch.get((d, hh), 0)
            lv = level(v, busiest)
            fill = EMPTY if lv < 0 else RAMP[lv]
            x = px0 + hh * (cw + cg)
            y = py0 + d * (chh + cg)
            out.append('<rect class="r" x="%d" y="%d" width="%d" height="%d" rx="2" '
                       'fill="%s" style="animation-delay:%.2fs"><title>%02d:00 &#183; %d'
                       '</title></rect>'
                       % (x, y, cw, chh, fill, 0.8 + (hh * 7 + d) * 0.004, hh, v))
    for hh in (0, 6, 12, 18):
        out.append('<text class="s" x="%d" y="%d">%02d</text>'
                   % (px0 + hh * (cw + cg), py0 + 7 * (chh + cg) + 14, hh))

    out.append("</svg>")
    return "\n".join(out)


# --------------------------------------------------------------------- main ---

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    print("summoning data for %s ..." % USER)

    total, weeks = fetch_calendar()
    stats = fetch_profile()
    cur, longest = streaks(weeks)
    print("  contributions=%d streak=%d/%d repos=%d stars=%d"
          % (total, cur, longest, stats["repos"], stats["stars"]))

    try:
        punch = fetch_punchcard(stats["names"])
    except Exception as exc:                       # noqa: BLE001
        print("  punch card unavailable (%s)" % exc)
        punch = collections.Counter()

    with open(os.path.join(here, "dragon.svg"), "w", encoding="utf-8") as fh:
        fh.write(build_dragon_svg(weeks, total))
    with open(os.path.join(here, "dashboard.svg"), "w", encoding="utf-8") as fh:
        fh.write(build_dashboard_svg(stats, weeks, cur, longest, total, punch))
    print("wrote dragon.svg and dashboard.svg")


if __name__ == "__main__":
    main()
