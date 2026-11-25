# Pattern: explorer

"In situation X, do Y — not Z", for 3–8 situations. The reader picks a situation on the left (chips on
narrow screens); the panel shows the situation, an optional struck-through common mistake, and the answer
stamping in inside a rainbow border.

Use it for decision tables people misremember: error handling, escalation rules, AI fallback behaviour,
on-call runbooks. If there is no "common mistake" worth showing, omit `bad`; the pattern still works.

## Spec

```json
{
  "pattern": "explorer",
  "title": "The API call failed. Now what?",
  "bad_label": "Common mistake",
  "good_label": "Do this instead",
  "cases": [
    {"label": "429 Too Many", "situation": "You are rate limited",
     "bad": "Retry immediately in a loop", "good": "Wait for Retry-After, then retry"}
  ],
  "note": "Source: … / 'Common mistake' is illustrative"
}
```

| Field | Required | Notes |
|---|---|---|
| `cases[].label` | yes | Chip text. ≤ 22 ASCII / 11 CJK characters keeps chips on one line |
| `cases[].situation` | no | Panel heading; defaults to `label` |
| `cases[].bad` | no | Shown struck through. Say in `note` if these are invented |
| `cases[].good` | yes | The answer; one sentence |
| `bad_label`, `good_label` | no | Defaults: "Common mistake", "Do this instead"; 「よくある間違い」「こうする」 when the spec is Japanese (see `lang` in SKILL.en.md) |
| `cases[].importance` | no | Importance 1-4. A badge (stars and a word) appears next to the situation heading. 4 (Critical, rainbow edge) once per diagram. Default words Low / Medium / High / Critical (低・中・高・最重要 in a Japanese spec) |
| `cases[].importance_label` | no | Changes the badge word; one or two words. Use with `importance` |
| `cases[].cutin` | no | A one-line verdict that cuts in on a slanted band when the situation is picked ("Stop here!"). It puts the verdict before the answer. One short line; one or two per diagram. Not with `reveal:"flip"` (it would give the hidden answer away) |
| `reveal` | no | `"flip"` turns the answer into a face-down card: the back shows `cases[].hint` (default "Guess the answer, then flip") and a "Flip ▶" button; pressing it turns the card to the answer. Readers guess before they check, so the answer sticks. Change the buttons with `flip_label`, `unflip_label`. The default (`"stamp"`) stamps the answer in |
| `cases[].hint` | no | The back of the card with `reveal:"flip"`. A short teaser (e.g. "Importance ★★: what do you fix?") |
| `flip_label`, `unflip_label` | no | Words on the flip and hide buttons. Short |

## Limits

- 2–8 cases (build.py stops outside that range); 3 or more reads best. More than 8 does not fit 500px on
  phones; split into two diagrams.
- The first case is what PDF/print shows. Put the most important one first.
- Focal point is the answer box; do not add other gold or rainbow elements.
