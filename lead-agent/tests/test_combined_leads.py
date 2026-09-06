from pathlib import Path

import close_client
import combined_leads as svc
import vault_leads
from close_client import CloseAPIError


class FakeSettings:
    def __init__(self, tmp_path):
        self.vault_path = tmp_path

    @property
    def leads_dir(self) -> Path:
        return self.vault_path / "Leads"


def _write(monkeypatch, tmp_path, firma, **updates):
    monkeypatch.setattr(vault_leads, "get_settings", lambda: FakeSettings(tmp_path))
    path = vault_leads.write_prospect(firma)
    if updates:
        vault_leads.update_fields(path, updates)
    return path


def test_vault_only_lead_without_close_match(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_leads, "get_settings", lambda: FakeSettings(tmp_path))
    _write(monkeypatch, tmp_path, "Muster GmbH", status="neu", score="4")
    monkeypatch.setattr(close_client, "search_leads", lambda query, limit=100: [])

    results = svc.get_combined_leads()

    assert len(results) == 1
    assert results[0]["firma"] == "Muster-GmbH"
    assert results[0]["quelle"] == "vault"
    assert results[0]["close_lead_id"] == ""


def test_merges_vault_lead_with_matching_close_lead(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_leads, "get_settings", lambda: FakeSettings(tmp_path))
    _write(monkeypatch, tmp_path, "Verknuepft AG", status="kontaktiert", score="7", close_lead_id="lead_1")
    monkeypatch.setattr(
        close_client, "search_leads",
        lambda query, limit=100: [{"id": "lead_1", "display_name": "Verknuepft AG", "status_label": "Qualified", "contacts": []}],
    )

    results = svc.get_combined_leads()

    assert len(results) == 1
    r = results[0]
    assert r["quelle"] == "beide"
    assert r["close_lead_id"] == "lead_1"
    assert r["close_link"] == "https://app.close.com/lead/lead_1/"
    # Vault-Status hat Vorrang vor Close-status_label, wenn beide vorhanden sind.
    assert r["status"] == "kontaktiert"


def test_close_only_lead_appears_without_vault_file(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_leads, "get_settings", lambda: FakeSettings(tmp_path))
    monkeypatch.setattr(
        close_client, "search_leads",
        lambda query, limit=100: [{"id": "lead_close_only", "display_name": "Nur In Close GmbH", "status_label": "New Lead", "contacts": []}],
    )

    results = svc.get_combined_leads()

    assert len(results) == 1
    assert results[0]["firma"] == "Nur In Close GmbH"
    assert results[0]["quelle"] == "close"
    assert results[0]["vault_path"] == ""


def test_vault_lead_with_close_id_excluded_when_close_filter_does_not_match(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_leads, "get_settings", lambda: FakeSettings(tmp_path))
    _write(monkeypatch, tmp_path, "Gefiltert Raus", status="neu", close_lead_id="lead_2")
    # Close-Suche mit Status-Filter liefert diesen Lead NICHT zurück -> muss
    # aus dem kombinierten Ergebnis verschwinden (AND-Semantik).
    monkeypatch.setattr(close_client, "search_leads", lambda query, limit=100: [])

    results = svc.get_combined_leads({"status": "qualifiziert"})

    assert results == []


def test_score_min_filters_out_lower_scored_vault_leads(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_leads, "get_settings", lambda: FakeSettings(tmp_path))
    _write(monkeypatch, tmp_path, "Niedriger Score", score="3")
    _write(monkeypatch, tmp_path, "Hoher Score", score="9")
    monkeypatch.setattr(close_client, "search_leads", lambda query, limit=100: [])

    results = svc.get_combined_leads({"score_min": "5"})

    firmen = {r["firma"] for r in results}
    assert firmen == {"Hoher-Score"}


def test_freitext_matches_vault_body(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_leads, "get_settings", lambda: FakeSettings(tmp_path))
    path = _write(monkeypatch, tmp_path, "Werkzeugbau Spezialist")
    path.write_text(path.read_text(encoding="utf-8") + "\nSchwerpunkt: Kunststoffverarbeitung.\n", encoding="utf-8")
    monkeypatch.setattr(close_client, "search_leads", lambda query, limit=100: [])

    results = svc.get_combined_leads({"freitext": "kunststoffverarbeitung"})

    assert len(results) == 1
    assert results[0]["firma"] == "Werkzeugbau-Spezialist"


def test_quelle_filter_restricts_to_one_source(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_leads, "get_settings", lambda: FakeSettings(tmp_path))
    _write(monkeypatch, tmp_path, "Nur Vault Firma")
    monkeypatch.setattr(
        close_client, "search_leads",
        lambda query, limit=100: [{"id": "lead_only_close", "display_name": "Nur Close Firma", "contacts": []}],
    )

    results = svc.get_combined_leads({"quelle": "close"})

    assert [r["firma"] for r in results] == ["Nur Close Firma"]


def test_close_api_error_does_not_break_vault_only_results(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_leads, "get_settings", lambda: FakeSettings(tmp_path))
    _write(monkeypatch, tmp_path, "Trotzdem Sichtbar")

    def raise_close_error(query, limit=100):
        raise CloseAPIError(500, "Close down")

    monkeypatch.setattr(close_client, "search_leads", raise_close_error)

    results = svc.get_combined_leads()

    assert len(results) == 1
    assert results[0]["quelle"] == "vault"


def test_letzter_kontakt_vor_tagen_excludes_vault_only_leads(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_leads, "get_settings", lambda: FakeSettings(tmp_path))
    _write(monkeypatch, tmp_path, "Ohne Close Verknuepfung")
    monkeypatch.setattr(close_client, "search_leads", lambda query, limit=100: [])

    results = svc.get_combined_leads({"letzter_kontakt_vor_tagen": "7"})

    assert results == []


def test_letzter_kontakt_vor_tagen_keeps_lead_with_old_activity(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_leads, "get_settings", lambda: FakeSettings(tmp_path))
    _write(monkeypatch, tmp_path, "Lange Kein Kontakt", close_lead_id="lead_old")
    monkeypatch.setattr(
        close_client, "search_leads",
        lambda query, limit=100: [{"id": "lead_old", "display_name": "Lange Kein Kontakt", "contacts": []}],
    )
    monkeypatch.setattr(
        close_client, "list_activities",
        lambda lead_id, limit=1: [{"date_created": "2020-01-01T10:00:00Z"}],
    )

    results = svc.get_combined_leads({"letzter_kontakt_vor_tagen": "30"})

    assert len(results) == 1
    assert results[0]["letzter_kontakt"] == "2020-01-01"


def test_get_combined_leads_returns_all_close_only_leads_beyond_old_100_cap(tmp_path, monkeypatch):
    """Regressionstest für den Pagination-Bugfix 2026-09-06: vorher wurde ein
    ungefilterter Aufruf durch zwei überlagerte Ursachen stillschweigend auf
    100 Treffer gedeckelt - close_client.search_leads() hat nur eine
    Close-Seite abgerufen UND combined_leads hatte selbst einen limit=100-
    Default. Hier direkt auf combined_leads-Ebene simuliert (close_client.
    search_leads liefert bereits "alles", wie es nach dem Client-seitigen
    Fix der Fall ist) - prüft NUR die zweite Ursache: den kombinierten
    Default-Limit-Cutoff."""
    monkeypatch.setattr(vault_leads, "get_settings", lambda: FakeSettings(tmp_path))
    monkeypatch.setattr(
        close_client, "search_leads",
        lambda query, limit=5000: [
            {"id": f"lead_{i}", "display_name": f"Close-Firma {i}", "contacts": []}
            for i in range(300)
        ],
    )

    results = svc.get_combined_leads()

    assert len(results) == 300


def test_letzter_kontakt_vor_tagen_drops_lead_with_recent_activity(tmp_path, monkeypatch):
    from datetime import datetime, timedelta

    monkeypatch.setattr(vault_leads, "get_settings", lambda: FakeSettings(tmp_path))
    _write(monkeypatch, tmp_path, "Gerade Kontaktiert", close_lead_id="lead_recent")
    monkeypatch.setattr(
        close_client, "search_leads",
        lambda query, limit=100: [{"id": "lead_recent", "display_name": "Gerade Kontaktiert", "contacts": []}],
    )
    recent = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    monkeypatch.setattr(close_client, "list_activities", lambda lead_id, limit=1: [{"date_created": recent}])

    results = svc.get_combined_leads({"letzter_kontakt_vor_tagen": "30"})

    assert results == []
