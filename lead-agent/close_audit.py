"""Vault<->Close-Abgleich (Umsetzungsplan 2026-09-06): findet Firmen, die es
in BEIDEN Systemen gibt, aber (noch) nicht über close_lead_id verknüpft
sind - Auslöser war die Beobachtung, dass F-Tronic als voller
Kunden/F-Tronic/-Ordner UND als eigener Close-Lead existiert, ohne dass der
Lead-Agent das je bemerkt hat (vault_kunden.py deckt genau diese Lücke ab,
siehe dortiger Docstring).

audit() ist bewusst READ-ONLY (schreibt nichts) - Namensabgleich ist
Best-Effort (siehe name_matching.py), keine Garantie gegen falsche Treffer
bei zwei unterschiedlichen Firmen mit zufällig ähnlichem Namen. Tatsächliches
Verknüpfen (link()) bzw. Neuanlegen in Close bleibt ein separater,
bewusster zweiter Schritt (siehe mcp_server.py: link_vault_to_close /
sync_lead_to_close) statt automatischem Anlegen/Verknüpfen direkt aus dem
Audit heraus."""
from pathlib import Path

import close_client
import name_matching
import vault_kunden
import vault_leads
from close_client import CloseAPIError

# Wie viele unverknüpfte Close-Leads OHNE jeden Vault-Treffer maximal einzeln
# aufgelistet werden - bei >1000 Close-Leads und nur ~30 Vault-Firmen sind
# das fast immer die meisten, eine volle Liste wäre nur Rauschen. Der Fokus
# liegt auf der Vault-Seite ("die im Vault sind"), nicht auf einem
# vollständigen Close-Export.
_MAX_UNMATCHED_CLOSE_PREVIEW = 20


def _vault_entities() -> list[dict]:
    """Alle Vault-Firmen mit Kontaktbezug: Kunden/-Ordner (etablierte
    Beziehung, "Kontakt besteht") UND Leads/*.md (frische Leads)."""
    entities = []
    for k in vault_kunden.list_kunden():
        entities.append({"firma": k["firma"], "typ": "kunde", "path": k["path"], "close_lead_id": k["close_lead_id"]})
    for lead in vault_leads.list_leads():
        firma = name_matching.strip_date_prefix(Path(lead["filename"]).stem)
        entities.append({
            "firma": firma, "typ": "lead", "path": lead["path"],
            "close_lead_id": (lead["fields"].get("close_lead_id") or "").strip(),
        })
    return entities


def audit() -> dict:
    try:
        close_leads = close_client.search_leads("", limit=5000)
    except CloseAPIError as e:
        return {"ok": False, "error": str(e)}

    # Erster Treffer gewinnt bei mehreren Close-Leads mit demselben
    # normalisierten Namen (bei über tausend Leads real möglich) - bewusste
    # Vereinfachung, keine Dublettenauflösung hier.
    close_by_norm: dict[str, dict] = {}
    for c in close_leads:
        norm = name_matching.normalize(c.get("display_name") or c.get("name") or "")
        if norm:
            close_by_norm.setdefault(norm, c)

    matched_close_ids: set[str] = set()
    bereits_verknuepft = 0
    neu_verknuepfbar = []
    kunden_ohne_close = []
    leads_ohne_close = []

    for e in _vault_entities():
        norm = name_matching.normalize(e["firma"])
        close_match = close_by_norm.get(norm)

        if e["close_lead_id"]:
            bereits_verknuepft += 1
            if close_match:
                matched_close_ids.add(close_match["id"])
            continue

        if close_match:
            matched_close_ids.add(close_match["id"])
            neu_verknuepfbar.append({
                "firma": e["firma"], "typ": e["typ"], "vault_path": e["path"],
                "close_lead_id": close_match["id"],
                "close_name": close_match.get("display_name") or close_match.get("name"),
            })
        elif e["typ"] == "kunde":
            kunden_ohne_close.append({"firma": e["firma"], "vault_path": e["path"]})
        else:
            leads_ohne_close.append({"firma": e["firma"], "vault_path": e["path"]})

    unmatched_close = [
        {"close_lead_id": c["id"], "firma": c.get("display_name") or c.get("name")}
        for c in close_leads if c.get("id") not in matched_close_ids
    ]

    return {
        "ok": True,
        "bereits_verknuepft": bereits_verknuepft,
        "neu_verknuepfbar": neu_verknuepfbar,
        "kunden_ohne_close_kontakt": kunden_ohne_close,
        "leads_ohne_close_kontakt": leads_ohne_close,
        "close_leads_gesamt": len(close_leads),
        "close_leads_ohne_vault_treffer_anzahl": len(unmatched_close),
        "close_leads_ohne_vault_treffer_beispiele": unmatched_close[:_MAX_UNMATCHED_CLOSE_PREVIEW],
    }


def link(firma_or_path: str, close_lead_id: str) -> dict:
    """Schreibt eine bereits gefundene Verknüpfung fest (typischerweise ein
    Eintrag aus audit()['neu_verknuepfbar']) - legt NICHTS neu in Close an,
    reiner Vault-seitiger Schreibzugriff. Für Kunden/-Ordner in
    close_lead_id.txt, für Leads/*.md im Frontmatter."""
    kunde = vault_kunden.find_kunde(firma_or_path)
    if kunde:
        vault_kunden.link_to_close(Path(kunde["path"]), close_lead_id)
        return {"ok": True, "typ": "kunde", "vault_path": kunde["path"], "close_lead_id": close_lead_id}

    lead = vault_leads.find_lead(firma_or_path)
    if lead:
        vault_leads.update_fields(Path(lead["path"]), {"close_lead_id": close_lead_id})
        return {"ok": True, "typ": "lead", "vault_path": lead["filename"], "close_lead_id": close_lead_id}

    return {"ok": False, "error": f"Kein Vault-Eintrag (Kunde/Lead) gefunden für '{firma_or_path}'"}
