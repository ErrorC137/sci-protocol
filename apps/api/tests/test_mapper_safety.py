"""Safety rules of the form mapper: when unsure, red. A wrong green value is the worst failure, because green
reads as 'from your profile' on the review screen."""

import json
import re

import pytest

from app.forms import mapper
from app.forms.mapper import DECLARATION, PLACEHOLDER, PLACEHOLDER_TH, has_placeholder, map_fields
from app.models.schemas import Applicant, FieldSpec, Grant, ProjectProfile

PROFILE = dict(
    nickname="Agri-waste materials pilot", fields=["materials", "agritech"],
    subdomains=["Biomass valorization", "Construction materials", "Agri-waste utilization"], trl=4,
    evidence=["lab_result", "prototype"], applicant_type="university", country="TH",
    funding_min_usd=5000, funding_max_usd=50000, uses_of_funds=["pilot_run", "equipment", "certification"], months_to_milestone=9,
)
APPLICANT = Applicant(name="Dr. Demo Researcher", email="researcher@example.ac.th", phone="+66 2 000 0000",
                      organization="Example University", position="Assistant Professor", address="Bangkok, Thailand")
FIELDS_TH = "วัสดุศาสตร์, เทคโนโลยีการเกษตร"
BUDGET_HINT = "หมวดค่าใช้จ่าย: ☐ ครุภัณฑ์ ☐ วัสดุ ☐ การทดสอบและรับรองมาตรฐาน"


def grant(**kw) -> Grant:
    return Grant(id="g", title="Test grant", source="test", source_ref="test", **kw)


def run(*specs: FieldSpec, g: Grant | None = None, profile: dict | None = None) -> dict:
    filled, _ = map_fields(list(specs), ProjectProfile(**(profile or PROFILE)), APPLICANT, g or grant())
    return {f.field_id: f for f in filled}


def fill(label: str, type: str = "text", g: Grant | None = None, profile: dict | None = None, **kw):
    return run(FieldSpec(id="f", label=label, type=type, **kw), g=g, profile=profile)["f"]


def is_red(f) -> bool:
    return f.status == "red" and f.value in (None, "", []) and f.source == "none"


def _fake_model(monkeypatch, specs=()) -> list:
    """A model that answers every field it is sent (and any listed in specs, asked or not)."""
    sent: list = []

    def structured(**kw):
        asked = json.loads(kw["user"].split("\n\n", 1)[1])["fields"]
        sent.extend(asked)
        answers = [(f["id"], f["type"]) for f in asked] + [(s.id, s.type) for s in specs]
        return {"fields": [{"field_id": i, "action": "fill", "value": "true" if t == "checkbox" else "1,000", "rationale": "guess"}
                           for i, t in answers]}

    monkeypatch.setattr(mapper.llm, "enabled", lambda: True)
    monkeypatch.setattr(mapper.llm, "structured", structured)
    return sent


@pytest.fixture()
def eager_model(monkeypatch):
    """Red must come from the safety rules, not from nothing else matching: anything sent to this model gets filled."""
    return _fake_model(monkeypatch)


# 1. Declarations -------------------------------------------------------------------------------

DECLARATIONS = [
    "ข้าพเจ้าขอรับรองว่าข้อมูลข้างต้นถูกต้องและครบถ้วน",
    "ข้าพเจ้ารับรองว่าข้อความข้างต้นเป็นความจริง",
    "ข้าพเจ้ายืนยันว่าได้แนบเอกสารครบถ้วนแล้ว",
    "ข้าพเจ้าตกลงปฏิบัติตามประกาศของแหล่งทุน",
    "ข้าพเจ้าได้อ่านและเข้าใจหลักเกณฑ์การขอรับทุนแล้ว",
    "ข้อมูลทั้งหมดถูกต้องครบถ้วน",
    "ข้อความข้างต้นเป็นความจริง",
    "I certify that the information above is correct",
    "We declare that the budget is accurate",
    "I confirm that I am eligible to apply",
    "We agree to share the results publicly",
    "I have read the call guidelines",
    "I/We confirm the details above",
]


@pytest.mark.parametrize("ftype", ["checkbox", "text"])
@pytest.mark.parametrize("label", DECLARATIONS)
def test_declarations_are_red_and_never_ticked(label, ftype, eager_model):
    f = fill(label, ftype)
    assert is_red(f) and f.value is not True and "Declarations" in f.rationale


def test_declaration_in_hint_is_red(eager_model):
    assert is_red(fill("ยอมรับ", "checkbox", hint="ข้าพเจ้าได้อ่านและเข้าใจเงื่อนไขการรับทุนแล้ว ☐ ยอมรับ"))
    assert is_red(fill("Yes", "checkbox", hint="I agree to the terms of the award"))


@pytest.mark.parametrize("text", ["การทดสอบและรับรองมาตรฐาน", "การขอรับรองมาตรฐาน มอก.", "certified reference material",
                                  "Certification body", "Testing & certification"])
def test_technical_certification_is_not_a_declaration(text):
    assert not DECLARATION.search(text)


def test_certification_use_of_funds_is_still_ticked():
    f = fill("การทดสอบและรับรองมาตรฐาน", "checkbox", hint=BUDGET_HINT)
    assert f.value is True and f.status == "green"


# 2. Bank and identity vocabulary ---------------------------------------------------------------

NEVER = [
    "ธนาคาร", "ชื่อธนาคาร", "ชื่อบัญชี", "หมายเลขบัญชี", "เลขบัญชี", "เลขที่บัญชี", "สถาบันการเงิน", "หมายเลขพร้อมเพย์",
    "บัตรประจำตัวประชาชน", "เลขประจำตัวประชาชน", "เลขประจำตัวผู้เสียภาษี", "เลขที่หนังสือเดินทาง", "ผู้มีอำนาจลงนาม",
    "ลายมือชื่อ", "ลงชื่อ", "ตราประทับ", "Bank name", "Account number", "Account name", "IBAN", "SWIFT code",
    "Routing number", "Passport number", "National ID", "Tax ID", "Employer/Taxpayer Identification Number (EIN/TIN)",
    "Signature", "Authorised signatory", "Company stamp", "Official seal",
]


@pytest.mark.parametrize("label", NEVER)
def test_bank_identity_and_signature_fields_are_red(label, eager_model):
    f = fill(label)
    assert is_red(f) and f.rationale == "Only you can provide this"


def test_branch_is_red_only_next_to_a_bank(eager_model):
    assert is_red(fill("สาขา", hint="ธนาคาร … สาขา … เลขที่บัญชี …"))
    fs = run(FieldSpec(id="bank", label="ชื่อธนาคาร"), FieldSpec(id="branch", label="สาขา"))  # no hints: the neighbour decides
    assert is_red(fs["branch"])
    assert fill("สาขา").value == FIELDS_TH and fill("สาขาการวิจัย").status == "green"


# 3. Dates --------------------------------------------------------------------------------------

@pytest.mark.parametrize("label", ["พ.ศ.", "ปี พ.ศ. ที่เริ่มโครงการ", "วัน/เดือน/ปี", "วันที่ยื่นข้อเสนอ", "วันเดือนปีเกิด",
                                   "วัน เดือน ปี", "ปีงบประมาณ", "Start date", "DD/MM/YYYY"])
def test_date_labels_are_red(label, eager_model):
    assert is_red(fill(label))


def test_date_type_is_red_whatever_the_label(eager_model):
    assert is_red(fill("ชื่อโครงการ", "date"))  # would otherwise be the project title


# 4. Hint context -------------------------------------------------------------------------------

@pytest.mark.parametrize("label,hint", [
    ("ชื่อ", "ความเห็นของผู้บังคับบัญชา ชื่อ …"),
    ("ชื่อ", "ชื่อ … | prev: ความเห็นของหัวหน้าหน่วยงาน"),
    ("ชื่อ", "ผู้อนุมัติ ชื่อ …"),
    ("ชื่อ", "ผู้รับรอง ชื่อ …"),
    ("ชื่อ", "ชื่อบัญชีธนาคาร …"),
    ("ชื่อ", "ลายมือชื่อ … ( ชื่อ … )"),
    ("Name", "Supervisor"),
    ("Name", "Head of department endorsement"),
    ("Name", "Approver"),
    ("Name", "Referee 1"),
    ("Name", "Bank account holder"),
    ("Name", "Signature block"),
    ("Email", "Supervisor contact details"),
    ("หน่วยงาน", "ข้อมูลผู้บังคับบัญชา"),
    ("Supervisor's institution", None),
    ("ชื่อหัวหน้าหน่วยงาน", None),
    ("Partner organisation name", None),
])
def test_context_about_someone_else_makes_a_harmless_label_red(label, hint, eager_model):
    assert is_red(fill(label, hint=hint))


def test_harmless_name_without_context_is_still_filled():
    assert fill("ชื่อ").value == APPLICANT.name and fill("Name").status == "green"
    assert fill("ชื่อโครงการ", hint="ชื่อโครงการ … | prev: วันที่ยื่น …").status == "green"  # a date in the previous paragraph is another field's


# 5. Empty labels -------------------------------------------------------------------------------

@pytest.mark.parametrize("label", ["", "   ", "........", "(2)", ":"])
def test_empty_label_is_red_even_when_the_id_looks_fillable(label, eager_model):
    assert is_red(run(FieldSpec(id="email", label=label))["email"])
    assert is_red(run(FieldSpec(id="use_equipment", label=label, type="checkbox"))["use_equipment"])


# 6. Money --------------------------------------------------------------------------------------

@pytest.mark.parametrize("label,hint,figure,ph", [
    ("งบประมาณที่ขอรับการสนับสนุน", None, "1,650,000", PLACEHOLDER_TH),  # a Thai label with no currency means baht
    ("งบประมาณที่ขอ (บาท)", None, "1,650,000", PLACEHOLDER_TH),
    ("งบประมาณที่ขอ (ล้านบาท)", None, "1.65", PLACEHOLDER_TH),
    ("Amount requested (THB)", None, "1,650,000", PLACEHOLDER),
    ("Amount requested", "in Thai baht (฿)", "1,650,000", PLACEHOLDER),
    ("Amount requested (€)", None, "43,103", PLACEHOLDER),
    ("Amount requested (EUR)", None, "43,103", PLACEHOLDER),
    ("Amount requested (S$)", None, "65,000", PLACEHOLDER),
    ("Amount requested (thb)", None, "1,650,000", PLACEHOLDER),
    ("งบประมาณที่ขอ (ไม่เกิน 2 ล้านบาท)", None, "1,650,000", PLACEHOLDER_TH),  # a cap, not a unit of millions
])
def test_non_usd_amount_is_a_flagged_estimate_never_green(label, hint, figure, ph):
    f = fill(label, "number", hint=hint)
    assert f.status == "amber" and f.value.startswith(figure + " ") and ph in f.value and "estimate" in f.rationale


def test_usd_amount_is_green_only_when_the_form_says_usd():
    for label in ("Amount requested (USD)", "Funding goal ($)", "Funding goal (US$)"):
        f = fill(label, "number")
        assert f.value == "50,000" and f.status == "green", label
    assert fill("Amount requested", "number").status == "amber"  # no currency anywhere: not assumed to be USD
    eur = fill("Amount requested", "number", g=grant(currency="EUR"))
    assert eur.status == "amber" and PLACEHOLDER in eur.value
    assert is_red(fill("Amount (USD) / equivalent in THB", "number"))  # two currencies
    assert is_red(fill("Amount requested (KHR)", "number"))  # no exchange rate


def test_millions_field_never_gets_a_full_figure():
    th = fill("งบประมาณที่ขอ (ล้านบาท)", "number")
    assert th.status == "amber" and th.value.startswith("1.65 ") and "1,650,000" not in th.value
    usd = fill("Amount requested (USD million)", "number")
    assert usd.status == "amber" and usd.value == "0.05"
    g = grant(amount_max_usd=9090.91, currency="THB", raw={"amount_original": {"min": 0, "max": 300000, "currency": "THB"}})
    capped = fill("งบประมาณที่ขอ (ล้านบาท)", "number", g=g)
    assert capped.status == "amber" and capped.value == "0.3"


@pytest.mark.parametrize("label", ["งบประมาณ (%)", "สัดส่วนงบประมาณ (ร้อยละ)", "Budget share (%)", "ระยะเวลา (%)",
                                   "Amount requested (percent of total)"])
def test_percentage_field_never_gets_an_amount(label, eager_model):
    assert is_red(fill(label, "number"))


def test_grant_cap_in_its_own_currency_is_amber():
    g = grant(amount_max_usd=9090.91, currency="THB", raw={"amount_original": {"min": 0, "max": 300000, "currency": "THB"}})
    f = fill("Amount requested (THB)", "number", g=g)
    assert f.value == "300,000" and f.status == "amber"


@pytest.mark.parametrize("label", ["ค่าตอบแทน (บาท)", "ค่าจ้าง", "ค่าวัสดุ", "ค่าใช้สอย", "ค่าครุภัณฑ์", "ค่าเดินทาง",
                                   "Salaries (USD)", "Materials cost", "Equipment budget", "Travel (USD)",
                                   "Overhead amount", "Indirect costs (USD)"])
def test_budget_category_lines_are_red(label, eager_model):
    assert is_red(fill(label))


@pytest.mark.parametrize("label", ["Role in project", "ตำแหน่งในโครงการ", "หน้าที่ในโครงการ", "Website address",
                                   "Project duration (years)", "Duration (weeks)", "ระยะเวลา (ปี)", "Country of birth",
                                   "Previous employer", "หน่วยงานที่ให้ทุน"])
def test_other_values_the_profile_cannot_answer_are_red(label, eager_model):
    assert is_red(fill(label))


# 7. Table rows and track record ------------------------------------------------------------------

TEAM = "[table row] ส่วนที่ 3 คณะผู้วิจัย | ชื่อ-สกุล / ตำแหน่ง / หน่วยงาน / สาขาที่เชี่ยวชาญ / สัดส่วน (%)"


def test_team_table_row_gets_only_own_details_and_only_as_amber(eager_model):
    fs = run(*(FieldSpec(id=i, label=l, hint=TEAM) for i, l in
               [("n", "ชื่อ-สกุล"), ("p", "ตำแหน่ง"), ("o", "หน่วยงาน"), ("f", "สาขาที่เชี่ยวชาญ"), ("pct", "สัดส่วน (%)")]))
    assert (fs["n"].value, fs["p"].value, fs["o"].value) == (APPLICANT.name, APPLICANT.position, APPLICANT.organization)
    assert all(fs[i].status == "amber" for i in "npo")
    assert is_red(fs["f"]) and is_red(fs["pct"])  # profile fields are not a team member's expertise
    en = run(FieldSpec(id="n", label="Name", hint="[table row] Team members | Name / Role"),
             FieldSpec(id="r", label="Role", hint="[table row] Team members | Name / Role"))
    assert en["n"].status == "amber" and is_red(en["r"])


@pytest.mark.parametrize("label,hint", [
    ("รายการ", "[table row] งบประมาณ | รายการ / จำนวนเงิน (บาท)"),
    ("จำนวนเงิน (บาท)", "[table row] งบประมาณ | รายการ / จำนวนเงิน (บาท)"),
    ("กิจกรรม", "[table row] แผนการดำเนินงาน | กิจกรรม / ระยะเวลา"),
    ("ประเทศ", "[table row] พื้นที่ดำเนินการ | ประเทศ / จังหวัด"),
])
def test_other_table_rows_are_red(label, hint, eager_model):
    assert is_red(fill(label, hint=hint))


@pytest.mark.parametrize("label,hint", [
    ("ผลงานตีพิมพ์", None), ("ผลงานวิจัยที่ผ่านมา", None), ("ประวัติการศึกษา", None), ("ทุนที่เคยได้รับ", None),
    ("Publications", None), ("Track record", None), ("Previous grants", None),
    ("ชื่อเรื่อง", "ชื่อเรื่อง … | prev: ผลงานตีพิมพ์ที่เกี่ยวข้อง"),  # a paper's title, not the project title
])
def test_history_and_publications_are_red(label, hint, eager_model):
    assert is_red(fill(label, hint=hint))
    assert is_red(fill(label, "textarea", hint=hint, narrative=True))  # not even a scaffold


# 8. Checkbox matching --------------------------------------------------------------------------

def test_checkbox_needs_whole_words_not_substrings():
    assert fill("ค่าซ่อมแซมครุภัณฑ์", "checkbox", hint=BUDGET_HINT).value is not True  # repair costs, not equipment
    assert fill("ครุภัณฑ์คอมพิวเตอร์", "checkbox", hint=BUDGET_HINT).value is not True
    assert fill("Lab results reproduced by a third party", "checkbox").value is not True
    for label in ("ครุภัณฑ์", "ครุภัณฑ์และอุปกรณ์", "ครุภัณฑ์ (เครื่องมือวิทยาศาสตร์)", "ครุภัณฑ์/อุปกรณ์"):
        assert fill(label, "checkbox", hint=BUDGET_HINT).value is True, label
    mats = dict(PROFILE, uses_of_funds=["materials"])
    assert fill("วัสดุ", "checkbox", hint=BUDGET_HINT, profile=mats).value is True  # วัสดุ + และสิ่งสิ้นเปลือง


def test_checkbox_context_decides_which_vocabulary_counts():
    # a budget question: your research field 'Materials science' must not tick 'Materials'
    assert fill("Materials", "checkbox", hint="Use of funds").value is False
    # anywhere else, uses-of-funds words tick nothing
    assert fill("Equipment", "checkbox", hint="Which research areas does the project cover?").value is None
    assert fill("Pilot", "checkbox", hint="What stage is the research at?").value is not True  # 'pilot run' is a use of funds


def test_checkbox_group_never_ticks_consent_or_other():
    f = fill("Budget items", "checkbox", options=["Equipment", "Materials & consumables", "I agree to the funding terms", "Other (please specify)"])
    assert f.value == ["Equipment"]
    g = fill("Research areas", "checkbox", options=["Equipment", "Materials science", "Pilot run"])
    assert g.value == ["Materials science"]


# 9. Length limits never break a placeholder ------------------------------------------------------

def _whole_placeholders(v: str) -> bool:
    return v.count("[") == v.count("]") and len(re.findall(r"\[(?:YOU MUST ADD|ต้องเพิ่ม):[^\]]*\]", v)) == v.count("[")


@pytest.mark.parametrize("label,maxlen", [("Objectives", 120), ("Objectives", 60), ("วัตถุประสงค์", 90), ("วัตถุประสงค์", 40)])
def test_truncation_reinserts_the_placeholder(label, maxlen):
    f = fill(label, "textarea", narrative=True, maxlen=maxlen)
    assert len(f.value) <= maxlen and has_placeholder(f.value) and f.value.endswith("]") and _whole_placeholders(f.value)
    assert f.status == "amber" and any("Truncated" in w for w in f.warnings)


def test_truncation_with_no_room_for_a_placeholder_is_red():
    for label, ftype, maxlen in (("Objectives", "textarea", 15), ("งบประมาณที่ขอ (บาท)", "number", 12)):
        f = fill(label, ftype, narrative=ftype == "textarea", maxlen=maxlen)
        assert is_red(f) and any("Too long" in w for w in f.warnings)


# 10. Names and 'other' -----------------------------------------------------------------------------

def test_first_name_next_to_surname_is_red(eager_model):
    assert "first_name" not in Applicant.model_fields  # the profile only holds a full name
    hint = "ชื่อ … นามสกุล …"
    fs = run(FieldSpec(id="first", label="ชื่อ", hint=hint), FieldSpec(id="last", label="นามสกุล", hint=hint))
    assert is_red(fs["first"]) and is_red(fs["last"])
    fs = run(FieldSpec(id="first", label="ชื่อ"), FieldSpec(id="last", label="นามสกุล"))
    assert is_red(fs["first"]) and is_red(fs["last"])
    fs = run(FieldSpec(id="n", label="Name"), FieldSpec(id="s", label="Surname"))
    assert is_red(fs["n"]) and is_red(fs["s"])
    assert is_red(fill("First name")) and is_red(fill("Last name"))
    for full in ("ชื่อ-นามสกุล", "ชื่อและนามสกุล", "Name and surname", "Full name"):
        assert fill(full).value == APPLICANT.name, full


@pytest.mark.parametrize("label", ["อื่นๆ (โปรดระบุ)", "อื่น ๆ ระบุ", "Other (please specify)", "If other, please specify"])
def test_other_please_specify_is_red(label, eager_model):
    assert is_red(fill(label)) and is_red(fill(label, "checkbox"))


# 11. The model path -------------------------------------------------------------------------------

GUARDED = [
    FieldSpec(id="decl", label="ข้าพเจ้าได้อ่านและเข้าใจเงื่อนไขแล้ว", type="checkbox"),
    FieldSpec(id="bank", label="เลขที่บัญชี"),
    FieldSpec(id="when", label="วัน/เดือน/ปี"),
    FieldSpec(id="dt", label="Project start", type="date"),
    FieldSpec(id="blank", label="...."),
    FieldSpec(id="boss", label="ชื่อ", hint="ผู้บังคับบัญชา"),
    FieldSpec(id="row", label="รายการ", hint="[table row] งบประมาณ | รายการ / จำนวนเงิน"),
    FieldSpec(id="pct", label="สัดส่วน (%)", hint=TEAM),
]
FREE = FieldSpec(id="free", label="Expected number of users")  # ungated and not in the profile: the model may suggest


@pytest.mark.parametrize("bypass_rules", [False, True])
def test_model_cannot_fill_guarded_fields_or_mark_green(monkeypatch, bypass_rules):
    specs = [*GUARDED, FREE]
    sent = _fake_model(monkeypatch, specs)
    if bypass_rules:  # the model path must hold on its own, even if every field reached it
        monkeypatch.setattr(mapper, "deterministic", lambda spec, c, near="": None)
    fs = run(*specs)
    assert [f["id"] for f in sent] == ["free"]
    for s in GUARDED:
        assert is_red(fs[s.id]), s.id
    assert fs["free"].value == "1,000" and fs["free"].source == "llm" and fs["free"].status == "amber"
    assert not any(f.status == "green" for f in fs.values() if f.source == "llm")
