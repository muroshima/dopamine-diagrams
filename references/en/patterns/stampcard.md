# Pattern: stampcard

Like a mobile game's login bonus: every square is laid out up front, and the last one (the reward) is big, with a
rainbow border and gold text. Clicking a square stamps it "Done", and the squares before it turn done too. The panel
below says what that square is about. Nothing is selected at first, so the panel asks the reader how far along they are.

Use it for rollout plans and learning roadmaps: the steps on the way may be dull, so show up front what you get at the end.

## Spec

```json
{
  "pattern": "stampcard",
  "title": "Test automation: seven weeks to the reward",
  "days": [
    {"label": "Week 1", "name": "Count breakages", "detail": "List three months of incidents and count where things broke"},
    {"label": "Week 2", "name": "Write one test", "detail": "Write a single test for the part that breaks most"},
    {"label": "Week 3", "name": "Ship on Fridays", "detail": "CI tells you first when something breaks, so any day is a release day"}
  ]
}
```

| Field | Notes |
|---|---|
| `days[].name` | Required. The short name inside the square. The last square's `name` is the reward, shown big in gold |
| `days[].label` | The square's heading. Default "Day N" ("N日目" in Japanese). For weeks or stages write "Week 1", "Step 1" and so on |
| `days[].detail` | Shown in the panel below when the square is picked. One or two sentences |
| `current` | 0-based index of the square picked at first, to show progress. Default none (nothing picked, the prompt shows) |
| `prompt` | Panel text while nothing is picked. Default "How far along? Click a square" |
| `done_label` | The word on the stamp. Default "Done" ("済" in Japanese) |
| `reward_label` | The badge on the last square. Default "Reward" ("ごほうび" in Japanese) |

## Motion

- Only the picked square's stamp drops in, with `stamp` (`pop` at intensity 1). The squares before it switch to done
  without moving (solid green border, the "Done" stamp, a ✓ by the heading), so several stamps never land at once.
- Done squares are marked by the word and the ✓, not colour alone. Squares still to come have a dashed border and an
  empty stamp slot.
- The last square has a rainbow border (`.rb`) and 19px gold text. 19px bold counts as large text, so the solid colour
  at intensity 1 is still readable.
- The picked square lifts a little and its border glows (a still outline at intensity 1). The last square keeps
  its rainbow border and does not lift.

## Limits

- 3–8 squares (build.py stops outside that range). Wide screens put up to 6 in one row; 7–8 go in two rows with the
  reward on the right, two rows tall.
- On phones (≤ 560px) the squares wrap into 3 columns (2 for three squares) and the reward fills the rest of its row.
  When only one cell is left, the reward takes the next row at full width.
- `name` gets up to three lines in its square. build.py warns when it will not fit, when an English word is wider than
  the square, and when `label`, `done_label` or `reward_label` will not fit (roughly ≤ 20 ASCII / 12 CJK characters).
- Print/PDF keeps the squares and stamps as they are and shows the last square's (the reward's) detail in the panel:
  what you get at the end is the point of the diagram.
