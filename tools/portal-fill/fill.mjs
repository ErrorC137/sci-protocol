#!/usr/bin/env node
// sci-portal-fill: type a reviewed SCI application into a funder's web portal for you. Never submits.
//
//   1. In SCI, finish the review screen and download "Portal payload (.json)".
//   2. npx playwright@1.56.1 install chromium   (once)
//   3. node fill.mjs --payload my-app.portal.json --url https://portal.funder.example/apply
//   4. Log in yourself in the browser window, open the form page, press Enter here.
//      Multi-page wizards: go to the next page in the browser, press Enter again.
//   5. Check every green-outlined box, complete the rest, and submit it yourself.
//
// Options: --dry-run (show the matching, fill nothing)  --min-score 0.6  --profile <dir> (browser profile,
// keeps your portal login between runs; default ~/.sci-portal-profile)
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { createInterface } from "node:readline/promises";
import { chromium } from "playwright";
import { apply, match, scan } from "./lib.mjs";

const arg = (k, d) => { const i = process.argv.indexOf(`--${k}`); return i > 0 ? process.argv[i + 1] : d; };
const flag = (k) => process.argv.includes(`--${k}`);

const payload = JSON.parse(readFileSync(arg("payload") ?? die("--payload <file.portal.json> is required"), "utf8"));
if (!payload.reviewed) die("This application has not been reviewed in SCI yet. Finish the review screen first.");
const minScore = Number(arg("min-score", "0.6"));
const ctx = await chromium.launchPersistentContext(arg("profile", join(homedir(), ".sci-portal-profile")), { headless: false });
const page = ctx.pages()[0] ?? (await ctx.newPage());
if (arg("url")) await page.goto(arg("url"));
const rl = createInterface({ input: process.stdin, output: process.stdout });
let remaining = payload.fields;

console.log(`\n${payload.grant}: ${payload.fields.length} reviewed answers. Log in and open the form in the browser.`);
while (remaining.length) {
  const ans = (await rl.question("\nPress Enter to fill this page (q to quit): ")).trim().toLowerCase();
  if (ans === "q") break;
  const target = ctx.pages().at(-1);
  const controls = await scan(target);
  const { plan, unmatched, withheld } = match(controls, remaining, minScore);
  if (flag("dry-run")) {
    console.table(plan.map((p) => ({ answer: p.f.label, box: p.c.label || p.c.name, score: p.score.toFixed(2) })));
  } else {
    const done = await apply(target, plan);
    console.table(done);
    const filled = new Set(plan.filter((p, i) => done[i].ok && !Array.isArray(p.f.value)).map((p) => p.f.id));
    remaining = remaining.filter((f) => !filled.has(f.id));
  }
  if (withheld.length) console.log(`Left for you (declarations, signatures, dates, ID/bank numbers): ${withheld.map((f) => f.label).join("; ")}`);
  console.log(`${controls.length} boxes on this page; ${plan.length} matched; ${unmatched.length} answers not placed yet.`);
}
console.log("\nNothing was submitted. Review the green-outlined boxes, complete the rest, and submit in the browser yourself.");
rl.close();

function die(msg) { console.error(msg); process.exit(1); }
