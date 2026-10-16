"""Import the team's programme spreadsheet into the corpus and the crawler's watch list.

    python3 apps/api/scripts/import_sheet.py <sheet.xlsx|sheet.csv> [--date YYYY-MM-DD]

Columns (by header name): ID, Program Name, Region, Category, TRL Range, Funding / Support Details,
Description / Focus Areas, Official Working Link.

What it does, and what it deliberately does not do:
- Rows that are already in data/seed/grants.yaml (DUPLICATE_OF below) are not added again.
- Every other row is appended as `verified: false, confidence: low`, with the sheet's wording in `notes`.
  Nothing in the sheet was checked against the funder's site; the curate pipeline (python -m app.curate)
  is how entries get verified.
- Amounts are parsed only when the cell states a currency; ranges with max < min are dropped and flagged.
- Eligible countries come from the Region column only for government programmes (where the region really
  is the eligibility rule). Accelerators and investors are left 'not stated' rather than guessed.
- Every link is added to data/curate/sites.yaml so the crawler watches it.
- A report of what was added, skipped and flagged is written to docs/SHEET_IMPORT.md.
Running it twice adds nothing twice (refs are stable).
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from ruamel.yaml.comments import CommentedMap  # noqa: E402

from app.curate.review import _flow, _yaml  # noqa: E402
from app.curate.sites import Site, canonical, dump_sites, load_sites  # noqa: E402

SEED = ROOT / "data" / "seed" / "grants.yaml"
SITES = ROOT / "data" / "curate" / "sites.yaml"
REPORT = ROOT / "docs" / "SHEET_IMPORT.md"

# Funders the corpus does not have yet: key -> (name, type, country, website). Types use taxonomy.FUNDER_TYPES.
NEW_FUNDERS = {
    "doe_sbir": ("U.S. Department of Energy SBIR/STTR Programs Office", "government", "US", "https://science.osti.gov/sbir"),
    "nasa_sbir": ("NASA SBIR/STTR Program", "government", "US", "https://sbir.nasa.gov"),
    "darpa": ("DARPA (Defense Advanced Research Projects Agency)", "government", "US", "https://www.darpa.mil"),
    "usda_nifa": ("USDA National Institute of Food and Agriculture (NIFA)", "government", "US", "https://nifa.usda.gov"),
    "diu": ("Defense Innovation Unit (DIU)", "government", "US", "https://www.diu.mil"),
    "barda": ("BARDA DRIVe (U.S. HHS)", "government", "US", "https://medicalcountermeasures.gov"),
    "nist_mep": ("NIST Manufacturing Extension Partnership (MEP)", "government", "US", "https://www.nist.gov/mep"),
    "niaid": ("NIAID (U.S. National Institute of Allergy and Infectious Diseases)", "government", "US", "https://www.niaid.nih.gov"),
    "masschallenge": ("MassChallenge", "accelerator", "US", "https://masschallenge.org"),
    "pnp": ("Plug and Play Tech Center", "corporate", "US", "https://www.plugandplaytechcenter.com"),
    "anl_cri": ("Chain Reaction Innovations (Argonne National Laboratory)", "government", "US", "https://chainreaction.anl.gov"),
    "ornl_ic": ("Innovation Crossroads (Oak Ridge National Laboratory)", "government", "US", "https://innovationcrossroads.ornl.gov"),
    "in2": ("Wells Fargo Innovation Incubator (IN2)", "corporate", "US", "https://www.in2ecosystem.com"),
    "pml": ("Prime Movers Lab", "corporate", "US", "https://www.primemoverslab.com"),
    "eureka": ("EUREKA (Eurostars and Network Projects)", "multilateral", "BE", "https://www.eurekanetwork.org"),
    "eit_innoenergy": ("EIT InnoEnergy", "government", "NL", "https://www.innoenergy.com"),
    "eit_rawmaterials": ("EIT RawMaterials", "government", "DE", "https://eitrawmaterials.eu"),
    "eit_health": ("EIT Health", "government", "DE", "https://eithealth.eu"),
    "eit_digital": ("EIT Digital", "government", "BE", "https://www.eitdigital.eu"),
    "eit_food": ("EIT Food", "government", "BE", "https://www.eitfood.eu"),
    "eit_um": ("EIT Urban Mobility", "government", "ES", "https://www.eiturbanmobility.eu"),
    "innosuisse": ("Innosuisse (Swiss Innovation Agency)", "government", "CH", "https://www.innosuisse.ch"),
    "ffg": ("FFG (Austrian Research Promotion Agency)", "government", "AT", "https://www.ffg.at"),
    "exist": ("EXIST (German Federal Ministry for Economic Affairs)", "government", "DE", "https://www.exist.de"),
    "bpifrance": ("Bpifrance", "government", "FR", "https://www.bpifrance.fr"),
    "cdti": ("CDTI (Centre for the Development of Industrial Technology, Spain)", "government", "ES", "https://www.cdti.es"),
    "dsv": ("Deep Science Ventures", "accelerator", "GB", "https://www.deepscienceventures.com"),
    "cruk": ("Cancer Research UK", "foundation", "GB", "https://www.cancerresearchuk.org"),
    "innovate_uk": ("Innovate UK (UKRI)", "government", "GB", "https://www.ukri.org/councils/innovate-uk/"),
    "jst": ("Japan Science and Technology Agency (JST)", "government", "JP", "https://www.jst.go.jp"),
    "nedo": ("NEDO (New Energy and Industrial Technology Development Organization)", "government", "JP", "https://www.nedo.go.jp/english/"),
    "jetro": ("JETRO (Japan External Trade Organization)", "government", "JP", "https://www.jetro.go.jp/en/"),
    "kised": ("KISED (Korea Institute of Startup and Entrepreneurship Development)", "government", "KR", "https://www.kised.or.kr"),
    "kiat": ("KIAT (Korea Institute for Advancement of Technology)", "government", "KR", "https://www.kiat.or.kr"),
    "kist": ("KIST (Korea Institute of Science and Technology)", "government", "KR", "https://www.kist.re.kr"),
    "nstc_tw": ("National Science and Technology Council (Taiwan)", "government", "TW", "https://www.nstc.gov.tw"),
    "tta": ("Taiwan Tech Arena (TTA)", "accelerator", "TW", "https://taiwantecharena.tw"),
    "astar": ("A*STAR (Agency for Science, Technology and Research)", "government", "SG", "https://www.a-star.edu.sg"),
    "nrf_sg": ("National Research Foundation Singapore", "government", "SG", "https://www.nrf.gov.sg"),
    "start2": ("start2 Group", "accelerator", "DE", "https://www.start2.group"),
    "brin": ("BRIN (National Research and Innovation Agency, Indonesia)", "government", "ID", "https://www.brin.go.id"),
    "mdec": ("MDEC (Malaysia Digital Economy Corporation)", "government", "MY", "https://mdec.my"),
    "adbv": ("ADB Ventures (Asian Development Bank)", "multilateral", "PH", "https://adbventures.com"),
    "temasek_fdn": ("Temasek Foundation", "foundation", "SG", "https://www.temasekfoundation.org.sg"),
    "insead": ("INSEAD", "accelerator", "SG", "https://www.insead.edu"),
    "nxpo": ("NXPO (Office of National Higher Education Science Research and Innovation Policy Council)", "government", "TH", "https://www.nxpo.or.th"),
    "chula": ("Chulalongkorn University", "incubator", "TH", "https://www.chula.ac.th"),
    "true_incube": ("True Incube (True Corporation)", "corporate", "TH", "https://trueincube.com"),
    "ais": ("AIS The StartUp", "corporate", "TH", "https://startup.ais.co.th"),
    "banpu": ("Banpu (Banpu Champions for Change)", "corporate", "TH", "https://www.banpu.com"),
    "innospace": ("InnoSpace (Thailand)", "incubator", "TH", "https://innospacethailand.com"),
    "krungsri_finnovate": ("Krungsri Finnovate", "corporate", "TH", "https://www.krungsrifinnovate.com"),
    "beacon_vc": ("Beacon Venture Capital (KASIKORNBANK)", "corporate", "TH", "https://www.beaconvc.fund"),
    "scb10x": ("SCB 10X", "corporate", "TH", "https://scb10x.com"),
    "kx": ("KASIKORN X (KX)", "corporate", "TH", "https://www.kasikornx.com"),
    "tu": ("Thammasat University Science Park", "incubator", "TH", "https://www.tu.ac.th"),
    "cmu_step": ("Chiang Mai University Science and Technology Park (STeP)", "incubator", "TH", "https://step.cmu.ac.th"),
    "kku_sp": ("Khon Kaen University Science Park", "incubator", "TH", "https://kkusp.kku.ac.th"),
    "psu_sp": ("Prince of Songkla University Science Park", "incubator", "TH", "https://psusp.psu.ac.th"),
    "tgi": ("Thai-German Institute (TGI)", "government", "TH", "https://www.tgi.or.th"),
}

# Sheet ID -> funder key (existing keys: nsf, nih, eic, esg, sginnovate, nia, nstda, ...).
FUNDER_OF = {
    1: "nsf", 2: "nsf", 3: "nih", 4: "nih", 5: "doe_sbir", 6: "doe_sbir", 7: "arpae", 8: "nasa_sbir", 9: "nasa_sbir",
    10: "darpa", 11: "usda_nifa", 12: "usda_nifa", 13: "diu", 14: "barda", 15: "nist_mep", 16: "masschallenge", 17: "yc",
    18: "techstars", 19: "indiebio", 20: "pnp", 21: "activate", 22: "activate", 23: "anl_cri", 24: "ornl_ic", 25: "in2",
    26: "eic", 27: "eic", 28: "eic", 29: "eic", 30: "eic", 31: "eic", 32: "eureka", 33: "eureka", 34: "eit_innoenergy",
    35: "eit_rawmaterials", 36: "eit_health", 37: "eit_digital", 38: "innosuisse", 39: "ffg", 40: "exist", 41: "bpifrance",
    42: "cdti", 43: "msca", 44: "pml", 45: "cdl", 46: "eit_food", 47: "eit_um", 48: "dsv", 49: "cruk", 50: "innovate_uk",
    51: "jst", 52: "nedo", 53: "jetro", 54: "kised", 55: "kiat", 56: "kist", 57: "nstc_tw", 58: "tta", 59: "esg", 60: "esg",
    61: "esg", 62: "astar", 63: "nrf_sg", 64: "sginnovate", 65: "astar", 66: "start2", 67: "brin", 68: "mdec", 69: "mranti",
    70: "niaid", 71: "adbv", 72: "temasek_fdn", 73: "antler", 74: "iterative", 75: "insead", 76: "nia", 77: "nia", 78: "nia",
    79: "nia", 80: "tsri", 81: "nxpo", 82: "depa", 83: "nstda", 84: "nstda", 85: "chula", 86: "true_incube", 87: "ais",
    88: "banpu", 89: "innospace", 90: "krungsri_finnovate", 91: "beacon_vc", 92: "scb10x", 93: "kx", 94: "chula", 95: "tu",
    96: "cmu_step", 97: "kku_sp", 98: "psu_sp", 99: "tgi", 100: "tsri",
}

# Rows the corpus already covers (exact title of the existing entry). "likely" = judged the same programme
# from name and amount; worth a look.
DUPLICATE_OF = {
    1: "NSF SBIR/STTR Phase I (America's Seed Fund)",
    3: "NIH SBIR/STTR", 4: "NIH SBIR/STTR",
    7: "ARPA-E OPEN and Program Funding Opportunities",
    17: "Y Combinator", 18: "Techstars Accelerator", 19: "SOSV IndieBio (biotech)", 21: "Activate Fellowship",
    22: "Activate Fellowship (likely: Cyclotron Road is the Berkeley Lab programme Activate grew out of)",
    26: "EIC Pathfinder Open", 28: "EIC Transition", 29: "EIC Accelerator",
    43: "MSCA Postdoctoral Fellowships (the sheet row is MSCA in general)",
    45: "Creative Destruction Lab",
    59: "Startup SG Tech (Proof of Concept / Proof of Value)", 60: "Startup SG Tech (Proof of Concept / Proof of Value)",
    69: "MRANTI Technology Commercialisation Programmes (likely)",
    73: "Antler Residency (Southeast Asia)", 74: "Iterative Accelerator",
    76: "NIA Open Innovation Grant (likely: same 1.5M THB cap)",
    77: "NIA Thematic Innovation Program (likely)",
    78: "NIA Social Innovation Grant",
    80: "TSRI Fundamental Fund (FF)", 82: "depa Digital Startup Fund",
    100: "TSRI Fundamental Fund (FF) (the sheet lists it twice; this row links to NXPO, TSRI's site is tsri.or.th)",
}

# Problems found while importing. Only things we are confident about are stated as facts; the rest say "check".
FLAGS = {
    1: ["The sheet links to NIH's SBIR page; NSF's programme is at seedfund.nsf.gov."],
    2: ["The sheet links to NIH's SBIR page; the URL was replaced with NSF's seedfund.nsf.gov."],
    13: ["AFWERX (US Air Force) and DIU are separate organisations; check which programme is meant."],
    22: ["Check whether cyclotronroad.lbl.gov is still a separate programme page."],
    40: ["'Bied ForLab' is not a programme name we can identify; EXIST itself is real. Check the name."],
    50: ["We believe Innovate UK paused Smart grants in 2025 and could not confirm the current status. Check before showing it as open."],
    55: ["The amount range in the sheet is inverted (₩200,000,000 - ₩2,000,000), so the amount was left out."],
    64: ["'Summiteer' is not a programme name we can confirm for SGInnovate."],
    66: ["Check the programme name ('Global Applied DeepTech') against start2 Group's site."],
    67: ["The sheet says 'TRN' (read as TRL), and the name mixes BEKRAF/creative-economy and BRIN; check which programme is meant."],
    70: ["'International R&D Partnerships' is not a programme name we can confirm at NIAID."],
    72: ["Temasek Foundation mainly funds community and social programmes; check that it funds company R&D at all."],
    75: ["INSEAD Venture Competition is, as far as we know, for INSEAD students and alumni. Check eligibility."],
    81: ["NXPO is a policy office; most research money flows through TSRI and the PMUs. Check that it runs open calls."],
    84: ["'STEP' is Chiang Mai University's science park name; NSTDA runs Thailand Science Park. Check the name."],
    85: ["Bangkok Business Challenge is run by Sasin School of Management; the sheet's link is a Chula sustainability page. Check the link."],
    93: ["Check the name 'KASIKORN X-Change'; KBank's venture builder is known as KASIKORN X (KX)."],
}
SBIR_IDS = {1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12}
SBIR_NOTE = ("US SBIR/STTR is only for US small businesses majority-owned by US citizens or permanent residents. "
             "The programmes' authority lapsed on 1 Oct 2025; we could not verify whether it has been renewed since. Check before relying on it.")
URL_FIX = {2: "https://seedfund.nsf.gov"}

REGION_COUNTRIES = {
    "USA": ["US"], "EU": ["HE_ELIGIBLE"], "Switzerland": ["CH"], "Austria": ["AT"], "Germany": ["DE"], "France": ["FR"],
    "Spain": ["ES"], "UK": ["GB"], "Japan": ["JP"], "South Korea": ["KR"], "Taiwan": ["TW"], "Singapore": ["SG"],
    "Indonesia": ["ID"], "Malaysia": ["MY"], "Thailand": ["TH"],
}

FIELD_WORDS = [
    ("health", r"biomedical|health|clinical|medical|cancer|countermeasure|infectious"),
    ("biotech", r"biotech|biomedical|life science|bio\b|synthetic biology"),
    ("energy", r"energy|nuclear|fusion|battery|batteries|clean ?tech|climate|electri"),
    ("materials", r"material|raw material|mining|metal|chemistr"),
    ("manufacturing", r"manufactur|industrial|prototyp|hardware"),
    ("environmental", r"environment|sustainab|circular|recycl|waste|climate"),
    ("food_science", r"\bfood"),
    ("agritech", r"agri|farm"),
    ("digital", r"digital|software|computing|\bai\b|artificial intelligence|telecom|fintech|mobility"),
]

CURRENCY = [(r"S\$", "SGD"), (r"NTD|NT\$", "TWD"), (r"IDR", "IDR"), (r"THB|฿|บาท", "THB"), (r"€", "EUR"), (r"£", "GBP"),
            (r"¥|JPY", "JPY"), (r"₩|KRW", "KRW"), (r"\$|USD", "USD")]
_NUM = r"(\d[\d,]*(?:\.\d+)?)\s*([kKmM](?![a-z])|million|bn)?"


def _num(n: str, mult: str | None) -> float:
    v = float(n.replace(",", ""))
    m = (mult or "").lower()
    return v * (1_000 if m == "k" else 1_000_000 if m in ("m", "million") else 1_000_000_000 if m == "bn" else 1)


def parse_amount(text: str) -> tuple[dict | None, str | None]:
    """{'min','max','currency'} from the first amount phrase in the cell, or (None, reason)."""
    if not text or not re.search(r"\d", text):
        return None, None
    cur = next((c for pat, c in CURRENCY if re.search(pat, text)), None)
    if cur is None:
        return None, "amount without a currency"
    first = re.split(r"\s\+\s|/yr|\(|grant \+", text)[0]  # '€2.5M grant + €15M equity' -> the grant part
    nums = [_num(n, m) for n, m in re.findall(_NUM, first)]
    if not nums:
        return None, None
    if re.search(r"%", first):
        return None, "percentage of cost, not an amount"
    if len(nums) >= 2:
        lo, hi = nums[0], nums[1]
        if hi < lo:
            return None, "range inverted"
        return {"min": lo, "max": hi, "currency": cur}, None
    v = nums[0]
    if re.search(r"up to", first, re.I):
        return {"min": None, "max": v, "currency": cur}, None
    if first.strip().endswith("+"):
        return {"min": v, "max": None, "currency": cur}, None
    return {"min": None, "max": v, "currency": cur}, None


def parse_trl(text: str) -> list[int] | None:
    m = re.search(r"(\d)\s*[-–]\s*(\d)", text or "")
    return [int(m.group(1)), int(m.group(2))] if m else None


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


def read_rows(path: Path) -> list[dict]:
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        import openpyxl  # local tooling only: pip install openpyxl

        ws = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0]
        rows = list(ws.iter_rows(values_only=True))
        hdr = [str(h).strip() if h is not None else "" for h in rows[0]]
        return [dict(zip(hdr, r)) for r in rows[1:] if any(c is not None for c in r)]
    return list(csv.DictReader(path.read_text(encoding="utf-8-sig").splitlines()))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet", type=Path)
    ap.add_argument("--date", default=date.today().isoformat())
    a = ap.parse_args()
    rows = read_rows(a.sheet)

    rt = _yaml()
    doc = rt.load(SEED.read_text(encoding="utf-8"))
    funders = {f["key"]: f for f in doc["funders"]}
    titles = {g["title"] for g in doc["grants"]}
    refs = {g["ref"] for g in doc["grants"]}
    added, dups, skipped, flagged = [], [], [], []

    for r in rows:
        i = int(r["ID"])
        name = str(r["Program Name"]).strip()
        fkey = FUNDER_OF.get(i)
        flags = list(FLAGS.get(i, []))
        if i in SBIR_IDS:
            flags.append(SBIR_NOTE)
        if flags:
            flagged.append((i, name, flags))
        if i in DUPLICATE_OF:
            dups.append((i, name, DUPLICATE_OF[i]))
            continue
        if fkey is None:
            skipped.append((i, name, "no funder mapping for this row"))
            continue
        if fkey not in funders:
            fname, ftype, fcountry, fsite = NEW_FUNDERS[fkey]
            f = _flow({"key": fkey, "name": fname, "type": ftype, "country": fcountry, "website": fsite})
            doc["funders"].append(f)
            funders[fkey] = f
        ref = f"sheet-{slug(name)}"
        if ref in refs or name in titles:
            skipped.append((i, name, "already imported"))
            continue
        support = str(r.get("Funding / Support Details") or "").strip()
        desc = str(r.get("Description / Focus Areas") or "").strip()
        category = str(r.get("Category") or "").strip()
        region = str(r.get("Region") or "").strip()
        amount, why = parse_amount(support)
        if why == "range inverted" and not any("inverted" in x for x in flags):
            flags.append(f"Amount range inverted in the sheet ({support}); left out.")
        e = {"ref": ref, "funder": fkey, "title": name, "summary": desc or None}
        text = f"{name} {desc}".lower()
        fields = [k for k, pat in FIELD_WORDS if re.search(pat, text)]
        e["fields"] = fields
        trl = parse_trl(str(r.get("TRL Range") or ""))
        if trl:
            e["trl"] = trl
        if funders[fkey]["type"] in ("government", "multilateral") and region in REGION_COUNTRIES:
            e["countries"] = REGION_COUNTRIES[region]
        if amount:
            e["amount"] = amount
        cat = category.lower()
        if re.search(r"venture|equity|co-investment", cat) or re.search(r"investment|equity", support, re.I):
            e["equity_taken"] = True
        elif cat == "grant":
            e["equity_taken"] = False
        e["url"] = URL_FIX.get(i) or str(r.get("Official Working Link") or "").strip() or funders[fkey]["website"]
        e["confidence"] = "low"
        e["verified"] = False
        note = f"From the team spreadsheet (row {i}, {a.date}); not checked against the funder's site. Category: {category}. Support: {support}."
        if amount is None and support:
            note += " Amount not structured: " + (why or "no figure in the cell") + "."
        if not e.get("countries"):
            note += f" Region in sheet: {region}; eligibility not stated."
        if flags:
            note += " CHECK: " + " ".join(flags)
        e["notes"] = note
        doc["grants"].append(CommentedMap((k, _flow(v)) for k, v in e.items() if v is not None))
        refs.add(ref)
        titles.add(name)
        added.append((i, name, fkey))

    with SEED.open("w", encoding="utf-8") as fh:
        rt.dump(doc, fh)

    # watch list: every link (deduplicated), tagged with its funder key
    sites = load_sites(SITES) if SITES.exists() else []
    have = {canonical(s.url) for s in sites}
    new_sites = 0
    for r in rows:
        i = int(r["ID"])
        url = URL_FIX.get(i) or str(r.get("Official Working Link") or "").strip()
        if url.startswith("http") and canonical(url) not in have:
            sites.append(Site(url=url, funder=FUNDER_OF.get(i), name=str(r["Program Name"]).strip()))
            have.add(canonical(url))
            new_sites += 1
    dump_sites(sites, SITES)

    lines = [f"# Spreadsheet import ({a.date})", "",
             f"Source: `{a.sheet.name}` ({len(rows)} rows). Script: `apps/api/scripts/import_sheet.py`.", "",
             f"- **Added to the corpus:** {len(added)} programmes, all `verified: false, confidence: low`.",
             f"- **Already in the corpus (not added again):** {len(dups)}.",
             f"- **Skipped:** {len(skipped)}.",
             f"- **Crawler watch list:** {new_sites} new URLs added to `data/curate/sites.yaml` ({len(sites)} total).",
             f"- **Rows with something to check:** {len(flagged)} (below).", "",
             "Nothing from the sheet was checked against the funders' sites (the build sandbox cannot reach them).",
             "Amounts, TRL bands and descriptions are the sheet's own; treat them as leads until someone opens each link.", "",
             "## Rows to check", ""]
    lines += [f"- **{i}. {n}**: " + " ".join(fl) for i, n, fl in flagged]
    lines += ["", "## Already in the corpus", ""] + [f"- {i}. {n} → {d}" for i, n, d in dups]
    if skipped:
        lines += ["", "## Skipped", ""] + [f"- {i}. {n}: {w}" for i, n, w in skipped]
    lines += ["", "## Added", ""] + [f"- {i}. {n} (`{k}`)" for i, n, k in added]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"added {len(added)}, duplicates {len(dups)}, skipped {len(skipped)}, flagged {len(flagged)}, new sites {new_sites}")


if __name__ == "__main__":
    main()
