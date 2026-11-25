# dopamine-diagrams

English version of `SKILL.md`. The Japanese `SKILL.md` is the one agents load; both say the same thing.
UI defaults (button labels and so on) are Japanese when the spec contains Japanese text, English otherwise.

Diagrams for readers who scroll past anything that does not glow. The look is loud on purpose, but the loudness
is spent on one or two focal points so the diagram still teaches something.

Everything is HTML + CSS. Interactions use hidden checkbox/radio inputs and `:checked`, so the same output runs
where JavaScript is banned (Zenn `html-embed`) and in slides.

## Files and when to read them

| File | Read when |
|---|---|
| `references/en/targets/zenn.md` | Output goes into a Zenn article |
| `references/en/targets/slides.md` | Output goes into a slide deck or PDF |
| `references/en/targets/standalone.md` | Output is a single HTML page (docs, blog, README preview) |
| `references/en/patterns/<pattern>.md` | After you pick a pattern: spec fields, limits, examples |
| `references/en/effects.md` | Before changing any effect or adding a new one (safety limits) |
| `references/en/interactions.md` | Before adding or changing a clickable state |
| `references/en/pitfalls.md` | When something renders wrong, and before writing new CSS |
| `references/en/citation.md` | The diagram summarises someone else's document |
| `templates/base.css`, `templates/parts/*.css` | Editing the look |
| `scripts/build.py` | Always: JSON spec → output |
| `scripts/check.mjs` | Always: render check after every build |

## Workflow (do not skip steps)

1. **Decide the target**: `zenn`, `slides`, or `standalone`. Read its file in `references/en/targets/`.
2. **Decide whether a diagram helps.** If a three-column table says the same thing, use the table.
3. **Pick a pattern** from the table below and read its `references/en/patterns/` file.
4. **Spend the emphasis budget** (next section): choose the one or two focal elements and the intensity level.
5. **Write the spec** as JSON (copy one from `examples/en/`). Content only; no HTML in the spec.
6. **Build**:
   ```sh
   python3 scripts/build.py spec.json --target zenn -o out.md
   python3 scripts/build.py a.json b.json --target slides -o deck.html
   python3 scripts/build.py spec.json --target standalone -o page.html --intensity 3
   ```
   build.py stops with `error: …` when a spec is missing a field or has a value that would break the output, and
   prints `WARN: …` when a label will not fit the phone layout. Fix the spec; do not ignore warnings.
7. **Check** until there are 0 FAIL:
   ```sh
   npm run setup          # once; uses the installed Google Chrome via playwright-core
   node scripts/check.mjs out.md --shots .check/out
   node scripts/check.mjs deck.html --pdf deck.pdf
   ```
   Without Node/Chrome the script still runs the static checks and says the rendered checks were skipped.
   Tell the user when that happened; do not claim the layout was verified.
8. **Look at the screenshots** (`--shots`: for zenn every state at 700px and 340px, light and dark; for the other
   targets the full page after the last click). The checker
   measures overflow, cut-off text (including labels wider than their SVG box), height, text size, wrapping and
   loop speed; it cannot see empty space, edges crossing each other or labels sitting on an edge.
9. If the diagram summarises a source document, apply `references/en/citation.md` to the `note`.

## Patterns

| You want to show… | Pattern | Interaction |
|---|---|---|
| Components and how a request flows between them | `architecture` | Flow animates along edges; hover a box to light its connections |
| "In situation X, do Y (not Z)" for several situations | `explorer` | Pick a situation; the answer stamps in inside a rainbow border |
| A vague statement that must become concrete items | `decompose` | Click to split it; pieces stamp in one by one; a gold "done" stamp lands |
| The habit vs. the better way | `compare` | Click to flip "before" into "after" inside a rainbow border |
| A cycle that repeats (and when to restart from the goal) | `loop` | Light runs round the ring; steps light up in turn |
| Linear steps | `flow` | Light runs along the line; pick a step to read it; the focal step sits in a rainbow border |
| Levels / maturity / staged plans | `ladder` | Pick your level; "now" and a gold "next move" appear |
| The rare case the average hides | `proportion` | 100 dots; one click fades the majority and lights up the one that matters |

Nothing fits? Compose from the `base.css` primitives, then run the checker.

## Emphasis budget

The effects only work when most of the diagram is calm.

- **One or two focal elements per diagram.** Gold text, rainbow border and neon go there and nowhere else.
  In `architecture`, list them in `focal`; in `flow`, set `focal` to one step. In the other patterns the answer
  area (or the top level, or the gem) is already the focal point.
- **Intensity** (`--intensity` or `"intensity"` in the spec):
  - `1` calm: plain title, accent-colour border, soft entrance. For internal docs and conservative decks.
  - `2` standard (default): rainbow title, gold, neon, stamps, rainbow border.
  - `3` full: faster border spin and pulse, glowing flow lines. For a hero diagram or a talk opener.
- Never put two rainbow borders side by side. Never make every node focal.

## Hard rules

- **No flashing.** No animation loop shorter than 0.5s, and no on/off blinking at any speed. Glow must ease in
  and out over ≥1s. Zenn bans flashing embeds and WCAG 2.3.1 caps flashes at 3 per second. The checker fails
  loops under 0.5s.
- **Motion off means fully readable.** Every element's base style is its final state; animations only add the
  entrance. `prefers-reduced-motion` and `@media print` turn all animation off.
- **Text ≥ 12px as rendered**, including SVG text after scaling. `build.py` sizes architecture text for the
  narrowest width; the checker verifies it.
- **Colour is never the only signal.** Every state change also changes text (button label, strikethrough, tag).
- **No JavaScript in the zenn target.** The other targets also avoid it so one spec works everywhere.
- **Do not edit generated output by hand.** Change the spec or the templates and rebuild.

## Extending

New pattern = a renderer function in `scripts/build.py` (registered in `RENDER`), a CSS file in
`templates/parts/`, a reference file in `references/en/patterns/`, and an example spec in `examples/en/`.
Generate state selectors with the diagram's unique id (see `render_explorer`), keep CSS class names prefixed
per pattern, then run the checker on all three targets.
