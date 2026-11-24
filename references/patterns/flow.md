# Pattern: flow

Numbered steps on a line with light running along it. Clicking a step shows its detail below; the focal step
(the last one by default) shows its detail inside a rainbow border.

Use it for linear processes: release steps, onboarding, an incident timeline.

## Spec

```json
{
  "pattern": "flow",
  "title": "How a change reaches production",
  "steps": [
    {"label": "Branch", "detail": "Work on a feature branch; main stays deployable"},
    {"label": "Ship", "detail": "Merge deploys automatically"}
  ],
  "focal": 4
}
```

| Field | Notes |
|---|---|
| `steps[].label` | ≤ 10 ASCII / 6 CJK characters; it sits under a 44px circle |
| `steps[].detail` | One or two sentences |
| `focal` | Index of the step that matters most; default is the last |

## Limits

- 3–7 steps. With more than 4 steps, phones wrap the steps into rows of three and hide the line.
- Print/PDF shows only the focal step's detail and highlights its circle.
