# Pattern: compare

A "before" panel (red badge, items with red edges, a complaint) flips to an "after" panel inside a rainbow
border (green badge, green items, a gold headline) when the reader clicks the button.

Use it for "the habit vs. the better way": copied approval flows, manual vs. automated steps, old vs. new
architecture in words. For two *diagrams* side by side, use two specs instead.

## Spec

```json
{
  "pattern": "compare",
  "title": "Does every request need sign-off?",
  "button": "Question the habit ▶",
  "back": "Back",
  "before": {"label": "Before", "title": "Everything waits for the manager",
             "items": ["Routine renewal", "Small office purchase"], "message": "Why it hurts"},
  "after":  {"label": "After", "title": "Route by risk",
             "items": [{"text": "Routine renewal → automatic", "tone": "good"},
                       {"text": "New vendor → manager", "tone": "neutral"}],
             "headline": "Half the queue gone", "message": "What changed"}
}
```

| Field | Notes |
|---|---|
| `before`, `after` | `label` (badge), `title`, `items`, `message`; `after.headline` is shown in gold |
| `items[]` | A string, or `{"text", "tone"}` with tone `bad`, `good` or `neutral`. Defaults: before `bad`, after `good` |
| `metric` | Optional. `{"label", "before", "after", "unit"}`, whole numbers from 0. The before panel shows the before value; switching to after rolls the number from before to after. One focal number only |
| `metric.goal`, `metric.better` | Optional. With a goal, both panels show a gauge with a goal line, and say "Reached ✓" or "Not yet" in words and with the border. better is `lower` or `higher`; by default it follows the direction from before to after (required when before equals after). Keep the goal label ("Goal 15") short |
| `before.cutin`, `after.cutin` | Optional. A one-line verdict on a slanted band when the panel appears; usually on `after` only |

## Limits

- 2–6 items per side; keep each under ~30 characters so two fit per row on phones.
- Print/PDF shows both panels stacked, without the button.
