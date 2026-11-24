#!/usr/bin/env node
// Render checks for dopamine-diagrams output.
//
//   node scripts/check.mjs OUT.md|OUT.html [--target zenn|standalone|slides] [--shots DIR] [--pdf FILE]
//
// Static checks always run. Rendered checks run when playwright-core (npm run setup) and Google Chrome
// are available; otherwise they are skipped with a warning. Exit code 1 if any FAIL.
//
// zenn:       each html-embed block at widths 700/591/561/559/340, light+dark, after every click:
//             height <= 500px, no horizontal overflow, text >= 12px, buttons/tags on one line,
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
const blocks = target === "zenn" ? [...src.matchAll(/```html-embed\n([\s\S]*?)\n```/g)].map((m) => m[1]) : [src];
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
  const out = { h: roots.length ? Math.ceil(Math.max(...roots.map((r) => r.getBoundingClientRect().bottom + window.scrollY))) : document.documentElement.scrollHeight, overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
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

async function runStates(page, where, maxH) {
  const labels = await page.$$("label[for]");
  const check = async (state) => {
    const r = await page.evaluate(PROBE);
    const w = `${where} [${state}]`;
    if (maxH && r.h > maxH) fail(w, `height ${r.h}px > ${maxH}px`);
    if (r.overflowX) fail(w, "horizontal overflow");
    if (r.minFont < 11.95) fail(w, `text ${r.minFont.toFixed(1)}px < 12px at ${r.minFontAt}`);
    if (r.wrapped.length) fail(w, `button/tag wraps: ${[...new Set(r.wrapped)].join(", ")}`);
    if (r.fastLoops.length) fail(w, `animation loop < 0.5s (flashing risk): ${[...new Set(r.fastLoops)].join(", ")}`);
    r.slides.forEach((s, i) => { if (s.over) fail(`${w} slide ${i + 1}`, `content overflows the slide (${s.h}px > 720px)`); });
  };
  await page.waitForTimeout(300);
  await check("initial");
  for (const [i, l] of labels.entries()) {
    try { await l.click({ timeout: 2000 }); } catch { continue; }   // hidden label of an inactive state
    await page.waitForTimeout(800);
    await check(`click ${i + 1}`);
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
        await runStates(page, where, 500);
        if (shots) await page.screenshot({ path: path.join(shots, `block${bi + 1}-${w}-${t}.png`), clip: { x: 0, y: 0, width: w, height: 500 } });
        await page.close();
      }); });
    } else {
      const widths = target === "slides" ? [1280] : [1200, 768, 375];
      for (const w of widths) for (const t of themes) jobs.push(async () => {
        const page = await browser.newPage({ viewport: { width: w, height: target === "slides" ? 720 : 900 } });
        await page.goto(pathToFileURL(path.resolve(file)).href);
        await page.evaluate((th) => document.documentElement.setAttribute("data-theme", th), t);
        await runStates(page, `${path.basename(file)} @${w}px ${t}`, 0);
        if (shots) await page.screenshot({ path: path.join(shots, `${target}-${w}-${t}.png`), fullPage: true });
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
