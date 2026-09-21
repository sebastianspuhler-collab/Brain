import sys
from pathlib import Path

import pytest

# lead-agent/ ist ein flaches Modul-Verzeichnis (kein app.*-Package wie
# backend/) - hier explizit auf sys.path setzen, damit `import close_client`
# etc. unabhängig davon funktioniert, von wo aus pytest gestartet wird.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class FakeSettings:
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.close_source_field_id = ""

    @property
    def leads_dir(self) -> Path:
        return self.vault_path / "Leads"


class FakeClose:
    """In-Memory-Ersatz für close_client: speichert Leads/Kontakte/Notizen und
    protokolliert alle Schreibaufrufe in self.calls."""

    def __init__(self):
        self.leads: dict[str, dict] = {}
        self.notes: list[tuple[str, str]] = []
        self.calls: list[tuple] = []
        self.down = False
        self._n = 0
        self.custom_fields = [
            {"id": "cf_branche", "name": "Branche", "type": "text"},
            {"id": "cf_ma", "name": "Mitarbeiteranzahl", "type": "number"},
            {"id": "cf_umsatz", "name": "Umsatz", "type": "text"},
        ]
        self.statuses = [{"id": "stat_1", "label": "Nicht erreicht"}, {"id": "stat_2", "label": "Termin vereinbart"}]

    def add_lead(self, name, url="", contacts=None, custom=None, status="Nicht erreicht", addresses=None) -> dict:
        self._n += 1
        lid = f"lead_{self._n}"
        lead = {
            "id": lid, "display_name": name, "name": name, "url": url, "status_label": status,
            "contacts": contacts or [], "custom": custom or {}, "addresses": addresses or [],
            "date_created": "2026-08-02T10:00:00+00:00", "description": "",
        }
        self.leads[lid] = lead
        return lead

    def _check(self):
        if self.down:
            raise self._err(503, "Close down")

    @staticmethod
    def _err(code, msg):
        import close_client
        return close_client.CloseAPIError(code, msg)

    # --- close_client-API ---
    def find_lead_candidates(self, queries):
        self._check()
        found = {}
        for q in queries:
            q = (q or "").lower().strip()
            for lid, lead in self.leads.items():
                hay = f"{lead['display_name']} {lead['url']} " + " ".join(
                    e["email"] for c in lead["contacts"] for e in c.get("emails", []))
                if q and q in hay.lower():
                    found[lid] = lead
        return list(found.values())

    def search_leads(self, query="", limit=25, cached=False):
        self._check()
        return list(self.leads.values())[:limit]

    def get_lead(self, lead_id):
        self._check()
        return self.leads[lead_id]

    def create_lead(self, name, contacts=None, custom_fields=None, extra=None):
        self._check()
        lead = self.add_lead(name, contacts=[dict(c, id=f"cont_{self._n}", emails=c.get("emails", []), phones=c.get("phones", [])) for c in (contacts or [])])
        for k, v in (custom_fields or {}).items():
            fname = next(f["name"] for f in self.custom_fields if f"custom.{f['id']}" == k)
            lead["custom"][fname] = v
        lead.update({k: v for k, v in (extra or {}).items()})
        self.calls.append(("create_lead", name, custom_fields, extra))
        return lead

    def update_lead(self, lead_id, data):
        self._check()
        lead = self.leads[lead_id]
        for k, v in data.items():
            if k.startswith("custom."):
                fname = next(f["name"] for f in self.custom_fields if f"custom.{f['id']}" == k)
                lead["custom"][fname] = v
            elif k == "status_id":
                lead["status_label"] = next(s["label"] for s in self.statuses if s["id"] == v)
            else:
                lead[k] = v
        self.calls.append(("update_lead", lead_id, data))
        return lead

    def tag_lead_source(self, lead_id):
        return {}

    def create_note(self, lead_id, text):
        self._check()
        self.notes.append((lead_id, text))
        self.calls.append(("create_note", lead_id))
        return {"id": "note_1"}

    def create_contact(self, lead_id, name, title="", emails=None, phones=None):
        self._check()
        self._n += 1
        c = {"id": f"cont_{self._n}", "name": name, "title": title,
             "emails": [{"email": e} for e in emails or []], "phones": [{"phone": p} for p in phones or []]}
        self.leads[lead_id]["contacts"].append(c)
        self.calls.append(("create_contact", lead_id, name))
        return c

    def update_contact(self, contact_id, data):
        self._check()
        for lead in self.leads.values():
            for c in lead["contacts"]:
                if c["id"] == contact_id:
                    c.update(data)
        self.calls.append(("update_contact", contact_id, data))
        return {}

    def list_lead_statuses(self):
        self._check()
        return self.statuses

    def status_id_for(self, label):
        self._check()
        return next((s["id"] for s in self.statuses if s["label"].lower() == label.strip().lower()), None)

    def custom_field_ids(self):
        self._check()
        return {f["name"].lower(): {"id": f["id"], "type": f["type"], "name": f["name"]} for f in self.custom_fields}

    def list_lead_custom_fields(self):
        return self.custom_fields

    def list_activities(self, lead_id, limit=25):
        return []

    def writes(self, kind):
        return [c for c in self.calls if c[0] == kind]


@pytest.fixture
def vault(tmp_path, monkeypatch):
    import prospects
    import table_io
    import vault_kunden
    import vault_leads

    settings = FakeSettings(tmp_path)
    for mod in (vault_leads, vault_kunden, prospects, table_io):
        monkeypatch.setattr(mod, "get_settings", lambda: settings)
    (tmp_path / "Leads" / "MD").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def close(monkeypatch, vault, tmp_path):
    import close_client

    fake = FakeClose()
    for name in (
        "find_lead_candidates", "search_leads", "get_lead", "create_lead", "update_lead", "tag_lead_source",
        "create_note", "create_contact", "update_contact", "list_lead_statuses", "status_id_for",
        "custom_field_ids", "list_lead_custom_fields", "list_activities",
    ):
        monkeypatch.setattr(close_client, name, getattr(fake, name))
    monkeypatch.setattr(close_client, "SNAPSHOT_PATH", tmp_path / "snapshot.json")
    return fake
