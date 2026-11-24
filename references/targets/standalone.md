# Target: standalone HTML

```sh
python3 scripts/build.py a.json b.json --target standalone -o page.html --title "Page title"
node scripts/check.mjs page.html --shots .check/page
```

One self-contained page; diagrams are stacked in a 760px column. No external files, so it can be attached,
hosted anywhere, or opened from disk.

- Dark mode follows the OS (`prefers-color-scheme`) unless `<html data-theme="light|dark">` is set.
- No height limit, but keep each diagram under one screen; a diagram that needs scrolling is two diagrams.
- The checker renders at 1200, 768 and 375px in light and dark.
- To embed in another site, copy one `<div class="dd …">` together with both `<style>` blocks.
  The CSS is scoped to `.dd`, and state selectors use the diagram's unique id.
