// Scan a web form, match reviewed answers to its boxes by label, fill them. Never submits.
//
// Safety rules (mirrors apps/api/app/forms/mapper.py):
//   * declarations, consent, signatures, bank / ID numbers and dates are never touched, even if a
//     payload carries a value for them;
//   * passwords, file uploads, captchas and hidden inputs are never touched;
//   * no key presses (Enter submits forms) and no clicks on buttons - fill() / check() / selectOption() only.

export const DECLARATION =
  /declar|\bcertify\b|i confirm|i agree|consent|acknowledg|attest|undertake|terms and conditions|true and correct|privacy policy|ขอรับรอง|คำรับรอง|ยินยอม|รับทราบ|ยอมรับเงื่อนไข|เป็นความจริงทุกประการ/i;
export const NEVER_FILL =
  /signature|sign here|bank|account number|iban|swift|passport|national id|id card|tax id|captcha|password|otp|ลงชื่อ|ลายมือชื่อ|บัญชีธนาคาร|เลขที่บัญชี|เลขประจำตัวประชาชน|บัตรประชาชน|เลขประจำตัวผู้เสียภาษี|หนังสือเดินทาง|รหัสผ่าน/i;
export const DATE_LABEL = /\bdate\b|วันที่|วัน\s*\/?\s*เดือน\s*\/?\s*ปี/i;

const THAI_DIGITS = "๐๑๒๓๔๕๖๗๘๙";
export function norm(s) {
  return String(s ?? "")
    .replace(/[๐-๙]/g, (d) => String(THAI_DIGITS.indexOf(d)))
    .toLowerCase()
    .replace(/[*:：()（）\[\]{}"'“”‘’.,;!?_\-–—/\\|]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

// Dice coefficient on character bigrams: works for Thai (no spaces between words) and English alike.
function bigrams(s) {
  const t = norm(s).replace(/\s/g, "");
  const m = new Map();
  for (let i = 0; i < t.length - 1; i++) m.set(t.slice(i, i + 2), (m.get(t.slice(i, i + 2)) || 0) + 1);
  return { m, n: Math.max(0, t.length - 1) };
}
export function similarity(a, b) {
  const A = bigrams(a), B = bigrams(b);
  if (!A.n || !B.n) return norm(a) && norm(a) === norm(b) ? 1 : 0;
  let hit = 0;
  for (const [k, v] of A.m) hit += Math.min(v, B.m.get(k) || 0);
  return (2 * hit) / (A.n + B.n);
}

// Runs in the page: every fillable control with the best label we can find for it.
export async function scan(page) {
  return page.evaluate(() => {
    const SKIP = new Set(["hidden", "password", "file", "submit", "button", "image", "reset", "search"]);
    const text = (el) => (el ? (el.innerText || el.textContent || "").replace(/\s+/g, " ").trim() : "");
    const labelOf = (el) => {
      if (el.labels && el.labels.length) return text(el.labels[0]);
      if (el.getAttribute("aria-label")) return el.getAttribute("aria-label");
      const by = el.getAttribute("aria-labelledby");
      if (by) return by.split(/\s+/).map((id) => text(document.getElementById(id))).join(" ");
      // table layouts: label in the previous cell
      const td = el.closest("td, th");
      if (td && td.previousElementSibling) return text(td.previousElementSibling);
      // nearest preceding text in the same block
      let n = el;
      for (let i = 0; i < 4 && n; i++) {
        let p = n.previousElementSibling;
        while (p && !text(p)) p = p.previousElementSibling;
        if (p) return text(p).slice(0, 200);
        n = n.parentElement;
      }
      return el.getAttribute("placeholder") || el.getAttribute("title") || el.name || el.id || "";
    };
    const out = [];
    const els = document.querySelectorAll("input, textarea, select");
    els.forEach((el, i) => {
      const type = (el.tagName === "INPUT" ? (el.getAttribute("type") || "text") : el.tagName).toLowerCase();
      if (SKIP.has(type) || el.disabled || el.readOnly) return;
      const r = el.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) return; // not rendered (other wizard step / collapsed)
      const sel = `sci-${i}`;
      el.setAttribute("data-sci", sel);
      const group = type === "checkbox" || type === "radio" ? (el.closest("fieldset")?.querySelector("legend")?.innerText || "") : "";
      out.push({
        sel, type, name: el.name || "", id: el.id || "", label: labelOf(el), group: group.trim(),
        placeholder: el.getAttribute("placeholder") || "", value: type === "checkbox" || type === "radio" ? el.checked : el.value,
        options: el.tagName === "SELECT" ? [...el.options].map((o) => ({ value: o.value, label: o.text.trim() })) : [],
        optionValue: el.value,
      });
    });
    return out;
  });
}

const blocked = (s) => DECLARATION.test(s) || NEVER_FILL.test(s) || DATE_LABEL.test(s);

// Greedy one-to-one assignment, best scores first. Choice controls (checkbox / radio) match on the
// option label for list answers, or on the question label for single yes/no answers.
export function match(controls, fields, minScore = 0.6) {
  const pairs = [];
  for (const f of fields) {
    if (blocked(f.label)) continue;
    for (const c of controls) {
      const ctext = `${c.label} ${c.group}`;
      if (blocked(ctext) || blocked(c.name)) continue;
      let score = 0;
      if (c.name && (c.name === f.id || c.id === f.id)) score = 1.01;
      else if (c.type === "checkbox" || c.type === "radio") {
        const opts = Array.isArray(f.value) ? f.value : typeof f.value === "string" ? [f.value] : [];
        if (opts.length) {
          const groupOk = !c.group || similarity(c.group, f.label) >= minScore - 0.15;
          score = groupOk ? Math.max(...opts.map((o) => similarity(c.label, o))) : 0;
        } else if (typeof f.value === "boolean") score = similarity(c.label, f.label);
      } else score = Math.max(similarity(c.label, f.label), similarity(c.placeholder, f.label) * 0.9);
      if (score >= minScore) pairs.push({ c, f, score });
    }
  }
  pairs.sort((a, b) => b.score - a.score);
  const usedC = new Set(), plan = [], doneF = new Map();
  for (const p of pairs) {
    if (usedC.has(p.c.sel)) continue;
    const multi = Array.isArray(p.f.value) || p.c.type === "radio";
    if (!multi && doneF.has(p.f.id)) continue;
    usedC.add(p.c.sel);
    doneF.set(p.f.id, true);
    plan.push(p);
  }
  const unmatched = fields.filter((f) => !doneF.has(f.id) && !blocked(f.label));
  const withheld = fields.filter((f) => blocked(f.label));
  return { plan, unmatched, withheld };
}

const asText = (v) => (Array.isArray(v) ? v.join(", ") : typeof v === "boolean" ? (v ? "Yes" : "No") : String(v ?? ""));

export async function apply(page, plan) {
  const done = [];
  for (const { c, f, score } of plan) {
    const loc = page.locator(`[data-sci="${c.sel}"]`);
    try {
      if (c.type === "checkbox") {
        const want = typeof f.value === "boolean" ? f.value : true; // list answer: this option was matched
        if (want) await loc.check(); else await loc.uncheck();
      } else if (c.type === "radio") {
        await loc.check();
      } else if (c.type === "select") {
        const v = asText(f.value);
        const opt = c.options.map((o) => ({ ...o, s: Math.max(similarity(o.label, v), similarity(o.value, v)) })).sort((a, b) => b.s - a.s)[0];
        if (!opt || opt.s < 0.6) throw new Error(`no option like "${v}"`);
        await loc.selectOption(opt.value);
      } else if (c.type === "number") {
        const n = asText(f.value).replace(/[^\d.]/g, "");
        if (!n) throw new Error("not a number");
        await loc.fill(n);
      } else {
        await loc.fill(asText(f.value)); // fill() types no Enter: it cannot submit the form
      }
      await loc.evaluate((el) => { el.style.outline = "3px solid #16a34a"; el.title = "Filled by SCI - check before you submit"; });
      done.push({ field: f.label, control: c.label || c.name, score: Math.round(score * 100) / 100, ok: true });
    } catch (e) {
      await loc.evaluate((el) => { el.style.outline = "3px solid #d97706"; }).catch(() => {});
      done.push({ field: f.label, control: c.label || c.name, ok: false, error: String(e.message || e).split("\n")[0] });
    }
  }
  return done;
}
