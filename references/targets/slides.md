# Target: slides (16:9 HTML deck → PDF)

```sh
python3 scripts/build.py title.json flow.json --target slides -o deck.html --title "Deck name"
node scripts/check.mjs deck.html --shots .check/deck --pdf deck.pdf
```

Each spec becomes one `<section class="slide">` of 1280×720. The heading is `slide_title` (falls back to
`title`); the diagram's own title is hidden so it is not repeated. The diagram is zoomed 1.3× and centred.

## Presenting

Open `deck.html` in a browser and present full screen. Clicks work as in the web version, so you can reveal
the breakdown or switch cases live. Scroll or use Page Down between slides.

## PDF

Print to PDF (the checker's `--pdf`, or Chrome: Print → Save as PDF, margins none, background graphics on).

- All motion stops in print. Every element's base style is its final frame, so nothing is half-faded.
- There are no clicks in a PDF. Each pattern decides what to print:
  - `decompose` prints the broken-down state (the useful one).
  - `explorer` prints the first case. Put the most important case first, or make one slide per case.
  - `architecture` prints as is.

## Layout limits

- Content must fit 720px; the checker fails if a slide overflows.
- Keep one diagram per slide. For a dense architecture, split overview and detail into two slides.
- PowerPoint: embed the PDF page as an image, or present the HTML. Editable PPTX export is out of scope.
