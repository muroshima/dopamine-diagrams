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
  "back_label": "Goal changed? Go back to the top",
  "laps": 3
}
```

| Field | Notes |
|---|---|
| `steps` | 3–6 short labels (≤ 12 ASCII / 7 CJK characters; build.py warns above that and stops outside 3–6) |
| `goal` | Optional. Without it the ring moves up and the diagram is shorter |
| `back_label` | Optional; needs `goal`. Draws the red return line and its legend |
| `center` | Optional gold word and a grey line in the middle of the ring |
| `laps` | Optional lap badges (a pachinko pseudo-sequence). An integer N (2–5) gives "×2" to "×N"; a list of strings (1–4, not empty) gives badges with those words. They stamp in one by one beside the title (pop at lv1), starting at 0.6s and 0.8s apart, and stay. No loop. Each later badge is 2px larger and only the last one has a static glow. They sit outside the ring's SVG, so they never cover the goal, the steps or the centre words. On narrow screens they wrap below the title |

## Limits

- The SVG is 400 units wide and capped at 360px so it fits Zenn's 500px height with a goal and legend.
  Fonts are 16 units, which keeps them ≥ 12px at 340px.
- Gradient-filled text prints as a box in Chrome PDFs; print switches it to solid orange.
- Lap badges share the title's line with a "Laps" label. If the title and the badges do not fit one line at PC width,
  the badges wrap and the diagram can pass Zenn's 500px; build.py warns then. At phone width they add a line. Screen
  readers hear "Laps: lap 2, lap 3". Print drops their background for dark orange text in an outline.
