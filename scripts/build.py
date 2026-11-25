#!/usr/bin/env python3
"""Build dopamine-diagrams from JSON specs.

  python3 scripts/build.py SPEC.json [SPEC.json ...] --target zenn|standalone|slides -o OUT [--intensity 1|2|3]

zenn        -> Markdown with one ```html-embed block per spec (HTML + <style> only, no JS)
standalone  -> one self-contained HTML page (light/dark via prefers-color-scheme or data-theme)
slides      -> one HTML deck, 1280x720 per spec, printable to PDF (motion stops in print)

Standard library only.
"""
import argparse, hashlib, html, json, math, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TPL = ROOT / "templates"
ZENN_MAX_BYTES = 50 * 1024

DARK_VARS = ("--bg:#161b22;--ink:#e6edf3;--mut:#9da7b3;--line:#30363d;--card:#0d1117;--a:#fb923c;--as:#431407;"
             "--b:#60a5fa;--bs:#172554;--g:#4ade80;--gs:#052e16;--r:#f87171;--rs:#450a0a;--y:#facc15;--ys:#422006;"
             "--v:#a78bfa;--glow:#ffd54f")
CHIP_ON = ("background:linear-gradient(180deg,#ff8a3d,#e8430c);border-color:transparent;color:#fff;"
           "animation:dd-neon var(--pulse) ease-in-out infinite")
CHIP_ON_LV1 = "background:var(--a);border-color:transparent;color:#fff"

def E(s):
    """Escape user text for HTML. Newlines become spaces (a newline + ``` would close the Zenn fence)."""
    return html.escape(re.sub(r"[\r\n]+", " ", str(s)), quote=True).replace("`", "&#96;")


COLOR_RE = re.compile(r"(#[0-9a-fA-F]{3,8}|var\(--[a-z]+\)|[a-zA-Z]{3,20}|rgba?\([ \d.,%]+\))")


def fail(msg):
    raise SystemExit(f"error: {msg}")


def need(spec, *fields):
    for f in fields:
        if f not in spec or spec[f] in ("", None, [], {}):
            fail(f"pattern {spec.get('pattern')}: field '{f}' is required")


def typed(spec, field, typ, default=None, required=True):
    """Return spec[field] if it has the expected type; stop with a message otherwise."""
    if field not in spec or spec[field] is None:
        if required:
            fail(f"pattern {spec.get('pattern', '?')}: field '{field}' is required")
        return default
    v = spec[field]
    ok = isinstance(v, typ) and not isinstance(v, bool)
    if not ok:
        tn = typ.__name__ if isinstance(typ, type) else "/".join(t.__name__ for t in typ)
        fail(f"field '{field}' must be {tn}; got {type(v).__name__} {v!r:.40}")
    return v


def items_of(spec, field, item_typ, need_keys=(), lo=1, hi=None):
    v = typed(spec, field, list)
    if len(v) < lo or (hi is not None and len(v) > hi):
        fail(f"'{field}' needs {lo}" + (f" to {hi}" if hi else " or more") + f" items; got {len(v)}")
    for it in v:
        if not isinstance(it, item_typ) or isinstance(it, bool):
            fail(f"every item of '{field}' must be {'an object' if item_typ is dict else 'a string'}; got {it!r:.40}")
        if item_typ is dict:
            for k in need_keys:
                if k not in it or not isinstance(it[k], (str, int, float)) or it[k] == "":
                    fail(f"every item of '{field}' needs a text field '{k}'; got {it!r:.60}")
    return v


def as_index(v, n, name):
    if not isinstance(v, int) or isinstance(v, bool) or not 0 <= v < n:
        fail(f"{name} must be an integer from 0 to {n-1}; got {v!r}")
    return v


def text_w(s, fs):
    """Rough rendered width of text in px (CJK ~1em, others ~0.6em)."""
    return sum(fs if ord(c) > 0x2E7F else fs * 0.6 for c in str(s))


# Default UI words. Japanese when the spec contains Japanese text, English otherwise.
DEFAULTS = {
    "ja": {"bad_label": "よくある間違い", "good_label": "こうする", "done": "完了！", "decompose_button": "分解する ▶",
           "compare_button": "直す ▶", "proportion_button": "よく見る ▶", "back": "戻る", "now_label": "いま",
           "next_label": "次の一手", "prompt": "いまどの段？ 段をクリック", "gem_title": "見落としてはいけない1件",
           "before": "ビフォー", "after": "アフター"},
    "en": {"bad_label": "Common mistake", "good_label": "Do this instead", "done": "Done!",
           "decompose_button": "Break it down ▶", "compare_button": "Show the fix ▶", "proportion_button": "Look closer ▶",
           "back": "Back", "now_label": "Now", "next_label": "Next move", "prompt": "Where are you? Click a step",
           "gem_title": "The one that matters", "before": "Before", "after": "After"},
}


def T(spec, key):
    return DEFAULTS["ja" if has_cjk(json.dumps(spec, ensure_ascii=False)) else "en"][key]


# ---------------------------------------------------------------- explorer
def render_explorer(spec, u, lv):
    need(spec, "title")
    cases = items_of(spec, "cases", dict, ("label", "good"), lo=2, hi=8)
    bad_l = spec.get("bad_label", T(spec, "bad_label"))
    good_l = spec.get("good_label", T(spec, "good_label"))
    inp = "".join(f'<input class="h" type="radio" name="{u}-m" id="{u}-m{i}"{" checked" if i == 0 else ""}>'
                  for i in range(len(cases)))
    labs = "".join(f'<label for="{u}-m{i}"><span class="ex-no">{i+1:02d}</span>{E(c["label"])}</label>'
                   for i, c in enumerate(cases))
    pans = ""
    for i, c in enumerate(cases):
        bad = (f'<div class="ex-bad"><b>{E(bad_l)}</b><s>{E(c["bad"])}</s></div>' if c.get("bad") else "")
        pans += (f'<div class="ex-p ex-p{i}"><div class="ex-hd"><span class="ex-num gold">{i+1:02d}</span>'
                 f'<span class="ex-sit">{E(c.get("situation", c["label"]))}</span></div>{bad}'
                 f'<div class="ex-good rb"><div class="in"><b class="gold">{E(good_l)}</b>'
                 f'<div class="ex-ok">{E(c["good"])}</div></div></div></div>')
    body = (f'{inp}<div class="ttl">{E(spec["title"])}</div>'
            f'<div class="ex-g"><div class="ex-ls">{labs}</div><div class="ex-ps">{pans}</div></div>')
    chip = CHIP_ON_LV1 if lv == 1 else CHIP_ON
    css = []
    for i in range(len(cases)):
        sel = f"#{u}-m{i}:checked~.ex-g"
        css.append(f"{sel} label[for={u}-m{i}]{{{chip}}}{sel} label[for={u}-m{i}] .ex-no{{color:#fff}}")
        css.append(f"#{u}-m{i}:focus-visible~.ex-g label[for={u}-m{i}]{{outline:2px solid var(--b);outline-offset:1px}}")
        css.append(f"{sel} .ex-p{i}{{display:block;animation:pop .3s ease}}")
        css.append(f"{sel} .ex-p{i} .ex-good{{animation:var(--enter) .55s ease-out .15s both}}")
    return body, "".join(css)


# ---------------------------------------------------------------- decompose
def render_decompose(spec, u, lv):
    root = typed(spec, "root", dict)
    need(root, "text")
    kids = items_of(spec, "children", dict, ("text",), lo=2, hi=6)
    n = len(kids)
    cols = n if n <= 5 else 3
    kd = "".join(f'<div class="dc-k" style="--i:{i}"><span class="dc-tag">{E(k["tag"])}</span>{E(k["text"])}</div>'
                 if k.get("tag") else f'<div class="dc-k" style="--i:{i}">{E(k["text"])}</div>'
                 for i, k in enumerate(kids))
    ttl = f'<div class="ttl">{E(spec["title"])}</div>' if spec.get("title") else ""
    body = (f'<input class="h" type="checkbox" id="{u}-s">{ttl}'
            f'<div class="dc-root"><span class="dc-kick">{E(root.get("kicker", ""))}</span>{E(root["text"])}'
            f'<span class="dc-done gold">{E(spec.get("done", T(spec, "done")))}</span></div>'
            f'<div class="dc-mid"><label for="{u}-s" class="btn shine"><span class="dc-t1">{E(spec.get("button", T(spec, "decompose_button")))}</span>'
            f'<span class="dc-t2">{E(spec.get("back", T(spec, "back")))}</span></label>'
            f'<div class="dc-hint">{E(spec.get("hint", ""))}</div></div>'
            f'<div class="dc-kids" style="grid-template-columns:repeat({cols},1fr)">{kd}</div>')
    s = f"#{u}-s:checked"
    pulse = "" if lv == 1 else ",dd-goldpulse 1.8s ease-in-out 1.2s infinite"
    neon = "box-shadow:0 0 0 2px var(--g)" if lv == 1 else "animation:dd-neon var(--pulse) ease-in-out infinite"
    css = (f"#{u}-s:focus-visible~.dc-mid .btn{{outline:2px solid var(--b);outline-offset:2px}}"
           f"{s}~.dc-mid .dc-t1,{s}~.dc-mid .dc-hint{{display:none}}{s}~.dc-mid .dc-t2{{display:inline}}"
           f"{s}~.dc-root{{border-style:solid;border-color:var(--g);{neon}}}"
           f"{s}~.dc-root .dc-done{{display:block;animation:var(--enter) .6s ease-out .55s both{pulse}}}"
           f"{s}~.dc-kids .dc-k{{opacity:1;filter:none;transform:none;border-color:var(--g);"
           f"animation:var(--enter) .5s ease-out both;animation-delay:calc(var(--i)*.09s);box-shadow:0 0 10px rgba(34,197,94,.35)}}"
           # PDF has no clicks: print the broken-down state
           f"@media print{{#{u} .dc-k{{opacity:1;filter:none;transform:none;border-color:var(--g)}}"
           f"#{u} .dc-kids{{margin-top:14px}}#{u} .dc-hint,#{u} .dc-mid{{display:none}}#{u} .dc-done{{display:block}}#{u} .dc-root{{border-style:solid;border-color:var(--g)}}}}")
    return body, css


# ---------------------------------------------------------------- architecture
def _bez(p0, p1, p2, p3, t=0.5):
    return tuple((1-t)**3*a + 3*(1-t)**2*t*b + 3*(1-t)*t**2*c + t**3*d for a, b, c, d in zip(p0, p1, p2, p3))


def _arch_svg(spec, u, mode, focal):
    tiers = spec["tiers"]
    edges = spec.get("edges", [])
    T = len(tiers)
    pos = {}   # id -> (cx, cy, w, h, tier)
    out = []
    tid = {n["id"]: ti for ti, t in enumerate(tiers) for n in t["nodes"]}
    idx = {n["id"]: i for i, n in enumerate(n for t in tiers for n in t["nodes"])}   # class names use indices, never ids
    if mode == "wide":
        # Column widths come from the node text, gaps from the edge labels between neighbouring tiers.
        # If that needs more than 600 user units, the viewBox widens and every font grows with it, so text
        # still renders >= 12px when the embed is only 529px wide (Zenn PC at ~561px). Iterate to settle.
        W, top, gap, MINW, NARROWEST = 600, 40, 18, 600, 529
        FS, FSS, FSE = 16, 14, 14
        for _ in range(4):
            colw = [max(max(text_w(n["label"], FS) + 28, text_w(n.get("sub", ""), FSS) + 20) for n in t["nodes"]) for t in tiers]
            gaps = []
            for ti in range(T - 1):
                labs = [text_w(e["label"], FSE) + 18 for e in edges
                        if e.get("label") and sorted((tid[e["from"]], tid[e["to"]])) == [ti, ti + 1]]
                gaps.append(max([34] + labs))
            need = 12 + sum(c + 16 for c in colw) + sum(gaps)
            W = max(MINW, need)
            small = max(14, round(12.3 * W / NARROWEST * 2) / 2)
            if small == FSS:
                break
            FS, FSS, FSE = small + 2, small, small
        extra = (W - need) / max(T - 1, 1) if T > 1 else 0
        nh = round(FS + FSS + 26) if any(n.get("sub") for t in tiers for n in t["nodes"]) else round(FS + 22)
        maxn = max(len(t["nodes"]) for t in tiers)
        H = top + maxn * (nh + gap) + 6
        x = 6 if T > 1 else (W - colw[0] - 16) / 2
        for ti, t in enumerate(tiers):
            bw = colw[ti] + 16
            cx = x + bw / 2
            out.append(f'<rect class="ar-band" x="{x:.1f}" y="6" width="{bw:.1f}" height="{H-8:.1f}" rx="10"/>'
                       f'<text class="ar-tier" x="{cx:.1f}" y="27">{E(t["name"])}</text>')
            k = len(t["nodes"])
            y0 = top + (maxn - k) * (nh + gap) / 2
            for ni, n in enumerate(t["nodes"]):
                pos[n["id"]] = (cx, y0 + ni * (nh + gap) + nh / 2, colw[ti], nh, ti)
            if ti < T - 1:
                x += bw + gaps[ti] + extra
    else:
        # Tiers become rows. Each row is a band with its name at the top-left, so edges never cross the name.
        W = 320
        FS, FSS, FSE = 15, 13, 13
        nh = 48 if any(n.get("sub") for t in tiers for n in t["nodes"]) else 34
        rowgap = 26
        y = 6
        band_top, names = [], []
        for ti, t in enumerate(tiers):
            band_top.append(y)
            k = len(t["nodes"])
            bh = 22 + nh + 8
            out.append(f'<rect class="ar-band" x="2" y="{y:.1f}" width="{W-4}" height="{bh:.1f}" rx="10"/>')
            names.append((t["name"], y))
            cy = y + 22 + nh / 2
            for ni, n in enumerate(t["nodes"]):
                cx = W * (ni + .5) / k
                want = max(text_w(n["label"], FS) + 24, text_w(n.get("sub", ""), FSS) + 16)
                w = min(W / k - 12, want)
                if want > w + 1:
                    print(f"WARN: architecture node '{n['id']}' is too long for the phone layout "
                          f"({k} nodes in its tier); shorten the label/sub or move a node to another tier", file=sys.stderr)
                pos[n["id"]] = (cx, cy, w, nh, ti)
            y += bh + rowgap
        H = y - rowgap + 4
    # adjacency for hover dimming
    nb = {i: set() for i in pos}
    for e in edges:
        nb[e["from"]].add(e["to"]); nb[e["to"]].add(e["from"])
    # edges first (under nodes)
    eds, curves = [], []
    for e in edges:
        a, b = pos[e["from"]], pos[e["to"]]
        if b[4] < a[4]:
            raise SystemExit(f'edge {e["from"]}->{e["to"]} goes backwards; order tiers so edges flow forward')
        if mode == "wide":
            if b[4] == a[4]:
                down = b[1] > a[1]
                p0 = (a[0], a[1] + (a[3]/2 if down else -a[3]/2)); p3 = (b[0], b[1] - (b[3]/2 if down else -b[3]/2))
                p1 = (p0[0], (p0[1]+p3[1])/2); p2 = (p3[0], (p0[1]+p3[1])/2)
            else:
                p0 = (a[0] + a[2]/2, a[1]); p3 = (b[0] - b[2]/2, b[1]); dx = (p3[0]-p0[0]) * .5
                p1 = (p0[0]+dx, p0[1]); p2 = (p3[0]-dx, p3[1])
        else:
            if b[4] == a[4]:
                right = b[0] > a[0]
                p0 = (a[0] + (a[2]/2 if right else -a[2]/2), a[1]); p3 = (b[0] - (b[2]/2 if right else -b[2]/2), b[1])
                p1 = ((p0[0]+p3[0])/2, p0[1]); p2 = ((p0[0]+p3[0])/2, p3[1])
            else:
                p0 = (a[0], a[1] + a[3]/2); p3 = (b[0], b[1] - b[3]/2); dy = (p3[1]-p0[1]) * .5
                p1 = (p0[0], p0[1]+dy); p2 = (p3[0], p3[1]-dy)
        curves.append((p0, p1, p2, p3))
        d = f"M{p0[0]:.1f} {p0[1]:.1f} C{p1[0]:.1f} {p1[1]:.1f},{p2[0]:.1f} {p2[1]:.1f},{p3[0]:.1f} {p3[1]:.1f}"
        lab = ""
        if e.get("label"):
            mx, my = _bez(p0, p1, p2, p3)
            if mode != "wide" and b[4] == a[4] + 1:
                # Phone rows: the plain midpoint lands on the next band's top edge, where the tier name sits.
                # Put the label in the middle of the gap between the two bands instead (y is monotonic in t).
                target, lo_t, hi_t = band_top[b[4]] - rowgap / 2, 0.0, 1.0
                for _ in range(30):
                    mid = (lo_t + hi_t) / 2
                    lo_t, hi_t = (mid, hi_t) if _bez(p0, p1, p2, p3, mid)[1] < target else (lo_t, mid)
                mx, my = _bez(p0, p1, p2, p3, lo_t)
            lw = text_w(e["label"], FSE) + 10
            lab = (f'<rect class="ar-elabel-bg" x="{mx-lw/2:.1f}" y="{my-FSE/2-4:.1f}" width="{lw:.1f}" height="{FSE+8:.0f}" rx="4"/>'
                   f'<text class="ar-elabel" x="{mx:.1f}" y="{my+FSE*0.35:.1f}">{E(e["label"])}</text>')
        eds.append(f'<g class="ar-ed x-{idx[e["from"]]} x-{idx[e["to"]]}"><path class="ar-base" d="{d}"/>'
                   f'<path class="ar-flow" d="{d}"/>{lab}</g>')
    if mode != "wide":
        # Tier names sit in the top corner of their band. Use the left corner unless an edge enters the band
        # there (long Japanese names reach the first node's column); then the right corner if that one is free.
        for name, by in names:
            nw = text_w(name, FSS) * 1.04 + 6
            xs = [x for p0, p1, p2, p3 in curves for t in [i / 40 for i in range(41)]
                  for x, yy in [_bez(p0, p1, p2, p3, t)] if by <= yy <= by + 22]
            left_busy = any(6 <= x <= 12 + nw for x in xs)
            right_busy = any(W - 12 - nw <= x <= W - 6 for x in xs)
            if left_busy and not right_busy:
                out.append(f'<text class="ar-tier" x="{W-12}" y="{by+16:.1f}" style="text-anchor:end">{E(name)}</text>')
            else:
                out.append(f'<text class="ar-tier" x="12" y="{by+16:.1f}" style="text-anchor:start">{E(name)}</text>')
    nodes = []
    gid = f"{u}-{mode[0]}-rbw"
    for nid, (cx, cy, w, h, _) in pos.items():
        n = next(n for t in tiers for n in t["nodes"] if n["id"] == nid)
        cls = f"ar-node n-{idx[nid]} " + " ".join(f"nb-{i}" for i in sorted(idx[x] for x in nb[nid]))
        style = ""
        if nid in focal:
            cls += " ar-focal"; style = f' style="stroke:url(#{gid})"'
        sub = n.get("sub")
        ly = cy + (-4 if sub else 5)
        t = f'<text class="lb" x="{cx:.1f}" y="{ly:.1f}">{E(n["label"])}</text>'
        if sub:
            t += f'<text class="sb" x="{cx:.1f}" y="{cy+FSS+2:.1f}">{E(sub)}</text>'
        nodes.append(f'<g class="{cls.strip()}"><rect x="{cx-w/2:.1f}" y="{cy-h/2:.1f}" width="{w:.1f}" height="{h:.1f}" rx="9"{style}/>{t}</g>')
    defs = (f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ff2d55"/>'
            f'<stop offset=".25" stop-color="#ffd700"/><stop offset=".5" stop-color="#22c55e"/>'
            f'<stop offset=".75" stop-color="#3b82f6"/><stop offset="1" stop-color="#a855f7"/></linearGradient></defs>')
    aria = E(spec.get("alt", spec["title"]))
    fsv = f"--fs:{FS}px;--fss:{FSS}px;--fse:{FSE}px"
    return (f'<svg class="ar-svg ar-{mode}" viewBox="0 0 {W:.0f} {H:.0f}" style="{fsv}" role="img" aria-label="{aria}">'
            f'{defs}{"".join(out)}{"".join(eds)}{"".join(nodes)}</svg>'), list(pos)


def render_architecture(spec, u, lv):
    need(spec, "title")
    ids = []
    for t in items_of(spec, "tiers", dict, ("name",), lo=1, hi=6):
        for n in items_of(t, "nodes", dict, ("id", "label"), lo=1, hi=4):
            if n["id"] in ids:
                fail(f"architecture: duplicate node id '{n['id']}'")
            ids.append(n["id"])
    spec.setdefault("edges", [])
    for e in items_of(spec, "edges", dict, lo=0):
        for end in ("from", "to"):
            if e.get(end) not in ids:
                fail(f"architecture: edge {end} '{e.get(end)}' is not a node id")
    focal = spec.get("focal", [])
    if isinstance(focal, (str, int)) and not isinstance(focal, bool):
        focal = [focal]
    if not isinstance(focal, list) or any(not isinstance(f, (str, int)) or isinstance(f, bool) for f in focal):
        fail("architecture: focal must be a node id or a list of node ids")
    focal = set(focal)
    if len(focal) > 2:
        fail("architecture: at most 2 focal nodes (emphasis budget)")
    for f in focal:
        if f not in ids:
            fail(f"architecture: focal '{f}' is not a node id")
    wide, _ = _arch_svg(spec, u, "wide", focal)
    narrow, _ = _arch_svg(spec, u, "narrow", focal)
    body = f'<div class="ttl">{E(spec["title"])}</div>{wide}{narrow}'
    css = []
    for s in range(len(ids)):
        css.append(f"#{u} svg:has(.n-{s}:hover) .ar-ed:not(.x-{s}){{opacity:.15}}"
                   f"#{u} svg:has(.n-{s}:hover) .ar-node:not(.n-{s}):not(.nb-{s}){{opacity:.35}}")
    return body, "".join(css)


# ---------------------------------------------------------------- compare
def render_compare(spec, u, lv):
    need(spec, "title")
    for side in ("before", "after"):
        d = typed(spec, side, dict)
        for it in d.get("items", []) if isinstance(d.get("items", []), list) else fail(f"compare: {side}.items must be a list"):
            if isinstance(it, dict):
                if not isinstance(it.get("text"), (str, int, float)):
                    fail(f"compare: every {side} item needs 'text'; got {it!r:.60}")
            elif not isinstance(it, (str, int, float)):
                fail(f"compare: {side} items must be strings or objects with 'text'")
    def panel(side, key, default_tone):
        d = spec[key]
        items = "".join(
            f'<div class="cp-item {E(it.get("tone", default_tone)) if isinstance(it, dict) else default_tone}">'
            f'{E(it["text"] if isinstance(it, dict) else it)}</div>' for it in d.get("items", []))
        head = f'<div class="cp-head"><span class="cp-badge">{E(d.get("label", T(spec, side.lower())))}</span>{E(d.get("title", ""))}</div>'
        gold = f'<span class="gold">{E(d["headline"])}</span>' if d.get("headline") else ""
        msg = f'<div class="cp-msg">{gold}{E(d.get("message", ""))}</div>' if (d.get("message") or gold) else ""
        return head + f'<div class="cp-items">{items}</div>' + msg
    body = (f'<input class="h" type="checkbox" id="{u}-s">'
            f'<div class="cp-top"><div class="ttl">{E(spec["title"])}</div>'
            f'<label for="{u}-s" class="btn shine"><span class="cp-t1">{E(spec.get("button", T(spec, "compare_button")))}</span>'
            f'<span class="cp-t2">{E(spec.get("back", T(spec, "back")))}</span></label></div>'
            f'<div class="cp-stage"><div class="cp-panel cp-before">{panel("Before", "before", "bad")}</div>'
            f'<div class="cp-panel cp-after rb"><div class="in">{panel("After", "after", "good")}</div></div></div>')
    s = f"#{u}-s:checked"
    css = (f"#{u}-s:focus-visible~.cp-top .btn{{outline:2px solid var(--b);outline-offset:2px}}"
           f"{s}~.cp-top .cp-t1,{s}~.cp-stage .cp-before{{display:none}}{s}~.cp-top .cp-t2{{display:inline}}"
           f"{s}~.cp-stage .cp-after{{display:block;animation:var(--enter) .55s ease-out both}}"
           f"@media print{{#{u} .cp-before,#{u} .cp-after{{display:block}}#{u} .cp-after{{margin-top:10px}}#{u} .cp-top .btn{{display:none}}}}")
    return body, css


# ---------------------------------------------------------------- loop
def render_loop(spec, u, lv):
    need(spec, "title")
    steps = items_of(spec, "steps", str)
    n = len(steps)
    if not 3 <= n <= 6:
        fail(f"loop: 3 to 6 steps fit the ring; got {n}")
    goal = typed(spec, "goal", str, required=False)
    for lab in steps:
        if text_w(lab, 16) + 20 > 140:
            print(f"WARN: loop step '{lab}' is too long for the ring (keep it to ~12 ASCII / 7 CJK characters)", file=sys.stderr)
    if goal and text_w(goal, 19) + 40 > 300:
        print(f"WARN: loop goal '{goal}' is too long; it will be cut off on phones", file=sys.stderr)
    back = spec.get("back_label") if goal else None
    cx, R = 200, 118
    cy = 238 if goal else 150
    H = (430 if back else 390) if goal else cy + R + 34
    gid = f"{u}-lpg"; rid = f"{u}-lpr"
    angs = [-90 + 360 * i / n for i in range(n)]
    nodes, tris = "", ""
    last = None
    for i, (lab, a) in enumerate(zip(steps, angs)):
        x = cx + R * math.cos(math.radians(a)); y = cy + R * math.sin(math.radians(a))
        w = text_w(lab, 16) + 20
        nodes += (f'<g class="lp-node" style="--lpdur:{n}s"><rect x="{x-w/2:.1f}" y="{y-17:.1f}" width="{w:.1f}" height="34" rx="9" '
                  f'style="animation-delay:{i}s"/><text x="{x:.1f}" y="{y+6:.1f}">{E(lab)}</text></g>')
        last = (x, y, w)
    for i in range(n):
        a = -90 + 360 * (i + .5) / n
        x = cx + R * math.cos(math.radians(a)); y = cy + R * math.sin(math.radians(a))
        tris += f'<path class="lp-tri" d="M-6 -6 L6 0 L-6 6 Z" transform="translate({x:.1f} {y:.1f}) rotate({a+90:.1f})"/>'
    defs = (f'<defs><marker id="{u}-ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
            f'<path d="M0 0L10 5L0 10z" class="lp-ahp"/></marker>'
            f'<marker id="{u}-ahr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
            f'<path d="M0 0L10 5L0 10z" class="lp-ahr"/></marker>'
            f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff9c4"/><stop offset=".45" stop-color="#ffd700"/>'
            f'<stop offset=".55" stop-color="#ff8f00"/><stop offset="1" stop-color="#ffe066"/></linearGradient>'
            f'<linearGradient id="{rid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ff2d55"/><stop offset=".25" stop-color="#ffd700"/>'
            f'<stop offset=".5" stop-color="#22c55e"/><stop offset=".75" stop-color="#3b82f6"/><stop offset="1" stop-color="#a855f7"/></linearGradient></defs>')
    top = ""
    if goal:
        gw = max(170, text_w(goal, 19) + 40)
        top = (f'<g class="lp-goal"><rect x="{cx-gw/2:.1f}" y="14" width="{gw:.1f}" height="40" rx="10" style="stroke:url(#{rid})"/>'
               f'<text x="{cx}" y="41" style="fill:url(#{gid})">{E(goal)}</text></g>'
               f'<line x1="{cx}" y1="56" x2="{cx}" y2="{cy-R-20}" class="lp-down" marker-end="url(#{u}-ah)"/>')
        if back:
            lx, ly, lw = last
            top += (f'<path d="M{lx-lw/2+8:.1f} {ly-17:.1f} C {lx-lw/2-30:.1f} {ly-90:.1f}, 40 60, {cx-gw/2-4:.1f} 36" class="lp-back" marker-end="url(#{u}-ahr)"/>'
                    f'<g class="lp-lg"><line x1="40" y1="410" x2="80" y2="410" class="lp-back"/><text x="88" y="416">{E(back)}</text></g>')
    center = typed(spec, "center", dict, {}, required=False)
    ct = (f'<text x="{cx}" y="{cy+2}" class="lp-ct" style="fill:url(#{gid})">{E(center.get("text", ""))}</text>'
          f'<text x="{cx}" y="{cy+24}" class="lp-cs">{E(center.get("sub", ""))}</text>') if center else ""
    aria = E(spec.get("alt", f'{spec["title"]}: ' + " → ".join(steps)))
    svg = (f'<svg class="lp-svg" viewBox="0 0 400 {H}" role="img" aria-label="{aria}">{defs}{top}'
           f'<circle cx="{cx}" cy="{cy}" r="{R}" class="lp-ring"/><circle cx="{cx}" cy="{cy}" r="{R}" class="lp-flow"/>'
           f'{tris}{nodes}{ct}</svg>')
    return f'<div class="ttl">{E(spec["title"])}</div>{svg}', ""


# ---------------------------------------------------------------- flow
def render_flow(spec, u, lv):
    need(spec, "title")
    steps = items_of(spec, "steps", dict, ("label",))
    n = len(steps)
    if not 2 <= n <= 7:
        fail(f"flow: 2 to 7 steps; got {n}")
    focal = as_index(spec.get("focal", n - 1), n, "flow: focal")
    inp = "".join(f'<input class="h" type="radio" name="{u}-f" id="{u}-f{i}"{" checked" if i == 0 else ""}>' for i in range(n))
    track = "".join(f'<label for="{u}-f{i}" class="fl-step{" fl-focal" if i == focal else ""}"><span class="fl-dot">{i+1}</span>'
                    f'<span class="fl-lb">{E(st["label"])}</span></label>' for i, st in enumerate(steps))
    pans = ""
    for i, st in enumerate(steps):
        inner = (f'<div class="fl-ph"><span class="gold">{i+1:02d}</span>{E(st["label"])}</div>'
                 f'<div class="fl-tx">{E(st.get("detail", ""))}</div>')
        if i == focal:
            inner = f'<div class="rb"><div class="in">{inner}</div></div>'
        pans += f'<div class="fl-p fl-p{i}">{inner}</div>'
    body = (f'{inp}<div class="ttl">{E(spec["title"])}</div>'
            f'<div class="fl-track{" fl-many" if n > 4 else ""}">{track}</div><div class="fl-panel">{pans}</div>')
    dot_on = ("background:var(--a);border-color:transparent;color:#fff" if lv == 1 else
              "background:linear-gradient(180deg,#ff8a3d,#e8430c);border-color:transparent;color:#fff;animation:dd-neon var(--pulse) ease-in-out infinite")
    css = []
    for i in range(n):
        sel = f"#{u}-f{i}:checked"
        css.append(f"{sel}~.fl-track label[for={u}-f{i}] .fl-dot{{{dot_on}}}")
        css.append(f"#{u}-f{i}:focus-visible~.fl-track label[for={u}-f{i}] .fl-dot{{outline:2px solid var(--b);outline-offset:2px}}")
        css.append(f"{sel}~.fl-panel .fl-p{i}{{display:block;animation:pop .3s ease}}")
        if i == focal:
            css.append(f"{sel}~.fl-panel .fl-p{i} .rb{{animation:var(--enter) .55s ease-out both}}")
    # PDF has no clicks and no room for every detail: print the focal step
    css.append(f"@media print{{#{u} .fl-p{{display:none!important}}#{u} .fl-p{focal}{{display:block!important}}#{u} .fl-p .rb{{margin:0}}"
               f"#{u} .fl-dot{{background:var(--card)!important;color:var(--b)!important;border-color:var(--b)!important}}"
               f"#{u} .fl-focal .fl-dot{{background:var(--a)!important;color:#fff!important;border-color:var(--a)!important}}}}")
    return body, "".join(css)


# ---------------------------------------------------------------- ladder
def render_ladder(spec, u, lv):
    need(spec, "title")
    lvls = items_of(spec, "levels", dict, ("name",))
    if not 2 <= len(lvls) <= 6:
        fail(f"ladder: 2 to 6 levels; got {len(lvls)}")
    barw = (529 - 6 * (len(lvls) - 1)) / len(lvls) - 20      # 561px embed minus padding = 529; bar border + padding = 20
    for l in lvls:
        if text_w(l["name"], 12) > barw * 2:
            print(f"WARN: ladder level name '{l['name']}' needs more than two lines on its bar; shorten it", file=sys.stderr)
    n = len(lvls)
    now_l = spec.get("now_label", T(spec, "now_label"))
    next_l = spec.get("next_label", T(spec, "next_label"))
    inp = "".join(f'<input class="h" type="radio" name="{u}-l" id="{u}-l{i}">' for i in range(n))
    bars = ""
    for i, l in enumerate(lvls):
        h = 34 + 66 * i / max(n - 1, 1)      # shortest bar (75px) still fits "Lv.N" + a two-line name
        top = i == n - 1 and spec.get("top_focal", True)
        bars += (f'<label for="{u}-l{i}" class="ld-b ld-b{i}{" ld-top rb" if top else ""}" style="height:{h:.0f}%">'
                 f'<span class="in"><span class="ld-n">{E(l.get("short", f"Lv.{i+1}"))}</span><span class="ld-nm">{E(l["name"])}</span></span></label>')
    pans = f'<div class="ld-p ld-p0">{E(spec.get("prompt", T(spec, "prompt")))}</div>'
    pans += "".join(f'<div class="ld-p ld-q{i}"><b class="ld-pt">{E(l.get("short", f"Lv.{i+1}"))} {E(l["name"])}</b>'
                    f'<div>{E(now_l)}: {E(l.get("now", ""))}</div>'
                    f'<div class="ld-nx">{E(next_l)} ▶ <span class="gold">{E(l.get("next", ""))}</span></div></div>' for i, l in enumerate(lvls))
    body = f'{inp}<div class="ttl">{E(spec["title"])}</div><div class="ld-st">{bars}</div><div class="ld-pn">{pans}</div>'
    on = "background:var(--a);color:#fff" if lv == 1 else "background:linear-gradient(180deg,#ff8a3d,#e8430c);color:#fff"
    neon = "" if lv == 1 else "animation:dd-neon var(--pulse) ease-in-out infinite;"
    pulse = "" if lv == 1 else ",dd-goldpulse 1.8s ease-in-out .8s infinite"
    css = []
    for i in range(n):
        sel = f"#{u}-l{i}:checked"
        css.append(f"{sel}~.ld-st label[for={u}-l{i}]{{transform:translateY(-5px);{neon}}}"
                   f"{sel}~.ld-st label[for={u}-l{i}]>.in{{{on}}}"
                   f"#{u}-l{i}:focus-visible~.ld-st label[for={u}-l{i}]{{outline:2px solid var(--b);outline-offset:2px}}"
                   f"{sel}~.ld-pn .ld-p0{{display:none}}{sel}~.ld-pn .ld-q{i}{{display:block;animation:pop .35s ease}}"
                   f"{sel}~.ld-pn .ld-q{i} .gold{{animation:var(--enter) .55s ease-out .2s both{pulse}}}")
    return body, "".join(css)


# ---------------------------------------------------------------- proportion
PR_COLORS = ["var(--b)", "#14b8a6", "#8b5cf6", "#f59e0b"]


def render_proportion(spec, u, lv):
    need(spec, "title")
    groups = items_of(spec, "groups", dict, ("label",), lo=1, hi=8)
    for g in groups:
        if not isinstance(g.get("count"), int) or isinstance(g.get("count"), bool) or g["count"] < 0:
            fail(f"proportion: count of '{g['label']}' must be a non-negative integer")
        if g.get("color") is not None and not COLOR_RE.fullmatch(str(g["color"])):
            fail(f"proportion: color {g['color']!r} is not a plain CSS colour (#hex, name, rgb(), var(--x))")
    if groups[-1]["count"] == 0:
        fail("proportion: the last group hides the gem, so it needs at least 1 dot")
    total = sum(g["count"] for g in groups)
    if total != 99:
        raise SystemExit(f"proportion: group counts must add up to 99 (the 100th dot is the gem); got {total}")
    cols = [g.get("color") or (PR_COLORS[i % len(PR_COLORS)] if i < len(groups) - 1 else "#9ca3af") for i, g in enumerate(groups)]
    seq = [c for g, c in zip(groups, cols) for _ in range(g["count"])]
    start_last = 99 - groups[-1]["count"]
    gem_at = as_index(spec.get("gem_at", start_last + groups[-1]["count"] // 2), 100, "proportion: gem_at")
    if gem_at < start_last:   # the legend counts the gem in the last group, so it must sit there
        fail(f"proportion: gem_at must be inside the last group ({start_last} to 99); got {gem_at}")
    gem_bg = seq[min(gem_at, len(seq) - 1)]          # hide the gem in the colour of its neighbours
    seq.insert(gem_at, "gem")
    dots = "".join(f'<i class="pr-gem" style="--d:0s;background:{gem_bg}"></i>' if c == "gem" else
                   f'<i style="--d:{(i % 10) * .03 + (i // 10) * .03:.2f}s;background:{c}"></i>' for i, c in enumerate(seq))
    lgd = "".join(f'<div class="pr-lgd"><span class="pr-sw" style="background:{c}"></span>{E(g["label"])} {g["count"] + (1 if gi == len(groups) - 1 else 0)}</div>'
                  for gi, (g, c) in enumerate(zip(groups, cols)))
    gem = typed(spec, "gem", dict, {}, required=False)
    body = (f'<input class="h" type="checkbox" id="{u}-s">'
            f'<div class="pr-top"><div class="ttl">{E(spec["title"])}</div>'
            f'<label for="{u}-s" class="btn shine"><span class="pr-t1">{E(spec.get("button", T(spec, "proportion_button")))}</span>'
            f'<span class="pr-t2">{E(spec.get("back", T(spec, "back")))}</span></label></div>'
            f'<div class="pr-g"><div class="pr-dots">{dots}</div><div class="pr-side">'
            f'<div class="pr-v1">{lgd}<p class="pr-say">{E(spec.get("say", ""))}</p><p class="pr-sub">{E(spec.get("say_sub", ""))}</p></div>'
            f'<div class="pr-v2"><div class="pr-gemt gold">{E(gem.get("title", T(spec, "gem_title")))}</div>'
            f'<p>{E(gem.get("text", ""))}</p><p class="pr-sub">{E(gem.get("sub", ""))}</p></div></div></div>')
    s = f"#{u}-s:checked"
    glow = ("box-shadow:0 0 0 3px var(--ys),0 0 16px var(--glow),0 0 32px var(--a);animation:dd-gem 1.4s ease-in-out infinite;"
            if lv > 1 else "box-shadow:0 0 0 3px var(--a);")
    css = (f"#{u}-s:focus-visible~.pr-top .btn{{outline:2px solid var(--b);outline-offset:2px}}"
           f"{s}~.pr-top .pr-t1,{s}~.pr-g .pr-v1{{display:none}}{s}~.pr-top .pr-t2{{display:inline}}"
           f"{s}~.pr-g .pr-v2{{display:block}}"
           f"{s}~.pr-g .pr-v2 .pr-gemt{{animation:var(--enter) .6s ease-out .3s both{'' if lv == 1 else ',dd-goldpulse 1.8s ease-in-out 1s infinite'}}}"
           f"{s}~.pr-g .pr-v2 p{{animation:pop .4s ease .6s both}}"
           f"{s}~.pr-g .pr-dots i{{opacity:.15;transform:scale(.75)}}"
           f"{s}~.pr-g .pr-dots .pr-gem{{opacity:1;transform:scale(1.4);background:radial-gradient(circle at 35% 30%,#fffde7,#ffd700 45%,#ff8f00)!important;"
           f"{glow}transition-delay:0s;z-index:2}}")
    if lv > 1:
        css += (f"{s}~.pr-g .pr-dots .pr-gem::before{{content:'';position:absolute;left:50%;top:50%;width:110px;height:110px;margin:-55px 0 0 -55px;"
                f"border-radius:50%;background:repeating-conic-gradient(rgba(255,215,0,.55) 0 10deg,transparent 10deg 30deg);"
                f"-webkit-mask:radial-gradient(circle,#000 20%,transparent 70%);mask:radial-gradient(circle,#000 20%,transparent 70%);"
                f"animation:dd-spin 6s linear infinite;z-index:-1}}")
    css += (f"@media print{{#{u} .pr-dots i{{opacity:.15}}#{u} .pr-dots .pr-gem{{opacity:1;transform:scale(1.4);background:#ffd700!important}}"
            f"#{u} .pr-v2{{display:block}}#{u} .pr-v1 .pr-say,#{u} .pr-v1 .pr-sub,#{u} .pr-top .btn{{display:none}}}}")
    return body, css


RENDER = {"explorer": render_explorer, "decompose": render_decompose, "architecture": render_architecture,
          "compare": render_compare, "loop": render_loop, "flow": render_flow, "ladder": render_ladder,
          "proportion": render_proportion}


# ---------------------------------------------------------------- assembly
def build_one(spec, idx, intensity, target):
    if not isinstance(spec, dict):
        fail(f"spec #{idx + 1} must be a JSON object with a 'pattern' field; got {type(spec).__name__}")
    pat = spec.get("pattern")
    if pat not in RENDER:
        raise SystemExit(f"unknown pattern: {pat} (known: {', '.join(RENDER)})")
    lv = intensity or spec.get("intensity", 2)
    if type(lv) is not int or lv not in (1, 2, 3):
        fail(f"intensity must be 1, 2 or 3; got {lv!r}")
    u = "dd" + hashlib.sha1(f"{idx}:{json.dumps(spec, sort_keys=True)}".encode()).hexdigest()[:6]
    body, state_css = RENDER[pat](spec, u, lv)
    note = f'<div class="note">{E(spec["note"])}</div>' if spec.get("note") else ""
    html_ = f'<div class="dd lv{lv}" id="{u}">{body}{note}</div>'
    return pat, html_, state_css


def base_css(target):
    css = (TPL / "base.css").read_text(encoding="utf-8")
    dark = f'[data-theme="dark"] .dd{{{DARK_VARS}}}'
    if target != "zenn":   # Zenn signals dark mode only via data-theme; OS preference must not leak in
        dark += f'@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]) .dd{{{DARK_VARS}}}}}'
    return css.replace("/*DARK*/", dark)


def part_css(pat):
    return (TPL / "parts" / f"{pat}.css").read_text(encoding="utf-8")


def minify(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s+", " ", css)
    return re.sub(r"\s*([{};:,>])\s*", r"\1", css).strip()


def has_cjk(s):
    return bool(re.search(r"[぀-ヿ㐀-鿿]", s))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("specs", nargs="+")
    ap.add_argument("--target", required=True, choices=["zenn", "standalone", "slides"])
    ap.add_argument("--intensity", type=int, choices=[1, 2, 3])
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--title", default="Diagrams")
    a = ap.parse_args()
    specs = []
    for f in a.specs:
        try:
            specs.append(json.loads(pathlib.Path(f).read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as e:
            fail(f"{f}: {e}")
    built = [build_one(s, i, a.intensity, a.target) for i, s in enumerate(specs)]
    lang = "ja" if has_cjk(json.dumps(specs, ensure_ascii=False)) else "en"
    out = pathlib.Path(a.out)

    if a.target == "zenn":
        blocks = []
        for (pat, h, st), s in zip(built, specs):
            block = f"<style>{minify(base_css('zenn') + part_css(pat) + st)}</style>\n{h}"
            size = len(block.encode())
            if size > ZENN_MAX_BYTES:
                print(f"ERROR: {s.get('title', pat)} is {size} bytes (> 50KB Zenn limit)", file=sys.stderr)
                sys.exit(1)
            blocks.append(f"```html-embed\n{block}\n```")
            print(f"{pat:13s} {size:6d} bytes")
        out.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    else:
        pats = sorted({p for p, _, _ in built})
        css = minify(base_css(a.target) + "".join(part_css(p) for p in pats) + "".join(st for _, _, st in built))
        page_bg = ("body{margin:0;background:#f4f4f5;color:#1f2328}"
                   "[data-theme=dark] body{background:#0d1117}"
                   "@media (prefers-color-scheme:dark){:root:not([data-theme=light]) body{background:#0d1117}}")
        if a.target == "standalone":
            shell = ("body{padding:24px 16px}.dd-wrap{max-width:760px;margin:0 auto 28px}")
            items = "".join(f'<div class="dd-wrap">{h}</div>' for _, h, _ in built)
        else:
            shell = ("@page{size:1280px 720px;margin:0}"
                     ".slide{width:1280px;height:720px;overflow:hidden;box-sizing:border-box;padding:44px 72px;display:flex;"
                     "flex-direction:column;break-after:page;font-family:system-ui,-apple-system,'Hiragino Sans','Noto Sans JP',sans-serif}"
                     ".slide h2{font-size:34px;margin:0 0 18px;color:#1f2328}"
                     "[data-theme=dark] .slide h2{color:#e6edf3}"
                     "@media (prefers-color-scheme:dark){:root:not([data-theme=light]) .slide h2{color:#e6edf3}}"
                     ".stage{flex:1;display:flex;align-items:center;justify-content:center;min-height:0}"
                     ".slide .dd{width:100%;max-width:860px;zoom:1.3}.slide .dd .ttl{display:none}"
                     "@media screen{body{background:#52525b}.slide{margin:16px auto;background:#f4f4f5}"
                     "[data-theme=dark] .slide{background:#0d1117}"
                     "@media (prefers-color-scheme:dark){:root:not([data-theme=light]) .slide{background:#0d1117}}}")
            items = "".join(f'<section class="slide"><h2>{E(s.get("slide_title", s.get("title", "")))}</h2>'
                            f'<div class="stage">{h}</div></section>' for (_, h, _), s in zip(built, specs))
        doc = (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
               f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{E(a.title)}</title>'
               f'<style>{page_bg}{shell}</style><style>{css}</style></head><body>{items}</body></html>\n')
        out.write_text(doc, encoding="utf-8")
        print(f"{a.target}: {len(built)} diagram(s), {len(doc.encode())} bytes")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
