import zipfile
from io import BytesIO

import pytest

from app.config import get_settings
from app.services.avv_service import (
    BESCHAFFUNGSAGENT_AVV,
    AvvTemplateMissing,
    build_replacements,
    fill_avv,
)


def _fake_docx_bytes(document_xml: str) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("word/document.xml", document_xml)
        z.writestr("[Content_Types].xml", "<Types/>")
    return buf.getvalue()


def test_build_replacements_maps_all_placeholders():
    data = {
        "kundenname": "Schaufler",
        "kunde_adresse": "Musterstraße 1",
        "bestellnummer": "BEST-1",
        "bestelldatum": "2026-07-01",
        "angebotsnummer": "AG0024",
        "angebotsdatum": "2026-06-15",
    }
    replacements = build_replacements(data, BESCHAFFUNGSAGENT_AVV)

    assert replacements["{{KUNDE_FIRMA}}"] == "Schaufler"
    assert replacements["{{PRODUKT_NAME}}"] == "Beschaffungsagent"
    assert replacements["{{UNTERAUFTRAGNEHMER_KI_LAND}}"] == "Irland"


def test_build_replacements_falls_back_for_missing_optional_fields():
    replacements = build_replacements({"kundenname": "Schaufler"}, BESCHAFFUNGSAGENT_AVV)
    assert replacements["{{KUNDE_ADRESSE}}"] == "— bitte ergänzen —"
    assert replacements["{{BESTELLNUMMER}}"] == "— bitte ergänzen —"


def test_fill_avv_replaces_placeholders_in_document_xml(tmp_path, monkeypatch):
    template = tmp_path / "AVV_Prozessia_TEMPLATE.docx"
    template.write_bytes(_fake_docx_bytes("<w:t>{{KUNDE_FIRMA}} - {{PRODUKT_NAME}}</w:t>"))
    monkeypatch.setattr(type(get_settings()), "avv_template_path", property(lambda self: template))
    get_settings.cache_clear()

    replacements = build_replacements({"kundenname": "Schaufler"}, BESCHAFFUNGSAGENT_AVV)
    result_bytes = fill_avv(replacements)

    with zipfile.ZipFile(BytesIO(result_bytes)) as z:
        content = z.read("word/document.xml").decode("utf-8")
    assert "Schaufler - Beschaffungsagent" in content
    assert "{{" not in content
    get_settings.cache_clear()


def test_fill_avv_raises_clear_error_when_template_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(type(get_settings()), "avv_template_path", property(lambda self: tmp_path / "missing.docx"))
    get_settings.cache_clear()

    with pytest.raises(AvvTemplateMissing):
        fill_avv({})
    get_settings.cache_clear()
