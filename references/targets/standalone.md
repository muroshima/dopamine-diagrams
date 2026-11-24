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
- To embed in another site, copy the `<div class="dd …">` and the **second** `<style>` block only. The first
  block styles this page (`body` background and padding) and would change the host page. The second block is
  scoped to `.dd` and the diagrams' unique ids; it also contains the rules of the other diagrams on the page,
  which are harmless. For a single diagram, build a page with just that spec.
