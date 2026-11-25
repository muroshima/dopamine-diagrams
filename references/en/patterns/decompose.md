# Pattern: decompose

A vague statement ("comply with the law", "make it secure", "improve UX") sits in a dashed box with a warning
underneath. One click: the box turns solid and glows, 2–6 concrete pieces stamp in one after another, and a
gold stamp ("Testable!") lands on the corner.

Use it whenever the point is "this sentence cannot be built or tested until it is broken down".

## Spec

```json
{
  "pattern": "decompose",
  "title": "Turn a slogan into requirements",
  "root": {"kicker": "Vague requirement", "text": "Make the system secure"},
  "button": "Break it down ▶",
  "back": "Back",
  "hint": "You can neither build nor test this sentence",
  "done": "Testable!",
  "stepup": ["Hard to break in, easy to trace", "Five checks, each pass or fail"],
  "children": [
    {"tag": "Access", "text": "Admins must sign in with MFA"}
  ],
  "note": "Example content"
}
```

| Field | Required | Notes |
|---|---|---|
| `root.text` | yes | The vague statement |
| `root.kicker` | no | Small label above it ("External requirement", "Slogan") |
| `children[].text` | yes | One concrete, checkable item |
| `children[].tag` | no | Category label. Keep it ≤ 14 ASCII / 7 CJK characters; it must not wrap |
| `button`, `back`, `hint`, `done` | no | Button labels, warning under the button, gold stamp text |
| `title` | no | Omit when the surrounding text already introduces it |
| `stepup` | no | 1–3 strings: `root.text` made a little more concrete each time, the last one testable. On click these appear before the items, one by one 0.6s apart with a "▼", each a little bigger than the last; only the last one stamps and sits in the rainbow border (a step-up). The gold done stamp pops with the last line. Then the items go from their faint preview to full; they start within 2s of the click. Without it the items appear at once, as before |

## Limits

- 2–6 children (build.py stops outside that range). Up to 5 sit in one row on wide screens; 6 becomes 3×2. Phones stack them.
- Print/PDF shows the broken-down state with the stamp, without the button.
- Keep each `stepup` line on one line. Later steps are bigger, so on a 340px phone the last step (rainbow border) fits about 30 Latin or 15–16 CJK characters, the earlier ones about 32 Latin or 17 CJK. build.py warns per step when longer.
- build.py estimates the broken-down height on phones (wrapped lines and item lines included) and warns near 500px. Drop or shorten a step or an item.
- Print/PDF shows the steps at their final size too, with a gap below the root.
