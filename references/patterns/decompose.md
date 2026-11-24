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

## Limits

- 2–6 children. Up to 5 sit in one row on wide screens; 6 becomes 3×2. Phones stack them.
- Print/PDF shows the broken-down state with the stamp, without the button.
