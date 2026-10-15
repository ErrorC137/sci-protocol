"""HTML form extraction: <input|select|textarea> + their <label>s (brief §5.1)."""

from __future__ import annotations

from bs4 import BeautifulSoup, Tag

from ..models.schemas import FieldSpec
from .fieldkind import guess_type, humanize, is_narrative

SKIP_TYPES = {"hidden", "submit", "button", "reset", "image", "file", "password"}
TYPE_MAP = {"email": "email", "tel": "tel", "number": "number", "date": "date", "checkbox": "checkbox",
            "radio": "radio", "url": "text", "text": "text", "search": "text"}


def _text(t: Tag | None) -> str:
    return " ".join(t.get_text(" ", strip=True).split()) if t else ""


def _label_for(soup: BeautifulSoup, el: Tag) -> str:
    if el.get("id"):
        lab = soup.find("label", attrs={"for": el["id"]})
        if lab:
            return _text(lab)
    parent = el.find_parent("label")
    if parent:
        return _text(parent)
    if el.get("aria-label"):
        return el["aria-label"]
    if el.get("aria-labelledby"):
        ref = soup.find(id=el["aria-labelledby"])
        if ref:
            return _text(ref)
    if el.get("placeholder"):
        return el["placeholder"]
    return humanize(el.get("name") or el.get("id") or "")


def parse_html(data: bytes) -> tuple[list[FieldSpec], str | None]:
    soup = BeautifulSoup(data, "html.parser")
    forms = soup.find_all("form")
    root = max(forms, key=lambda f: len(f.find_all(["input", "select", "textarea"]))) if forms else soup
    title = _text(soup.find("title")) or None

    specs: list[FieldSpec] = []
    groups: dict[str, FieldSpec] = {}
    for el in root.find_all(["input", "select", "textarea"]):
        name = el.get("name") or el.get("id")
        if not name:
            continue
        required = el.has_attr("required") or el.get("aria-required") == "true"
        maxlen = int(el["maxlength"]) if el.get("maxlength", "").isdigit() else None

        if el.name == "textarea":
            label = _label_for(soup, el)
            specs.append(FieldSpec(id=name, label=label, type="textarea", maxlen=maxlen, required=required,
                                   hint=el.get("placeholder"), narrative=True))
            continue
        if el.name == "select":
            label = _label_for(soup, el)
            opts = [_text(o) or o.get("value", "") for o in el.find_all("option") if (o.get("value") or _text(o))]
            opts = [o for o in opts if not o.lower().startswith(("select", "choose", "--"))]
            specs.append(FieldSpec(id=name, label=label, type="select", options=opts, required=required))
            continue

        itype = (el.get("type") or "text").lower()
        if itype in SKIP_TYPES:
            continue
        if itype == "radio" or (itype == "checkbox" and len(root.find_all("input", attrs={"name": name})) > 1):
            # Grouped choices: one FieldSpec per name, options from each choice's label.
            fs = groups.get(name)
            if fs is None:
                legend = el.find_parent("fieldset")
                group_label = _text(legend.find("legend")) if legend and legend.find("legend") else humanize(name)
                fs = FieldSpec(id=name, label=group_label, type="radio" if itype == "radio" else "checkbox", required=required)
                groups[name] = fs
                specs.append(fs)
            fs.options.append(_label_for(soup, el) or el.get("value", ""))
            continue

        label = _label_for(soup, el)
        ftype = guess_type(label, TYPE_MAP.get(itype, "text"))
        specs.append(FieldSpec(id=name, label=label, type=ftype, maxlen=maxlen, required=required,
                               hint=el.get("placeholder"), narrative=is_narrative(label, ftype, maxlen)))
    return specs, title
