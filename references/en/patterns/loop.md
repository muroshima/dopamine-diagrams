# Pattern: loop

Steps on a ring with dashes of light running round it; each step lights up in turn. Optionally a goal box
sits above the ring with an arrow into the first step, and a red dashed line from the last step back up to
the goal ("if the goal itself changes, go back to the top").

Use it for cycles: build–measure–learn, incident review, requirement updates after launch.

## Spec

```json
{
  "pattern": "loop",
  "title": "Requirements keep moving after launch",
  "goal": "Goal",
  "steps": ["Elicit", "Specify", "Build", "Operate", "Feedback"],
  "center": {"text": "Again", "sub": "change is the default"},
  "back_label": "Goal changed? Go back to the top"
}
```

| Field | Notes |
|---|---|
| `steps` | 3–6 short labels (≤ 12 ASCII / 7 CJK characters; build.py warns above that and stops outside 3–6) |
| `goal` | Optional. Without it the ring moves up and the diagram is shorter |
| `back_label` | Optional; needs `goal`. Draws the red return line and its legend |
| `center` | Optional gold word and a grey line in the middle of the ring |

## Limits

- The SVG is 400 units wide and capped at 360px so it fits Zenn's 500px height with a goal and legend.
  Fonts are 16 units, which keeps them ≥ 12px at 340px.
- Gradient-filled text prints as a box in Chrome PDFs; print switches it to solid orange.
