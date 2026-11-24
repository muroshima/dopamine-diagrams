# Pitfalls (all hit while building the first diagrams)

| Symptom | Cause | Fix (already in the templates) |
|---|---|---|
| PC readers on Zenn get the phone layout | Zenn's embed was 591px wide in a 1100px window; the suggested 640px breakpoint catches it | Breakpoint 560px; checker renders 700/591/561/559/340 |
| A horizontal scrollbar flashes when an answer appears | `stamp` scales to 2.2× and transforms extend the scrollable area | `overflow:hidden` on `.dd` |
| Rainbow border shows gaps or only covers part of a wide box | The rotating pseudo-element was sized with `inset:-60%`; a wide, short box is not covered at every angle | Pseudo-element is a fixed 1400px square centred on the box |
| Gold text turns grey | A pattern rule like `.k span{color:var(--mut)}` beat `.gold{color:transparent}` | `.gold` sets `color:transparent!important` |
| Gold text is unreadable in light mode | Thin gradient text on cream | 1px dark text stroke + dark drop shadow |
| SVG text under 12px on narrow screens | SVG scales down with its container | build.py sizes fonts for the narrowest width and passes them as CSS variables; checker measures with `getScreenCTM()` |
| Focal node loses its rainbow stroke on phones | Gradient defined in the hidden wide SVG; `display:none` SVGs do not paint their gradients | Each SVG defines its own gradient id; stroke is set inline |
| Edge labels sit on top of boxes | Fixed column widths left no room between tiers | Gaps are computed from the widest label between each pair of tiers |
| Tier names crossed by edges in the narrow layout | Names were centred where edges run | Names sit top-left inside a row band |
| Embed height checks always fail | Measuring `documentElement.scrollHeight` returns the viewport height | Measure the bottom of the `.dd` element |
| "Button wraps" false alarm in slides | Slides zoom the diagram 1.3×; the check compared zoomed box height with unzoomed font size | Multiply by the computed `zoom` |
| PDF shows a half-faded or empty state | Animation never runs in print; elements started at opacity 0 | Base style is the final frame; `@media print` disables animation and shows the useful state |
| A slide's heading disappears in the PDF | Print showed every step's detail, so the content overflowed and the centred stage pushed it up; screen checks could not see it | Print shows only the focal state; checker also renders slides with print media |
| Gold text becomes a solid box or gets lines through it in the PDF | Chrome's PDF output mishandles `background-clip:text` and gradient-filled SVG text | `@media print` turns gold and rainbow text into solid colours |
| Dark mode turns on in a light Zenn page | `prefers-color-scheme` followed the OS | zenn target only listens to `data-theme` |
