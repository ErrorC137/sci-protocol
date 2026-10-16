// node --test test.mjs  -  runs headless against a local portal-like form; nothing leaves the machine.
import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { chromium } from "playwright";
import { apply, match, scan, similarity } from "./lib.mjs";

const FORM = `<!doctype html><meta charset="utf-8"><title>ระบบยื่นข้อเสนอโครงการ</title>
<form id="f" onsubmit="window.__submitted = true; event.preventDefault()">
  <label for="t">ชื่อโครงการ (ภาษาไทย) *</label><input id="t" name="proj_title">
  <table><tr><td>ชื่อ-นามสกุล หัวหน้าโครงการ</td><td><input name="pi"></td></tr>
         <tr><td>อีเมล</td><td><input type="email" name="mail"></td></tr></table>
  <input aria-label="หน่วยงาน/สังกัด" name="org">
  <select name="country" aria-label="ประเทศ"><option value="">--</option><option value="TH">ประเทศไทย</option><option value="SG">สิงคโปร์</option></select>
  <label>งบประมาณที่ขอรับการสนับสนุน (บาท)<input type="number" name="budget"></label>
  <fieldset><legend>หมวดค่าใช้จ่าย</legend>
    <label><input type="checkbox" name="c1">ครุภัณฑ์</label>
    <label><input type="checkbox" name="c2">ค่าตอบแทนบุคลากร</label>
    <label><input type="checkbox" name="c3">การผลิตทดลอง (pilot)</label></fieldset>
  <fieldset><legend>ประเภทผู้ยื่น</legend>
    <label><input type="radio" name="kind" value="u">มหาวิทยาลัยหรือสถาบันวิจัย</label>
    <label><input type="radio" name="kind" value="s">สตาร์ทอัพ (นิติบุคคล)</label></fieldset>
  <label for="obj">วัตถุประสงค์ของโครงการ</label><textarea id="obj" name="objectives"></textarea>
  <label for="d">วันที่ยื่นข้อเสนอ</label><input type="date" id="d" name="submitted_on">
  <label for="pw">รหัสผ่าน</label><input type="password" id="pw">
  <label for="up">แนบไฟล์ข้อเสนอ</label><input type="file" id="up">
  <label><input type="checkbox" name="decl">ข้าพเจ้าขอรับรองว่าข้อมูลข้างต้นเป็นความจริงทุกประการ</label>
  <div style="display:none"><label for="s2">ขั้นตอนที่ 2: แผนการดำเนินงาน</label><input id="s2"></div>
  <button type="submit">ส่งข้อเสนอ</button>
</form>`;

const FIELDS = [
  { id: "tbl0:r0:c1", label: "ชื่อโครงการ", type: "text", value: "Upcycled cathode pilot" },
  { id: "tbl0:r1:c1", label: "ชื่อ-นามสกุล หัวหน้าโครงการ", type: "text", value: "Dr. Demo Researcher" },
  { id: "tbl0:r5:c1", label: "อีเมล", type: "email", value: "researcher@example.ac.th" },
  { id: "tbl0:r3:c1", label: "หน่วยงาน/สังกัด", type: "text", value: "Example University" },
  { id: "sdt:country", label: "ประเทศ", type: "text", value: "ประเทศไทย" },
  { id: "p5:b1", label: "งบประมาณที่ขอรับการสนับสนุน (บาท)", type: "number", value: "1,650,000" },
  { id: "uses", label: "หมวดค่าใช้จ่าย", type: "checkbox_group", value: ["ครุภัณฑ์", "การผลิตทดลอง (pilot)"] },
  { id: "applicant_type", label: "ประเภทผู้ยื่น", type: "radio", value: "มหาวิทยาลัยหรือสถาบันวิจัย" },
  { id: "tbl1:r3:c0", label: "วัตถุประสงค์", type: "textarea", value: "เพื่อพัฒนา...\nบรรทัดที่สอง" },
  // Must never be touched even if present in a payload:
  { id: "ff:declaration", label: "ข้าพเจ้าขอรับรองว่าข้อมูลข้างต้นเป็นความจริงทุกประการ", type: "checkbox", value: true },
  { id: "date", label: "วันที่ยื่นข้อเสนอ", type: "date", value: "2026-10-15" },
  { id: "plan", label: "แผนการดำเนินงาน", type: "textarea", value: "step 2 text" },
];

let browser, page;
before(async () => {
  browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  page = await browser.newPage();
  await page.setContent(FORM);
});
after(async () => browser?.close());

test("similarity handles Thai without word spaces", () => {
  assert.ok(similarity("ชื่อโครงการ (ภาษาไทย) *", "ชื่อโครงการ") > 0.6);
  assert.ok(similarity("อีเมล", "ที่อยู่") < 0.3);
});

test("scan sees visible, fillable controls only", async () => {
  const controls = await scan(page);
  const types = controls.map((c) => c.type);
  assert.ok(!types.includes("password") && !types.includes("file"));
  assert.ok(!controls.some((c) => c.label.includes("ขั้นตอนที่ 2")), "hidden wizard step must not be scanned");
  assert.equal(controls.find((c) => c.name === "pi").label, "ชื่อ-นามสกุล หัวหน้าโครงการ"); // table layout
  assert.equal(controls.find((c) => c.name === "c1").group, "หมวดค่าใช้จ่าย");
});

test("fills matched boxes, never declarations, dates or submit", async () => {
  const { plan, unmatched, withheld } = match(await scan(page), FIELDS);
  assert.deepEqual(withheld.map((f) => f.id).sort(), ["date", "ff:declaration"]);
  assert.deepEqual(unmatched.map((f) => f.id), ["plan"]); // its box is on a step not shown yet
  const done = await apply(page, plan);
  assert.ok(done.every((d) => d.ok), JSON.stringify(done.filter((d) => !d.ok)));
  const v = await page.evaluate(() => {
    const f = document.getElementById("f");
    const val = (n) => f.elements[n].value;
    const on = (n) => f.elements[n].checked;
    return { title: val("proj_title"), pi: val("pi"), mail: val("mail"), org: val("org"), country: val("country"),
      budget: val("budget"), c1: on("c1"), c2: on("c2"), c3: on("c3"), kind: f.querySelector("input[name=kind]:checked")?.value,
      obj: val("objectives"), decl: on("decl"), date: val("submitted_on"), submitted: !!window.__submitted };
  });
  assert.deepEqual(v, { title: "Upcycled cathode pilot", pi: "Dr. Demo Researcher", mail: "researcher@example.ac.th",
    org: "Example University", country: "TH", budget: "1650000", c1: true, c2: false, c3: true, kind: "u",
    obj: "เพื่อพัฒนา...\nบรรทัดที่สอง", decl: false, date: "", submitted: false });
});
