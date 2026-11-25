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
  "focal": 1
}
```

| Field | Notes |
|---|---|
| `steps[].label` | ≤ 10 ASCII / 6 CJK characters; it sits under a 44px circle |
| `steps[].detail` | One or two sentences |
| `focal` | 0-based index of the step that matters most; default is the last. build.py rejects an index outside the steps |
| `hush` | `true`: when the focal step is picked, the title and the other steps stop moving, and the running line stops and fades over 1s (a pachinko freeze). Text never fades, so it stays as readable. Focus without adding effects. Avoid it with `focal: 0`: that step is picked from the start |
| `steps[].new` | `true` ("NEW") or a short word ("added", "edit"). A small tilted tag on the step's circle. Marks what changed this time, separate from the focal step. Three per diagram at most. Not on architecture boxes (they would collide with edges and labels) |

## Limits

- 2–7 steps (build.py stops outside that range). With more than 4 steps, phones wrap the steps into rows of three and hide the line.
- Print/PDF shows only the focal step's detail and highlights its circle.
