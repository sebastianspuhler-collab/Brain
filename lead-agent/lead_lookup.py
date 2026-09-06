"""Löst EINEN Lead über Vault (Leads/*.md) UND Close CRM auf - gemeinsamer
Baustein für enrich_lead/save_lead_enrichment (mcp_server.py). Getrennt von
combined_leads.py, weil dort eine ganze (gefilterte) Liste zusammengeführt
wird, hier dagegen genau EIN Lead mit vollen Close-Detaildaten (Kontakte,
nicht nur die schlanke Listenansicht) benötigt wird.

WICHTIG (Architektur-Entscheidung Teil B): ein MCP-Server-Tool läuft als
eigenständiger Python-Prozess und hat KEINEN Zugriff auf Claude Codes native
Tools (WebSearch, Read, ...) - das ist ausschließlich dem Chat-Agenten
vorbehalten (--tools/--allowedTools in claude_agent.py). enrich_lead kann
also nicht selbst recherchieren, sondern nur: (1) den Lead auflösen, (2)
zeigen was bereits bekannt ist und welche Kernfelder fehlen. Der Agent
recherchiert die Lücken danach SELBST per WebSearch und schreibt das Ergebnis
über save_lead_enrichment zurück - siehe SYSTEM_PROMPT in claude_agent.py."""
import close_client
import vault_leads
from close_client import CloseAPIError

# Felder, die enrich_lead als "Kernfelder" prüft - werden NICHT von
# vault_leads.write_prospect vorbelegt (siehe dortiger Docstring), sondern
# erst durch save_lead_enrichment ergänzt, sobald recherchiert.
CORE_FIELDS = ("branche", "groesse", "produkt_leistung", "zielgruppe")


def resolve(identifier: str) -> dict:
    """identifier: eine close_lead_id (beginnt mit 'lead_', Close-Konvention)
    ODER ein Firmenname/Dateiname-Stichwort (wie überall sonst im
    Lead-Agenten, siehe vault_leads.find_lead). Gibt immer
    {"vault": dict|None, "close": dict|None, "close_lead_id": str|None}
    zurück - beide None heißt: nichts gefunden."""
    vault_lead = None
    close_lead = None
    close_lead_id = None

    if identifier.startswith("lead_"):
        close_lead_id = identifier
        vault_lead = vault_leads.find_lead_by_close_id(identifier)
    else:
        vault_lead = vault_leads.find_lead(identifier)
        if vault_lead:
            close_lead_id = (vault_lead["fields"].get("close_lead_id") or "").strip() or None

    if close_lead_id:
        try:
            close_lead = close_client.get_lead(close_lead_id)
        except CloseAPIError:
            close_lead = None
    elif not vault_lead:
        # Weder Vault-Treffer noch bekannte close_lead_id -> letzter Versuch:
        # direkt in Close nach dem Namen suchen (deckt Leads ab, die nur in
        # Close existieren, siehe close_search_leads-Tool).
        try:
            candidates = close_client.search_leads(identifier, limit=1)
        except CloseAPIError:
            candidates = []
        if candidates:
            close_lead = candidates[0]
            close_lead_id = close_lead.get("id")

    return {"vault": vault_lead, "close": close_lead, "close_lead_id": close_lead_id}


def missing_core_fields(resolved: dict) -> list[str]:
    vault_fields = (resolved.get("vault") or {}).get("fields", {})
    return [f for f in CORE_FIELDS if not vault_fields.get(f)]
