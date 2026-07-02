from app.routers.onboarding import _build_readme, _resolve_avv_data, _resolve_produkt_info
from app.services.github_service import slugify


def test_slugify_lowercases_and_replaces_spaces():
    assert slugify("Schaufler Fischer Group") == "schaufler-fischer-group"
    assert slugify("Müller_GmbH") == "müller-gmbh"


def test_resolve_produkt_info_for_beschaffungsagent():
    data = {"projekttyp": "beschaffungsagent", "features": ["AB-Abgleich", "Mahnwesen"]}
    name, beschreibung, features = _resolve_produkt_info(data)
    assert name == "Beschaffungsagent"
    assert "Beschaffungsdokumenten" in beschreibung
    assert features == ["AB-Abgleich", "Mahnwesen"]


def test_resolve_produkt_info_for_stuecklistenagent():
    data = {"projekttyp": "stuecklistenagent", "features": ["Triple-Lock Extraktion"]}
    name, _, features = _resolve_produkt_info(data)
    assert name == "Stücklistenagent"
    assert features == ["Triple-Lock Extraktion"]


def test_resolve_produkt_info_for_neues_projekt_uses_ai_fields():
    data = {
        "projekttyp": "neues_projekt",
        "produkt_name": "Individuallösung X",
        "contract_description": "Kurzbeschreibung für den Vertrag.",
        "features": ["Feature A"],
    }
    name, beschreibung, features = _resolve_produkt_info(data)
    assert name == "Individuallösung X"
    assert beschreibung == "Kurzbeschreibung für den Vertrag."
    assert features == ["Feature A"]


def test_resolve_avv_data_for_product_types_is_hardcoded():
    avv = _resolve_avv_data({"projekttyp": "beschaffungsagent"})
    assert avv["unterauftragnehmer_ki_land"] == "Irland"


def test_resolve_avv_data_for_neues_projekt_uses_data_fields():
    data = {
        "projekttyp": "neues_projekt",
        "produkt_name": "X",
        "unterauftragnehmer_ki_firma": "OpenAI Ireland Ltd.",
        "unterauftragnehmer_ki_land": "Irland",
    }
    avv = _resolve_avv_data(data)
    assert avv["unterauftragnehmer_ki_firma"] == "OpenAI Ireland Ltd."


def test_build_readme_includes_tech_stack_and_plan():
    data = {
        "project_title": "Endin Procurement Agent",
        "contract_description": "Automatisiert die Beschaffung.",
        "tech_stack": ["React", "FastAPI"],
        "implementation_plan": [
            {"phase": "Phase 1", "title": "Setup", "duration": "2 Wochen", "tasks": ["Repo aufsetzen", "CI einrichten"]}
        ],
    }
    readme = _build_readme(data)
    assert "# Endin Procurement Agent" in readme
    assert "- React" in readme
    assert "- FastAPI" in readme
    assert "Phase 1: Setup (2 Wochen)" in readme
    assert "- [ ] Repo aufsetzen" in readme
