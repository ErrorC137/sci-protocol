"""PDF form extraction (brief §5.1).

    pdf_acroform : pypdf  -> field names/types/flags directly from the AcroForm
    pdf_flat     : pdfplumber text + layout -> label heuristics; OCR (Tesseract) if there's no text
                   layer; optional LLM pass to clean up the inferred field list
"""

from __future__ import annotations

import io
import logging
import re

import pdfplumber
from pypdf import PdfReader
from pypdf.generic import ArrayObject

from .. import llm
from ..models.schemas import FieldSpec
from .fieldkind import guess_type, humanize, is_narrative

log = logging.getLogger("sci.forms")

FF_REQUIRED = 1 << 1
FF_MULTILINE = 1 << 12
FF_RADIO = 1 << 15
FF_PUSHBUTTON = 1 << 16


_INHERITABLE = ("/FT", "/Ff", "/MaxLen", "/Opt", "/TU", "/DV")


def _walk(nodes, parent: str, inherited: dict):
    """Yield (qualified_name, attrs, widgets) for each terminal field. pypdf's get_fields() drops keys
    such as /MaxLen, so the AcroForm tree is walked directly, applying PDF attribute inheritance."""
    for ref in nodes or []:
        node = ref.get_object()
        t = node.get("/T")
        name = f"{parent}.{t}" if parent and t is not None else (str(t) if t is not None else parent)
        attrs = {**inherited, **{k: node[k] for k in _INHERITABLE if k in node}}
        kids = [k.get_object() for k in node.get("/Kids") or []]
        child_fields = [k for k in kids if "/T" in k]
        if child_fields:
            yield from _walk(child_fields, name, attrs)
        else:
            yield name, attrs, (kids or [node])


def _options(opts) -> list[str]:
    out = []
    if isinstance(opts, ArrayObject):
        for o in opts:
            o = o.get_object() if hasattr(o, "get_object") else o
            out.append(str(o[1] if isinstance(o, ArrayObject) and len(o) > 1 else o))
    return out


def _states(widgets: list) -> list[str]:
    states: list[str] = []
    for w in widgets:
        ap = w.get("/AP")
        normal = ap.get_object().get("/N") if ap else None
        if normal is not None and hasattr(normal.get_object(), "keys"):
            states += [str(k).lstrip("/") for k in normal.get_object().keys() if k != "/Off"]
    return list(dict.fromkeys(states))


def parse_acroform(data: bytes) -> tuple[list[FieldSpec], str | None]:
    reader = PdfReader(io.BytesIO(data))
    title = (reader.metadata or {}).get("/Title") if reader.metadata else None
    acro = reader.trailer["/Root"].get("/AcroForm")
    if acro is None:
        return [], None

    page_index = {p.indirect_reference.idnum: i for i, p in enumerate(reader.pages, start=1) if p.indirect_reference}
    # Visual order: position of each widget in its page's /Annots.
    annot_order: dict[int, tuple[int, int]] = {}
    for pno, page in enumerate(reader.pages, start=1):
        for i, a in enumerate(page.get("/Annots") or []):
            if hasattr(a, "idnum"):
                annot_order[a.idnum] = (pno, i)

    found = []
    for name, attrs, widgets in _walk(acro.get_object().get("/Fields"), "", {}):
        if not name:
            continue
        first = widgets[0]
        ref = getattr(first, "indirect_reference", None)
        pos = annot_order.get(ref.idnum) if ref else None
        page = pos[0] if pos else (page_index.get(first["/P"].idnum) if "/P" in first and hasattr(first["/P"], "idnum") else None)
        found.append((pos or (page or 999, 0), name, attrs, widgets, page))
    found.sort(key=lambda x: x[0])

    specs: list[FieldSpec] = []
    for _, name, attrs, widgets, page in found:
        ft = attrs.get("/FT")
        flags = int(attrs.get("/Ff", 0) or 0)
        label = str(attrs.get("/TU") or humanize(name))
        maxlen = int(attrs["/MaxLen"]) if attrs.get("/MaxLen") is not None else None
        options: list[str] = []
        if ft == "/Tx":
            base = "textarea" if flags & FF_MULTILINE else "text"
        elif ft == "/Btn":
            if flags & FF_PUSHBUTTON:
                continue
            if flags & FF_RADIO:
                base, options = "radio", _states(widgets)
            else:
                base = "checkbox"
        elif ft == "/Ch":
            base, options = "select", _options(attrs.get("/Opt"))
        elif ft == "/Sig":
            base = "signature"
        else:
            continue
        ftype = guess_type(label, base)
        specs.append(
            FieldSpec(
                id=name, label=label, type=ftype, options=options, maxlen=maxlen,
                required=bool(flags & FF_REQUIRED), page=page, narrative=is_narrative(label, ftype, maxlen),
            )
        )
    return specs, str(title) if title else None


_LABEL_LINE = re.compile(r"^\s*(?:\d+[.)]\s*)?(?P<label>[A-Za-z฀-๿][^:_]{1,90}?)\s*[:：]?\s*(?:_{3,}|\.{5,}|\[\s*\]|☐|□)?\s*$")


def _text_pages(data: bytes) -> tuple[list[str], str]:
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        pages = [p.extract_text() or "" for p in pdf.pages]
    if sum(len(t.strip()) for t in pages) > 50:
        return pages, "layout_heuristic"
    try:  # scanned PDF: OCR fallback (needs the tesseract binary + pytesseract)
        import pytesseract

        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = [pytesseract.image_to_string(p.to_image(resolution=200).original) for p in pdf.pages]
        return pages, "ocr"
    except Exception as ex:
        log.warning("no text layer and OCR unavailable: %s", ex)
        return pages, "layout_heuristic"


def parse_flat(data: bytes) -> tuple[list[FieldSpec], str]:
    pages, method = _text_pages(data)
    specs: list[FieldSpec] = []
    for pno, text in enumerate(pages, start=1):
        for i, line in enumerate(text.splitlines()):
            raw = line.strip()
            if not raw or len(raw) > 120:
                continue
            looks_like_field = raw.endswith((":", "：")) or "___" in raw or "....." in raw or "☐" in raw or "□" in raw
            m = _LABEL_LINE.match(raw)
            if not (looks_like_field and m):
                continue
            label = m.group("label").strip(" .")
            ftype = "checkbox" if ("☐" in raw or "□" in raw or "[ ]" in raw) else guess_type(label)
            specs.append(
                FieldSpec(id=f"p{pno}_l{i}", label=label, type=ftype, page=pno, narrative=is_narrative(label, ftype, None))
            )

    if llm.enabled() and pages:
        refined = _llm_fields("\n\n".join(f"--- page {i} ---\n{t}" for i, t in enumerate(pages, 1))[:60_000])
        if refined:
            return refined, "llm"
    return specs, method


_SCHEMA = {
    "type": "object",
    "properties": {
        "fields": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "type": {"type": "string", "enum": ["text", "textarea", "number", "date", "email", "tel", "checkbox", "signature"]},
                    "page": {"type": "integer"},
                    "required": {"type": "boolean"},
                },
                "required": ["label", "type", "page", "required"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["fields"],
    "additionalProperties": False,
}


def _llm_fields(text: str) -> list[FieldSpec] | None:
    result = llm.structured(
        system=(
            "You extract the list of fields an applicant must fill in from the text of a flat (non-fillable) "
            "grant application form. Return each blank, box or question the applicant answers, in document order. "
            "Use the form's own wording for labels. Do not include instructions, headings or office-use-only boxes."
        ),
        user=text,
        schema=_SCHEMA,
        effort="low",
    )
    if not result or not result.get("fields"):
        return None
    return [
        FieldSpec(
            id=f"f{i}", label=f["label"][:200], type=f["type"], page=f.get("page"), required=bool(f.get("required")),
            narrative=is_narrative(f["label"], f["type"], None),
        )
        for i, f in enumerate(result["fields"])
    ]
