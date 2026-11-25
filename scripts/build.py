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
             "--b:#60a5fa;--bs:#172554;--g:#4ade80;--gs:#052e16;--r:#f87171;--rs:#450a0a;--y:#facc15;--ys:#422006;--yt:#fde68a;--bt:#93c5fd;"
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


def tier_w(s, fs):
    """Upper bound for a tier name (.ar-tier is weight 800 with .04em tracking; bold capitals ~0.75em, M/W ~1em).
    It is a guess: build.py warns from it, check.mjs measures the real text."""
    def one(c):
        o = ord(c)
        if o >= 0x1F000 or 0x2600 <= o <= 0x27BF or 0x2B00 <= o <= 0x2BFF or 0x2300 <= o <= 0x23FF:   # emoji
            return 1.3
        if 0xFF61 <= o <= 0xFF9F:     # half-width katakana
            return 0.55
        if o >= 0x2000:               # CJK, and symbols (arrows, boxes, dashes) that Japanese fonts draw full width
            return 1.0
        if c in "MWmw@%&":
            return 1.0
        if c.isupper() or c.isdigit():
            return 0.76
        return 0.32 if c == " " else 0.6
    return sum((one(c) + .04) * fs for c in str(s))


# Default UI words: spec["lang"] if given, else Japanese when any text has kana, else English (see spec_lang).
DEFAULTS = {
    "ja": {"bad_label": "よくある間違い", "good_label": "こうする", "done": "完了！", "decompose_button": "分解する ▶",
           "compare_button": "直す ▶", "proportion_button": "よく見る ▶", "back": "戻る", "now_label": "いま",
           "next_label": "次の一手", "prompt": "いまどの段？ 段をクリック", "gem_title": "見落としてはいけない1件",
           "before": "ビフォー", "after": "アフター", "tier1": "低", "tier2": "中", "tier3": "高", "tier4": "最重要",
           "goal": "目標", "reached": "到達 ✓", "not_reached": "未達",
           "flip": "めくる ▶", "unflip": "伏せる", "hidden": "答えを予想してからめくる"},
    "en": {"bad_label": "Common mistake", "good_label": "Do this instead", "done": "Done!",
           "decompose_button": "Break it down ▶", "compare_button": "Show the fix ▶", "proportion_button": "Look closer ▶",
           "back": "Back", "now_label": "Now", "next_label": "Next move", "prompt": "Where are you? Click a step",
           "gem_title": "The one that matters", "before": "Before", "after": "After", "tier1": "Low", "tier2": "Medium", "tier3": "High",
           "tier4": "Critical", "goal": "Goal", "reached": "Reached ✓", "not_reached": "Not yet", "flip": "Flip ▶",
           "unflip": "Hide", "hidden": "Guess the answer, then flip"},
}


def spec_lang(spec):
    """"lang" in the spec wins; otherwise Japanese when any text has kana (kanji alone could be Chinese or a place name)."""
    lang = spec.get("lang")
    if lang is not None:
        if not isinstance(lang, str) or lang not in DEFAULTS:
            fail(f"lang must be one of {sorted(DEFAULTS)}; got {lang!r:.40}")
        return lang
    # hiragana, katakana (without the middle dot U+30FB, common in non-Japanese text too), half-width katakana
    return "ja" if re.search(r"[\u3041-\u309f\u30a0-\u30fa\u30fc-\u30ff\u31f0-\u31ff\uff66-\uff9f]",
                             json.dumps(spec, ensure_ascii=False)) else "en"


def T(spec, key):
    return DEFAULTS[spec_lang(spec)][key]


def tier_badge(spec, item, where):
    """Importance badge from item["importance"] (1-4): colour, line, stars and a word together. "" when absent."""
    t = item.get("importance")
    if t is None:
        if item.get("importance_label") is not None:
            fail(f"{where}: importance_label needs importance (1 to 4)")
        return ""
    if isinstance(t, bool) or not isinstance(t, int) or not 1 <= t <= 4:
        fail(f"{where}: importance must be an integer 1 to 4; got {t!r:.40}")
    word = item.get("importance_label", T(spec, f"tier{t}"))
    if not isinstance(word, str) or not word.strip():
        fail(f"{where}: importance_label must be a non-empty string; got {word!r:.40}")
    if text_w(word, 12) > 110:
        print(f"WARN: {where}: importance_label '{word}' is long for a badge; keep it to a word or two", file=sys.stderr)
    return f'<span class="tb t{t}"><span class="st" aria-hidden="true">{"★" * t}</span>{E(word)}</span>'


def hush_on(spec, where):
    """spec["hush"]: when the answer appears, everything else stops and dims (a pachinko freeze)."""
    h = spec.get("hush", False)
    if not isinstance(h, bool):
        fail(f"{where}: hush must be true or false; got {h!r:.40}")
    return h


# Hush stops motion; only decoration without text fades (text keeps its contrast, also in print).
STILL = "animation-play-state:paused!important"
FADE = "animation-play-state:paused!important;opacity:.35"


def hush_base(sel):
    """Fade in and out over 1s both ways; no fade with reduced motion (it would be a sudden dim) or in print."""
    return (f"{sel}{{transition:opacity 1s ease}}"
            f"@media (prefers-reduced-motion:reduce){{{sel}{{opacity:1!important}}}}@media print{{{sel}{{opacity:1!important}}}}")


def cutin(item, where):
    """A slanted band that cuts in once with a one-line verdict, like a pachinko cut-in. "" when absent."""
    t = item.get("cutin")
    if t is None:
        return ""
    if not isinstance(t, str) or not t.strip():
        fail(f"{where}: cutin must be a non-empty string; got {t!r:.40}")
    if text_w(t, 16) > 260:
        print(f"WARN: {where}: cutin '{t[:30]}' is long; keep it to one short line", file=sys.stderr)
    return f'<div class="ci"><span>{E(t)}</span></div>'


def tier_count_check(spec, items, where):
    tops = sum(1 for it in items if isinstance(it, dict) and it.get("importance") == 4)
    if tops > 1:
        print(f"WARN: {where}: {tops} items use importance 4; keep the top level for one item so it still means the most "
              f"important",
              file=sys.stderr)


# ---------------------------------------------------------------- explorer
def render_explorer(spec, u, lv):
    need(spec, "title")
    cases = items_of(spec, "cases", dict, ("label", "good"), lo=2, hi=8)
    tier_count_check(spec, cases, "explorer")
    bad_l = spec.get("bad_label", T(spec, "bad_label"))
    good_l = spec.get("good_label", T(spec, "good_label"))
    reveal = spec.get("reveal")
    if reveal not in (None, "stamp", "flip"):
        fail(f"explorer: reveal must be 'stamp' or 'flip'; got {reveal!r:.40}")
    flip = reveal == "flip"
    if flip and any(c.get("cutin") for c in cases):
        fail("explorer: cutin cannot be used with reveal 'flip'; the band would give the hidden answer away")
    inp = "".join(f'<input class="h" type="radio" name="{u}-m" id="{u}-m{i}"{" checked" if i == 0 else ""}>'
                  for i in range(len(cases)))
    if flip:   # one checkbox per case turns its card over
        inp += "".join(f'<input class="h" type="checkbox" id="{u}-f{i}">' for i in range(len(cases)))
    labs = "".join(f'<label for="{u}-m{i}"><span class="ex-no">{i+1:02d}</span>{E(c["label"])}</label>'
                   for i, c in enumerate(cases))
    def text_opt(d, key, default, where, limit):
        v = d.get(key, default)
        if not isinstance(v, str) or not v.strip():
            fail(f"explorer: {where}{key} must be a non-empty string; got {v!r:.40}")
        if text_w(v, 14) > limit:
            print(f"WARN: explorer: {where}{key} '{v[:30]}' is long; the card may not fit the phone layout",
                  file=sys.stderr)
        return v
    flip_l = text_opt(spec, "flip_label", T(spec, "flip"), "", 120) if flip else ""
    unflip_l = text_opt(spec, "unflip_label", T(spec, "unflip"), "", 70) if flip else ""

    def flip_card(i, c):
        """A face-down card, like a gacha pull: the back says what to expect, flipping shows the answer."""
        hint = text_opt(c, "hint", T(spec, "hidden"), f"case {i+1} ", 280)
        return (f'<div class="ex-card"><div class="ex-cin">'
                f'<div class="ex-back"><span class="ex-q" aria-hidden="true">?</span><span>{E(hint)}</span>'
                f'<label for="{u}-f{i}" class="btn shine">{E(flip_l)}</label></div>'
                f'<div class="ex-face ex-good rb"><div class="in"><b class="gold">{E(good_l)}</b>'
                f'<div class="ex-ok">{E(c["good"])}</div>'
                f'<label for="{u}-f{i}" class="ex-unflip">{E(unflip_l)}</label>'
                f'</div></div></div></div>')

    pans = ""
    for i, c in enumerate(cases):
        bad = (f'<div class="ex-bad"><b>{E(bad_l)}</b><s>{E(c["bad"])}</s></div>' if c.get("bad") else "")
        pans += (f'<div class="ex-p ex-p{i}"><div class="ex-hd"><span class="ex-num gold">{i+1:02d}</span>'
                 f'<span class="ex-sit">{E(c.get("situation", c["label"]))}</span>{tier_badge(spec, c, f"explorer case {i+1}")}</div>'
                 f'{cutin(c, f"explorer case {i+1}")}{bad}'
                 + (flip_card(i, c) if flip else
                    f'<div class="ex-good rb"><div class="in"><b class="gold">{E(good_l)}</b>'
                    f'<div class="ex-ok">{E(c["good"])}</div></div></div>') + '</div>')
    body = (f'{inp}<div class="ttl">{E(spec["title"])}</div>'
            f'<div class="ex-g"><div class="ex-ls">{labs}</div><div class="ex-ps">{pans}</div></div>')
    chip = CHIP_ON_LV1 if lv == 1 else CHIP_ON
    css = []
    for i in range(len(cases)):
        sel = f"#{u}-m{i}:checked~.ex-g"
        css.append(f"{sel} label[for={u}-m{i}]{{{chip}}}{sel} label[for={u}-m{i}] .ex-no{{color:#fff}}")
        css.append(f"#{u}-m{i}:focus-visible~.ex-g label[for={u}-m{i}]{{outline:2px solid var(--b);outline-offset:1px}}")
        css.append(f"{sel} .ex-p{i}{{display:block;animation:pop .3s ease}}{sel} .ex-p{i} .ci{{animation:dd-cut .55s cubic-bezier(.2,.8,.2,1) both}}")
        if flip:
            # only the shown case's card can be focused or read; the hidden side of a card is hidden from both
            css.append(f"#{u}-m{i}:not(:checked)~#{u}-f{i}{{visibility:hidden}}"
                       f"#{u}-f{i}:checked~.ex-g .ex-p{i} .ex-face{{visibility:visible;transition-delay:0s}}"
                       f"#{u}-f{i}:checked~.ex-g .ex-p{i} .ex-back{{visibility:hidden;transition-delay:.3s}}")
            css.append(f"#{u}-f{i}:checked~.ex-g .ex-p{i} .ex-cin{{transform:rotateY(180deg)}}"
                       f"#{u}-f{i}:focus-visible~.ex-g .ex-p{i} label[for={u}-f{i}]{{outline:2px solid var(--b);outline-offset:2px}}")
        else:
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
    nord = {n["id"]: ni for t in tiers for ni, n in enumerate(t["nodes"])}   # position inside its tier
    tnames = []   # tier names, drawn over the edges with a halo so a line passing under one never hides it
    if mode == "wide":
        # Column widths come from the node text, gaps from the edge labels between neighbouring tiers.
        # If that needs more than 600 user units, the viewBox widens and every font grows with it, so text
        # still renders >= 12px when the embed is only 529px wide (Zenn PC at ~561px). solve() picks the font.
        W, top, gap, MINW, NARROWEST = 600, 40, 18, 600, 529

        def measure(FS, FSS, FSE, with_names):
            colw = [max([tier_w(t["name"], FSS) + 4 if with_names else 0]
                        + [max(text_w(n["label"], FS) + 28, text_w(n.get("sub", ""), FSS) + 20) for n in t["nodes"]])
                    for t in tiers]
            gaps = []
            def bulge_need(t):
                # room beside a column for its same-tier bulges (same nesting rule as the routing, plus slack)
                grp = sorted((e for e in edges if tid[e["from"]] == tid[e["to"]] == t
                              and (e.get("label") or abs(nord[e["from"]] - nord[e["to"]]) > 1)),
                             key=lambda e: abs(nord[e["from"]] - nord[e["to"]]))
                done, need_ = [], 0
                for e in grp:
                    lo, hi = sorted((nord[e["from"]], nord[e["to"]]))
                    lw_i = text_w(e["label"], FSE) + 10 if e.get("label") else 0
                    off = max(14, lw_i / 2 + 10)
                    for (lo2, hi2, off2, lw2) in done:
                        if lo < hi2 and lo2 < hi:
                            off = max(off, off2 + lw2 / 2 + lw_i / 2 + 10)
                    done.append((lo, hi, off, lw_i))
                    need_ = max(need_, off + lw_i / 2 + 6)
                return need_ * 1.3 if need_ else 0   # slack: the real offsets follow the curve (see boff)

            for ti in range(T - 1):
                # labels of edges between neighbouring tiers, and of edges that skip tiers (on their first hop)
                labs = [text_w(e["label"], FSE) + 18 for e in edges if e.get("label")
                        and (sorted((tid[e["from"]], tid[e["to"]])) == [ti, ti + 1]
                             or (tid[e["from"]] == ti and tid[e["to"]] > ti + 1))]
                # same-tier edges bulge into the gap on their right (the last tier: on its left); both sides add up
                side_need = bulge_need(ti) if ti < T - 1 else 0
                if ti == T - 2:
                    side_need += bulge_need(T - 1)
                gaps.append(max([34, side_need + 10] + labs))
            need = 12 + sum(c + 16 for c in colw) + sum(gaps)
            if T == 1:   # the single column is centred: room for its bulges on both sides
                need += 2 * bulge_need(0)
            return colw, gaps, need, max(MINW, need)

        def solve(with_names):
            # Fonts scale with W (the SVG is squeezed to NARROWEST px) and W grows with the fonts. Take the
            # smallest font, in 0.5 steps up to FMAX, whose text still renders >= 12.3px at NARROWEST.
            # None fits -> text grows faster than W; the caller warns and check.mjs reports small text.
            # FMAX bounds the search; past it the fixed parts (line widths, corner radii) look tiny anyway.
            FMAX = 64
            f = 14.0
            while f <= FMAX:
                colw, gaps, need, W = measure(f + 2, f, f, with_names)
                if round(12.3 * W / NARROWEST * 2) / 2 <= f:
                    return True, f + 2, f, f, colw, gaps, need, W
                f += 0.5
            return (False, 16.0, 14.0, 14.0) + measure(16, 14, 14, with_names)

        ok, FS, FSS, FSE, colw, gaps, need, W = solve(True)
        if not ok:
            # Long tier names: size the fonts from the nodes alone, then let the names widen their columns.
            ok, FS, FSS, FSE, colw, gaps, need, W = solve(False)
            if not ok:
                print("WARN: architecture has too much text side by side (node labels or edge labels); "
                      "shorten them or use fewer tiers", file=sys.stderr)
            W0 = W
            for ti, t in enumerate(tiers):
                colw[ti] = max(colw[ti], tier_w(t["name"], FSS) + 4)
            need = 12 + sum(c + 16 for c in colw) + sum(gaps)
            W = max(W, need)
            if ok and W > W0 and FSS * NARROWEST / W < 12:
                print(f"WARN: architecture tier names are too long for the side-by-side layout "
                      f"(by estimate, text may drop below 12px at {NARROWEST}px); if check.mjs reports small text, "
                      f"shorten them", file=sys.stderr)
        extra = (W - need) / max(T - 1, 1) if T > 1 else 0
        ty = max(27, math.ceil(1.1 * FSS + 6))   # tier name baseline: ascent ~1em (Japanese), ~1.1em (emoji); band top y=6
        top = max(top, ty + math.ceil(0.3 * FSS) + 6)   # room for the descent before the first node
        nh = round(FS + FSS + 26) if any(n.get("sub") for t in tiers for n in t["nodes"]) else round(FS + 22)
        maxn = max(len(t["nodes"]) for t in tiers)
        H = top + maxn * (nh + gap) + 6
        x = 6 if T > 1 else (W - colw[0] - 16) / 2
        band_x, gapw = [], [g + extra for g in gaps]
        for ti, t in enumerate(tiers):
            bw = colw[ti] + 16
            cx = x + bw / 2
            band_x.append((x, x + bw))
            out.append(f'<rect class="ar-band" x="{x:.1f}" y="6" width="{bw:.1f}" height="{H-8:.1f}" rx="10"/>')
            tnames.append(f'<text class="ar-tier" x="{cx:.1f}" y="{ty}">{E(t["name"])}</text>')
            k = len(t["nodes"])
            y0 = top + (maxn - k) * (nh + gap) / 2
            for ni, n in enumerate(t["nodes"]):
                pos[n["id"]] = (cx, y0 + ni * (nh + gap) + nh / 2, colw[ti], nh, ti)
            if ti < T - 1:
                x += bw + gaps[ti] + extra
    else:
        # Tiers become rows. Each row is a band with its name along the top edge, where no edge crosses it.
        W = 320
        FS, FSS, FSE = 15, 13, 13
        nh = 48 if any(n.get("sub") for t in tiers for n in t["nodes"]) else 34
        rowgap = 26
        bh = 22 + nh + 8
        y = 6
        band_top, names = [], []
        for ti, t in enumerate(tiers):
            band_top.append(y)
            k = len(t["nodes"])
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
    # ---- edges. Drawn under the tier names and the nodes, so they are routed around nodes rather than through.
    M = 4   # clearance between a routed line and a node box
    boxes = [(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2) for (cx, cy, w, h, _) in pos.values()]

    def free_spot(lo, hi, blocks, target):
        """Point in [lo, hi] outside every (b0, b1) block, nearest to target; None when no gap is wide enough."""
        ivs, cur = [], lo
        for b0, b1 in sorted(blocks):
            if b0 > cur:
                ivs.append((cur, b0))
            cur = max(cur, b1)
        if cur < hi:
            ivs.append((cur, hi))
        best = None
        for i0, i1 in ivs:
            if i1 - i0 < 6:
                continue
            q = (i0 + i1) / 2 if i1 - i0 < 30 else min(max(target, i0 + 8), i1 - 8)
            if best is None or abs(q - target) < abs(best - target):
                best = q
        return best

    def hseg(p, q):   # cubic leaving and entering horizontally
        mx = (p[0] + q[0]) / 2
        return (p, (mx, p[1]), (mx, q[1]), q)

    def vseg(p, q):   # cubic leaving and entering vertically
        my = (p[1] + q[1]) / 2
        return (p, (p[0], my), (q[0], my), q)

    def straight(p, q):
        return (p, ((2 * p[0] + q[0]) / 3, (2 * p[1] + q[1]) / 3), ((p[0] + 2 * q[0]) / 3, (p[1] + 2 * q[1]) / 3), q)

    def bulge(p0, p3, axis, g):
        """Same-tier edge that swings out to coordinate g on axis (0 = x, 1 = y); the curve's apex reaches g."""
        if axis == 0:
            return (p0, (p0[0] + (g - p0[0]) * 4 / 3, p0[1]), (p3[0] + (g - p3[0]) * 4 / 3, p3[1]), p3)
        return (p0, (p0[0], p0[1] + (g - p0[1]) * 4 / 3), (p3[0], p3[1] + (g - p3[1]) * 4 / 3), p3)

    def through(pts, mid):
        """Segments for a polyline whose odd legs cross a tier band in a straight line."""
        return [straight(pts[i], pts[i + 1]) if i % 2 else mid(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]

    nb = {i: set() for i in pos}   # adjacency for hover dimming
    for e in edges:
        nb[e["from"]].add(e["to"]); nb[e["to"]].add(e["from"])
    eds, curves, lrects, routes, lpos = [], [], [], [], {}
    extra_h, lanes = 0, {}

    def bulged(e):
        return tid[e["from"]] == tid[e["to"]] and (e.get("label") or abs(nord[e["from"]] - nord[e["to"]]) > 1)
    brank = {}
    for t_i in range(T):
        group = sorted((i for i, e in enumerate(edges) if bulged(e) and tid[e["from"]] == t_i),
                       key=lambda i: abs(nord[edges[i]["from"]] - nord[edges[i]["to"]]))
        for k, i in enumerate(group):
            brank[i] = k
    # Wide: apex offset per bulge, shortest span first. A bulge sits outside every earlier bulge whose span overlaps
    # its own, past that bulge's label, so nested lines and labels never cross; disjoint ones stay close to the column.
    boff = {}

    def bulge_x_at(y, ya, yb, off):
        """x (from the node edge) of a wide bulge from ya to yb with apex offset off, where it crosses height y."""
        p0, p3, c = (0, ya), (0, yb), (off + 8) * 4 / 3   # the band edge is 8 past the node edge
        lo_t, hi_t = 0.0, 0.5
        up = (yb > ya)
        if not min(ya, yb) <= y <= max(ya, yb):
            return 0
        for _ in range(30):   # y is monotonic on each half; search the half that holds y
            mid = (lo_t + hi_t) / 2
            yy = _bez(p0, (c, ya), (c, yb), p3, mid)[1]
            lo_t, hi_t = (mid, hi_t) if (yy < y) == up else (lo_t, mid)
        t1 = lo_t
        x1 = _bez(p0, (c, ya), (c, yb), p3, t1)[0]
        lo_t, hi_t = 0.5, 1.0
        for _ in range(30):
            mid = (lo_t + hi_t) / 2
            yy = _bez(p0, (c, ya), (c, yb), p3, mid)[1]
            lo_t, hi_t = (mid, hi_t) if (yy < y) == up else (lo_t, mid)
        x2 = _bez(p0, (c, ya), (c, yb), p3, lo_t)[0]
        return min(x1, x2)

    for t_i in range(T):
        done = []   # (lo, hi, label rect relative to the node edge)
        for i in sorted((i for i in brank if tid[edges[i]["from"]] == t_i), key=lambda i: brank[i]):
            e = edges[i]
            a_, b_ = pos[e["from"]], pos[e["to"]]
            lo, hi = sorted((nord[e["from"]], nord[e["to"]]))
            lw_i = text_w(e["label"], FSE) + 10 if e.get("label") else 0
            dy = min(a_[3] / 2 - 4, a_[3] * (.22 + .1 * brank[i])) * (1 if b_[1] > a_[1] else -1)
            ya, yb = a_[1] + dy, b_[1] - dy
            off = max(14, lw_i / 2 + 10)
            for _ in range(80):   # push out until this curve passes outside every inner label it spans
                if all(bulge_x_at(min(max(ly, min(ya, yb)), max(ya, yb)), ya, yb, off) >= lx1 + 6
                       for (lo2, hi2, (lx1, ly)) in done if lo <= lo2 and hi2 <= hi):
                    break
                off += 4
            boff[i] = off
            if lw_i:
                done.append((lo, hi, (off + 8 + lw_i / 2, (a_[1] + b_[1]) / 2)))

    def self_check(routes, pts_of):
        """Measure the finished drawing and warn about what a reader would misread. The router is a heuristic; this
        check is the guarantee: a line under a node it does not connect, two lines between different nodes running
        together, or a label lying on another line always produces a WARN."""
        for ri, (e, a, b, segs) in enumerate(routes):
            for nid, (cx, cy, w, h, _) in pos.items():
                if nid in (e["from"], e["to"]):
                    continue
                if any(cx - w / 2 + 3 < x < cx + w / 2 - 3 and cy - h / 2 + 3 < y < cy + h / 2 - 3 for x, y in pts_of[ri]):
                    print(f"WARN: architecture edge {e['from']}->{e['to']} runs under node '{nid}' in the {mode} layout; "
                          f"connect neighbouring tiers or put fewer nodes in between", file=sys.stderr)
                    break
        dense = pts_of

        def seg_dist(px, py, ax, ay, bx, by):
            dx, dy = bx - ax, by - ay
            L = dx * dx + dy * dy
            t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
            return math.hypot(px - ax - t * dx, py - ay - t * dy)
        grids = []
        for B in dense:   # 10-unit cells -> indices of the segments touching them
            g = {}
            for k in range(len(B) - 1):
                (x0, y0), (x1, y1) = B[k], B[k + 1]
                for gx in range(int(min(x0, x1) // 10), int(max(x0, x1) // 10) + 1):
                    for gy in range(int(min(y0, y1) // 10), int(max(y0, y1) // 10) + 1):
                        g.setdefault((gx, gy), []).append(k)
            grids.append(g)

        def by_node(pt, nid):   # within 18 units of the node's box
            cx, cy, w, h, _ = pos[nid]
            return abs(pt[0] - cx) <= w / 2 + 18 and abs(pt[1] - cy) <= h / 2 + 18
        for ri in range(len(routes)):
            for rj in range(ri + 1, len(routes)):
                ei, ej = routes[ri][0], routes[rj][0]
                A, B = dense[ri], dense[rj]
                grid = grids[rj]
                near = []
                for x, y in A:
                    gx, gy = int(x // 10), int(y // 10)
                    ks = {k for dx in (-1, 0, 1) for dy in (-1, 0, 1) for k in grid.get((gx + dx, gy + dy), ())}
                    near.append(any(seg_dist(x, y, *B[k], *B[k + 1]) < 5 for k in ks))
                # stretches where the two lines are within a stroke of each other; one that starts or ends at a node
                # both lines share is a fan-out (a line splitting towards two nodes) and reads correctly
                shared = {ei["from"], ei["to"]} & {ej["from"], ej["to"]}
                run, longest, start = 0, 0, None
                for k, flag in enumerate(near + [False]):
                    if flag:
                        if run == 0:
                            start = k
                        run += 1
                        continue
                    if run:
                        touches = any(by_node(A[start], n) or by_node(A[min(k, len(A)) - 1], n) for n in shared)
                        if not touches:
                            seg_len = sum(math.dist(A[m], A[m + 1]) for m in range(start, min(k, len(A) - 1)))
                            longest = max(longest, seg_len)
                    run = 0
                if longest > 24:
                    print(f"WARN: architecture edges {ei['from']}->{ei['to']} and {ej['from']}->{ej['to']} run together "
                          f"in the {mode} layout and may read as connected; reorder nodes or drop an edge", file=sys.stderr)
        for ri, (e, a, b, segs) in enumerate(routes):
            if not e.get("label") or ri not in lpos:
                continue
            x0, x1, y0, y1 = lpos[ri]
            others = [q for rj, ps in enumerate(pts_of) if rj != ri for q in ps]
            if any(x0 + 2 < qx < x1 - 2 and y0 + 2 < qy < y1 - 2 for qx, qy in others):
                print(f"WARN: architecture edge label '{e['label']}' ({e['from']}->{e['to']}) lies on another line in the "
                      f"{mode} layout; shorten the label or drop an edge", file=sys.stderr)

    def no_lane(e, tier_name):
        print(f"WARN: architecture edge {e['from']}->{e['to']} has no clear lane through tier '{tier_name}' in the {mode} "
              f"layout; it may run under a node or along another line. Put fewer nodes in that tier or connect "
              f"neighbouring tiers", file=sys.stderr)
    for ei, e in enumerate(edges):
        a, b = pos[e["from"]], pos[e["to"]]
        if b[4] < a[4]:
            raise SystemExit(f'edge {e["from"]}->{e["to"]} goes backwards; order tiers so edges flow forward')
        same, near = b[4] == a[4], abs(nord[e["from"]] - nord[e["to"]]) == 1
        lwid = text_w(e["label"], FSE) + 10 if e.get("label") else 0
        if mode == "wide":
            if same and near and not e.get("label"):
                down = b[1] > a[1]
                p0 = (a[0], a[1] + (a[3]/2 if down else -a[3]/2)); p3 = (b[0], b[1] - (b[3]/2 if down else -b[3]/2))
                segs = [vseg(p0, p3)]
            elif same:   # swing out beside the column; nested when several share a side
                side = 1 if (a[4] < T - 1 or T == 1) else -1
                k = brank[ei]
                edge_x = band_x[a[4]][1] if side > 0 else band_x[a[4]][0]
                g = edge_x + side * boff[ei]
                # off the side centre (where tier-to-tier lines leave), and apart for each nested bulge
                dy = min(a[3] / 2 - 4, a[3] * (.22 + .1 * k)) * (1 if b[1] > a[1] else -1)
                segs = [bulge((a[0] + side * a[2] / 2, a[1] + dy), (b[0] + side * b[2] / 2, b[1] - dy), 0, g)]
            else:        # cross intermediate columns through free space between their nodes and other such lines
                start, end = (a[0] + a[2] / 2, a[1]), (b[0] - b[2] / 2, b[1])
                pts = [start]
                for ti in range(a[4] + 1, b[4]):
                    x0b, x1b = band_x[ti]
                    target = a[1] + (b[1] - a[1]) * (((x0b + x1b) / 2 - start[0]) / (end[0] - start[0]))
                    blocks = [(cy - h / 2 - M, cy + h / 2 + M) for (cx, cy, w, h, t2) in pos.values() if t2 == ti]
                    blocks += [(v - 7, v + 7) for v in lanes.get(ti, [])]
                    yy = free_spot(ty + 8, H - 8, blocks, target)
                    if yy is None:
                        no_lane(e, tiers[ti]["name"])
                        yy = free_spot(ty + 8, H - 8, blocks[:len(blocks) - len(lanes.get(ti, []))], target)
                        yy = target if yy is None else yy
                    lanes.setdefault(ti, []).append(yy)
                    pts += [(x0b, yy), (x1b, yy)]
                pts.append(end)
                segs = through(pts, hseg)
        else:
            if same and near and not e.get("label"):
                right = b[0] > a[0]
                p0 = (a[0] + (a[2]/2 if right else -a[2]/2), a[1]); p3 = (b[0] - (b[2]/2 if right else -b[2]/2), b[1])
                segs = [hseg(p0, p3)]
            elif same:   # swing below the row into the gap, nested by span; the last row gets extra room
                # Always the gap below the row: the row below never uses it for its own bulges, so they cannot meet.
                level = brank[ei]
                depth = 8 + 7 * level
                if (depth > rowgap - 8) if a[4] < T - 1 else level >= 2:
                    print(f"WARN: architecture tier '{tiers[a[4]]['name']}' has too many same-tier edges for the phone "
                          f"layout; they bunch up and are hard to tell apart. Connect fewer nodes inside the tier",
                          file=sys.stderr)
                side = 1
                g = band_top[a[4]] + bh + depth
                if a[4] == T - 1:
                    extra_h = max(extra_h, depth + 12)
                # off the bottom centre (where row-to-row lines leave), and apart for each nested bulge
                dx = min(a[2] / 2 - 4, a[2] * (.22 + .1 * level)) * (1 if b[0] > a[0] else -1)
                segs = [bulge((a[0] + dx, a[1] + side * a[3] / 2), (b[0] - dx, b[1] + side * b[3] / 2), 1, g)]
            else:        # rows in between: go down through free space between their nodes and other such lines
                start, end = (a[0], a[1] + a[3] / 2), (b[0], b[1] - b[3] / 2)
                pts = [start]
                for ti in range(a[4] + 1, b[4]):
                    y0b = band_top[ti]
                    target = a[0] + (b[0] - a[0]) * (((y0b + bh / 2) - start[1]) / (end[1] - start[1]))
                    blocks = [(cx - w / 2 - M, cx + w / 2 + M) for (cx, cy, w, h, t2) in pos.values() if t2 == ti]
                    blocks += [(v - 7, v + 7) for v in lanes.get(ti, [])]
                    xx = free_spot(6, W - 6, blocks, target)
                    if xx is None:
                        no_lane(e, tiers[ti]["name"])
                        xx = free_spot(6, W - 6, blocks[:len(blocks) - len(lanes.get(ti, []))], target)
                        xx = target if xx is None else xx
                    lanes.setdefault(ti, []).append(xx)
                    pts += [(xx, y0b), (xx, y0b + bh)]
                pts.append(end)
                segs = through(pts, vseg)
        curves.extend(segs)
        routes.append((e, a, b, segs))
    # labels after every route is known, so a label can keep clear of nodes, other labels and other lines
    pts_of = [[_bez(*sg, k / 60) for sg in segs for k in range(61)] for _, _, _, segs in routes]
    for ri, (e, a, b, segs) in enumerate(routes):
        d = f"M{segs[0][0][0]:.1f} {segs[0][0][1]:.1f}" + "".join(
            f" C{p1[0]:.1f} {p1[1]:.1f},{p2[0]:.1f} {p2[1]:.1f},{p3[0]:.1f} {p3[1]:.1f}" for _, p1, p2, p3 in segs)
        lab = ""
        if e.get("label"):
            lw, lh = text_w(e["label"], FSE) + 10, FSE + 8
            others = [q for rj, ps in enumerate(pts_of) if rj != ri for q in ps]

            def fits(pt, strict):
                x0, y0, x1, y1 = pt[0] - lw / 2, pt[1] - lh / 2, pt[0] + lw / 2, pt[1] + lh / 2
                if x0 < 2 or x1 > W - 2 or y0 < 2 or y1 > H + extra_h - 2:
                    return False
                if any(x0 < bx1 - 2 and x1 > bx0 + 2 and y0 < by1 - 2 and y1 > by0 + 2 for bx0, by0, bx1, by1 in boxes):
                    return False
                if any(x0 < l1 and x1 > l0 and y0 < m1 and y1 > m0 for l0, l1, m0, m1 in lrects):
                    return False
                return not strict or not any(x0 - 2 < qx < x1 + 2 and y0 - 2 < qy < y1 + 2 for qx, qy in others)
            cands = []
            if mode != "wide" and b[4] == a[4] + 1:
                # phone rows: prefer the middle of the gap between the two bands (the band top holds the tier name)
                target, lo_t, hi_t = band_top[b[4]] - rowgap / 2, 0.0, 1.0
                for _ in range(30):
                    mid = (lo_t + hi_t) / 2
                    lo_t, hi_t = (mid, hi_t) if _bez(*segs[0], mid)[1] < target else (lo_t, mid)
                cands.append((-1, _bez(*segs[0], lo_t)))
            cands += [(abs((si + k / 40) / len(segs) - .5), _bez(*sg, k / 40)) for si, sg in enumerate(segs) for k in range(41)]
            # also beside the line (touching it), for tight spots where a centred label would cover another line
            sx, sy = lw / 2 + 3, lh / 2 + 2
            cands += [(c + .6, (pt[0] + dx, pt[1] + dy)) for c, pt in list(cands)
                      for dx, dy in ((-sx, 0), (sx, 0), (0, -sy), (0, sy))]
            cands.sort(key=lambda c: c[0])
            spot = next((pt for _, pt in cands if fits(pt, True)), None) or next((pt for _, pt in cands if fits(pt, False)), None)
            if spot is None:
                spot = cands[0][1]
                print(f"WARN: architecture edge label '{e['label']}' ({e['from']}->{e['to']}) has no free spot along its line "
                      f"in the {mode} layout and will overlap a node or another label; shorten or drop it", file=sys.stderr)
            mx, my = spot
            lrects.append((mx - lw / 2, mx + lw / 2, my - lh / 2, my + lh / 2))
            lpos[ri] = lrects[-1]
            lab = (f'<rect class="ar-elabel-bg" x="{mx-lw/2:.1f}" y="{my-lh/2:.1f}" width="{lw:.1f}" height="{lh:.0f}" rx="4"/>'
                   f'<text class="ar-elabel" x="{mx:.1f}" y="{my+FSE*0.35:.1f}">{E(e["label"])}</text>')
        eds.append(f'<g class="ar-ed x-{idx[e["from"]]} x-{idx[e["to"]]}"><path class="ar-base" d="{d}"/>'
                   f'<path class="ar-flow" d="{d}"/>{lab}</g>')
    H += extra_h
    if mode == "wide":
        far = max((x for sg in curves for k in range(13) for x in [_bez(*sg, k / 12)[0]]), default=0)
        if far > W - 4:
            W = far + 8
            if FSS * 529 / W < 12:   # the fonts were sized for the narrower W
                print("WARN: architecture same-tier edges widen the side-by-side layout so text may drop below 12px at "
                      "529px; shorten their labels or connect fewer nodes inside a tier", file=sys.stderr)
    self_check(routes, pts_of)
    if mode != "wide":
        # Tier names sit on the top edge of their band, preferably where no edge passes (they are drawn over the
        # edges with a halo, so a crossing stays readable) and never on an edge label.
        for name, by in names:
            nw = tier_w(name, FSS)
            if nw > W - 24:
                print(f"WARN: architecture tier name '{name}' is too long for the phone layout "
                      f"(~{nw:.1f} of {W - 24} units); shorten it", file=sys.stderr)
                tnames.append(f'<text class="ar-tier" x="12" y="{by+16:.1f}" style="text-anchor:start">{E(name)}</text>')
                continue
            xs = [x for sg in curves for t in [i / 80 for i in range(81)] for x, yy in [_bez(*sg, t)] if by <= yy <= by + 22]
            spans = [(x0l, x1l) for x0l, x1l, y0l, y1l in lrects if y0l < by + 22 and y1l > by]
            cands = [12 + 4 * k for k in range(int((W - 24 - nw) // 4) + 1)] + [W - 12 - nw]
            clear = [x0 for x0 in cands if not any(a < x0 + nw + 4 and b > x0 - 4 for a, b in spans)]
            free = [x0 for x0 in clear if not any(x0 - 6 <= x <= x0 + nw + 6 for x in xs)]
            if not clear:
                print(f"WARN: architecture tier '{name}': edge labels may cover its name on the phone layout "
                      f"(estimated width); if check.mjs reports this tier, shorten the name or the labels", file=sys.stderr)
            x0 = (free or clear or [12])[0]
            if x0 == cands[-1] and x0 > 12:   # right corner: anchor at the end so a wider-than-estimated name grows left
                tnames.append(f'<text class="ar-tier" x="{W-12}" y="{by+16:.1f}" style="text-anchor:end">{E(name)}</text>')
            else:
                tnames.append(f'<text class="ar-tier" x="{x0:.1f}" y="{by+16:.1f}" style="text-anchor:start">{E(name)}</text>')
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
            f'{defs}{"".join(out)}{"".join(eds)}{"".join(tnames)}{"".join(nodes)}</svg>'), list(pos)


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
    m = spec.get("metric")
    if m is not None:
        if not isinstance(m, dict):
            fail("compare: metric must be an object with 'before' and 'after' numbers")
        for k in ("before", "after"):
            v = m.get(k)
            if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 10**9:
                fail(f"compare: metric.{k} must be a whole number from 0 to 1000000000; got {v!r:.40}")
        for k in ("label", "unit"):
            if k in m and not isinstance(m[k], str):
                fail(f"compare: metric.{k} must be a string")
        if "goal" in m:
            g = m["goal"]
            if isinstance(g, bool) or not isinstance(g, int) or not 0 <= g <= 10**9:
                fail(f"compare: metric.goal must be a whole number from 0 to 1000000000; got {g!r:.40}")
        if m.get("better", "lower" if m["after"] < m["before"] else "higher") not in ("lower", "higher"):
            fail("compare: metric.better must be 'lower' or 'higher'")
        if "goal" in m and "better" not in m and m["before"] == m["after"]:
            fail("compare: metric.before equals metric.after, so say which way is better: metric.better 'lower' or 'higher'")

    def metric(key):
        if m is None:
            return ""
        v, unit = m[key], E(m.get("unit", ""))
        if unit[:1].isascii() and unit[:1].isalpha():   # "40 min", but "40分"
            unit = " " + unit
        if key == "before":
            val = f'<b class="cp-mv">{v}{unit}</b>'
        else:   # counts from the before value to the after value when the after panel appears
            val = (f'<b class="cp-mv gold"><span class="cnt" aria-hidden="true" style="--from:{m["before"]};--to:{v}"></span>'
                   f'<span class="sr">{v}</span>{unit}</b>')
        return f'<div class="cp-metric"><span class="cp-ml">{E(m.get("label", ""))}</span>{val}</div>' + gauge(key)

    def gauge(key):
        """Bar with a goal line, like a rhythm game clear gauge: the label says whether the value reached the goal."""
        if m is None or "goal" not in m:
            return ""
        v, g = m[key], m["goal"]
        lower = m.get("better", "lower" if m["after"] < m["before"] else "higher") == "lower"
        ok = v <= g if lower else v >= g
        top = max(m["before"], m["after"], g) * 1.15 or 1
        unit = E(m.get("unit", ""))
        if unit[:1].isascii() and unit[:1].isalpha():
            unit = " " + unit
        glabel = f'{T(spec, "goal")} {g}{m.get("unit", "")}'
        if key == "before" and text_w(glabel, 12) > 90:
            print(f"WARN: compare: the goal label '{glabel}' is long and may run out of the panel on phones; "
                  f"shorten metric.unit", file=sys.stderr)
        st = T(spec, "reached" if ok else "not_reached")
        return (f'<div class="gg{" gg-ok" if ok else ""}"><div class="gg-bar">'
                f'<i class="gg-fill" style="--w:{v / top:.4f};--from-w:{m["before"] / top:.4f}"></i>'
                f'<span class="gg-goal{" gg-l" if g / top < .3 else " gg-r" if g / top > .7 else ""}" style="left:{g / top * 100:.2f}%"><span>{E(T(spec, "goal"))} {g}{unit}</span></span></div>'
                f'<b class="gg-st">{E(st)}</b></div>')

    def panel(side, key, default_tone):
        d = spec[key]
        items = "".join(
            f'<div class="cp-item {E(it.get("tone", default_tone)) if isinstance(it, dict) else default_tone}">'
            f'{E(it["text"] if isinstance(it, dict) else it)}</div>' for it in d.get("items", []))
        head = f'<div class="cp-head"><span class="cp-badge">{E(d.get("label", T(spec, side.lower())))}</span>{E(d.get("title", ""))}</div>'
        gold = f'<span class="gold">{E(d["headline"])}</span>' if d.get("headline") else ""
        msg = f'<div class="cp-msg">{gold}{E(d.get("message", ""))}</div>' if (d.get("message") or gold) else ""
        return head + cutin(d, f"compare {key}") + metric(key) + f'<div class="cp-items">{items}</div>' + msg
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
           f"{s}~.cp-stage .cp-after .cnt{{animation:dd-count 1.4s cubic-bezier(.2,.7,.2,1) .35s both}}"
           f"{s}~.cp-stage .cp-after .ci{{animation:dd-cut .55s cubic-bezier(.2,.8,.2,1) .2s both}}"
           f"#{u} .cp-before .ci{{animation:dd-cut .55s cubic-bezier(.2,.8,.2,1) .2s both}}"
           f"{s}~.cp-stage .cp-after .gg-fill{{animation:dd-fill 1.4s cubic-bezier(.2,.7,.2,1) .35s both}}"
           f"{s}~.cp-stage .cp-after .gg-ok .gg-st{{animation:var(--enter) .55s ease-out 1.6s both}}"
           f"@media print{{#{u} .cp-before,#{u} .cp-after{{display:block}}#{u} .cp-after{{margin-top:10px}}#{u} .cp-top .btn{{display:none}}}}")
    if hush_on(spec, "compare"):   # when "after" shows, the title and the button stop and dim
        css += (f"{s}~.cp-top .ttl,{s}~.cp-top .btn{{{STILL}}}{s}~.cp-top .btn::after{{{FADE}}}"
                + hush_base(f"#{u} .cp-top .btn::after"))
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
    hush = hush_on(spec, "flow")
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
            if hush:
                css.append(f"{sel}~.ttl,{sel}~.fl-track .fl-step:not(.fl-focal) .fl-dot{{{STILL}}}"
                           f"{sel}~.fl-track::before{{{FADE}}}" + hush_base(f"#{u} .fl-track::before"))
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
    tier_count_check(spec, lvls, "ladder")
    stepup = spec.get("stepup", False)
    if not isinstance(stepup, bool):
        fail(f"ladder: stepup must be true or false; got {stepup!r:.40}")
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
                    f'{tier_badge(spec, l, f"ladder level {i+1}")}'
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
        if stepup and i:
            # step-up: the levels below light up one by one from the bottom (bar colour and the ✓ together).
            # 0.6s apart, but the whole run stays within 2s, which wins for 5+ levels below
            gap = min(.6, 2 / i)
            for k in range(i):
                css.append(f"{sel}~.ld-st label[for={u}-l{k}]{{border-color:var(--g);animation:dd-passbar .4s ease-out {k * gap:.2f}s both}}"
                           f"{sel}~.ld-st label[for={u}-l{k}]>.in{{background:var(--gs);animation:dd-passin .4s ease-out {k * gap:.2f}s both}}"
                           f"{sel}~.ld-st label[for={u}-l{k}] .ld-n::after{{content:\" ✓\";color:var(--g);"
                           f"animation:var(--enter) .4s ease-out {k * gap:.2f}s both}}")
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
    spec_lang(spec)   # validate "lang" for every pattern, not only those with default words
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
    lang = "ja" if any(spec_lang(s) == "ja" for s in specs) else "en"
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
            shell = ("body{padding:24px 16px}.dd-wrap{max-width:760px;margin:0 auto 28px}"
                     "@media (max-width:400px){body{padding:16px 8px}}")   # phones: give the diagram the width Zenn gives it
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
