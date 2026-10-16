from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routers import forms as forms_router


def test_export_refuses_a_changed_source_form(monkeypatch):
    monkeypatch.setattr(forms_router.fetcher, "fetch", lambda ref: SimpleNamespace(data=b"new form", sha256="b" * 64))
    with pytest.raises(HTTPException) as ex:
        forms_router._source(SimpleNamespace(form_url="https://funder.example/form.pdf", source_sha256="a" * 64))
    assert ex.value.status_code == 409
    same = SimpleNamespace(form_url="https://funder.example/form.pdf", source_sha256="b" * 64)
    assert forms_router._source(same) == b"new form"
