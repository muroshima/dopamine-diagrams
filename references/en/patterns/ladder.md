# Pattern: ladder

Bars that rise left to right; the top one has a rainbow border. Clicking a bar shows "now" and the gold
"next move" for that level. Nothing is selected at first, so the panel asks the reader to place themselves.

Use it for maturity models, levels, staged rollout plans.

## Spec

```json
{
  "pattern": "ladder",
  "title": "How mature is your on-call?",
  "prompt": "Where is your team? Click a step",
  "now_label": "Now",
  "next_label": "Next move",
  "levels": [
    {"name": "Hero", "now": "One person knows how to fix things", "next": "Write down the top five fixes"}
  ]
}
```

| Field | Notes |
|---|---|
| `levels[].name` | Shown on the bar on wide screens (hidden on phones; the panel repeats it) |
| `levels[].short` | Bar label; default `Lv.N` |
| `stepup` | `true`: when a level is picked, the levels below it light up one by one from the bottom with a ✓ (a pachinko step-up). Bar colour and ✓ change together. 0.6s apart, but staying within 2s in total wins, so 5+ levels below are closer together |
| `levels[].importance`, `levels[].importance_label` | Importance 1-4 and its word. A badge appears in the selected level's heading (same as explorer; 4 once). For how much each level matters, not for the maturity itself |
| `levels[].now`, `next` | One sentence each |
| `top_focal` | `false` removes the rainbow border from the top bar |

## Limits

- 2–6 levels (build.py stops outside that range). A name must fit in two lines on its bar; build.py warns when
  it will not (roughly ≤ 24 ASCII / 12 CJK characters with 5 levels).
- Print/PDF shows the bars and the prompt.
