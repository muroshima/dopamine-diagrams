# Effects

All effects live in `templates/base.css` as classes. Use them only on focal elements (see the emphasis budget
in SKILL.en.md). Intensity level 1 turns most of them into static accents.

| Class | Looks like | Use on | Notes |
|---|---|---|---|
| `.ttl` | Title in a rainbow gradient that slowly flows (5s loop) | Diagram title | lv1: plain bold |
| `.gold` | Gold gradient text with a dark outline; its glow breathes (1.8s) | 1–2 focal words: the answer label, a stamp | Needs ≥ 16px to read; outline keeps contrast on light backgrounds |
| `.rb` + inner `.in` | Rainbow light running around a box (1.8s per turn; lv3 1.2s) | The one box the reader should end on | 6px band. Never two side by side |
| `.neon` / `.chip-on` | Box shadow that brightens and fades (1.6s) | Selected chip, the active gate | lv1: static outline |
| `.tb.t1`-`.t4` | Importance tier badge: colour, line style (dashed, double, solid with glow, rainbow edge), number of stars and a word change together. Static | Severity, risk, how much a level matters (spec `importance`) | lv1: no glow or rainbow on t3/t4 |
| `.shine` | A band of light crossing a button every 3s | Primary button, warning strip | |
| `stamp` keyframes | Drops in from 2.2× with a slight rotation | The answer appearing, "Done!" (「完了！」 in Japanese) | Use via `animation: var(--enter) …` so lv1 swaps it for `pop` |
| `pop` keyframes | Fades up 6px | Secondary content appearing | |
| `.btn` | Orange pill button with a 3D edge and glow | The `<label>` that toggles a state | |

## Safety limits (do not relax)

- **Loop period ≥ 1s for anything that changes brightness**, never a hard on/off. A rotating gradient border
  changes colour at a given pixel once per turn; keep a turn ≥ 1s. The checker fails any infinite loop
  under 0.5s. (Zenn: "激しく点滅する表示" is banned. WCAG 2.3.1: no more than three flashes per second.)
- **Final frame = base style.** Entrance animations must end where the element's normal CSS already is,
  because reduced-motion users and PDFs get no animation at all.
- **Transforms overflow.** `stamp` scales to 2.2×, which widens the page for a moment and shows a horizontal
  scrollbar inside fixed-height embeds. `.dd` has `overflow:hidden`; keep it.
- **Gold on light needs the outline.** Without `-webkit-text-stroke` and the dark drop shadow, gold text
  disappears on the cream background.

## Tokens

`--a` accent (orange), `--b` blue, `--g` green, `--r` red, `--y` yellow, `--v` violet, each with a soft
`--*s` background; `--bg`, `--card`, `--ink`, `--mut`, `--line`; `--glow` for halos. Dark values are injected by
`build.py` (`DARK_VARS`). Change both when re-skinning.
