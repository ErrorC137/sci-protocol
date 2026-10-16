"""Word (.docx) application forms - the most common format for Thai agency forms.

Field sources, in document order:
  sdt   content controls (w:sdt): text, checkbox, dropdown, date
  ff    legacy form fields (FORMTEXT / FORMCHECKBOX / FORMDROPDOWN)
  cell  a table cell that is blank (or only dots/underscores) next to, or below, a label cell
  blank a run of dots/underscores in a paragraph ("ชื่อ.................. นามสกุล..................")
  lines label-less dotted lines under a heading ("บทคัดย่อ" + three dotted lines), merged into one field
  cb    a ☐/□ glyph followed by its label text

parse() and fill() walk the document identically, so field ids are stable between the two.

A wrong label is worse than no label: a mislabelled field can be auto-filled with the wrong data and shown as
done. Whenever the caption is uncertain the label is left empty, and the mapper asks the researcher.
"""

from __future__ import annotations

import bisect
import copy
import io
import re
import zipfile
from dataclasses import dataclass
from typing import Callable

from docx import Document
from docx.oxml.ns import qn
from lxml import etree

from ..models.schemas import FieldSpec
from .fieldkind import guess_type, humanize, is_narrative

W14 = "http://schemas.microsoft.com/office/word/2010/wordml"
W15 = "http://schemas.microsoft.com/office/word/2012/wordml"
MC_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
BLANK_RE = re.compile(r"[\.…_]{4,}|(?:\. ){4,}")
CHECK_EMPTY, CHECK_FULL = "☐□", "☒"
GLYPH_RE = re.compile(f"[{CHECK_EMPTY}{CHECK_FULL}]")
ONLY_BLANK = re.compile(r"^[\s\.…_:：]*$")
MAX_LABEL = 160
OPAQUE = "\x00"  # stands in for text owned by another field (content control, field result, text box)
BREAK_RE = re.compile(f"[{CHECK_EMPTY}{CHECK_FULL}{OPAQUE}]|{BLANK_RE.pattern}")
# A unit written right after a blank ("...... บาท"); the lookahead stops "วัน" matching "วันที่", "ปี" matching "ปีงบประมาณ".
UNIT_RE = re.compile(r"\s*(ล้านบาท|บาท|เดือน|ปี|วัน|คน|ราย|%|baht|months|years|USD|THB)"
                     r"(?![^\W\d_]|[\u0e31\u0e34-\u0e3a\u0e47-\u0e4e])", re.I)
NUMBERING = re.compile(r"\(?(?:[\d๐-๙]+|[a-zA-Zก-ฮ])[.)]?")  # "1", "1.", "(1)", "ก." - a row number, not a caption
XML_ILLEGAL = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")
MAX_XML_PART, MAX_UNZIPPED, MAX_ENTRIES = 30 << 20, 100 << 20, 2000
# Content controls that are structure, not answers: building blocks (TOC, cover page), groups, pictures, repeaters.
NOT_FIELD_PR = {qn("w:docPartObj"), qn("w:docPartList"), qn("w:group"), qn("w:picture"), qn("w:citation"),
                qn("w:bibliography"), qn("w:equation"), f"{{{W15}}}repeatingSection", f"{{{W15}}}repeatingSectionItem"}
CONTAINER_CONTENT = (qn("w:tbl"), qn("w:tr"), qn("w:tc"), qn("w:sdt"), qn("w:ffData"))


def _clean_label(s: str) -> str:
    s = BLANK_RE.sub(" ", s.replace(OPAQUE, " "))
    s = re.sub(r"\s+", " ", s).strip(" :：-–\t")
    return s[:MAX_LABEL] if any(ch.isalpha() for ch in s) else ""


def _before_label(seg: str) -> str:
    """Caption written before a field: only the text after the last blank / ☐ / other field."""
    return _clean_label(BREAK_RE.split(seg)[-1])


def _after_label(seg: str) -> str:
    return _clean_label(BREAK_RE.split(seg)[0])


def _with_unit(label: str, after: str) -> str:
    m = UNIT_RE.match(after)
    if label and m and f"({m.group(1)})" not in label:
        return f"{label} ({m.group(1)})"
    return label


def _box_labels(befores: list[str], afters: list[str]) -> list[str]:
    """Checkbox captions normally follow the box ("☐ Yes ☐ No"). When the last box has nothing after it and the
    first has a caption before it that is not a prompt ("Yes ☐ No ☐", not "Tick one: ☐ A ☐ B ☐"), they lead."""
    after = [_after_label(s) for s in afters]
    if after and not after[-1]:
        lead = BREAK_RE.split(befores[0])[-1].strip()
        if _clean_label(lead) and not lead.endswith((":", "：")):
            return [_before_label(s) for s in befores]
    return after


def _squash(s: str, n: int) -> str:
    s = BLANK_RE.sub("…", re.sub(f"{OPAQUE}+", "…", s))
    return re.sub(r"\s+", " ", s).strip()[:n]


def _ival(el, default: int = 0) -> int:
    try:
        return int(el.get(qn("w:val")))
    except (AttributeError, TypeError, ValueError):
        return default


def _attr(el) -> str:
    return (el.get(qn("w:val")) or "").strip() if el is not None else ""


def _ancestor(el, tags: tuple[str, ...], stop: tuple[str, ...] = ()):
    p = el.getparent()
    while p is not None and p.tag not in stop:
        if p.tag in tags:
            return p
        p = p.getparent()
    return None


def _tag_label(tag: str) -> str:
    """A w:tag is an author-chosen key ('applicant_name'); opaque ids (GUIDs, numbers) are not captions."""
    if not tag or re.fullmatch(r"\{?[0-9a-fA-F-]{8,}\}?", tag):
        return ""
    return _clean_label(humanize(tag))


def _kids(el, tag: str) -> list:
    """Children with this tag, looking through row/cell-level content controls that wrap them."""
    out = []
    for ch in el:
        if ch.tag == tag:
            out.append(ch)
        elif ch.tag == qn("w:sdt") and ch.find(qn("w:sdtContent")) is not None:
            out.extend(_kids(ch.find(qn("w:sdtContent")), tag))
    return out


def _is_field_sdt(sdt) -> bool:
    pr, content = sdt.find(qn("w:sdtPr")), sdt.find(qn("w:sdtContent"))
    if pr is None or content is None or _ancestor(sdt, (MC_FALLBACK,)) is not None:
        return False
    if any(ch.tag in NOT_FIELD_PR for ch in pr):
        return False
    return next(content.iter(*CONTAINER_CONTENT), None) is None


@dataclass
class _Site:
    """Where a field lives in the XML, so fill() can write to it."""

    kind: str
    el: object
    extra: dict


class _Grid:
    """A table as rows of physical cells, plus the logical columns each cell covers (gridBefore / gridSpan),
    so 'the cell above' means the same column even when cells are merged."""

    def __init__(self, t: int, tbl):
        self.t, self.tbl = t, tbl
        trs = _kids(tbl, qn("w:tr"))
        self.rows = [_kids(tr, qn("w:tc")) for tr in trs]
        self.starts: list[list[int]] = []
        self.spans: list[list[tuple[int, object]]] = []
        self.pos: dict = {}  # cell -> (row, physical index, first logical column, is a vMerge continuation)
        for r, (tr, cells) in enumerate(zip(trs, self.rows)):
            trpr = tr.find(qn("w:trPr"))
            col = max(0, _ival(trpr.find(qn("w:gridBefore")) if trpr is not None else None))
            starts, spans = [], []
            for c, tc in enumerate(cells):
                pr = tc.find(qn("w:tcPr"))
                vm = pr.find(qn("w:vMerge")) if pr is not None else None
                self.pos[tc] = (r, c, col, vm is not None and vm.get(qn("w:val")) != "restart")
                starts.append(col)
                spans.append((col + max(1, _ival(pr.find(qn("w:gridSpan")) if pr is not None else None, 1)), tc))
                col = spans[-1][0]
            self.starts.append(starts)
            self.spans.append(spans)

    def at(self, r: int, col: int):
        if not 0 <= r < len(self.rows) or col < 0:
            return None
        k = bisect.bisect_right(self.starts[r], col) - 1
        return self.spans[r][k][1] if k >= 0 and col < self.spans[r][k][0] else None

    def cell(self, r: int, col: int):
        """The cell shown at (r, col): a vertically merged continuation resolves to the cell starting the merge."""
        tc = self.at(r, col)
        while tc is not None and self.pos[tc][3] and r > 0:
            r -= 1
            tc = self.at(r, col)
        return tc


class _Doc:
    """Facts every field finder shares: which content controls are fields, where each table cell sits, and the
    reading order of paragraphs in each body / cell."""

    def __init__(self, body):
        self.body = body
        self.sdts = list(body.iter(qn("w:sdt")))
        self.sdt_index = {s: i for i, s in enumerate(self.sdts)}
        self.field_sdts = {s for s in self.sdts if _is_field_sdt(s)}
        self.grids = [_Grid(t, tbl) for t, tbl in enumerate(body.iter(qn("w:tbl")))]
        self.cellpos = {tc: g for g in self.grids for tc in g.pos}
        self._blocks: dict = {}
        self._where: dict = {}  # block element -> its index in its container's blocks()
        self._tokens: dict = {}

    # -- text ---------------------------------------------------------------------------------------------
    def owned(self, t, stop) -> bool:
        """Is this w:t inside a field content control, a simple field or a text box (below `stop`)?"""
        p = t.getparent()
        while p is not None and p is not stop:
            if p.tag in (qn("w:txbxContent"), qn("w:fldSimple")) or (p.tag == qn("w:sdt") and p in self.field_sdts):
                return True
            p = p.getparent()
        return False

    def vis(self, el) -> str:
        """Visible text with other fields' text (control content, field codes/results, text boxes) blanked to
        OPAQUE - same length as the raw w:t text, so offsets still line up with _replace_span."""
        out, depth = [], 0
        for x in el.iter(qn("w:t"), qn("w:fldChar")):
            if x.tag == qn("w:fldChar"):
                kind = x.get(qn("w:fldCharType"))
                depth = depth + 1 if kind == "begin" else max(0, depth - 1) if kind == "end" else depth
                continue
            s = x.text or ""
            out.append(OPAQUE * len(s) if depth or self.owned(x, el) else s)
        return "".join(out)

    def has_field(self, el) -> bool:
        return (next(el.iter(qn("w:fldChar")), None) is not None
                or any(s in self.field_sdts for s in el.iter(qn("w:sdt"))))

    def in_field(self, el) -> bool:
        p = el.getparent()
        while p is not None:
            if p.tag == qn("w:sdt") and p in self.field_sdts:
                return True
            p = p.getparent()
        return False

    def tokens(self, p) -> list:
        """A paragraph as visible text strings split by field markers ('x', element): field content controls,
        complex fields (marked at 'begin'; code and result are dropped), simple fields and text boxes."""
        if p in self._tokens:
            return self._tokens[p]
        out: list = []
        depth = 0

        def walk(el):
            nonlocal depth
            for ch in el:
                tag = ch.tag
                if tag == qn("w:t"):
                    if not depth:
                        out.append(ch.text or "")
                elif tag == qn("w:fldChar"):
                    kind = ch.get(qn("w:fldCharType"))
                    if kind == "begin":
                        if not depth:
                            out.append(("x", ch))
                        depth += 1
                    elif kind == "end" and depth:
                        depth -= 1
                elif (tag == qn("w:sdt") and ch in self.field_sdts) or tag in (qn("w:txbxContent"), qn("w:fldSimple")):
                    out.append(("x", ch))
                else:
                    walk(ch)

        walk(p)
        self._tokens[p] = out
        return out

    def around(self, p, el) -> tuple[str, str]:
        """Text between the previous field and `el`, and between `el` and the next field, in paragraph p."""
        toks = self.tokens(p)
        j = next((k for k, t in enumerate(toks) if not isinstance(t, str) and t[1] is el), None)
        if j is None:
            return "", ""
        a = j
        while a > 0 and isinstance(toks[a - 1], str):
            a -= 1
        b = j + 1
        while b < len(toks) and isinstance(toks[b], str):
            b += 1
        return "".join(toks[a:j]), "".join(toks[j + 1:b])

    def box_label(self, p, el) -> str:
        boxes = [t[1] for t in self.tokens(p) if not isinstance(t, str) and _is_box(t[1])]
        if el not in boxes:
            return ""
        sides = [self.around(p, b) for b in boxes]
        return _box_labels([s[0] for s in sides], [s[1] for s in sides])[boxes.index(el)]

    # -- reading order --------------------------------------------------------------------------------------
    def blocks(self, container) -> list[tuple[str | None, object]]:
        """(local id, w:p) for each paragraph of a body / cell in reading order, looking through content controls
        that are not fields; (None, el) for tables and field controls, which interrupt a run of paragraphs.
        Ids count direct paragraphs only (p0, p1, ...), so they match the ids of earlier versions."""
        if container in self._blocks:
            return self._blocks[container]
        out: list[tuple[str | None, object]] = []

        def walk(parent, pre: str):
            n = 0
            for ch in parent:
                if ch.tag == qn("w:p"):
                    out.append((f"{pre}p{n}", ch))
                    n += 1
                elif ch.tag == qn("w:sdt") and ch not in self.field_sdts and ch.find(qn("w:sdtContent")) is not None:
                    walk(ch.find(qn("w:sdtContent")), f"sdt{self.sdt_index[ch]}:")
                elif ch.tag in (qn("w:tbl"), qn("w:sdt")):
                    out.append((None, ch))

        walk(container, "")
        self._blocks[container] = out
        self._where.update((el, k) for k, (_, el) in enumerate(out))
        return out

    def prev_para(self, el):
        """The nearest earlier paragraph with any content in el's body/cell; None if a table or field control,
        or the start of the cell, comes first."""
        cont = _ancestor(el, (qn("w:body"), qn("w:tc")), (qn("w:txbxContent"),))
        if cont is None:
            return None, ""
        seq = self.blocks(cont)
        k = self._where.get(el)
        if k is None or seq[k][1] is not el:
            return None, ""
        for pid, b in reversed(seq[:k]):
            if pid is None:
                return None, ""
            text = self.vis(b)
            if text.strip() or self.has_field(b):
                return b, text
        return None, ""

    def label_para(self, el) -> str:
        """The previous paragraph as a caption for el - only if it is plain text, not another field's line,
        and not a '( ... )' caption that belongs to the field above it."""
        p, text = self.prev_para(el)
        if p is None or self.has_field(p) or BREAK_RE.search(text):
            return ""
        s = text.strip()
        return "" if s.startswith("(") and s.endswith(")") else _clean_label(text)

    def para_hint(self, p, text: str) -> str:
        prev = _squash(self.prev_para(p)[1], 120)
        return _squash(text, 200) + (f" | prev: {prev}" if prev else "")

    # -- tables -------------------------------------------------------------------------------------------
    def caption(self, tc) -> str:
        """Text of a cell usable as another cell's label: plain text only - no fields, blanks, ☐ or row numbers."""
        if tc is None or self.has_field(tc):
            return ""
        text = self.vis(tc)
        if ONLY_BLANK.match(text) or BREAK_RE.search(text):
            return ""
        label = _clean_label(text)
        return "" if NUMBERING.fullmatch(label) else label

    def blank_cell(self, tc) -> bool:
        return not self.has_field(tc) and bool(ONLY_BLANK.match(self.vis(tc)))

    def cell_label(self, g: _Grid, r: int, col: int) -> tuple[str, str, int]:
        """(label, how, header row) for a blank cell: the label cell to its left, the one above, or - for the data
        rows of a repeating table - the column header further up, numbered by row ('ชื่อ-สกุล (2)')."""
        label = self.caption(g.at(r, col - 1))
        if label:
            return label, "left", r
        label = self.caption(g.cell(r - 1, col)) if r > 0 else ""
        if label:
            return label, "above", r - 1
        for up in range(r - 1, -1, -1):
            h = g.cell(up, col)
            if h is None:
                continue
            label = self.caption(h)
            if label:
                return f"{label} ({r - up})", "row", up
            if not self.blank_cell(h):
                break
        return "", "", -1

    def neighbour_label(self, host, field_el) -> str:
        """Caption for a control / form field with no text of its own: the cell to the left (or above) - only for
        the first field in its cell - else the paragraph before."""
        tc = _ancestor(host, (qn("w:tc"),), (qn("w:txbxContent"),))
        g = self.cellpos.get(tc) if tc is not None else None
        if g is not None and self.first_field(tc) is field_el:
            r, _, col, _ = g.pos[tc]
            label = self.caption(g.at(r, col - 1)) or (self.caption(g.cell(r - 1, col)) if r > 0 else "")
            if label:
                return label
        return self.label_para(host)

    def first_field(self, tc):
        for x in tc.iter(qn("w:sdt"), qn("w:fldChar")):
            if (x.tag == qn("w:sdt") and x in self.field_sdts) or x.find(qn("w:ffData")) is not None:
                return x
        return None


def _is_box(el) -> bool:
    if el.tag == qn("w:sdt"):
        pr = el.find(qn("w:sdtPr"))
        return pr is not None and pr.find(f"{{{W14}}}checkbox") is not None
    ff = el.find(qn("w:ffData")) if el.tag == qn("w:fldChar") else None
    return ff is not None and ff.find(qn("w:checkBox")) is not None


def _sdt_fields(cx: _Doc) -> list[tuple[FieldSpec, _Site]]:
    found, used = [], set()
    for i, sdt in enumerate(cx.sdts):
        if sdt not in cx.field_sdts:
            continue
        pr, content = sdt.find(qn("w:sdtPr")), sdt.find(qn("w:sdtContent"))
        tag = _attr(pr.find(qn("w:tag")))
        ftype, options = "text", []
        lst = pr.find(qn("w:dropDownList"))
        lst = lst if lst is not None else pr.find(qn("w:comboBox"))
        if pr.find(f"{{{W14}}}checkbox") is not None:
            ftype = "checkbox"
        elif lst is not None:
            ftype = "select"
            options = [li.get(qn("w:displayText")) or li.get(qn("w:value")) or "" for li in lst.findall(qn("w:listItem"))]
        elif pr.find(qn("w:date")) is not None:
            ftype = "date"
        label = _clean_label(_attr(pr.find(qn("w:alias")))) or _tag_label(tag)
        if not label:
            p = _ancestor(sdt, (qn("w:p"),), (qn("w:body"), qn("w:tc"), qn("w:txbxContent")))
            if p is not None and ftype == "checkbox":
                label = cx.box_label(p, sdt)
            elif p is not None:  # inline control: caption before it in the paragraph, else its cell / paragraph
                before, after = cx.around(p, sdt)
                label = _with_unit(_before_label(before) or cx.neighbour_label(p, sdt), after)
            elif ftype != "checkbox":
                label = cx.neighbour_label(sdt, sdt)
        fid = f"sdt:{tag}" if tag else f"sdt:{i}"
        while fid in used:  # duplicate tags: the first keeps sdt:{tag}, later ones get their document index
            fid = f"{fid}:{i}"
        used.add(fid)
        ftype = guess_type(label, ftype)
        found.append((FieldSpec(id=fid, label=label, type=ftype, options=options, narrative=is_narrative(label, ftype, None)),
                      _Site("sdt", content, {"sdt": sdt})))
    return found


def _ff_fields(cx: _Doc) -> list[tuple[FieldSpec, _Site]]:
    found, used = [], set()
    for i, fc in enumerate(cx.body.iter(qn("w:fldChar"))):
        ff = fc.find(qn("w:ffData")) if fc.get(qn("w:fldCharType")) == "begin" else None
        if ff is None or _ancestor(fc, (MC_FALLBACK,)) is not None:
            continue
        name = _attr(ff.find(qn("w:name")))
        run = fc.getparent()
        p = _ancestor(fc, (qn("w:p"),))
        dd = ff.find(qn("w:ddList"))
        maxlen, options = None, []
        if ff.find(qn("w:checkBox")) is not None:
            ftype = "checkbox"
            label = cx.box_label(p, fc) if p is not None else ""
        else:
            if dd is not None:
                ftype = "select"
                options = [e.get(qn("w:val")) or "" for e in dd.findall(qn("w:listEntry"))]
            else:
                ti = ff.find(qn("w:textInput"))
                ml = ti.find(qn("w:maxLength")) if ti is not None else None
                ftype, maxlen = "text", (_ival(ml) or None) if ml is not None else None
            label = ""
            if p is not None:
                before, after = cx.around(p, fc)
                label = _before_label(before) or cx.neighbour_label(p, fc)
                label = _with_unit(label, after) if ftype == "text" else label
        label = label or (_clean_label(humanize(name)) if name else "")
        fid = f"ff:{name or f'ff{i}'}"
        while fid in used:
            fid = f"{fid}:{i}"
        used.add(fid)
        ftype = guess_type(label, ftype)
        found.append((FieldSpec(id=fid, label=label, type=ftype, options=options, maxlen=maxlen,
                                narrative=is_narrative(label, ftype, maxlen)), _Site("ff", run, {"ff": ff, "fc": fc})))
    return found


def _para_fields(cx: _Doc, p, pid: str) -> list[tuple[FieldSpec, _Site]]:
    """Dotted blanks and ☐ glyphs in one paragraph. Paragraphs holding a control or a field code are skipped:
    their text is not a reliable caption for anything."""
    if cx.in_field(p) or cx.has_field(p):
        return []
    text = cx.vis(p)
    out: list[tuple[FieldSpec, _Site]] = []
    hint = None
    end = 0
    for k, m in enumerate(BLANK_RE.finditer(text)):
        seg, end = text[end:m.start()], m.end()
        unit = UNIT_RE.match(text, end)
        label = _with_unit(_before_label(seg), text[end:])
        if unit:
            end = unit.end()  # the unit belongs to this blank, not to the next blank's caption
        if not label:
            continue
        hint = hint or cx.para_hint(p, text)
        ftype = guess_type(label)
        out.append((FieldSpec(id=f"{pid}:b{k}", label=label, type=ftype, narrative=is_narrative(label, ftype, None), hint=hint),
                    _Site("blank", p, {"start": m.start(), "end": m.end()})))
    glyphs = list(GLYPH_RE.finditer(text))
    befores = [text[(glyphs[k - 1].end() if k else 0):m.start()] for k, m in enumerate(glyphs)]
    afters = [text[m.end():(glyphs[k + 1].start() if k + 1 < len(glyphs) else len(text))] for k, m in enumerate(glyphs)]
    k = 0
    for m, label in zip(glyphs, _box_labels(befores, afters)):
        if m.group() not in CHECK_EMPTY:
            continue
        if label:
            hint = hint or cx.para_hint(p, text)
            out.append((FieldSpec(id=f"{pid}:cb{k}", label=label, type="checkbox", hint=hint),
                        _Site("glyph", p, {"pos": m.start()})))
        k += 1
    return out


def _seq_fields(cx: _Doc, container, prefix: str) -> list[tuple[FieldSpec, _Site]]:
    """Paragraph fields of a body / cell. Consecutive dotted-only lines with no caption of their own become ONE
    field labelled by the heading above them (the first line's id; the value goes into the first line)."""
    def dotted(p) -> bool:
        if cx.in_field(p) or cx.has_field(p):
            return False
        text = cx.vis(p)
        return bool(ONLY_BLANK.match(text) and BLANK_RE.search(text))

    def empty(p) -> bool:
        return not cx.has_field(p) and not cx.vis(p).strip()

    out, seq, k = [], cx.blocks(container), 0
    while k < len(seq):
        pid, p = seq[k]
        k += 1
        if pid is None:
            continue
        if not dotted(p):
            out.extend(_para_fields(cx, p, prefix + pid))
            continue
        group = [p]
        while k < len(seq) and seq[k][0] is not None and (dotted(seq[k][1]) or empty(seq[k][1])):
            if dotted(seq[k][1]):
                group.append(seq[k][1])
            k += 1
        label = cx.label_para(p)
        if not label:
            continue
        text = cx.vis(p)
        spans = [m.span() for m in BLANK_RE.finditer(text)]
        rest = [(q, [m.span() for m in BLANK_RE.finditer(cx.vis(q))]) for q in group[1:]]
        ftype = guess_type(label)
        narrative = is_narrative(label, ftype, None)
        out.append((FieldSpec(id=f"{prefix}{pid}:b0", label=label, type="textarea" if narrative else ftype,
                              narrative=narrative, hint=cx.para_hint(p, text)),
                    _Site("lines", p, {"start": spans[0][0], "end": spans[-1][1], "rest": rest})))
    return out


def _table_fields(cx: _Doc) -> list[tuple[FieldSpec, _Site]]:
    found = []
    for g in cx.grids:
        if _ancestor(g.tbl, (MC_FALLBACK,)) is not None:
            continue  # the legacy copy of a text box's content
        for r, cells in enumerate(g.rows):
            for c, cell in enumerate(cells):
                _, _, col, cont = g.pos[cell]
                if cont or cx.in_field(cell) or cx.has_field(cell):
                    continue  # merged continuations are never fields; cells holding controls are not blanks
                prefix = f"tbl{g.t}:r{r}:c{c}"
                if not ONLY_BLANK.match(cx.vis(cell)):
                    found.extend(_seq_fields(cx, cell, prefix + ":"))  # label cells may still hold blanks/boxes
                    continue
                label, how, hr = cx.cell_label(g, r, col)
                if not label:
                    continue
                hint = None
                below = g.at(r + 1, col)
                first_row = (how == "above" and below is not None and not g.pos[below][3] and cx.blank_cell(below)
                             and cx.cell_label(g, r + 1, g.pos[below][2])[1:] == ("row", hr))
                if how == "row" or first_row:  # a data row of a repeating table: whose row it is is unknown
                    header = " / ".join(s for s in (_squash(cx.vis(h), 60) for h in g.rows[hr]) if s)
                    hint = f"[table row] {_squash(cx.prev_para(g.tbl)[1], 100)} | {header}"
                big = len(cell.findall(qn("w:p"))) >= 3 or how == "above"
                ftype = "textarea" if big and is_narrative(label, "text", None) else guess_type(label)
                found.append((FieldSpec(id=prefix, label=label, type=ftype, narrative=is_narrative(label, ftype, None),
                                        hint=hint), _Site("cell", cell, {})))
    return found


def _walk(doc) -> list[tuple[FieldSpec, _Site]]:
    body = doc.element.body
    cx = _Doc(body)
    found = _sdt_fields(cx) + _ff_fields(cx) + _table_fields(cx) + _seq_fields(cx, body, "")
    # Present fields in reading order (document position, then offset within a paragraph).
    order = {id(el): i for i, el in enumerate(body.iter())}
    found.sort(key=lambda fs: (order.get(id(fs[1].el), 0), fs[1].extra.get("start", fs[1].extra.get("pos", 0))))
    return found


def _open(data: bytes):
    """Check the zip before python-docx inflates it: declared sizes bound what zipfile will ever decompress."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            infos = zf.infolist()
    except Exception as ex:
        raise ValueError("not a valid Word .docx file (cannot open it as a zip archive)") from ex
    if len(infos) > MAX_ENTRIES:
        raise ValueError(f"Word file has too many parts ({len(infos)} > {MAX_ENTRIES})")
    if sum(i.file_size for i in infos) > MAX_UNZIPPED:
        raise ValueError(f"Word file is too large when unpacked (over {MAX_UNZIPPED >> 20} MB)")
    big = next((i.filename for i in infos if i.file_size > MAX_XML_PART and i.filename.endswith((".xml", ".rels"))), None)
    if big:
        raise ValueError(f"Word file part {big} is too large (over {MAX_XML_PART >> 20} MB)")
    try:
        return Document(io.BytesIO(data))
    except Exception as ex:
        raise ValueError(f"not a readable Word .docx file ({type(ex).__name__})") from ex


def parse_docx(data: bytes) -> tuple[list[FieldSpec], str | None]:
    doc = _open(data)
    try:
        title = doc.core_properties.title or None
        if not title:
            first = next((p.text.strip() for p in doc.paragraphs if p.text.strip()), None)
            title = first[:120] if first else None
        specs, seen = [], set()
        for spec, _ in _walk(doc):
            if spec.id not in seen:
                seen.add(spec.id)
                specs.append(spec)
    except Exception as ex:
        raise ValueError(f"could not read the fields of this Word form ({type(ex).__name__})") from ex
    return specs, title


# ---------------------------------------------------------------------------
# Filling
# ---------------------------------------------------------------------------

def _as_text(v) -> str:
    if v is None:
        s = ""
    elif isinstance(v, list):
        s = ", ".join(_as_text(x) for x in v)
    elif isinstance(v, bool):
        s = "Yes" if v else "No"
    else:
        s = str(v)
    return XML_ILLEGAL.sub("", s.replace("\r\n", "\n").replace("\r", "\n"))


def _set_t(t, text: str) -> None:
    """Set a w:t's text; newlines become w:br + w:t siblings in the same run."""
    lines = text.split("\n")
    t.text = lines[0]
    t.set(XML_SPACE, "preserve")
    for line in lines[1:]:
        br, nt = etree.Element(qn("w:br")), etree.Element(qn("w:t"))
        nt.text = line
        nt.set(XML_SPACE, "preserve")
        t.addnext(br)
        br.addnext(nt)
        t = nt


def _replace_span(p, start: int, end: int, new: str) -> None:
    """Replace characters [start, end) of a paragraph's text across runs, keeping the first run's formatting."""
    pos = 0
    first_t = None
    for t in list(p.iter(qn("w:t"))):
        s = t.text or ""
        a, b = pos, pos + len(s)
        pos = b
        if b <= start or a >= end:
            continue
        lo, hi = max(start, a) - a, min(end, b) - a
        if first_t is None:
            first_t = t
            _set_t(t, s[:lo] + new + s[hi:])
        else:
            _set_t(t, s[:lo] + s[hi:])


def _set_runs_text(container, value: str, template_run=None) -> None:
    """Make the container's (cell / sdtContent) first paragraph contain exactly `value`."""
    paras = container.findall(qn("w:p")) or [container]
    p = paras[0]
    runs = p.findall(qn("w:r"))
    base = template_run if template_run is not None else (runs[0] if runs else None)
    for r in runs:
        p.remove(r)
    new_r = copy.deepcopy(base) if base is not None else etree.SubElement(p, qn("w:r"))
    for child in list(new_r):
        if child.tag != qn("w:rPr"):
            new_r.remove(child)
    lines = value.split("\n")
    for i, line in enumerate(lines):
        t = etree.SubElement(new_r, qn("w:t"))
        t.text = line
        t.set(XML_SPACE, "preserve")
        if i < len(lines) - 1:
            etree.SubElement(new_r, qn("w:br"))
    if new_r.getparent() is None:
        p.append(new_r)


def _glyph(state, default: str) -> str:
    try:
        return chr(int(state.get(f"{{{W14}}}val"), 16))
    except (AttributeError, TypeError, ValueError, OverflowError):
        return default


def _ff_result(fc, value: str, create: bool) -> None:
    """Write `value` as the result of the complex field that begins at fc (between 'separate' and 'end')."""
    p = _ancestor(fc, (qn("w:p"),))
    if p is None:
        return
    depth, sep, end, texts = 0, None, None, []
    for x in p.iter(qn("w:fldChar"), qn("w:t")):
        if depth == 0 and x is not fc:
            continue
        if x.tag == qn("w:t"):
            if sep is not None and depth == 1:
                texts.append(x)
            continue
        kind = x.get(qn("w:fldCharType"))
        if kind == "begin":
            depth += 1
        elif kind == "separate" and depth == 1:
            sep = x
        elif kind == "end":
            depth -= 1
            if depth == 0:
                end = x
                break
    if end is None:
        return  # the field runs past this paragraph - leave it rather than guess
    if texts:
        _set_t(texts[0], value)
        for t in texts[1:]:
            t.text = ""
        return
    if not create:
        return
    end_run = end.getparent()
    if any(ch is not end and ch.tag != qn("w:rPr") for ch in end_run):  # 'end' shares its run: write inside it
        if sep is None:
            end.addprevious(etree.Element(qn("w:fldChar")))
            end.getprevious().set(qn("w:fldCharType"), "separate")
        t = etree.Element(qn("w:t"))
        end.addprevious(t)
        _set_t(t, value)
        return
    rpr = fc.getparent().find(qn("w:rPr"))

    def run():
        r = etree.Element(qn("w:r"))
        if rpr is not None:
            r.append(copy.deepcopy(rpr))
        return r

    if sep is None:
        r = run()
        etree.SubElement(r, qn("w:fldChar")).set(qn("w:fldCharType"), "separate")
        end_run.addprevious(r)
    r = run()
    t = etree.SubElement(r, qn("w:t"))
    end_run.addprevious(r)
    _set_t(t, value)


def fill_docx(data: bytes, values: dict[str, object]) -> bytes:
    doc = _open(data)
    try:
        return _fill(doc, values)
    except Exception as ex:
        raise ValueError(f"could not fill this Word form ({type(ex).__name__})") from ex


def _fill(doc, values: dict[str, object]) -> bytes:
    sites = _walk(doc)
    # Paragraph blanks shift character offsets, so fill them right-to-left within each paragraph.
    sites.sort(key=lambda fs: -(fs[1].extra.get("start", fs[1].extra.get("pos", 0))))

    def do_sdt(spec, site, v):
        pr = site.extra["sdt"].find(qn("w:sdtPr"))
        box = pr.find(f"{{{W14}}}checkbox")
        if box is not None:
            checked = box.find(f"{{{W14}}}checked")
            if checked is None:
                checked = etree.Element(f"{{{W14}}}checked")
                box.insert(0, checked)  # schema order: checked, checkedState, uncheckedState
            checked.set(f"{{{W14}}}val", "1" if v is True else "0")
            glyph = _glyph(box.find(f"{{{W14}}}checkedState" if v is True else f"{{{W14}}}uncheckedState"),
                           CHECK_FULL if v is True else "☐")
            ts = list(site.el.iter(qn("w:t")))
            if not ts:
                _set_runs_text(site.el, glyph)
            for k, t in enumerate(ts):
                t.text = glyph if k == 0 else ""
            return
        _set_runs_text(site.el, _as_text(v))
        # Otherwise Word keeps showing (and on click, clears) the value as placeholder text.
        for el in pr.findall(qn("w:showingPlcHdr")):
            pr.remove(el)
        for rs in list(site.el.iter(qn("w:rStyle"))):
            if rs.get(qn("w:val")) == "PlaceholderText":
                rs.getparent().remove(rs)

    def do_ff(spec, site, v):
        ff = site.extra["ff"]
        cb, dd = ff.find(qn("w:checkBox")), ff.find(qn("w:ddList"))
        if cb is not None:
            checked = cb.find(qn("w:checked"))
            if checked is None:
                checked = etree.SubElement(cb, qn("w:checked"))
            checked.set(qn("w:val"), "1" if v is True else "0")
            return
        text = _as_text(v)
        if dd is not None:
            opts = [e.get(qn("w:val")) for e in dd.findall(qn("w:listEntry"))]
            if text not in opts:
                return  # not one of the form's options: leave the selection alone
            res = dd.find(qn("w:result"))
            if res is None:
                res = etree.Element(qn("w:result"))
                dd.insert(0, res)  # schema order: result, default, listEntry*
            res.set(qn("w:val"), str(opts.index(text)))
            _ff_result(site.extra["fc"], text, create=False)
            return
        _ff_result(site.extra["fc"], text, create=True)

    def do_cell(spec, site, v):
        _set_runs_text(site.el, _as_text(v))

    def do_blank(spec, site, v):
        _replace_span(site.el, site.extra["start"], site.extra["end"], f" {_as_text(v)} ")

    def do_lines(spec, site, v):
        for p, spans in site.extra["rest"]:
            for a, b in reversed(spans):
                _replace_span(p, a, b, "")
        _replace_span(site.el, site.extra["start"], site.extra["end"], _as_text(v))

    def do_glyph(spec, site, v):
        if v is True:
            _replace_span(site.el, site.extra["pos"], site.extra["pos"] + 1, CHECK_FULL)

    handlers: dict[str, Callable] = {"sdt": do_sdt, "ff": do_ff, "cell": do_cell, "blank": do_blank, "lines": do_lines,
                                     "glyph": do_glyph}
    done = set()
    for spec, site in sites:
        if spec.id in done or spec.id not in values:
            continue
        v = values[spec.id]
        if v in (None, "", []):
            continue
        handlers[site.kind](spec, site, v)
        done.add(spec.id)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
