"""Form templates and application drafts. There is deliberately no submit endpoint."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel, Field

from ..deps import get_store
from ..forms import fetch as fetcher
from ..forms import fill
from ..forms.docx_form import fill_docx
from ..forms import service as forms
from ..models.schemas import Applicant, Application, FormTemplate, ProjectProfile

router = APIRouter()


def _grant(grant_id: str):
    g = get_store().get_grant(grant_id)
    if not g:
        raise HTTPException(404, "grant not found")
    return g


def _app(app_id: str) -> Application:
    a = get_store().get_application(app_id)
    if not a:
        raise HTTPException(404, "application not found")
    return a


@router.get("/grants/{grant_id}/form", response_model=FormTemplate)
def grant_form(grant_id: str, refresh: bool = False) -> FormTemplate:
    g = _grant(grant_id)
    if not g.form_url:
        raise HTTPException(404, "this opportunity has no known form - upload one via /forms/upload")
    try:
        return forms.get_template(get_store(), g.form_url, refresh=refresh)
    except Exception as ex:
        raise HTTPException(502, f"could not fetch or parse the form: {ex}") from ex


@router.post("/forms/upload", response_model=FormTemplate)
async def upload_form(file: UploadFile = File(...)) -> FormTemplate:
    data = await file.read()
    try:
        ref = fetcher.store_upload(data)
        return forms.get_template(get_store(), ref)
    except ValueError as ex:
        raise HTTPException(400, str(ex)) from ex


class CreateApplication(BaseModel):
    grant_id: str
    template_id: str | None = None  # defaults to the grant's own form
    profile: ProjectProfile
    applicant: Applicant = Field(default_factory=Applicant)


class ApplicationOut(BaseModel):
    application: Application
    template: FormTemplate
    summary: dict[str, int]
    problems: list[dict]


def _out(a: Application) -> ApplicationOut:
    t = get_store().get_template(a.template_id)
    return ApplicationOut(application=a, template=t, summary=a.summary(), problems=forms.review_problems(a))


@router.post("/applications", response_model=ApplicationOut)
def create_application(body: CreateApplication) -> ApplicationOut:
    store = get_store()
    g = _grant(body.grant_id)
    if body.template_id:
        t = store.get_template(body.template_id)
        if not t:
            raise HTTPException(404, "template not found")
    else:
        t = grant_form(g.id)
    return _out(forms.create_application(store, g, t, body.profile, body.applicant))


@router.get("/applications/{app_id}", response_model=ApplicationOut)
def get_application(app_id: str) -> ApplicationOut:
    return _out(_app(app_id))


class Edits(BaseModel):
    edits: list[dict] = Field(max_length=500)


@router.patch("/applications/{app_id}", response_model=ApplicationOut)
def edit_application(app_id: str, body: Edits) -> ApplicationOut:
    return _out(forms.update_fields(get_store(), _app(app_id), body.edits))


class Review(BaseModel):
    attest: bool


@router.post("/applications/{app_id}/review", response_model=ApplicationOut)
def review(app_id: str, body: Review):
    try:
        return _out(forms.mark_reviewed(get_store(), _app(app_id), body.attest))
    except forms.ReviewIncomplete as ex:
        return JSONResponse(status_code=422, content={"detail": "review incomplete", "problems": ex.problems})


@router.get("/applications/{app_id}/export")
def export(app_id: str, format: str = Query("pdf", pattern="^(pdf|docx|json|portal|md)$")):
    store = get_store()
    a = _app(app_id)
    if not a.reviewed:
        raise HTTPException(403, "Export is locked until you complete the review screen.")
    t = store.get_template(a.template_id)
    g = _grant(a.grant_id)
    name = "".join(c if c.isalnum() else "-" for c in g.title.lower())[:60].strip("-")
    if format == "pdf":
        if t.kind != "pdf_acroform":
            raise HTTPException(400, "PDF export is only available for fillable PDF forms; use format=md or json")
        pdf = fill.fill_pdf(fetcher.fetch(t.form_url).data, a.fields)
        return Response(pdf, media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{name}-prefilled.pdf"'})
    if format == "docx":
        if t.kind != "docx_form":
            raise HTTPException(400, "Word export is only available for .docx forms; use format=md or json")
        out = fill_docx(fetcher.fetch(t.form_url).data, {f.field_id: f.value for f in a.fields})
        return Response(out, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        headers={"Content-Disposition": f'attachment; filename="{name}-prefilled.docx"'})
    if format == "portal":
        return JSONResponse(fill.portal_payload(a, g, t), headers={"Content-Disposition": f'attachment; filename="{name}.portal.json"'})
    if format == "json":
        return JSONResponse(fill.web_payload(a), headers={"Content-Disposition": f'attachment; filename="{name}.json"'})
    return PlainTextResponse(fill.copy_paste_pack(a, g, t), media_type="text/markdown",
                             headers={"Content-Disposition": f'attachment; filename="{name}.md"'})


@router.get("/demo-forms/{name}")
def demo_form(name: str):
    p = (fetcher.DEMO_DIR / name).resolve()
    if fetcher.DEMO_DIR.resolve() not in p.parents or not p.exists():
        raise HTTPException(404, "not found")
    media = {".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}.get(p.suffix, "text/html")
    return Response(p.read_bytes(), media_type=media)
