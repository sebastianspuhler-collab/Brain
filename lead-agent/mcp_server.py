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
import re
from pathlib import Path

from mcp.server.fastmcp import FastMCP

import close_audit
import close_client
import combined_leads
import dedup
import export_leads as export_leads_module
import gmail_client
import lead_lookup
import prospects
import table_io
import vault_kunden
import vault_leads
from close_client import CloseAPIError
from config import get_settings

mcp = FastMCP("lead-agent-tools")


def _build_lead_filter(
    branche: str = "", status: str = "", score_min: str = "", region: str = "",
    letzter_kontakt_vor_tagen: str = "", freitext: str = "", quelle: str = "",
    limit: str = "5000",
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
    "Legt einen Prospect an - DUBLETTENFREI: prüft vorher LIVE gegen Vault (Leads+Kunden) und Close "
    "(Firmenname UND Domain). (a) Exakt dieselbe Firma vorhanden -> es wird KEIN neuer Lead angelegt, "
    "sondern der bestehende ergänzt (nur leere Felder werden gefüllt, Abweichungen stehen unter "
    "nicht_ueberschrieben, Ergebnis-aktion sagt es klar). (b) Nur ähnlicher Name (z.B. 'Kaiser GmbH' vs "
    "'Kaiser Elektrotechnik') -> NICHTS wird geschrieben, Ergebnis enthält duplikat_verdacht + aehnliche: "
    "dann Website/Ort prüfen und entweder update_lead (dieselbe Firma) oder save_prospect mit "
    "bestaetigt_neu=True (andere Firma). (c) Sonst: Vault-Lead + Close-Lead (mit Website, Ort, Branche, "
    "Mitarbeiterzahl, Umsatz, Kontakt mit Rolle als Titel) + Startnotiz mit Quellen in Close. "
    "Zwei Auslöser: NACH eigener Recherche (mehrere Quellen gegengecheckt) ODER wenn Sebastian einen "
    "Kontakt direkt nennt (dann ohne Recherche sofort anlegen, quelle z.B. 'Messekontakt'/'Sebastian "
    "(manuell)'). PFLICHT bei quelle='Recherche...': jede Angabe zu branche/mitarbeiter/umsatz/ort braucht "
    "belegende URLs in quellen (mit Leerzeichen/Komma getrennt) - ohne Beleg wird abgelehnt. NIE Fakten "
    "raten: unbekannt = leer lassen. kontakt_name ohne Rolle in Klammern - die Rolle in kontakt_rolle. "
    "warnungen im Ergebnis (z.B. E-Mail passt nicht zum Namen) MÜSSEN dem Nutzer genannt werden. "
    "aehnlich_zu: Referenzfirma (z.B. 'F-Tronic') + konkrete Begründung in notiz."
))
def save_prospect(
    firma: str, kontakt_name: str = "", kontakt_email: str = "", notiz: str = "", quelle: str = "Recherche",
    website: str = "", ort: str = "", branche: str = "", mitarbeiter: str = "", umsatz: str = "",
    kontakt_rolle: str = "", kontakt_telefon: str = "", aehnlich_zu: str = "", quellen: str = "",
    bestaetigt_neu: bool = False,
) -> dict:
    return prospects.save_prospect(
        firma, kontakt_name, kontakt_email, notiz, quelle, website, ort, branche, mitarbeiter, umsatz,
        kontakt_rolle, kontakt_telefon, aehnlich_zu, quellen, bestaetigt_neu,
    )


@mcp.tool(description=(
    "ÄNDERT einen BESTEHENDEN Lead in Vault UND Close (Firmenname, close_lead_id 'lead_...' oder Vault-"
    "Dateiname; bei mehreren passenden Leads kommt eine mehrdeutig-Liste statt eines geratenen Treffers - "
    "dann close_lead_id nehmen). Alle Felder optional, mindestens eines nötig: website, ort, branche, "
    "mitarbeiter, umsatz, Kontakt (kontakt_name/_email/_rolle/_telefon: legt den Kontakt an oder ergänzt "
    "den vorhandenen, Match per E-Mail bzw. Name), notiz (Vault-Notiz + Close-Note), close_status "
    "(Close-Pipeline-Status, nur vorhandene Labels - siehe close_lead_statuses), status/score (Vault-"
    "Bewertung), aehnlich_zu, quellen. STANDARD: nur LEERE Felder werden gefüllt, abweichende Bestandswerte "
    "bleiben stehen und erscheinen unter nicht_ueberschrieben; ueberschreiben=True ersetzt sie bewusst "
    "(nur nutzen, wenn Sebastian die Korrektur will oder ein Bestandswert nachweislich falsch ist). Das "
    "Ergebnis listet jede Änderung unter geaendert - dem Nutzer knapp wiedergeben. Faktenfelder brauchen bei "
    "quelle='Recherche' Quell-URLs in quellen, bei Angaben von Sebastian quelle='Sebastian (manuell)'. "
    "KORREKTUREN (nur mit ueberschreiben=True): zusammenfassung ersetzt den Zusammenfassungs-Text im Vault-"
    "Lead (z.B. wenn dort nachweislich falsche Angaben stehen - neuen, belegten Text schreiben); "
    "kontakt_email_entfernen löscht eine falsch zugeordnete E-Mail aus Close-Kontakten und Vault-Text; "
    "mit ueberschreiben=True ersetzt ein angegebener Kontakt außerdem den Kontakt-Abschnitt im Vault."
))
def update_lead(
    lead: str, website: str = "", ort: str = "", branche: str = "", mitarbeiter: str = "", umsatz: str = "",
    kontakt_name: str = "", kontakt_email: str = "", kontakt_rolle: str = "", kontakt_telefon: str = "",
    notiz: str = "", close_status: str = "", status: str = "", score: str = "", aehnlich_zu: str = "",
    quellen: str = "", quelle: str = "Recherche", ueberschreiben: bool = False,
    zusammenfassung: str = "", kontakt_email_entfernen: str = "",
) -> dict:
    return prospects.update_lead(
        lead, website, ort, branche, mitarbeiter, umsatz, kontakt_name, kontakt_email, kontakt_rolle,
        kontakt_telefon, notiz, close_status, status, score, aehnlich_zu, quellen, quelle, ueberschreiben,
        zusammenfassung, kontakt_email_entfernen,
    )


@mcp.tool(description=(
    "Gleicht eine LISTE von Firmen gegen Vault (Leads+Kunden) UND Close ab - rein lesend. Jeder Eintrag "
    "'Firma' oder 'Firma | website' (optional '| email'; Website verbessert die Trefferquote über die "
    "Domain). Ergebnis je Firma: vorhanden (exakt, mit close_lead_id/Status), aehnlich (Kandidaten prüfen) "
    "oder neu. IMMER nutzen, bevor du eine Rechercheliste als Neuanlagen präsentierst, und für 'welche "
    "davon sind schon in Close?'. Bei >5 Firmen lädt es einmal alle Close-Leads (erstmals ~30 s)."
))
def check_companies(firmen: list[str]) -> dict:
    return prospects.check_companies(firmen)


@mcp.tool(description=(
    "Liest eine Excel-(.xlsx) oder CSV-Datei aus dem Vault (z.B. eine Firmenliste in _inbox/ oder ein "
    "früherer Export) und gibt Spalten + Zeilen zurück (max. 1000). Danach z.B. check_companies mit den "
    "Firmennamen/Websites der Zeilen. Pfad relativ zum Vault."
))
def read_table(path: str, sheet: str = "", max_rows: int = 500) -> dict:
    return table_io.read_table(path, sheet, max_rows)


@mcp.tool(description=(
    "Liefert die in Close konfigurierten Lead-Status (Pipeline-Stufen) - nur diese können mit "
    "update_lead(close_status=...) gesetzt werden."
))
def close_lead_statuses() -> dict:
    try:
        return {"ok": True, "status": [s.get("label") for s in close_client.list_lead_statuses()]}
    except CloseAPIError as e:
        return {"ok": False, "error": str(e)}


@mcp.tool(description=(
    "Verknüpft eine BEREITS bestehende Vault-Firma mit Close CRM: entweder "
    "ein Lead (Leads/*.md, z.B. automatisch aus einer E-Mail/einem "
    "Kalendertermin erkannt) ODER ein etablierter Kunde (Kunden/<Firma>/-"
    "Ordner - jemand, mit dem bereits Kontakt besteht). Legt sie in Close an "
    "(oder aktualisiert sie, falls schon verknüpft) und schreibt die "
    "Verknüpfung zurück (Lead-Frontmatter bzw. Kunden/<Firma>/"
    "close_lead_id.txt). name_or_path: Dateiname/Ordnername/Stichwort. "
    "WICHTIG: für einen bereits per Namensabgleich GEFUNDENEN Treffer aus "
    "audit_vault_close_matches()['neu_verknuepfbar'] NICHT dieses Tool "
    "nutzen (würde einen zweiten, doppelten Close-Lead anlegen), sondern "
    "link_vault_to_close mit der schon bekannten close_lead_id."
))
def sync_lead_to_close(name_or_path: str, bestaetigt_neu: bool = False) -> dict:
    lead = vault_leads.find_lead(name_or_path)
    kunde = None if lead else vault_kunden.find_kunde(name_or_path)
    if not lead and not kunde:
        return {"ok": False, "error": f"Kein Lead oder Kundenordner gefunden für '{name_or_path}'"}

    if lead:
        # Datumspräfix (YYYY-MM-DD-) aus dem Dateinamen entfernen, für einen
        # saubereren Close-Lead-Namen.
        firma = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", Path(lead["filename"]).stem)
        existing_id = (lead["fields"].get("close_lead_id") or "").strip()
    else:
        firma = kunde["firma"]
        existing_id = kunde["close_lead_id"]

    try:
        if existing_id:
            close_client.update_lead(existing_id, {"name": firma})
            close_lead_id = existing_id
        else:
            # Erst prüfen, ob es die Firma in Close schon gibt (z.B. aus dem
            # Massenimport) - sonst entsteht eine Dublette.
            matches = dedup.find_matches(firma)
            exact_with_id = [m for m in matches["exakt"] if m["close_lead_id"]]
            if exact_with_id:
                close_lead_id = exact_with_id[0]["close_lead_id"]
            elif matches["aehnlich"] and not bestaetigt_neu:
                return {
                    "ok": False, "duplikat_verdacht": True, "aehnliche": matches["aehnlich"],
                    "hinweis": "Ähnliche Firmen existieren bereits - nichts angelegt. Dieselbe Firma: link_vault_to_close mit deren close_lead_id; andere Firma: erneut mit bestaetigt_neu=True.",
                }
            else:
                close_lead = close_client.create_lead(firma)
                close_client.tag_lead_source(close_lead["id"])
                close_lead_id = close_lead["id"]

        if lead:
            vault_leads.update_fields(Path(lead["path"]), {"close_lead_id": close_lead_id})
            vault_path = lead["filename"]
        else:
            vault_kunden.link_to_close(Path(kunde["path"]), close_lead_id)
            vault_path = kunde["path"]

        return {"ok": True, "close_lead_id": close_lead_id, "vault_path": vault_path}
    except CloseAPIError as e:
        return {"ok": False, "error": str(e)}


@mcp.tool(description=(
    "Sucht Leads direkt in Close CRM (Stichwort in Name/Kontakten/Website; leer = alle). Liefert je Lead "
    "id, Name, Status, Website, Ort, Branche, Mitarbeiter, Kontakte (Name, Rolle, E-Mail) und Anlagedatum. "
    "status: optional exakter Close-Status als Filter (z.B. 'Termin vereinbart'). limit (Default 50, max "
    "500). Für Listen über Vault UND Close mit Filtern stattdessen get_combined_leads."
))
def close_search_leads(query: str = "", status: str = "", limit: int = 50) -> dict:
    limit = max(1, min(int(limit or 50), 500))
    q = query.strip()
    if status.strip():
        q = f'{q} status:"{status.strip()}"'.strip()
    try:
        leads = close_client.search_leads(q, limit=limit + 1)
    except CloseAPIError as e:
        return {"ok": False, "error": f"Close-Fehler: {e}"}
    rows = []
    for lead in leads[:limit]:
        custom = lead.get("custom") or {}
        rows.append({
            "close_lead_id": lead.get("id"),
            "firma": lead.get("display_name") or lead.get("name"),
            "status": lead.get("status_label", ""),
            "website": lead.get("url") or "",
            "ort": combined_leads._close_city(lead),
            "branche": combined_leads._close_custom(lead, "branche"),
            "mitarbeiter": combined_leads._close_custom(lead, "mitarbeiteranzahl"),
            "kontakte": [
                {"name": c.get("name", ""), "rolle": c.get("title") or "", "emails": [e.get("email") for e in c.get("emails", []) if e.get("email")]}
                for c in lead.get("contacts") or []
            ],
            "angelegt": (lead.get("date_created") or "")[:10],
        })
    return {"ok": True, "anzahl": len(rows), "gekuerzt": len(leads) > limit, "leads": rows}


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
    "Prüft GRÜNDLICH über Vault (Kunden/<Firma>/-Ordner MIT bestehendem "
    "Kontakt UND Leads/*.md) und Close CRM hinweg, welche Firmen es in "
    "BEIDEN Systemen gibt, aber noch NICHT über close_lead_id verknüpft "
    "sind (Namensabgleich, z.B. 'F-Tronic' vs. 'f-tronic GmbH' - erkennt "
    "auch Kunden, die längst als eigenständiger Close-Lead existieren, aber "
    "nie verknüpft wurden). Rein LESEND, schreibt nichts. Liefert: "
    "neu_verknuepfbar (Namensmatch gefunden, nur noch verknüpfen -> "
    "link_vault_to_close nutzen, NICHT sync_lead_to_close - sonst entsteht "
    "ein doppelter Close-Lead), kunden_ohne_close_kontakt (etablierte "
    "Kunden OHNE jeden Close-Eintrag - Kandidaten fürs Neuanlegen, aber "
    "erst mit Sebastian abstimmen WELCHE, nicht blind alle anlegen), "
    "leads_ohne_close_kontakt (dasselbe für frische Leads), sowie "
    "close_leads_ohne_vault_treffer_anzahl (nur eine Zahl + kleine "
    "Vorschau, keine Vollliste - der Fokus liegt auf der Vault-Seite)."
))
def audit_vault_close_matches() -> dict:
    return close_audit.audit()


@mcp.tool(description=(
    "Verknüpft eine Vault-Firma (Kunde ODER Lead) mit einer BEREITS "
    "bekannten close_lead_id - für Treffer aus "
    "audit_vault_close_matches()['neu_verknuepfbar']. Legt NICHTS neu in "
    "Close an (reiner Vault-Schreibzugriff, keine Close-API-Aufrufe) - für "
    "eine noch fehlende Close-Neuanlage stattdessen sync_lead_to_close nutzen."
))
def link_vault_to_close(firma_or_path: str, close_lead_id: str) -> dict:
    return close_audit.link(firma_or_path, close_lead_id)


@mcp.tool(description=(
    "Recherche-AUSGANGSPUNKT (Sebastians 'Recherchetool'): liefert das "
    "bekannte Profil eines Referenz-Leads ODER -Kunden (Firma, bekannte "
    "Felder, Kontakt, Close-Link) als Vorlage, um WEITERE ähnliche "
    "Prospects zu finden - NICHT selbst recherchierend (kein WebSearch-"
    "Zugriff hier, siehe enrich_lead). name_or_close_id kann auch ein "
    "bestehender Kunde sein (Kunden/<Firma>/), z.B. für 'finde mehr Firmen "
    "wie F-Tronic'. IMMER SO NUTZEN: 1) find_similar_leads_context "
    "aufrufen, 2) ist typ 'kunde', zusätzlich NATIV per Glob/Read in "
    "vault_path/**/*.md (Meetings/Dokumente/Angebote) lesen für Branche/"
    "Kontext - dort steht meist mehr als im schlanken Profil hier, 3) mit "
    "diesem Profil per eigenem WebSearch nach ähnlichen Unternehmen suchen "
    "(gleiche Branche/Region/Größenordnung), 4) JEDEN Treffer über "
    "save_prospect anlegen (schreibt Vault-Lead UND Close-Lead in einem "
    "Schritt - kein weiteres 'in Close anlegen'-Tool nötig)."
))
def find_similar_leads_context(name_or_close_id: str) -> dict:
    resolved = lead_lookup.resolve(name_or_close_id)
    vault_lead = resolved["vault"]
    kunde = resolved["kunde"]
    close_lead = resolved["close"]
    if not vault_lead and not kunde and not close_lead:
        return {
            "ok": False,
            "error": (
                f"Kein Lead/Kunde gefunden für '{name_or_close_id}' - als "
                "Referenz für die Recherche wird ein bekannter Ausgangspunkt gebraucht."
            ),
        }

    profil: dict = {}
    if vault_lead:
        profil.update({k: v for k, v in vault_lead["fields"].items() if v})
    if close_lead:
        profil["close_name"] = close_lead.get("display_name") or close_lead.get("name") or ""

    firma = (
        Path(vault_lead["filename"]).stem if vault_lead
        else kunde["firma"] if kunde
        else profil.get("close_name") or name_or_close_id
    )
    typ = "kunde" if kunde else ("lead" if vault_lead else "nur_close")

    return {
        "ok": True,
        "firma": firma,
        "typ": typ,
        "vault_path": kunde["path"] if kunde else (vault_lead["filename"] if vault_lead else ""),
        "close_lead_id": resolved["close_lead_id"] or "",
        "bekanntes_profil": profil,
        "hinweis": (
            "Ist typ 'kunde': zusätzlich nativ per Glob/Read in "
            "vault_path/**/*.md recherchieren, dort steht der eigentliche "
            "Kontext. Danach per WebSearch nach ähnlichen Firmen suchen und "
            "jeden Treffer mit save_prospect anlegen."
        ),
    }


@mcp.tool(description=(
    "Kombinierte Lead-Abfrage: führt Vault-Leads (Leads/*.md) UND Close-CRM-"
    "Leads in EINER strukturierten Liste zusammen, gematcht über "
    "close_lead_id. Deckt Filter-Kombinationen ab, die close_search_leads "
    "oder natives Glob allein nicht können (z.B. 'Status qualifiziert UND "
    "Score über 7 UND letzter Kontakt vor 14 Tagen'). BEVORZUGTES Tool für "
    "JEDE Anfrage nach 'meine Leads'/'zeig mir...'/einer Liste oder Tabelle "
    "von Leads - nicht einzeln Glob(Leads/) und close_search_leads von Hand "
    "kombinieren. Alle Parameter optional und frei kombinierbar, leer lassen "
    "= kein Filter auf dieses Feld. status matcht den Vault-Status "
    "(neu/kontaktiert/...) ODER den Close-Status (Nicht erreicht/Termin "
    "vereinbart/...). branche/region/freitext durchsuchen Vault-Felder, "
    "Notiztext UND Close-Felder (Branche, Ort, Kontakte, Website). "
    "angelegt_seit_tagen: nur Leads jünger als N Tage. quelle: "
    "'vault'|'close'|'beide' schränkt auf eine Herkunft ein. Jede Zeile "
    "hat auch website, ort, branche, mitarbeiter, umsatz, close_status, "
    "aehnlich_zu. WICHTIG: close_verfuegbar=false heißt, die Liste ist "
    "unvollständig (nur Vault) - das dem Nutzer sagen. Willst du das Ergebnis als "
    "herunterladbare Datei statt als Chat-Tabelle, nutze stattdessen/zusätzlich "
    "export_leads mit denselben Filtern (spalten wählbar)."
))
def get_combined_leads(
    branche: str = "", status: str = "", score_min: str = "", region: str = "",
    letzter_kontakt_vor_tagen: str = "", freitext: str = "", quelle: str = "",
    limit: str = "5000", angelegt_seit_tagen: str = "",
) -> dict:
    filter = _build_lead_filter(branche, status, score_min, region, letzter_kontakt_vor_tagen, freitext, quelle, limit)
    if angelegt_seit_tagen:
        filter["angelegt_seit_tagen"] = angelegt_seit_tagen
    rows, meta = combined_leads.get_combined_leads_with_meta(filter)
    out = {"anzahl": len(rows), **meta, "leads": rows}
    if not meta["close_verfuegbar"]:
        out["warnung"] = "Close nicht erreichbar - Liste enthält NUR Vault-Leads und ist unvollständig. Dem Nutzer sagen."
    return out


@mcp.tool(description=(
    "Erzeugt eine ECHTE CSV- oder XLSX-Datei (kein CSV-Text im Chat!) aus "
    "get_combined_leads mit denselben Filterparametern - IMMER nutzen, wenn "
    "Sebastian eine Liste/Tabelle/einen Export von Leads als Datei will, "
    "statt eine Tabelle als Rohtext auszugeben. format: 'csv' oder 'xlsx' "
    "(xlsx bevorzugen, wenn nicht anders gewünscht). Gib den zurückgegebenen "
    "download_url als klickbaren Markdown-Link in deiner Antwort aus (z.B. "
    "'[Excel-Export herunterladen](download_url)') - die Datei wird nach 24h "
    "automatisch aufgeräumt, also nicht als Dauerablage bewerben. spalten: "
    "kommagetrennt aus firma, kontakt, quelle, status, score, letzter_kontakt, "
    "close_lead_id, close_link, vault_path, website, ort, branche, mitarbeiter, "
    "umsatz, close_status, aehnlich_zu, quellen, angelegt (leer = Standardspalten)."
))
def export_leads(
    format: str = "csv", branche: str = "", status: str = "", score_min: str = "",
    region: str = "", letzter_kontakt_vor_tagen: str = "", freitext: str = "", quelle: str = "",
    spalten: str = "", angelegt_seit_tagen: str = "",
) -> dict:
    filter = _build_lead_filter(branche, status, score_min, region, letzter_kontakt_vor_tagen, freitext, quelle)
    if angelegt_seit_tagen:
        filter["angelegt_seit_tagen"] = angelegt_seit_tagen
    return export_leads_module.export_leads(filter, format, spalten or None)


@mcp.tool(description=(
    "Exportiert eine BELIEBIGE, von dir zusammengestellte Tabelle als echte xlsx/csv-Datei - z.B. "
    "Rechercheergebnisse, das Ergebnis von check_companies, eine Auswahl/Umsortierung. rows: Liste von "
    "Objekten (ein Objekt pro Zeile, gleiche Schlüssel); spalten: optionale Reihenfolge/Auswahl der "
    "Schlüssel (leer = alle); dateiname: kurzer Name ohne Endung. download_url als klickbaren "
    "Markdown-Link ausgeben. Für reine Vault/Close-Bestandslisten ist export_leads bequemer."
))
def export_table(rows: list[dict], spalten: list[str] | None = None, format: str = "xlsx", dateiname: str = "tabelle") -> dict:
    return export_leads_module.export_table(rows, spalten, format, dateiname)


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
    if not resolved["vault"] and not resolved["kunde"] and not resolved["close"]:
        return {"ok": False, "error": f"Kein Lead/Kunde gefunden für '{name_or_close_id}' (weder Vault noch Close)."}

    vault_lead = resolved["vault"]
    kunde = resolved["kunde"]
    close_lead = resolved["close"]
    bekannt: dict = {}
    if vault_lead:
        bekannt.update({k: v for k, v in vault_lead["fields"].items() if v})
    if kunde:
        bekannt["vault_typ"] = "bestehender Kunde (Kunden/-Ordner, kein Frontmatter für Kernfelder)"
    if close_lead:
        bekannt["close_name"] = close_lead.get("display_name") or close_lead.get("name") or ""
        contacts = close_lead.get("contacts") or []
        if contacts:
            bekannt["close_kontakt"] = contacts[0].get("name", "")
            emails = [e.get("email") for e in contacts[0].get("emails", []) if e.get("email")]
            if emails:
                bekannt["close_email"] = emails[0]

    firma = (
        Path(vault_lead["filename"]).stem if vault_lead
        else kunde["firma"] if kunde
        else bekannt.get("close_name") or name_or_close_id
    )

    return {
        "ok": True,
        "firma": firma,
        "vault_path": vault_lead["filename"] if vault_lead else (kunde["path"] if kunde else ""),
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
        status = status.strip().lower()
        if status not in prospects.VAULT_STATUSES:
            return {"ok": False, "error": f"status '{status}' ungültig (erlaubt: {', '.join(prospects.VAULT_STATUSES)})."}
        updates["status"] = status
    if score:
        try:
            float(score.replace(",", "."))
        except ValueError:
            return {"ok": False, "error": f"score '{score}' ist keine Zahl."}
        updates["score"] = score.replace(",", ".")
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
