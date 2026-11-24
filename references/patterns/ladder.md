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
| `levels[].now`, `next` | One sentence each |
| `top_focal` | `false` removes the rainbow border from the top bar |

## Limits

- 3–6 levels. Print/PDF shows the bars and the prompt.
