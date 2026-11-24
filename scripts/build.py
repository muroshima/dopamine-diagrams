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

E = lambda s: html.escape(str(s), quote=True)


def slug(s):
    s = re.sub(r"[^A-Za-z0-9_-]", "-", str(s))
    if not re.match(r"[A-Za-z_]", s):
        s = "n" + s
    return s


def text_w(s, fs):
    """Rough rendered width of text in px (CJK ~1em, others ~0.6em)."""
    return sum(fs if ord(c) > 0x2E7F else fs * 0.6 for c in str(s))


# ---------------------------------------------------------------- explorer
def render_explorer(spec, u, lv):
    cases = spec["cases"]
    bad_l = spec.get("bad_label", "Common mistake")
    good_l = spec.get("good_label", "Do this instead")
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
    kids = spec["children"]
    n = len(kids)
    cols = n if n <= 5 else 3
    root = spec["root"]
    kd = "".join(f'<div class="dc-k" style="--i:{i}"><span class="dc-tag">{E(k["tag"])}</span>{E(k["text"])}</div>'
                 if k.get("tag") else f'<div class="dc-k" style="--i:{i}">{E(k["text"])}</div>'
                 for i, k in enumerate(kids))
    ttl = f'<div class="ttl">{E(spec["title"])}</div>' if spec.get("title") else ""
    body = (f'<input class="h" type="checkbox" id="{u}-s">{ttl}'
            f'<div class="dc-root"><span class="dc-kick">{E(root.get("kicker", ""))}</span>{E(root["text"])}'
            f'<span class="dc-done gold">{E(spec.get("done", "Done!"))}</span></div>'
            f'<div class="dc-mid"><label for="{u}-s" class="btn shine"><span class="dc-t1">{E(spec.get("button", "Break it down ▶"))}</span>'
            f'<span class="dc-t2">{E(spec.get("back", "Back"))}</span></label>'
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
        for ti, t in enumerate(tiers):
            k = len(t["nodes"])
            bh = 22 + nh + 8
            out.append(f'<rect class="ar-band" x="2" y="{y:.1f}" width="{W-4}" height="{bh:.1f}" rx="10"/>'
                       f'<text class="ar-tier" x="12" y="{y+16:.1f}" style="text-anchor:start">{E(t["name"])}</text>')
            cy = y + 22 + nh / 2
            for ni, n in enumerate(t["nodes"]):
                cx = W * (ni + .5) / k
                w = min(W / k - 12, max(text_w(n["label"], FS) + 24, text_w(n.get("sub", ""), FSS) + 16))
                pos[n["id"]] = (cx, cy, w, nh, ti)
            y += bh + rowgap
        H = y - rowgap + 4
    # adjacency for hover dimming
    nb = {i: set() for i in pos}
    for e in edges:
        nb[e["from"]].add(e["to"]); nb[e["to"]].add(e["from"])
    # edges first (under nodes)
    eds = []
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
        d = f"M{p0[0]:.1f} {p0[1]:.1f} C{p1[0]:.1f} {p1[1]:.1f},{p2[0]:.1f} {p2[1]:.1f},{p3[0]:.1f} {p3[1]:.1f}"
        lab = ""
        if e.get("label"):
            mx, my = _bez(p0, p1, p2, p3)
            lw = text_w(e["label"], FSE) + 10
            lab = (f'<rect class="ar-elabel-bg" x="{mx-lw/2:.1f}" y="{my-FSE/2-4:.1f}" width="{lw:.1f}" height="{FSE+8:.0f}" rx="4"/>'
                   f'<text class="ar-elabel" x="{mx:.1f}" y="{my+FSE*0.35:.1f}">{E(e["label"])}</text>')
        eds.append(f'<g class="ar-ed x-{slug(e["from"])} x-{slug(e["to"])}"><path class="ar-base" d="{d}"/>'
                   f'<path class="ar-flow" d="{d}"/>{lab}</g>')
    nodes = []
    gid = f"{u}-{mode[0]}-rbw"
    for nid, (cx, cy, w, h, _) in pos.items():
        n = next(n for t in tiers for n in t["nodes"] if n["id"] == nid)
        cls = f"ar-node n-{slug(nid)} " + " ".join(f"nb-{slug(x)}" for x in nb[nid])
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
    focal = set(spec.get("focal", []))
    wide, ids = _arch_svg(spec, u, "wide", focal)
    narrow, _ = _arch_svg(spec, u, "narrow", focal)
    body = f'<div class="ttl">{E(spec["title"])}</div>{wide}{narrow}'
    css = []
    for nid in ids:
        s = slug(nid)
        css.append(f"#{u} svg:has(.n-{s}:hover) .ar-ed:not(.x-{s}){{opacity:.15}}"
                   f"#{u} svg:has(.n-{s}:hover) .ar-node:not(.n-{s}):not(.nb-{s}){{opacity:.35}}")
    return body, "".join(css)


RENDER = {"explorer": render_explorer, "decompose": render_decompose, "architecture": render_architecture}


# ---------------------------------------------------------------- assembly
def build_one(spec, idx, intensity, target):
    pat = spec["pattern"]
    if pat not in RENDER:
        raise SystemExit(f"unknown pattern: {pat} (known: {', '.join(RENDER)})")
    lv = int(intensity or spec.get("intensity", 2))
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
    specs = [json.loads(pathlib.Path(p).read_text(encoding="utf-8")) for p in a.specs]
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
                     ".slide .dd{width:100%;max-width:860px;zoom:1.3}.slide .dd>.ttl{display:none}"
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
