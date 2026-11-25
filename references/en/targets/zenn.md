# Target: Zenn (`html-embed`)

Zenn renders a fenced code block with the language `html-embed` as a sandboxed figure
(announced 2026-11-11, Beta: https://info.zenn.dev/2026-11-11-html-embed ,
spec: https://zenn.dev/zenn/articles/markdown-guide "HTML/CSS の埋め込み").

```sh
python3 scripts/build.py spec.json --target zenn -o out.md   # one ```html-embed block per spec
node scripts/check.mjs out.md --shots .check/out
```

Paste each block into the article as is.

## Platform limits (as of 2026-11)

| Limit | Value | How this skill handles it |
|---|---|---|
| Allowed content | HTML + `<style>` only; no `<html>/<head>/<body>` | build.py emits exactly that |
| JavaScript | not executed (`<script>`, `onclick`) | all states are `:checked` / `:hover` |
| Links, forms | `<a>` is plain text; form controls hidden except checkbox/radio | buttons are `<label for>` |
| External files | `<link>`, `@import`, web fonts, `<iframe>` not loaded | system fonts, inline SVG |
| Size | 50KB per block | build.py fails above 50KB; one pattern is ~9–18KB |
| Article length | 80,000 characters of body text (embed blocks count) | ~8,500–18,000 characters per block: about 5 per article, 4 if they are all large (see "Article length" below) |
| Height | 500px shown, the rest scrolls inside | checker fails above 500px in any state |
| Dark mode | `<html data-theme="dark">` | `[data-theme="dark"] .dd` swaps tokens; OS preference is ignored on purpose |
| Flashing | banned; Zenn may stop the embed | checker fails loops < 0.5s |

## Article length: ~8,500–18,000 characters per block

A Zenn article body is capped at 80,000 characters, and the contents of `html-embed` blocks count. Most of a
block is CSS, so for each block build.py drops the rules that need a class or id its HTML does not have, and
any `@keyframes` and `@property` nothing uses (inside `@media` and `@supports` too). It does not look at the
pattern; it only matches the output HTML against the CSS, so new classes and effects need no extra work.
Selectors it cannot decide from the HTML (`:not(...)`, attribute selectors, element-only selectors, `:root`)
are kept. standalone and slides do the same with the union of every diagram on the page.

Characters per block for the ten samples (2026-11, counting the ```` ``` ```` lines):

| | Smallest | Largest | Average | All ten |
|---|---|---|---|---|
| Before pruning | 13,561 | 23,411 | 18,710 | 187,100 |
| After pruning | 8,741 (decompose) | 17,897 (explorer) | 13,321 | 133,208 |

**Rule of thumb: about 5 per article.** 80,000 / ~13,000 is 6, but the article text needs room too, so plan
on about 5. If they are all state-heavy diagrams such as combo, explorer and stampcard (~15,000–18,000
characters), stop at 4. For zenn output build.py prints each block's size as `chars`; add up the blocks you use.

## Width: use 560px, not 640px, as the breakpoint

Zenn's prompt suggests `@media (max-width: 640px)` and "about 700px on PC". Measured on a published article
on 2026-11-25 (embed width by browser window width):

| Window | 1440 | 1280 | 1100 | 1024 | 768 | phone |
|---|---|---|---|---|---|---|
| Embed | 706px | 706px | **591px** | **515px** | 649px | ~340px |

Between about 1000px and 1200px Zenn shows a sidebar and the article column shrinks, so ordinary PC windows
give 515–600px. With a 640px breakpoint those readers get the phone layout. This skill switches at 560px: wide
layouts still fit at 561px with text ≥ 12px, and below that (e.g. a 1024px window) the phone layout is the
right choice. The checker renders at 700, 591, 561, 559 and 340px.
Re-measure if Zenn changes its layout: open a published article, run
`[...document.querySelectorAll('iframe[src*="embed.zenn.studio/html"]')].map(f=>f.getBoundingClientRect().width)`
in the console.

## Notes

- Embeds load lazily; a fresh page shows 150px-tall placeholders until scrolled into view.
- Zenn draws a frame and the label "ユーザー作成コンテンツ" around each embed; budget ~30px for it visually.
- Older zenn-cli previews show the block as code. Preview on zenn.dev to see it rendered.
