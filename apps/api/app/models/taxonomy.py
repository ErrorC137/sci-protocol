"""Controlled vocabularies. The intake wizard offers only these values, which is what keeps the
profile non-confidential: two levels of category plus stage, never a description of the invention."""

from __future__ import annotations

FIELDS: dict[str, dict] = {
    "materials": {
        "label": "Materials science",
        "subdomains": [
            "Biomass valorization",
            "Bio-based composites",
            "Polymers & plastics",
            "Construction materials",
            "Ceramics & glass",
            "Metals & alloys",
            "Nanomaterials",
            "Coatings & surfaces",
            "Battery materials",
            "Recycling & circular materials",
            "Textiles & fibres",
        ],
    },
    "agritech": {
        "label": "Agritech",
        "subdomains": [
            "Crop science",
            "Precision agriculture",
            "Aquaculture",
            "Livestock",
            "Post-harvest & storage",
            "Agri-waste utilization",
            "Soil health",
            "Biofertilizers & biopesticides",
        ],
    },
    "biotech": {
        "label": "Biotechnology",
        "subdomains": [
            "Synthetic biology",
            "Fermentation & enzymes",
            "Diagnostics",
            "Therapeutics",
            "Microbiome",
            "Bioinformatics",
            "Vaccines",
            "Longevity",
        ],
    },
    "energy": {
        "label": "Energy",
        "subdomains": [
            "Solar & PV",
            "Energy storage",
            "Hydrogen",
            "Bioenergy & biofuels",
            "Grid & efficiency",
            "Carbon capture & utilization",
        ],
    },
    "environmental": {
        "label": "Environmental",
        "subdomains": [
            "Water treatment",
            "Air quality",
            "Waste management",
            "Climate adaptation",
            "Biodiversity & conservation",
            "Pollution remediation",
        ],
    },
    "food_science": {
        "label": "Food science",
        "subdomains": [
            "Alternative proteins",
            "Functional foods",
            "Food safety",
            "Food processing",
            "Packaging",
            "Nutrition",
        ],
    },
    "health": {
        "label": "Health & medtech",
        "subdomains": [
            "Medical devices",
            "Digital health",
            "Public health",
            "Assistive technology",
            "Women's health",
            "Brain health",
        ],
    },
    "digital": {
        "label": "Digital & deep tech",
        "subdomains": [
            "AI & data",
            "IoT & sensors",
            "Robotics & automation",
            "Blockchain & web3",
            "Semiconductors",
            "Quantum",
            "Open-source public goods",
        ],
    },
    "manufacturing": {
        "label": "Advanced manufacturing",
        "subdomains": [
            "Process engineering",
            "Additive manufacturing",
            "Industrial automation",
            "Scale-up & pilot production",
        ],
    },
}

TRL_LEVELS: dict[int, dict[str, str]] = {
    1: {"name": "Basic principles observed", "plain": "You have an idea grounded in observed science, no experiments yet."},
    2: {"name": "Concept formulated", "plain": "You've worked out how the idea could be applied; still on paper."},
    3: {"name": "Proof of concept", "plain": "First lab experiments show the core idea works."},
    4: {"name": "Validated in the lab", "plain": "Components work together in the lab under controlled conditions."},
    5: {"name": "Validated in a relevant environment", "plain": "Tested in conditions close to real use (e.g. with real feedstock)."},
    6: {"name": "Demonstrated in a relevant environment", "plain": "A working prototype or pilot has run in near-real conditions."},
    7: {"name": "Demonstrated in an operational environment", "plain": "A near-final system has run in the real setting."},
    8: {"name": "System complete and qualified", "plain": "Final product is built, tested and certified."},
    9: {"name": "Proven in operation", "plain": "The product is in commercial use."},
}

EVIDENCE: dict[str, dict] = {
    "lab_result": {"label": "Lab result", "trl_range": (3, 4)},
    "prototype": {"label": "Prototype", "trl_range": (4, 6)},
    "pilot": {"label": "Pilot", "trl_range": (6, 7)},
    "pre_production": {"label": "Pre-production", "trl_range": (7, 8)},
    "in_market": {"label": "In market", "trl_range": (8, 9)},
}

APPLICANT_TYPES: dict[str, str] = {
    "individual": "Individual researcher (no organisation applying)",
    "university": "University or research-institute lab",
    "startup": "Registered startup",
    "sme": "Established SME",
    "consortium": "Consortium (multiple organisations)",
}
ENTITY_APPLICANT_TYPES = {"startup", "sme"}

INSTITUTION_TYPES: dict[str, str] = {
    "university": "University",
    "government_lab": "Government research agency",
    "hospital": "Hospital / clinical",
    "private_company": "Private company",
    "independent": "Independent / none",
}

USES_OF_FUNDS: dict[str, str] = {
    "equipment": "Equipment",
    "materials": "Materials & consumables",
    "personnel": "Personnel",
    "pilot_run": "Pilot run",
    "certification": "Testing & certification",
    "ip_filing": "IP filing",
}

CONSTRAINTS: dict[str, str] = {
    "no_equity": "Unwilling to give equity",
    "no_ip_assignment": "Unwilling to assign IP",
    "local_currency": "Needs funding in local currency",
}

FUNDER_TYPES = ["government", "accelerator", "incubator", "foundation", "corporate", "web3", "crowdfunding", "multilateral"]
APPLICATION_MODES = ["pdf_form", "web_form", "email", "portal"]

# ISO-3166 alpha-2 -> (name, currency). Focused on SEA plus common funder jurisdictions.
COUNTRIES: dict[str, tuple[str, str]] = {
    "TH": ("Thailand", "THB"), "SG": ("Singapore", "SGD"), "MY": ("Malaysia", "MYR"), "ID": ("Indonesia", "IDR"),
    "VN": ("Vietnam", "VND"), "PH": ("Philippines", "PHP"), "KH": ("Cambodia", "KHR"), "LA": ("Laos", "LAK"),
    "MM": ("Myanmar", "MMK"), "BN": ("Brunei", "BND"), "TL": ("Timor-Leste", "USD"),
    "JP": ("Japan", "JPY"), "KR": ("South Korea", "KRW"), "CN": ("China", "CNY"), "TW": ("Taiwan", "TWD"),
    "HK": ("Hong Kong", "HKD"), "IN": ("India", "INR"), "AU": ("Australia", "AUD"), "NZ": ("New Zealand", "NZD"),
    "US": ("United States", "USD"), "CA": ("Canada", "CAD"), "GB": ("United Kingdom", "GBP"),
    "DE": ("Germany", "EUR"), "FR": ("France", "EUR"), "NL": ("Netherlands", "EUR"), "CH": ("Switzerland", "CHF"),
    "IL": ("Israel", "ILS"), "AE": ("United Arab Emirates", "AED"), "BR": ("Brazil", "BRL"), "KE": ("Kenya", "KES"),
    "NG": ("Nigeria", "NGN"), "ZA": ("South Africa", "ZAR"),
}

# Region shorthands used in the curated corpus, expanded at ingest.
REGIONS: dict[str, list[str]] = {
    "ASEAN": ["BN", "KH", "ID", "LA", "MY", "MM", "PH", "SG", "TH", "VN", "TL"],
    "EU27": [
        "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT", "LV", "LT",
        "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE",
    ],
    # Horizon Europe associated countries - approximate; association status changes, verify per call.
    "HE_ASSOCIATED": [
        "AL", "AM", "BA", "FO", "GE", "IS", "IL", "XK", "MD", "ME", "NZ", "MK", "NO", "RS", "TN", "TR", "UA",
        "GB", "CH", "CA", "KR",
    ],
}
REGIONS["HE_ELIGIBLE"] = REGIONS["EU27"] + REGIONS["HE_ASSOCIATED"]

GLOBAL = "*"


def expand_countries(codes: list[str] | None) -> list[str]:
    out: list[str] = []
    for c in codes or []:
        c = c.strip().upper()
        if c in ("*", "GLOBAL", "ANY"):
            return [GLOBAL]
        out.extend(REGIONS.get(c, [c]))
    return sorted(set(out))


def field_label(field_id: str) -> str:
    return FIELDS.get(field_id, {}).get("label", field_id)


def country_name(code: str) -> str:
    return COUNTRIES.get(code.upper(), (code, ""))[0]


def as_dict() -> dict:
    """Everything the intake wizard renders, served at GET /meta/taxonomy."""
    return {
        "fields": [{"id": k, "label": v["label"], "subdomains": v["subdomains"]} for k, v in FIELDS.items()],
        "trl": [{"level": k, **v} for k, v in TRL_LEVELS.items()],
        "evidence": [{"id": k, "label": v["label"], "trl_range": list(v["trl_range"])} for k, v in EVIDENCE.items()],
        "applicant_types": [{"id": k, "label": v} for k, v in APPLICANT_TYPES.items()],
        "institution_types": [{"id": k, "label": v} for k, v in INSTITUTION_TYPES.items()],
        "uses_of_funds": [{"id": k, "label": v} for k, v in USES_OF_FUNDS.items()],
        "constraints": [{"id": k, "label": v} for k, v in CONSTRAINTS.items()],
        "countries": [{"code": k, "name": v[0], "currency": v[1]} for k, v in sorted(COUNTRIES.items(), key=lambda x: x[1][0])],
        "funder_types": FUNDER_TYPES,
    }


# Thai labels, used when an application form is in Thai.
FIELDS_TH: dict[str, str] = {
    "materials": "วัสดุศาสตร์", "agritech": "เทคโนโลยีการเกษตร", "biotech": "เทคโนโลยีชีวภาพ", "energy": "พลังงาน",
    "environmental": "สิ่งแวดล้อม", "food_science": "วิทยาศาสตร์การอาหาร", "health": "สุขภาพและการแพทย์",
    "digital": "ดิจิทัลและเทคโนโลยีเชิงลึก", "manufacturing": "การผลิตขั้นสูง",
}
USES_OF_FUNDS_TH: dict[str, str] = {
    "equipment": "ครุภัณฑ์", "materials": "วัสดุและสิ่งสิ้นเปลือง", "personnel": "ค่าตอบแทนบุคลากร",
    "pilot_run": "การผลิตทดลอง (pilot)", "certification": "การทดสอบและรับรองมาตรฐาน", "ip_filing": "การยื่นจดทรัพย์สินทางปัญญา",
}
EVIDENCE_TH: dict[str, str] = {
    "lab_result": "ผลการทดลองระดับห้องปฏิบัติการ", "prototype": "ต้นแบบ", "pilot": "การทดสอบนำร่อง",
    "pre_production": "ก่อนการผลิตจริง", "in_market": "จำหน่ายในตลาดแล้ว",
}
APPLICANT_TYPES_TH: dict[str, str] = {
    "individual": "นักวิจัยอิสระ (บุคคล)", "university": "มหาวิทยาลัยหรือสถาบันวิจัย", "startup": "สตาร์ทอัพ (นิติบุคคล)",
    "sme": "วิสาหกิจขนาดกลางและขนาดย่อม (SME)", "consortium": "กลุ่มความร่วมมือ (Consortium)",
}
COUNTRY_TH: dict[str, str] = {"TH": "ประเทศไทย"}
