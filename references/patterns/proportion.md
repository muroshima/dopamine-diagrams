# Pattern: proportion

100 dots coloured by group, with a legend and what a summary would conclude ("fix the big groups first").
One click fades every dot except one, which turns gold with rotating rays, and the side text explains why that
single item matters more than the majority.

Use it for "the average hides the important case": rare but critical tickets, minority users, outliers.

## Spec

```json
{
  "pattern": "proportion",
  "title": "100 support tickets, summarised by AI",
  "button": "Read them yourself ▶",
  "back": "Back to the summary",
  "groups": [{"label": "Password reset", "count": 40}, {"label": "Billing question", "count": 32}, {"label": "Other", "count": 27}],
  "say": "AI: \"Fix password reset and billing first\"",
  "say_sub": "Counting the majority is what AI does well",
  "gem": {"title": "The one that matters", "text": "One ticket filed under \"Other\" was the first sign of a data leak", "sub": "…"},
  "note": "Counts are illustrative"
}
```

| Field | Notes |
|---|---|
| `groups[].count` | Must add up to **99**; the 100th dot is the gem, hidden in the last group (legend counts it there) |
| `groups[].color` | Optional CSS colour; defaults to blue, teal, violet, amber, and grey for the last group |
| `gem_at` | Optional dot index 0–99; default is the middle of the last group |

## Limits

- Say in `note` when the counts are invented.
- Print/PDF shows the revealed state (faded dots, gold dot, explanation).
