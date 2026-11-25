# Interactions without JavaScript

Every clickable state is a hidden `<input type="radio|checkbox" class="h">` plus a `<label for>` that acts as
the button. CSS reacts with `#id:checked ~ …`.

| Need | Input | Example |
|---|---|---|
| One of N views (tabs, cases) | `radio`, same `name`, first one `checked` | `explorer` |
| Before / after, show / hide | `checkbox` | `decompose` |
| Trace one element on hover | none; `svg:has(.n-x:hover) .edge:not(.x-x)` | `architecture` |

## Rules

1. **Inputs come first** inside `.dd`, before everything they control. `~` only reaches later siblings, so the
   input must be a sibling of (an ancestor of) the controlled elements. Nesting the input inside a panel
   breaks every selector.
2. **Unique ids per diagram.** Slides and pages hold several diagrams; build.py prefixes ids with the diagram id
   (`dd3f2a1c-m0`). Never hand-write ids like `tab1`.
3. **The label text must change too**, not only the colour (e.g. "Break it down ▶" becomes "Back"; in a Japanese spec 「分解する ▶」 becomes 「戻る」).
4. **Keyboard**: hidden inputs stay focusable. Add a `:focus-visible` outline on the matching label
   (build.py does this for every generated state).
5. **Touch**: `:hover` effects are a bonus. Nothing important may depend on hover alone.
6. **Print**: decide which state a PDF should show and add an `@media print` rule for it
   (`decompose` does this).
7. **Zenn**: checkbox and radio are the only inputs that render. `<button>` and text inputs are hidden.
