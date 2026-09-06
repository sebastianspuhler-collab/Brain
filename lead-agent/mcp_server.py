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
import combined_leads
import export_leads as export_leads_module
import gmail_client
import lead_lookup
import vault_leads
from close_client import CloseAPIError
from config import get_settings

mcp = FastMCP("lead-agent-tools")


def _build_lead_filter(
    branche: str = "", status: str = "", score_min: str = "", region: str = "",
    letzter_kontakt_vor_tagen: str = "", freitext: str = "", quelle: str = "",
    limit: str = "100",
) -> dict:
    """Übersetzt die flachen Tool-Parameter (MCP/FastMCP-Schemata sind am
    einfachsten mit simplen Skalar-Typen, kein verschachteltes dict-Argument
    wie beim Rest der Tools hier) in den dict-Filter, den
    combined_leads.get_combined_leads() erwartet - gemeinsam genutzt von
    get_combined_leads und export_leads, keine doppelte Mapping-Logik."""
    filter: dict = {}
    if branche:
        filter["branche"] = branche
    if status:
        filter["status"] = status
    if score_min:
        filter["score_min"] = score_min
    if region:
        filter["region"] = region
    if letzter_kontakt_vor_tagen:
        filter["letzter_kontakt_vor_tagen"] = letzter_kontakt_vor_tagen
    if freitext:
        filter["freitext"] = freitext
    if quelle:
        filter["quelle"] = quelle
    if limit:
        filter["limit"] = limit
    return filter


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


@mcp.tool(description=(
    "Kombinierte Lead-Abfrage: führt Vault-Leads (Leads/*.md) UND Close-CRM-"
    "Leads in EINER strukturierten Liste zusammen, gematcht über "
    "close_lead_id. Deckt Filter-Kombinationen ab, die close_search_leads "
    "oder natives Glob allein nicht können (z.B. 'Status qualifiziert UND "
    "Score über 7 UND letzter Kontakt vor 14 Tagen'). BEVORZUGTES Tool für "
    "JEDE Anfrage nach 'meine Leads'/'zeig mir...'/einer Liste oder Tabelle "
    "von Leads - nicht einzeln Glob(Leads/) und close_search_leads von Hand "
    "kombinieren. Alle Parameter optional und frei kombinierbar, leer lassen "
    "= kein Filter auf dieses Feld. branche/region entsprechen "
    "Vault-Frontmatter-Feldern, die meist erst durch enrich_lead/"
    "save_lead_enrichment befüllt werden - vorher greift für sie nur die "
    "Freitextsuche im Notiz-Body. quelle: 'vault'|'close'|'beide' schränkt "
    "das Ergebnis auf eine Herkunft ein. Willst du das Ergebnis als "
    "herunterladbare Datei statt als Chat-Tabelle, nutze stattdessen/zusätzlich "
    "export_leads mit denselben Filtern."
))
def get_combined_leads(
    branche: str = "", status: str = "", score_min: str = "", region: str = "",
    letzter_kontakt_vor_tagen: str = "", freitext: str = "", quelle: str = "",
    limit: str = "100",
) -> list[dict]:
    filter = _build_lead_filter(branche, status, score_min, region, letzter_kontakt_vor_tagen, freitext, quelle, limit)
    return combined_leads.get_combined_leads(filter)


@mcp.tool(description=(
    "Erzeugt eine ECHTE CSV- oder XLSX-Datei (kein CSV-Text im Chat!) aus "
    "get_combined_leads mit denselben Filterparametern - IMMER nutzen, wenn "
    "Sebastian eine Liste/Tabelle/einen Export von Leads als Datei will, "
    "statt eine Tabelle als Rohtext auszugeben. format: 'csv' oder 'xlsx' "
    "(xlsx bevorzugen, wenn nicht anders gewünscht). Gib den zurückgegebenen "
    "download_url als klickbaren Markdown-Link in deiner Antwort aus (z.B. "
    "'[Excel-Export herunterladen](download_url)') - die Datei wird nach 24h "
    "automatisch aufgeräumt, also nicht als Dauerablage bewerben."
))
def export_leads(
    format: str = "csv", branche: str = "", status: str = "", score_min: str = "",
    region: str = "", letzter_kontakt_vor_tagen: str = "", freitext: str = "", quelle: str = "",
) -> dict:
    filter = _build_lead_filter(branche, status, score_min, region, letzter_kontakt_vor_tagen, freitext, quelle)
    return export_leads_module.export_leads(filter, format)


@mcp.tool(description=(
    "Recherche-VORBEREITUNG für einen Lead mit dünnen Daten (fehlende "
    "Branche/Größe/Produkt-Leistung/Zielgruppe): löst den Lead über Vault+"
    "Close auf und zeigt, was bereits bekannt ist sowie welche Kernfelder "
    "fehlen. WICHTIG: recherchiert NICHT selbst - dieses Tool läuft als "
    "eigener Server-Prozess ohne Zugriff auf dein natives WebSearch-Tool. "
    "IMMER SO NUTZEN, wenn für eine Bewertung/Filterung nötige Kernfelder "
    "fehlen: 1) enrich_lead aufrufen, 2) die zurückgegebenen "
    "fehlende_kernfelder per eigenem WebSearch recherchieren (Firma + ggf. "
    "Domain aus close_email), 3) Ergebnis per save_lead_enrichment "
    "zurückschreiben - ERST WENN WebSearch nichts Verwertbares liefert oder "
    "die Lücke keine Faktenfrage ist (z.B. Präferenzfragen wie 'was zählt "
    "für dich als perfekt'), den Nutzer fragen statt zu raten."
))
def enrich_lead(name_or_close_id: str) -> dict:
    resolved = lead_lookup.resolve(name_or_close_id)
    if not resolved["vault"] and not resolved["close"]:
        return {"ok": False, "error": f"Kein Lead gefunden für '{name_or_close_id}' (weder Vault noch Close)."}

    vault_lead = resolved["vault"]
    close_lead = resolved["close"]
    bekannt: dict = {}
    if vault_lead:
        bekannt.update({k: v for k, v in vault_lead["fields"].items() if v})
    if close_lead:
        bekannt["close_name"] = close_lead.get("display_name") or close_lead.get("name") or ""
        contacts = close_lead.get("contacts") or []
        if contacts:
            bekannt["close_kontakt"] = contacts[0].get("name", "")
            emails = [e.get("email") for e in contacts[0].get("emails", []) if e.get("email")]
            if emails:
                bekannt["close_email"] = emails[0]

    firma = Path(vault_lead["filename"]).stem if vault_lead else bekannt.get("close_name") or name_or_close_id

    return {
        "ok": True,
        "firma": firma,
        "vault_path": vault_lead["filename"] if vault_lead else "",
        "close_lead_id": resolved["close_lead_id"] or "",
        "bekannt": bekannt,
        "fehlende_kernfelder": lead_lookup.missing_core_fields(resolved),
        "hinweis": (
            "Fehlende Kernfelder jetzt per WebSearch recherchieren, danach "
            "save_lead_enrichment aufrufen - Nutzer nur fragen, wenn die "
            "Recherche nichts Verwertbares liefert."
        ),
    }


@mcp.tool(description=(
    "Schreibt recherchierte Kernfelder (branche, groesse, produkt_leistung, "
    "zielgruppe) zu einem Lead zurück - als Close-Note UND als Update im "
    "Vault-Frontmatter der zugehörigen Lead-Datei. Immer NACH eigener "
    "WebSearch-Recherche nutzen (siehe enrich_lead), nur die tatsächlich "
    "recherchierten Felder befüllen (andere leer lassen). quelle_notiz kurz "
    "benennen, woher die Angaben stammen (z.B. 'Firmenwebsite + LinkedIn, "
    "recherchiert 2026-09-06')."
))
def save_lead_enrichment(
    name_or_close_id: str, branche: str = "", groesse: str = "",
    produkt_leistung: str = "", zielgruppe: str = "", quelle_notiz: str = "",
) -> dict:
    resolved = lead_lookup.resolve(name_or_close_id)
    if not resolved["vault"] and not resolved["close_lead_id"]:
        return {"ok": False, "error": f"Kein Lead gefunden für '{name_or_close_id}'."}

    updates = {k: v for k, v in {
        "branche": branche, "groesse": groesse,
        "produkt_leistung": produkt_leistung, "zielgruppe": zielgruppe,
    }.items() if v}
    if not updates:
        return {"ok": False, "error": "Keine Felder zum Schreiben übergeben."}

    result: dict = {"ok": True}

    if resolved["vault"]:
        vault_leads.update_fields(Path(resolved["vault"]["path"]), updates)
        result["vault_path"] = resolved["vault"]["filename"]

    close_lead_id = resolved["close_lead_id"]
    if close_lead_id:
        note = "Recherche-Anreicherung (Lead-Agent):\n" + "\n".join(f"{k}: {v}" for k, v in updates.items())
        if quelle_notiz:
            note += f"\nQuelle: {quelle_notiz}"
        try:
            close_client.create_note(close_lead_id, note)
            result["close_lead_id"] = close_lead_id
        except CloseAPIError as e:
            result["close_error"] = str(e)

    return result


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
