from app.services.contract_service import generate_contract


def test_contract_fills_all_fields():
    data = {
        "kundenname": "Schaufler Fischer Group",
        "kunde_adresse": "Musterstraße 1, 12345 Musterstadt",
        "ansprechpartner_name": "Max Mustermann",
        "ansprechpartner_email": "max@schaufler.de",
        "projektstart_datum": "2026-08-01",
        "setup_preis": "5000",
        "monatliche_rate": "800",
        "erp_system": "ProAlpha",
        "it_kontakt_name": "IT Support",
        "it_kontakt_email": "it@schaufler.de",
        "bestellnummer": "BEST-127412",
        "bestelldatum": "2026-07-01",
        "angebotsnummer": "AG0024",
        "angebotsdatum": "2026-06-15",
    }
    contract = generate_contract(data, "Beschaffungsagent", "Beschaffungsdokumenten", ["AB-Abgleich", "Mahnwesen"])

    assert "Schaufler Fischer Group" in contract
    assert "Max Mustermann" in contract
    assert "Beschaffungsagent" in contract
    assert "- AB-Abgleich" in contract
    assert "- Mahnwesen" in contract
    assert "5000" in contract
    assert "800" in contract
    assert "ProAlpha" in contract
    assert "AG0024" in contract


def test_contract_uses_fallback_for_missing_optional_fields():
    data = {
        "kundenname": "Minimal GmbH",
        "ansprechpartner_name": "A",
        "ansprechpartner_email": "a@minimal.de",
        "projektstart_datum": "2026-08-01",
        "setup_preis": "1000",
        "monatliche_rate": "100",
    }
    contract = generate_contract(data, "Stücklistenagent", "Stücklisten", [])

    assert "— bitte ergänzen —" in contract
    assert "(keine Features ausgewählt)" in contract
