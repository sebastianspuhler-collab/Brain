"""MCP-Server für die Lead-Agent-Tools (Close CRM + Vault-Lead-Schreibzugriff
+ Gmail-Entwurf) - eigenständige Kopie des Musters aus
backend/app/mcp_server.py (FastMCP, stdio-Transport), registriert in der
lokalen .mcp.json dieses Ordners.

Vault-LESEN (Leads/*.md, Kunden/, PLAYBOOK.md durchsuchen) läuft bewusst NICHT
über eigene Tools, sondern nativ über Claude Codes Read/Glob/Grep
(--add-dir /vault in claude_agent.py) - exakt dieselbe Begründung wie im
Hauptbackend-mcp_server.py ("deckt Claude Code nativ ab, kein Custom-Tool
nötig"). Was hier als Tool existiert, sind ausschließlich SCHREIBENDE/externe
Aktionen: Vault-Lead-Dateien werden trotzdem NUR über diese Tools angelegt/
verändert (nicht über natives Write/Edit, siehe claude_agent.py:
tools_value ohne "Write,Edit") - ein zentraler, geprüfter Ort für das
Frontmatter-Format statt N leicht abweichender Freitext-Schreibversuche des
Modells.

Start (stdio-Transport, für Registrierung in .mcp.json):
    python -m mcp_server   (oder: python mcp_server.py)
"""
from pathlib import Path

from mcp.server.fastmcp import FastMCP

import close_client
import gmail_client
import vault_leads
from close_client import CloseAPIError
from config import get_settings

mcp = FastMCP("lead-agent-tools")


def _format_lead_summary(lead: dict) -> str:
    f = lead["fields"]
    return (
        f"- {lead['filename']} | Firma: {Path(lead['filename']).stem} | "
        f"status: {f.get('status', '?')} | score: {f.get('score', '?')} | "
        f"quelle: {f.get('quelle', '?')} | close_lead_id: {f.get('close_lead_id') or '-'}"
    )


@mcp.tool(description=(
    "Legt einen NEU recherchierten Prospect an: schreibt einen Lead-Stub nach "
    "Leads/*.md (Vault) UND legt ihn als Lead in Close CRM an (Quelle-Feld "
    "'prozessia-lead-agent'), verknüpft beide sofort über close_lead_id im "
    "Frontmatter. Nutze dies NACH eigener Recherche (WebSearch) für jeden "
    "Prospect, der zum ICP aus PLAYBOOK.md passt - nicht für bereits "
    "bestehende Leads (dafür sync_lead_to_close)."
))
def save_prospect(firma: str, kontakt_name: str = "", kontakt_email: str = "", notiz: str = "", quelle: str = "Recherche") -> dict:
    path = vault_leads.write_prospect(firma, kontakt_name, kontakt_email, notiz, quelle)
    close_result: dict = {}
    try:
        contacts = []
        if kontakt_name or kontakt_email:
            contact: dict = {"name": kontakt_name or firma}
            if kontakt_email:
                contact["emails"] = [{"email": kontakt_email, "type": "office"}]
            contacts = [contact]
        close_lead = close_client.create_lead(firma, contacts=contacts or None)
        close_client.tag_lead_source(close_lead["id"])
        vault_leads.update_fields(path, {"close_lead_id": close_lead["id"]})
        close_result = {"close_lead_id": close_lead["id"]}
    except CloseAPIError as e:
        close_result = {"close_error": str(e)}
    return {"ok": True, "vault_path": str(path.relative_to(get_settings().vault_path)), **close_result}


@mcp.tool(description=(
    "Verknüpft einen BEREITS bestehenden Vault-Lead (z.B. automatisch aus einer "
    "E-Mail oder einem Kalendertermin erkannt, noch ohne close_lead_id) mit "
    "Close CRM: legt ihn dort an (oder aktualisiert ihn, falls close_lead_id "
    "schon gesetzt ist) und schreibt/aktualisiert close_lead_id im Frontmatter. "
    "name_or_path: Dateiname/Stichwort/Pfad, wie bei jeder Vault-Datei-Referenz."
))
def sync_lead_to_close(name_or_path: str) -> dict:
    lead = vault_leads.find_lead(name_or_path)
    if not lead:
        return {"ok": False, "error": f"Kein Lead gefunden für '{name_or_path}'"}

    firma = Path(lead["filename"]).stem
    # Datumspräfix (YYYY-MM-DD-) aus dem Dateinamen entfernen, für einen
    # saubereren Close-Lead-Namen.
    import re as _re
    firma = _re.sub(r"^\d{4}-\d{2}-\d{2}-", "", firma)

    existing_id = lead["fields"].get("close_lead_id")
    try:
        if existing_id:
            close_client.update_lead(existing_id, {"name": firma})
            close_lead_id = existing_id
        else:
            close_lead = close_client.create_lead(firma)
            close_client.tag_lead_source(close_lead["id"])
            close_lead_id = close_lead["id"]
        vault_leads.update_fields(Path(lead["path"]), {"close_lead_id": close_lead_id})
        return {"ok": True, "close_lead_id": close_lead_id, "vault_path": lead["filename"]}
    except CloseAPIError as e:
        return {"ok": False, "error": str(e)}


@mcp.tool(description=(
    "Sucht Leads direkt in Close CRM (Name/Firma als Stichwort). Nutzen, um den "
    "aktuellen Close-Stand zu sehen oder eine close_lead_id zu einem Firmennamen "
    "zu finden, wenn der Vault-Lead selbst keine close_lead_id im Frontmatter hat."
))
def close_search_leads(query: str = "") -> str:
    try:
        leads = close_client.search_leads(query)
    except CloseAPIError as e:
        return f"Close-Fehler: {e}"
    if not leads:
        return "Keine Treffer in Close."
    lines = [f"- {lead.get('id')} | {lead.get('display_name') or lead.get('name')}" for lead in leads]
    return "\n".join(lines)


@mcp.tool(description=(
    "Liefert Details zu einem Close-Lead: Kontakte, Opportunities (Pipeline-"
    "Stage, Wert) und die letzten Activities/Notes. Kombiniere das mit dem "
    "Vault-Lead (nativ per Read/Glob auf Leads/), um nach den PLAYBOOK.md-"
    "Regeln zu bewerten oder ein Sales-Brief zu schreiben."
))
def close_get_lead_detail(close_lead_id: str) -> str:
    try:
        lead = close_client.get_lead(close_lead_id)
        opportunities = close_client.list_opportunities(close_lead_id)
        activities = close_client.list_activities(close_lead_id, limit=10)
    except CloseAPIError as e:
        return f"Close-Fehler: {e}"

    lines = [f"Lead: {lead.get('display_name') or lead.get('name')} ({close_lead_id})"]
    contacts = lead.get("contacts") or []
    for c in contacts:
        emails = ", ".join(e.get("email", "") for e in c.get("emails", []))
        lines.append(f"  Kontakt: {c.get('name', '?')} <{emails}>")
    for opp in opportunities:
        lines.append(f"  Opportunity: {opp.get('status_label', '?')} | Wert: {opp.get('value', '?')}")
    for act in activities:
        lines.append(f"  Activity [{act.get('_type', '?')}] {act.get('date_created', '')[:10]}: {(act.get('note') or act.get('subject') or '')[:120]}")
    return "\n".join(lines)


@mcp.tool(description="Trägt eine Notiz in Close bei einem Lead ein (per close_lead_id, siehe Vault-Frontmatter oder close_search_leads).")
def create_close_note(close_lead_id: str, text: str) -> dict:
    try:
        note = close_client.create_note(close_lead_id, text)
        return {"ok": True, "note_id": note.get("id")}
    except CloseAPIError as e:
        return {"ok": False, "error": str(e)}


@mcp.tool(description=(
    "Setzt status und/oder score im Frontmatter eines Vault-Leads (status: "
    "neu/kontaktiert/qualifiziert/heiss/verloren/gewonnen, score: Zahl gemäß "
    "PLAYBOOK.md-Kriterien). Nutzen nach score_leads-artiger Bewertung im Chat "
    "oder wenn Sebastian einen Status direkt vorgibt ('markier X als heiß')."
))
def update_lead_status(name_or_path: str, status: str = "", score: str = "") -> dict:
    lead = vault_leads.find_lead(name_or_path)
    if not lead:
        return {"ok": False, "error": f"Kein Lead gefunden für '{name_or_path}'"}
    updates = {}
    if status:
        updates["status"] = status
    if score:
        updates["score"] = score
    if not updates:
        return {"ok": False, "error": "Weder status noch score angegeben."}
    vault_leads.update_fields(Path(lead["path"]), updates)
    return {"ok": True, "vault_path": lead["filename"], **updates}


@mcp.tool(description=(
    "Legt ein Sales-Brief für einen heißen Lead im Vault ab "
    "(Leads/Sales-Briefs/<Datum>-<Firma>-Sales-Brief.md). inhalt_markdown ist "
    "der fertige, von dir verfasste Brief-Text (Firma, was wir wissen, "
    "vermutete Pain Points, 3 Gesprächsaufhänger, 1 validierende Frage) - "
    "dieses Tool schreibt ihn nur mit dem richtigen Dateinamen/Frontmatter weg."
))
def generate_sales_brief(firma: str, inhalt_markdown: str) -> dict:
    from datetime import datetime
    settings = get_settings()
    briefs_dir = settings.leads_dir / "Sales-Briefs"
    briefs_dir.mkdir(parents=True, exist_ok=True)
    datum = datetime.now().strftime("%Y-%m-%d")
    safe_name = "".join(c for c in firma if c.isalnum() or c in " -")[:60].strip().replace(" ", "-")
    path = briefs_dir / f"{datum}-{safe_name}-Sales-Brief.md"
    frontmatter = f"---\ntags:\n  - Sales-Brief\nquelle: Lead-Agent\ndatum: {datum}\nkategorie: Sales\n---\n\n"
    path.write_text(frontmatter + inhalt_markdown, encoding="utf-8")
    return {"ok": True, "vault_path": str(path.relative_to(settings.vault_path))}


@mcp.tool(description=(
    "Legt einen Gmail-ENTWURF für eine personalisierte Outreach-Mail an (NIE "
    "senden - Sebastian liest und verschickt selbst). Fehlt die Empfänger-"
    "Mail, steht sie meist im Vault-Lead-Frontmatter oder -Body (nativ per "
    "Read nachsehen)."
))
def draft_outreach_email(to: str, subject: str, body: str, cc: str = "") -> dict:
    try:
        return {"ok": True, **gmail_client.create_draft(to, subject, body, cc=cc or None)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


if __name__ == "__main__":
    mcp.run(transport="stdio")
