# Pattern: architecture

Tiers of boxes (client → edge → backend → data, or any left-to-right story) with dashes of light flowing along
the connections. The focal box gets a rainbow border and a slow glow. Hovering a box dims everything that is
not connected to it (CSS `:has`), which lets readers trace one path without JavaScript.

Two SVGs are generated from the same spec: a wide one (tiers as columns) and a narrow one (tiers as rows).
The 560px media query shows one of them.

## Spec

```json
{
  "pattern": "architecture",
  "title": "Where does a request go?",
  "alt": "Text alternative describing the flow",
  "tiers": [
    {"name": "CLIENT", "nodes": [{"id": "web", "label": "Browser", "sub": "SPA"}]},
    {"name": "BACKEND", "nodes": [{"id": "api", "label": "API"}]}
  ],
  "edges": [{"from": "web", "to": "api", "label": "HTTPS"}],
  "focal": ["api"],
  "note": "Hover a box to trace its connections"
}
```

| Field | Required | Notes |
|---|---|---|
| `tiers[].name` | yes | Short; shown at the top of each column / row |
| `tiers[].nodes[].id` | yes | Unique; used for edges and hover selectors |
| `nodes[].label`, `nodes[].sub` | label yes | `sub` is a second, smaller line |
| `edges[]` | no | `from` must be in the same or an earlier tier (edges flow forward) |
| `edges[].label` | no | Short (≤ 10 characters). Gaps between tiers widen to fit labels |
| `focal` | no | 1 id, at most 2 |
| `alt` | recommended | Becomes the SVG `aria-label` |

## Limits (complexity budget)

- ≤ 4 tiers, ≤ 3 nodes per tier, ≤ 9 nodes in total. More than that is two diagrams.
- Edges between neighbouring tiers only, if they carry labels. Edges that skip a tier are drawn but their label
  may land on a box.
- Two pairs of edges that cross (A→D and B→C) look messy; reorder nodes within a tier, or drop one edge.
- On phones, 3 nodes share 320 units: keep labels ≤ 10 ASCII / 5 CJK characters there.
- Width grows past 600 units when labels need room, and all fonts grow with it so rendered text stays ≥ 12px
  at the narrowest wide layout (561px). The checker confirms it.
