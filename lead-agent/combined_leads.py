"""Kombinierte Lead-Abfrage: führt Vault-Leads (Leads/*.md, gelesen über
vault_leads.py) UND Close-CRM-Leads (gelesen über close_client.py) in EINER
Liste zusammen, gematcht über das vorhandene close_lead_id-Feld im
Vault-Frontmatter. Grund für ein eigenes Modul statt Inline-Logik in
mcp_server.py: export_leads.py nutzt get_combined_leads() als Datenquelle,
keine Dopplung der Filter-/Merge-Logik zwischen Chat-Tool und Export.

Filter-Strategie (Umbau 2026-09-21): ALLE Filter werden lokal gegen den
zusammengeführten Datensatz ausgewertet, nicht mehr als Close-Query. Die
frühere Variante (status/branche/region als Close-Query vorab) hatte zwei
echte Fehler: (1) Vault-Status ('neu', 'heiss', ...) und Close-Status
('Nicht erreicht', 'Termin vereinbart', ...) sind verschiedene Vokabulare -
ein Filter status=neu schickte 'neu' an Close, bekam nichts zurück und warf
damit alle Vault-Leads mit close_lead_id raus; (2) die Close-Query
custom.branche:"..." ist im Live-Test 2026-09-21 auch bei vorhandenen
Branche-Werten ohne Treffer geblieben. Close wird deshalb einmal komplett
geholt (Platten-Snapshot, siehe close_client.SNAPSHOT_PATH) und hier
gefiltert. status matcht Vault-Status ODER Close-Status."""
import re
from datetime import datetime
from pathlib import Path

import close_client
import vault_leads
from close_client import CloseAPIError

_DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")
_KONTAKT_RE = re.compile(r"## Kontakt\n(.+)", re.MULTILINE)

# Begrenzung für die letzter_kontakt_vor_tagen-Anreicherung (siehe
# _apply_letzter_kontakt_filter) - verhindert, dass eine große Trefferliste
# ungebremst N Einzel-Requests gegen Close auslöst.
MAX_LETZTER_KONTAKT_LOOKUPS = 50


def _close_link(close_lead_id: str) -> str:
    return f"https://app.close.com/lead/{close_lead_id}/"


def _company_from_filename(filename: str) -> str:
    return _DATE_PREFIX_RE.sub("", Path(filename).stem)


def _extract_contact(vault_lead: dict | None, close_lead: dict | None) -> str:
    if vault_lead:
        m = _KONTAKT_RE.search(vault_lead.get("body", ""))
        if m:
            line = m.group(1).strip().splitlines()[0].strip()
            if line:
                return line
    if close_lead:
        contacts = close_lead.get("contacts") or []
        if contacts:
            c = contacts[0]
            emails = ", ".join(e.get("email", "") for e in c.get("emails", []) if e.get("email"))
            name = c.get("name", "")
            if name and emails:
                return f"{name} <{emails}>"
            return name or emails
    return ""


def _close_custom(close_lead: dict | None, name: str) -> str:
    for k, v in ((close_lead or {}).get("custom") or {}).items():
        if k.strip().lower() == name and v not in (None, ""):
            return str(v)
    return ""


def _close_city(close_lead: dict | None) -> str:
    for a in (close_lead or {}).get("addresses") or []:
        if a.get("city"):
            return a["city"]
    return ""


def _record(vault_lead: dict | None, close_lead: dict | None) -> dict:
    """Ein einheitlicher Datensatz aus Vault-Lead und/oder Close-Lead. Vault-
    Werte haben Vorrang (dort schreibt der Agent), Close füllt Lücken."""
    fields = (vault_lead or {}).get("fields", {})
    close_id = (fields.get("close_lead_id") or "").strip() or ((close_lead or {}).get("id") or "")
    # Close-Name bevorzugen: der Dateiname ist bereinigt ("GmbH--Co-KG").
    firma = (
        (close_lead or {}).get("display_name") or (close_lead or {}).get("name")
        or (_company_from_filename(vault_lead["filename"]) if vault_lead else "?")
    )
    return {
        "firma": firma,
        "kontakt": _extract_contact(vault_lead, close_lead),
        "quelle": "beide" if (vault_lead and close_lead) else "vault" if vault_lead else "close",
        "status": fields.get("status") or (close_lead or {}).get("status_label") or "",
        "close_status": (close_lead or {}).get("status_label") or "",
        "score": fields.get("score") or "",
        "letzter_kontakt": "",
        "website": fields.get("website") or (close_lead or {}).get("url") or "",
        "ort": fields.get("ort") or _close_city(close_lead),
        "branche": fields.get("branche") or _close_custom(close_lead, "branche"),
        "mitarbeiter": fields.get("mitarbeiter") or _close_custom(close_lead, "mitarbeiteranzahl"),
        "umsatz": fields.get("umsatz") or _close_custom(close_lead, "umsatz"),
        "aehnlich_zu": fields.get("aehnlich_zu") or "",
        "quellen": fields.get("quellen") or "",
        "angelegt": ((close_lead or {}).get("date_created") or fields.get("datum") or "")[:10],
        "close_lead_id": close_id if close_id else "",
        "close_link": _close_link(close_id) if close_id else "",
        "vault_path": vault_lead["filename"] if vault_lead else "",
        "_vault_status": (fields.get("status") or "").strip().lower(),
        "_haystack": " ".join([
            firma, (vault_lead or {}).get("body", ""), " ".join(f"{k} {v}" for k, v in fields.items()),
            (close_lead or {}).get("description") or "", (close_lead or {}).get("url") or "",
            " ".join(str(v) for v in ((close_lead or {}).get("custom") or {}).values()),
            " ".join(
                f"{c.get('name', '')} {c.get('title', '')} " + " ".join(e.get("email", "") for e in c.get("emails", []))
                for c in (close_lead or {}).get("contacts") or []
            ),
            " ".join(
                " ".join(str(a.get(k) or "") for k in ("city", "state", "zipcode", "country"))
                for a in (close_lead or {}).get("addresses") or []
            ),
        ]).lower(),
    }


def _matches(rec: dict, filter: dict) -> bool:
    status = filter.get("status")
    if status:
        wanted = str(status).strip().lower()
        if wanted not in (rec["_vault_status"], rec["close_status"].strip().lower()):
            return False

    score_min = filter.get("score_min")
    if score_min not in (None, ""):
        try:
            if float(str(rec["score"]).replace(",", ".") or "nan") < float(score_min):
                return False
        except ValueError:
            return False

    hay = rec["_haystack"]
    for key in ("branche", "region"):
        needle = filter.get(key)
        if not needle:
            continue
        needle = str(needle).lower()
        own = (rec.get(key) or rec.get("ort") if key == "region" else rec.get(key)) or ""
        if needle not in str(own).lower() and needle not in hay:
            return False

    for key, value in (filter.get("custom_fields") or {}).items():
        if value and str(value).lower() not in hay:
            return False

    freitext = filter.get("freitext")
    if freitext and str(freitext).lower() not in hay:
        return False

    days = filter.get("angelegt_seit_tagen")
    if days not in (None, ""):
        try:
            created = datetime.fromisoformat(rec["angelegt"])
        except ValueError:
            return False
        if (datetime.now() - created).days > int(days):
            return False
    return True


def _apply_letzter_kontakt_filter(results: list[dict], min_days: int) -> list[dict]:
    now = datetime.now()
    kept: list[dict] = []
    lookups = 0
    for r in results:
        if not r["close_lead_id"]:
            # Ohne Close-Verknüpfung gibt es keine Aktivitäts-/Kontaktdaten -
            # "vor X Tagen" ist für diese Leads nicht bewertbar, deshalb raus
            # statt fälschlich einzuschließen.
            continue
        if lookups >= MAX_LETZTER_KONTAKT_LOOKUPS:
            break
        lookups += 1
        try:
            activities = close_client.list_activities(r["close_lead_id"], limit=1)
        except CloseAPIError:
            continue
        if not activities:
            kept.append(r)  # noch nie kontaktiert -> erfüllt "vor X Tagen" sicher
            continue
        last_raw = activities[0].get("date_created", "")
        r["letzter_kontakt"] = last_raw[:10]
        try:
            last_date = datetime.fromisoformat(last_raw.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            continue
        if (now - last_date).days >= min_days:
            kept.append(r)
    return kept


def get_combined_leads_with_meta(filter: dict | None = None) -> tuple[list[dict], dict]:
    """Wie get_combined_leads, liefert zusätzlich meta:
    {"close_verfuegbar": bool, "close_fehler": str, "gekuerzt": bool}.
    Ist Close nicht erreichbar, enthält das Ergebnis nur Vault-Leads - meta
    macht das sichtbar (statt einer stillschweigend unvollständigen Liste).

    filter (alle Felder optional, frei kombinierbar):
      branche, region, freitext: Teilstring in den Feldern bzw. im gesamten
        Datensatz (Vault-Text + Close-Felder + Kontakte)
      status: Vault-Status ODER Close-Status (exakt, Groß-/Kleinschreibung egal)
      score_min: Zahl
      angelegt_seit_tagen: int - nur Leads, die höchstens so alt sind
      letzter_kontakt_vor_tagen: int - nur für close-verknüpfte Leads
        auswertbar (siehe _apply_letzter_kontakt_filter)
      custom_fields: dict[str, str] - zusätzliche Teilstring-Filter
      quelle: "vault" | "close" | "beide"
      limit: int - Obergrenze Close-Abruf und Ergebnis (Default 5000)
    """
    filter = filter or {}
    limit = int(filter.get("limit") or 5000)

    meta = {"close_verfuegbar": True, "close_fehler": "", "gekuerzt": False}
    try:
        close_results = close_client.search_leads("", limit=limit, cached=True)
    except CloseAPIError as e:
        # Close nicht erreichbar/kein API-Key -> nicht hart fehlschlagen,
        # Vault-Daten sind trotzdem nutzbar - aber sichtbar machen.
        close_results = []
        meta.update(close_verfuegbar=False, close_fehler=str(e))
    close_by_id = {c["id"]: c for c in close_results if c.get("id")}

    records: list[dict] = []
    used_close_ids: set[str] = set()
    for lead in vault_leads.list_leads():
        close_id = (lead["fields"].get("close_lead_id") or "").strip()
        close_lead = close_by_id.get(close_id) if close_id else None
        if close_lead:
            used_close_ids.add(close_id)
        records.append(_record(lead, close_lead))
    for close_id, close_lead in close_by_id.items():
        if close_id not in used_close_ids:
            records.append(_record(None, close_lead))

    results = [r for r in records if _matches(r, filter)]

    quelle_filter = filter.get("quelle")
    if quelle_filter:
        results = [r for r in results if r["quelle"] == quelle_filter]

    letzter_kontakt_vor_tagen = filter.get("letzter_kontakt_vor_tagen")
    if letzter_kontakt_vor_tagen not in (None, ""):
        results = _apply_letzter_kontakt_filter(results, int(letzter_kontakt_vor_tagen))

    if len(results) > limit:
        meta["gekuerzt"] = True
    for r in results:
        r.pop("_haystack", None)
        r.pop("_vault_status", None)
    return results[:limit], meta


def get_combined_leads(filter: dict | None = None) -> list[dict]:
    return get_combined_leads_with_meta(filter)[0]
