# Effects

All effects live in `templates/base.css` as classes. Use them only on focal elements (see the emphasis budget
in SKILL.en.md). Intensity level 1 turns most of them into static accents.

| Class | Looks like | Use on | Notes |
|---|---|---|---|
| `.ttl` | Title in a rainbow gradient that slowly flows (5s loop) | Diagram title | lv1: plain bold |
| `.gold` | Gold gradient text with a dark outline; its glow breathes (1.8s) | 1–2 focal words: the answer label, a stamp | Needs ≥ 16px to read; outline keeps contrast on light backgrounds. lv1: dark amber text (≥ 4.5:1 in light and dark) |
| `.rb` + inner `.in` | Rainbow light running around a box (1.8s per turn; lv3 1.2s) | The one box the reader should end on | 6px band. Never two side by side |
| `.neon` / `.chip-on` | Box shadow that brightens and fades (1.6s) | Selected chip, the active gate | lv1: static outline. `.chip-on` has a deep orange background so white text stays ≥ 4.5:1 (solid at lv1), and prints as an outlined box |
| `.tb.t1`-`.t4` | Importance tier badge: colour, line style (dashed, double, solid with glow, rainbow edge), number of stars and a word change together. Static | Severity, risk, how much a level matters (spec `importance`) | lv1: no glow or rainbow on t3/t4 |
| `.btn` press | Sinks 3px onto its shadow while pressed (`:active`) | Every button | Same |
| `.cnt` | A number rolling from `--from` to `--to` (an `@property` integer drawn by a counter; 1.4s, easing out). With motion off only the final value shows; without `@property` it switches to the final value once, halfway. The real number sits in `.sr` for screen readers | compare `metric` | Same |
| `.gg` | Gauge with a goal line. Switching to after grows or shrinks it from the before length; when it reaches the goal, "Reached ✓" stamps in. Reaching is also said in words and by the border | compare `metric.goal` | The reached mark pops |
| Approach ring (architecture `focal`) | A ring 1.8x the size shrinks onto the focal box once and fades (a rhythm game tap circle). No loop; invisible when still | architecture focal boxes | Not shown |
| `.ci` | A slanted band slides in once from the left with one line and stays (0.55s, easing out). The text is not slanted | explorer `cases[].cutin`, compare `before.cutin` / `after.cutin` (not with `reveal:"flip"`) | Unslanted accent band. Print: border and text only |
| Hush (spec `hush`) | When the answer appears, the title and the other steps stop moving; only decoration without text (the running line, the light across the button) fades over 1s, and back over 1s. Text never fades | flow's focal step, compare's after | Same. No fading with reduced motion or in print |
| Step-up (ladder `stepup`) | The levels below the picked one light up from the bottom, each with a ✓; shown by the mark, not colour alone. One-way, never on and off | ladder | The mark pops instead of stamping |
| `.nb` | A small tilted tag on what changed (NEW in a gacha 10-pull summary). Pops in once, never glows | flow `steps[].new`, compare `items[].new` | Same. Print: border and text only |
| Lap badges (loop `laps`) | "×2", "×3" badges stamp in one at a time, 0.8s apart, and stay in a row (a pachinko pseudo-sequence). Each later one is larger, and the count is written as text. No loop, so nothing else keeps moving alongside the ring light | loop | The badges pop and have no glow |
| Combo and reach (combo) | A ticked condition's number turns into a ✓, and a CSS counter ("3/5") and a bar grow. With one left, a gold "One more!" appears, the remaining condition pulses with neon and gets a "Last one" tag. All met stamps in the verdict. No spinning reels (a fast spin is a flash) | Conditions that only count when all are met | No pulse (static outline), stamps pop, gold becomes dark amber |
| Stamp card (stampcard) | Only the picked square gets a "Done" stamp, dropping in once with `stamp`. The squares before it turn done without moving (solid border, "Done", ✓), so stamps never land several at once. No loop | stampcard | The stamp pops |
| Flip (explorer `reveal:"flip"`) | A face-down card turns once in .6s (`rotateY`). No loop | Answers readers should guess first | Same. Motion off switches at once; print shows the face only |
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
