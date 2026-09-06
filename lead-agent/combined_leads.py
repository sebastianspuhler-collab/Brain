"""Kombinierte Lead-Abfrage: führt Vault-Leads (Leads/*.md, gelesen über
vault_leads.py) UND Close-CRM-Leads (gelesen über close_client.py) in EINER
Liste zusammen, gematcht über das vorhandene close_lead_id-Feld im
Vault-Frontmatter. Grund für ein eigenes Modul statt Inline-Logik in
mcp_server.py: export_leads.py nutzt get_combined_leads() als Datenquelle,
keine Dopplung der Filter-/Merge-Logik zwischen Chat-Tool und Export.

Filter-Strategie (siehe Umsetzungsplan Teil A): Felder, die als Vault-
Frontmatter existieren (status, score - und branche/groesse/region/
produkt_leistung/zielgruppe, sobald sie über enrich_lead/save_lead_enrichment
befüllt wurden, siehe lead_lookup.py), werden lokal per Python gegen die
gelesenen Vault-Dateien geprüft. Für Close-Leads (inkl. reiner Close-Only-
Leads ohne Vault-Datei) wird derselbe Filter zusätzlich als Close-eigene
Such-Query-Syntax gebaut (siehe _build_close_query, developer.close.com/
topics/searching/) und über close_client.search_leads() ausgeführt -
KEINE eigene HTTP-Logik hier, bewusste Wiederverwendung des bestehenden,
schlankeren Bausteins statt einer zweiten Such-Implementierung.

STAND 2026-09-06: die Close-Query-Syntax für custom.<Feldname>:"<Wert>" ist
nach bestehender Close-Doku gebaut, aber noch NICHT gegen echte
Custom-Field-Namen in diesem Account live verifiziert (gleiche Einschränkung
wie webhooks.py-Docstring) - bei Bedarf gegen die tatsächlichen Feldnamen in
Close (Settings -> Custom Fields) abgleichen.
"""
import re
from datetime import datetime
from pathlib import Path

import close_client
import vault_leads
from close_client import CloseAPIError

_DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")
_KONTAKT_RE = re.compile(r"## Kontakt\n(.+)", re.MULTILINE)

# Vault-Frontmatter-Felder, die als reiner Substring-Filter gelten (auch
# gegen den Freitext-Body, falls das Feld selbst nicht gesetzt ist - vor
# einer enrich_lead-Anreicherung existieren branche/region z.B. noch gar
# nicht als eigenes Feld, siehe lead_lookup.CORE_FIELDS).
_TEXT_FILTER_FIELDS = ("branche", "region")

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


def _build_close_query(filter: dict) -> str:
    clauses: list[str] = []
    if filter.get("status"):
        clauses.append(f'status:"{filter["status"]}"')
    if filter.get("branche"):
        clauses.append(f'custom.branche:"{filter["branche"]}"')
    if filter.get("region"):
        clauses.append(f'custom.region:"{filter["region"]}"')
    for key, value in (filter.get("custom_fields") or {}).items():
        if value:
            clauses.append(f'custom.{key}:"{value}"')
    if filter.get("freitext"):
        clauses.append(str(filter["freitext"]))
    return " and ".join(clauses)


def _vault_matches(lead: dict, filter: dict) -> bool:
    fields = lead["fields"]
    haystack = f"{lead['filename']} {lead['body']}".lower()

    status = filter.get("status")
    if status and (fields.get("status") or "").strip().lower() != str(status).strip().lower():
        return False

    score_min = filter.get("score_min")
    if score_min not in (None, ""):
        try:
            if float(fields.get("score") or "nan") < float(score_min):
                return False
        except ValueError:
            return False

    for key in _TEXT_FILTER_FIELDS:
        needle = filter.get(key)
        if not needle:
            continue
        needle = str(needle).lower()
        if needle not in (fields.get(key) or "").lower() and needle not in haystack:
            return False

    for key, value in (filter.get("custom_fields") or {}).items():
        if not value:
            continue
        value = str(value).lower()
        if value not in (fields.get(key) or "").lower() and value not in haystack:
            return False

    freitext = filter.get("freitext")
    if freitext and str(freitext).lower() not in haystack:
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


def get_combined_leads(filter: dict | None = None) -> list[dict]:
    """filter (alle Felder optional, frei kombinierbar):
      branche, status, score_min, region: str/Zahl
      letzter_kontakt_vor_tagen: int - nur für close-verknüpfte Leads
        auswertbar (siehe _apply_letzter_kontakt_filter)
      freitext: str - Volltextsuche über Vault-Body UND Close-Quicksearch
      custom_fields: dict[str, str] - zusätzliche Close-Custom-Field-Filter
      quelle: "vault" | "close" | "beide" - Ergebnis auf eine Quelle einschränken
      limit: int - Obergrenze für Close-Suche und Gesamtergebnis (Default 100)
    """
    filter = filter or {}
    limit = int(filter.get("limit") or 100)

    vault_matches = [lead for lead in vault_leads.list_leads() if _vault_matches(lead, filter)]

    close_query = _build_close_query(filter)
    try:
        close_results = close_client.search_leads(close_query, limit=limit)
    except CloseAPIError:
        # Close nicht erreichbar/kein API-Key -> nicht hart fehlschlagen,
        # Vault-Daten sind trotzdem nutzbar (gleiches fail-open-Prinzip wie
        # sonst im Repo bei transienten externen Fehlern).
        close_results = []
    close_by_id = {c["id"]: c for c in close_results if c.get("id")}

    combined: dict[str, dict] = {}
    used_close_ids: set[str] = set()

    for lead in vault_matches:
        fields = lead["fields"]
        close_id = (fields.get("close_lead_id") or "").strip()
        close_lead = close_by_id.get(close_id) if close_id else None
        if close_id and not close_lead and close_query:
            # Close-seitige Kriterien sind gesetzt, dieser Lead kam aber nicht
            # in der Close-Trefferliste zurück -> erfüllt die Close-Bedingung
            # nicht, raus (AND-Semantik über beide Quellen).
            continue
        if close_id:
            used_close_ids.add(close_id)
        firma = _company_from_filename(lead["filename"])
        combined[lead["filename"]] = {
            "firma": firma,
            "kontakt": _extract_contact(lead, close_lead),
            "quelle": "beide" if close_lead else "vault",
            "status": fields.get("status") or (close_lead.get("status_label") if close_lead else "") or "",
            "score": fields.get("score") or "",
            "letzter_kontakt": "",
            "close_lead_id": close_id,
            "close_link": _close_link(close_id) if close_id else "",
            "vault_path": lead["filename"],
        }

    for close_id, close_lead in close_by_id.items():
        if close_id in used_close_ids:
            continue
        combined[f"close:{close_id}"] = {
            "firma": close_lead.get("display_name") or close_lead.get("name") or "?",
            "kontakt": _extract_contact(None, close_lead),
            "quelle": "close",
            "status": close_lead.get("status_label") or "",
            "score": "",
            "letzter_kontakt": "",
            "close_lead_id": close_id,
            "close_link": _close_link(close_id),
            "vault_path": "",
        }

    results = list(combined.values())

    quelle_filter = filter.get("quelle")
    if quelle_filter:
        results = [r for r in results if r["quelle"] == quelle_filter]

    letzter_kontakt_vor_tagen = filter.get("letzter_kontakt_vor_tagen")
    if letzter_kontakt_vor_tagen not in (None, ""):
        results = _apply_letzter_kontakt_filter(results, int(letzter_kontakt_vor_tagen))

    return results[:limit]
