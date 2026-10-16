"""Application lifecycle: template (cached per form) -> prefilled draft -> human review -> export.

There is no submit. Export is refused until the researcher has resolved every field (brief §5.2)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ..db.base import Store
from ..models.schemas import Applicant, Application, FormTemplate, Grant, ProjectProfile
from . import fetch as fetcher
from .mapper import has_placeholder, map_fields
from .docx_form import parse_docx
from .parse_html import parse_html
from .parse_pdf import parse_acroform, parse_flat


class ReviewIncomplete(Exception):
    def __init__(self, problems: list[dict]):
        super().__init__("review incomplete")
        self.problems = problems


def get_template(store: Store, form_ref: str, refresh: bool = False) -> FormTemplate:
    """Field extraction is the expensive step, so templates are cached per form, not per application."""
    cached = store.get_template_by_url(form_ref)
    if cached and not refresh:
        return cached
    form = fetcher.fetch(form_ref)
    if cached and cached.source_sha256 == form.sha256:
        return cached
    if form.kind == "pdf_acroform":
        fields, title = parse_acroform(form.data)
        extraction = "acroform"
    elif form.kind == "docx_form":
        fields, title = parse_docx(form.data)
        extraction = "docx"
    elif form.kind == "pdf_flat":
        fields, extraction = parse_flat(form.data)
        title = None
    else:
        fields, title = parse_html(form.data)
        extraction = "html"
    t = FormTemplate(
        id=cached.id if cached else str(uuid.uuid4()), form_url=form_ref, kind=form.kind, title=title,
        fields=fields, source_sha256=form.sha256, extraction=extraction,
    )
    store.save_template(t)
    return t


def create_application(
    store: Store, grant: Grant, template: FormTemplate, profile: ProjectProfile, applicant: Applicant
) -> Application:
    filled, used_llm = map_fields(template.fields, profile, applicant, grant)
    app = Application(id=str(uuid.uuid4()), grant_id=grant.id, template_id=template.id, fields=filled, llm_used=used_llm)
    store.save_application(app)
    return app


def update_fields(store: Store, app: Application, edits: list[dict]) -> Application:
    by_id = {f.field_id: f for f in app.fields}
    for e in edits:
        f = by_id.get(e.get("field_id"))
        if f is None:
            continue
        if "value" in e:
            v = e["value"]
            f.value = v
            f.source = "user"
            f.status = "green" if v not in (None, "", []) and not has_placeholder(v) else f.status
            f.confirmed = f.status == "green"
        if e.get("confirmed") is not None:
            f.confirmed = bool(e["confirmed"])
        if e.get("acknowledged_blank") is not None:
            f.acknowledged_blank = bool(e["acknowledged_blank"])
    app.reviewed, app.reviewed_at = False, None  # any edit re-opens review
    store.save_application(app)
    return app


def review_problems(app: Application) -> list[dict]:
    problems = []
    for f in app.fields:
        if has_placeholder(f.value):
            problems.append({"field_id": f.field_id, "label": f.label, "problem": "Draft still contains [YOU MUST ADD] placeholders"})
        elif f.status == "amber" and not f.confirmed:
            problems.append({"field_id": f.field_id, "label": f.label, "problem": "Inferred value not yet checked by you"})
        elif f.status == "red" and f.value in (None, "", []) and not f.acknowledged_blank:
            problems.append({"field_id": f.field_id, "label": f.label,
                             "problem": "Required field is empty" if f.required else "Empty - fill it or mark it intentionally blank"})
    return problems


def mark_reviewed(store: Store, app: Application, attest: bool) -> Application:
    if not attest:
        raise ReviewIncomplete([{"field_id": None, "label": "Final confirmation", "problem": "You must confirm you reviewed every field"}])
    problems = review_problems(app)
    if problems:
        raise ReviewIncomplete(problems)
    app.reviewed, app.reviewed_at = True, datetime.now(timezone.utc)
    store.save_application(app)
    return app
