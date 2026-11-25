#!/usr/bin/env node
// Render checks for dopamine-diagrams output.
//
//   node scripts/check.mjs OUT.md|OUT.html [--target zenn|standalone|slides] [--shots DIR] [--pdf FILE]
//
// Static checks always run. Rendered checks run when playwright-core (npm run setup) and Google Chrome
// are available; otherwise they are skipped with a warning. Exit code 1 if any FAIL.
//
// zenn:       fences intact; each html-embed block at widths 700/591/561/559/340, light+dark, after every click:
//             height <= 500px, no horizontal overflow (page or inside the diagram), text >= 12px, buttons/tags on one line,
//             no animation loop faster than 0.5s (Zenn bans flashing; WCAG 2.3.1)
// standalone: widths 1200/768/375, light+dark: overflow, text size, loop speed
// slides:     1280x720 per <section class="slide">: content fits the slide, text size, loop speed
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const args = process.argv.slice(2);
const file = args.find((a) => !a.startsWith("--") && !isOptVal(a));
function isOptVal(a) { const i = args.indexOf(a); return i > 0 && ["--target", "--shots", "--pdf"].includes(args[i - 1]); }
const opt = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : undefined; };
if (!file) { console.error("usage: node scripts/check.mjs OUT.md|OUT.html [--target zenn|standalone|slides] [--shots DIR] [--pdf FILE]"); process.exit(2); }
const src = fs.readFileSync(file, "utf8");
const target = opt("--target") || (file.endsWith(".md") ? "zenn" : src.includes('class="slide"') ? "slides" : "standalone");
const shots = opt("--shots");
const pdf = opt("--pdf");
const results = [];
const fail = (where, msg) => results.push(["FAIL", where, msg]);
const warn = (where, msg) => results.push(["WARN", where, msg]);

// ---------------------------------------------------------------- static
const blocks = target === "zenn" ? [...src.matchAll(/```html-embed\r?\n([\s\S]*?)\r?\n```/g)].map((m) => m[1]) : [src];
if (target === "zenn") {   // a stray newline + ``` inside the content closes the fence early and leaks HTML into the article
  const fences = src.split(/\r?\n/).filter((l) => /^```/.test(l)).length;
  if (fences % 2) fail("markdown", `odd number of \`\`\` fence lines (${fences}): a block is broken`);
  const outside = src.replace(/```html-embed\r?\n[\s\S]*?\r?\n```/g, "");
  if (/^\s*</m.test(outside)) fail("markdown", "HTML outside the html-embed blocks (a fence closed early?)");
}
if (target === "zenn" && blocks.length === 0) { console.error("no ```html-embed blocks found"); process.exit(2); }
blocks.forEach((b, i) => {
  const where = target === "zenn" ? `block ${i + 1}` : path.basename(file);
  const bytes = Buffer.byteLength(b);
  if (target === "zenn") {
    if (bytes > 50 * 1024) fail(where, `${bytes} bytes > 50KB`);
    const banned = [[/<script\b/i, "<script>"], [/\son[a-z]+\s*=/i, "inline event handler"], [/<a\b/i, "<a> (links do not navigate)"],
      [/<(form|button|textarea|select|iframe|link)\b/i, "form/iframe/link element"], [/@import/i, "@import"],
      [/<(html|head|body)\b/i, "<html>/<head>/<body>"], [/<input(?![^>]*type="(checkbox|radio)")/i, "text <input>"]];
    for (const [re, name] of banned) if (re.test(b)) fail(where, `contains ${name}`);
    if (!/\[data-theme="?dark"?\]/.test(b)) warn(where, "no [data-theme=dark] rule");
    if (!/@media\s*\(max-width/.test(b)) warn(where, "no narrow-width @media rule");
  } else if (/<script\b/i.test(b)) warn(where, "contains <script> (works here, but not on Zenn)");
  if (!/prefers-reduced-motion/.test(b)) warn(where, "no prefers-reduced-motion rule");
  for (const m of b.matchAll(/font-size:\s*([\d.]+)px/g)) if (parseFloat(m[1]) < 12) { fail(where, `font-size ${m[1]}px in CSS (< 12px)`); break; }
});

// ---------------------------------------------------------------- rendered
let chromium;
try { ({ chromium } = await import(pathToFileURL(path.resolve("node_modules/playwright-core/index.mjs")).href)); }
catch { try { ({ chromium } = await import("playwright-core")); } catch { chromium = null; } }

const PROBE = () => {
  const roots = [...document.querySelectorAll(".dd")];
  // Text cut off by the diagram's overflow:hidden. Measured per text node (Range), so decorative pseudo-elements
  // that are clipped on purpose (rainbow border square, gem rays) do not count.
  const clipped = [];
  const boxOf = (el, root) => {   // nearest ancestor that draws a box (border) or clips; null if a positioned layer sits in between
    for (let a = el; a && a !== root; a = a.parentElement) {
      const c = getComputedStyle(a);
      if (c.position === "absolute" || c.position === "fixed") return null;   // stamps etc. stick out on purpose
      if (a instanceof SVGElement) return null;
      if (c.overflowX !== "visible" || c.overflowY !== "visible" || parseFloat(c.borderTopWidth) > 0 && c.borderTopStyle !== "none" && a !== el) return a;
    }
    return null;
  };
  for (const r of roots) {
    const box = r.getBoundingClientRect();
    const tw = document.createTreeWalker(r, NodeFilter.SHOW_TEXT);
    for (let n = tw.nextNode(); n; n = tw.nextNode()) {
      if (!n.textContent.trim()) continue;
      const rg = document.createRange(); rg.selectNodeContents(n);
      const b = rg.getBoundingClientRect();
      if (!b.width || !b.height) continue;   // hidden state
      if (b.right > box.right + 1 || b.left < box.left - 1) { clipped.push(`${r.id} «${n.textContent.trim().slice(0, 24)}»`); break; }
      const host = boxOf(n.parentElement, r);
      if (host) {
        const hb = host.getBoundingClientRect();
        if (b.bottom > hb.bottom + 1 || b.top < hb.top - 1 || b.right > hb.right + 1 || b.left < hb.left - 1) {
          clipped.push(`${r.id} «${n.textContent.trim().slice(0, 24)}» outside its box`); break;
        }
      }
    }
  }
  // SVG labels must stay inside their own box (architecture / loop nodes, edge labels)
  for (const r of roots) for (const g of r.querySelectorAll(".ar-node, .lp-node")) {
    if (!g.getClientRects().length) continue;
    const rb = g.querySelector("rect").getBoundingClientRect();
    if (!rb.width) continue;
    for (const tx of g.querySelectorAll("text")) {
      const tb = tx.getBoundingClientRect();
      if (tb.left < rb.left - 1 || tb.right > rb.right + 1) { clipped.push(`${r.id} «${tx.textContent.slice(0, 24)}» wider than its node`); break; }
    }
  }
  // Architecture tier names: inside their band, and not under an edge label (user units of the SVG)
  for (const r of roots) for (const svg of r.querySelectorAll("svg.ar-svg")) {
    if (!svg.getClientRects().length) continue;
    const bands = [...svg.querySelectorAll("rect.ar-band")].map((b) => b.getBBox());
    for (const t of svg.querySelectorAll("text.ar-tier")) {
      const tb = t.getBBox();
      const band = bands.find((b) => tb.y >= b.y - 2 && tb.y + tb.height <= b.y + b.height + 2 && tb.x < b.x + b.width && tb.x + tb.width > b.x);
      const name = `${r.id} tier «${t.textContent.slice(0, 24)}»`;
      if (!band || tb.x < band.x - 1 || tb.x + tb.width > band.x + band.width + 1) { clipped.push(`${name} outside its band`); continue; }
      // an edge passing under the name is fine: names are drawn over edges with a halo
      const onLabel = [...svg.querySelectorAll("rect.ar-elabel-bg")].some((lr) => { const l = lr.getBBox();
        return l.x < tb.x + tb.width && l.x + l.width > tb.x && l.y < tb.y + tb.height && l.y + l.height > tb.y; });
      if (onLabel) clipped.push(`${name} under an edge label`);
    }
  }
  // An edge must not run under a node it does not connect (it would read as passing through that node)
  for (const r of roots) for (const svg of r.querySelectorAll("svg.ar-svg")) {
    if (!svg.getClientRects().length) continue;
    const rects = new Map([...svg.querySelectorAll(".ar-node")].map((g) => [[...g.classList].find((c) => /^n-\d+$/.test(c)), g.querySelector("rect").getBBox()]));
    for (const g of svg.querySelectorAll(".ar-ed")) {
      const ends = [...g.classList].filter((c) => /^x-\d+$/.test(c)).map((c) => "n-" + c.slice(2));
      const pth = g.querySelector("path.ar-base"), L = pth.getTotalLength();
      const hit = [...rects].find(([id, b]) => !ends.includes(id) && Array.from({ length: 151 }, (_, i) => pth.getPointAtLength(L * i / 150))
        .some((q) => q.x > b.x + 3 && q.x < b.x + b.width - 3 && q.y > b.y + 3 && q.y < b.y + b.height - 3));
      if (hit) clipped.push(`${r.id} edge ${ends.join("→")} runs under node ${hit[0]}`);
    }
  }
  // Edge labels must not sit under a node box (nodes are drawn after edges and would hide them)
  for (const r of roots) for (const svg of r.querySelectorAll("svg.ar-svg")) {
    if (!svg.getClientRects().length) continue;
    const nodes = [...svg.querySelectorAll(".ar-node rect")].map((n) => n.getBBox());
    for (const lt of svg.querySelectorAll("text.ar-elabel")) {   // the text itself and its background (sized from an estimate)
      const boxes = [lt.getBBox(), lt.previousElementSibling?.getBBox()].filter(Boolean);
      const hit = (l) => nodes.some((n) => l.x < n.x + n.width - 3 && l.x + l.width > n.x + 3 && l.y < n.y + n.height - 3 && l.y + l.height > n.y + 3);
      if (boxes.some(hit))   // 3 SVG units of slack: touching a corner is fine
        clipped.push(`${r.id} edge label «${lt.textContent.slice(0, 24)}» under a node`);
    }
  }
  const out = { clipped, h: roots.length ? Math.ceil(Math.max(...roots.map((r) => r.getBoundingClientRect().bottom + window.scrollY))) : document.documentElement.scrollHeight, overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    minFont: 99, minFontAt: "", wrapped: [], fastLoops: [], slides: [] };
  for (const el of document.querySelectorAll("body *")) {
    const cs = getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden" || !el.getClientRects().length) continue;
    const hasText = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
    if (hasText) {
      let fsz = parseFloat(cs.fontSize);
      if (el instanceof SVGElement && el.getScreenCTM) fsz *= el.getScreenCTM().a;
      const z = parseFloat(getComputedStyle(el.closest(".dd") || el).zoom || 1);
      fsz *= isNaN(z) ? 1 : z;
      if (fsz < out.minFont) { out.minFont = fsz; out.minFontAt = (el.className?.baseVal ?? el.className) + " «" + el.textContent.trim().slice(0, 24) + "»"; }
    }
    if (el.matches(".btn, .dc-tag")) { const zz = parseFloat(getComputedStyle(el.closest(".dd") || el).zoom || 1) || 1; const lh = parseFloat(cs.fontSize) * zz * 2.2; if (el.getBoundingClientRect().height > lh + 16) out.wrapped.push(el.textContent.trim().slice(0, 24)); }
    if (cs.animationName && cs.animationName !== "none") {
      const names = cs.animationName.split(","), durs = cs.animationDuration.split(","), its = cs.animationIterationCount.split(",");
      names.forEach((n, i) => { const d = parseFloat(durs[i % durs.length]); if (its[i % its.length].trim() === "infinite" && d > 0 && d < 0.5) out.fastLoops.push(`${n.trim()} ${d}s`); });
    }
  }
  for (const s of document.querySelectorAll(".slide")) out.slides.push({ over: s.scrollHeight > s.clientHeight + 1 || s.scrollWidth > s.clientWidth + 1, h: s.scrollHeight });
  return out;
};

async function runStates(page, where, maxH, shotFn) {
  const labels = await page.$$("label[for]");
  const check = async (state) => {
    // Finish entrance animations (stamp/pop) first: mid-animation a stamp is scaled up to 2.2x and would read
    // as overflow. Their end state is the base style, so this measures what the reader sees once it settles.
    await page.evaluate(() => document.getAnimations().forEach((a) => {
      if (a.effect?.getComputedTiming().iterations !== Infinity) a.finish(); }));
    const r = await page.evaluate(PROBE);
    const w = `${where} [${state}]`;
    if (maxH && r.h > maxH) fail(w, `height ${r.h}px > ${maxH}px`);
    if (r.overflowX) fail(w, "horizontal overflow");
    if (r.clipped.length) fail(w, `text runs past the diagram or out of its box: ${r.clipped.join(", ")}`);
    if (r.minFont < 11.95) fail(w, `text ${r.minFont.toFixed(1)}px < 12px at ${r.minFontAt}`);
    if (r.wrapped.length) fail(w, `button/tag wraps: ${[...new Set(r.wrapped)].join(", ")}`);
    if (r.fastLoops.length) fail(w, `animation loop < 0.5s (flashing risk): ${[...new Set(r.fastLoops)].join(", ")}`);
    r.slides.forEach((s, i) => { if (s.over) fail(`${w} slide ${i + 1}`, `content overflows the slide (${s.h}px > 720px)`); });
  };
  await page.waitForTimeout(300);
  await check("initial");
  if (shotFn) await shotFn(0);
  for (const [i, l] of labels.entries()) {
    try { await l.click({ timeout: 2000 }); } catch { continue; }   // hidden label of an inactive state
    await page.waitForTimeout(1300);
    await check(`click ${i + 1}`);
    if (shotFn) await shotFn(i + 1);
  }
}

if (!chromium) {
  warn("rendered", "playwright-core not installed (npm run setup) — rendered checks skipped");
} else {
  let browser;
  try { browser = await chromium.launch({ channel: process.env.CHROME_PATH ? undefined : "chrome", executablePath: process.env.CHROME_PATH, headless: true }); }
  catch (e) { warn("rendered", `cannot launch Chrome (${e.message.split("\n")[0]}) — set CHROME_PATH; rendered checks skipped`); }
  if (browser) {
    if (shots) fs.mkdirSync(shots, { recursive: true });
    const jobs = [];
    const themes = ["light", "dark"];
    if (target === "zenn") {
      blocks.forEach((b, bi) => { for (const w of [700, 591, 561, 559, 340]) for (const t of themes) jobs.push(async () => {
        const page = await browser.newPage({ viewport: { width: w, height: 800 } });
        await page.setContent(`<!doctype html><html${t === "dark" ? ' data-theme="dark"' : ""}><head><meta charset="utf-8"><style>html,body{margin:0}</style></head><body>${b}</body></html>`);
        const where = `block ${bi + 1} @${w}px ${t}`;
        const shotFn = shots && (w === 700 || w === 340)   // one screenshot per state at the widest and narrowest width
          ? (k) => page.screenshot({ path: path.join(shots, `block${bi + 1}-${w}-${t}-s${k}.png`), clip: { x: 0, y: 0, width: w, height: 500 } })
          : null;
        await runStates(page, where, 500, shotFn);
        await page.close();
      }); });
    } else {
      const widths = target === "slides" ? [1280] : [1200, 768, 375];
      for (const w of widths) for (const t of themes) jobs.push(async () => {
        const page = await browser.newPage({ viewport: { width: w, height: target === "slides" ? 720 : 900 } });
        await page.goto(pathToFileURL(path.resolve(file)).href);
        await page.evaluate((th) => document.documentElement.setAttribute("data-theme", th), t);
        await runStates(page, `${path.basename(file)} @${w}px ${t}`, 0);
        if (shots) { await page.waitForTimeout(1500); await page.screenshot({ path: path.join(shots, `${target}-${w}-${t}.png`), fullPage: true }); }
        if (target === "slides") {   // the PDF is what people send around: check the print layout too
          await page.emulateMedia({ media: "print" });
          const r = await page.evaluate(PROBE);
          r.slides.forEach((s, i) => { if (s.over) fail(`${path.basename(file)} print ${t} slide ${i + 1}`, `content overflows the slide in print (${s.h}px > 720px)`); });
          await page.emulateMedia({ media: "screen" });
        }
        await page.close();
      });
    }
    for (let i = 0; i < jobs.length; i += 6) await Promise.all(jobs.slice(i, i + 6).map((j) => j()));
    if (pdf && target === "slides") {
      const page = await browser.newPage();
      await page.goto(pathToFileURL(path.resolve(file)).href);
      await page.pdf({ path: pdf, width: "1280px", height: "720px", printBackground: true });
      await page.close();
      console.log(`pdf: ${pdf}`);
    }
    await browser.close();
  }
}

// ---------------------------------------------------------------- report
const uniq = [...new Map(results.map((r) => [r.join("|"), r])).values()];
for (const [lvl, where, msg] of uniq) console.log(`${lvl}  ${where}: ${msg}`);
const nf = uniq.filter((r) => r[0] === "FAIL").length;
console.log(`\n${target}: ${nf} FAIL, ${uniq.length - nf} WARN${chromium ? "" : " (static only)"}`);
process.exit(nf ? 1 : 0);
