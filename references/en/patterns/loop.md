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
  "laps": 3,
  "hush": true
}
```

| Field | Notes |
|---|---|
| `steps` | 3–6 short labels (≤ 12 ASCII / 7 CJK characters; build.py warns above that and stops outside 3–6) |
| `goal` | Optional. Without it the ring moves up and the diagram is shorter |
| `back_label` | Optional; needs `goal`. Draws the red return line and its legend |
| `center` | Optional gold word and a grey line in the middle of the ring |
| `laps` | Optional lap badges (a pachinko pseudo-sequence). An integer N (2–5) gives "×2" to "×N"; a list of strings (1–4, not empty) gives badges with those words. They stamp in one by one beside the title (pop at lv1), starting at 0.6s and 0.8s apart, and stay. No loop. Each later badge is 2px larger and only the last one has a static glow. They sit outside the ring's SVG, so they never cover the goal, the steps or the centre words. On narrow screens they wrap below the title |
| `hush` | Optional. `true`: the answer comes once the steps have lit up round the ring (with `laps`, at the end of the round in which the last badge lands): about n seconds after the page opens, n being the number of steps. At that moment the centre words stamp in (pop at lv1; hidden until then), and the light round the ring, the red return line, the goal glow and the rainbow title stop where they are; then the ring light fades over 1.2s and the background round the centre of the ring darkens a little over 1.2s (the title band is not darkened). The step lights (lv2 and lv3; at lv1 they never light) stop at the end of their round. There is no click, so it stays dark. In a diagram far down the page it is over before the reader gets there, who sees only the final state. The red legend text turns a darker red (`--rt`) so it stays readable on the darker background |

## Limits

- The SVG is 400 units wide and capped at 360px so it fits Zenn's 500px height with a goal and legend.
  Fonts are 16 units, which keeps them ≥ 12px at 340px.
- Gradient-filled text prints as a box in Chrome PDFs; print switches it to solid orange.
- Lap badges share the title's line with a "Laps" label. If the title and the badges do not fit one line at PC width,
  the badges wrap and the diagram can pass Zenn's 500px; build.py warns then. At phone width they add a line. Screen
  readers hear "Laps: lap 2, lap 3". Print drops their background for dark orange text in an outline.
