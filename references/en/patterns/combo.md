# Pattern: combo

Conditions that only count when every one of them is met, which the reader ticks one by one. It borrows the
rhythm game combo (the count grows while you keep hitting, and all of them make a FULL COMBO) and the pachinko
reach (one left says "one more", all of them lock it in).

Clicking a condition turns its number into a ✓ and its dashed border solid. The meter below counts "3/5", and
its bar grows from the left by the conditions met. With one left, a gold "One more!" appears, and the remaining
condition glows with a "Last one" tag. When all are met, the locked box opens and the verdict stamps in inside a
rainbow border.

Use it for release criteria, security requirements, pre-flight checklists: whenever the point is "missing even
one means it does not hold". If the conditions differ in weight, use explorer or ladder; if their order matters,
use flow.

## Spec

```json
{
  "pattern": "combo",
  "title": "Can we ship today? Five conditions",
  "conditions": [
    {"tag": "CI", "text": "Every test on main passes"},
    {"tag": "Review", "text": "Two or more people approved"}
  ],
  "result": {"stamp": "Ship it", "text": "Tag and deploy. If even one is missing, wait until tomorrow"},
  "prompt": "Tick each one you have checked",
  "reach_label": "One more!",
  "full_label": "All set!",
  "note": "Example content"
}
```

| Field | Required | Notes |
|---|---|---|
| `title` | yes | What has to be met for what to hold |
| `conditions[].text` | yes | One checkable condition. Phones stack them in one column, so with 6 keep each to two lines |
| `conditions[].tag` | no | Category label. Keep it ≤ 14 ASCII / 7 CJK characters |
| `result.text` | yes | The verdict once everything is met |
| `result.stamp` | no | Gold stamp on the verdict. Default "Unlocked!" (「確定！」 in Japanese) |
| `prompt` | no | Text beside the meter until only one is left. Default "Tick each one you have checked" |
| `count_label` | no | Word after "3/5". Default "met" |
| `reach_label` | no | Gold text when one is left. Default "One more!" |
| `full_label` | no | Gold text when all are met. Default "All set!" |
| `last_label` | no | Tag on the remaining condition. Default "Last one" |
| `locked_label` | no | Text in the verdict box until all are met. Default "Meet them all to unlock the verdict" |

The default words follow the spec's language, Japanese or English (see SKILL.en.md).

## How it works

- One hidden checkbox per condition, counted with `counter-increment`. The element that shows the number comes
  after the inputs in the document, so it sees the total.
- "One more" is a chain of sibling selectors, one per condition: that condition `:not(:checked)` and every other
  one `:checked`. No `:has()`.
- The bar has one segment per condition; ticked segments get `order:0` and gather on the left, so the bar grows
  from the left whatever the order of clicks.
- The state is shown by the number ("3/5"), words ("One more!", "All set!", "Last one"), marks (number and ✓) and
  the border style (dashed and solid), never by colour alone.
- No spinning reels: a fast spin is a flash in practice.

## Intensity

- lv1: stamps pop, gold text becomes dark amber text (≥ 4.5:1 against the background), the remaining condition gets a static outline, and the
  verdict border is a single accent colour.
- lv2: the remaining condition pulses with neon (1.6s); "One more!" and the verdict stamp glow gold.
- lv3: the pulse and the border spin are faster (1.2s).

## Limits

- 2–6 conditions (build.py stops outside that range). Wide screens put 4 or more in two columns and 3 or fewer in
  one; phones use one column.
- build.py warns when the conditions and the verdict are long enough to pass Zenn's 500px height on phones.
- Print/PDF ticks every condition and shows "N/N", "All set!" and the verdict. On paper, where nothing can be
  clicked, the met state is the most useful one.
