"""MCP-Server für die externen Aktions-Tools (Buffer, LinkedIn, YouTube,
Gmail-Anhänge, Meeting-/E-Mail-Suche).

Wrappt dieselbe Business-Logik wie app/services/tools.py:execute_tool() (der
Tool-Dispatcher für den bestehenden Anthropic-API-Chat-Loop), aber als
MCP-Tools für Claude Code im Headless-Modus (Abo-Auth statt API-Key).

Vault-Dateioperationen (read_file, vault_list/create/move/rename/delete) und
Task-Verwaltung (task_add/done/remove, tasks_set) sind bewusst NICHT hier -
die deckt Claude Code nativ über --add-dir auf den Vault-Ordner ab, ganz ohne
Custom-Tool.

Start (stdio-Transport, für Registrierung in .mcp.json):
    python -m app.mcp_server
"""
import re

from mcp.server.fastmcp import FastMCP

from app.config import get_settings
from app.services import carousel_service, classify, gmail_client, linkedin_service, memory, rag
from app.services import search_service, youtube_service

mcp = FastMCP("prozessia-tools")


@mcp.tool(description=(
    "Durchsucht Kunden/*/Meetings/ und Kunden/*/Dokumente/ nach Transkripten und Protokollen. "
    "Immer nutzen wenn von Meetings, Besprechungen, Transkripten, Protokollen oder Calls die Rede ist."
))
def search_meetings(query: str, firma: str = "") -> str:
    return search_service.search_meetings(query, firma=firma or "")


@mcp.tool(description=(
    "Sucht NUR im E-Mail-Cache (Gmail/Outlook) nach Absender/Betreff/Inhalt. "
    "Nur nutzen wenn explizit von einer E-Mail die Rede ist (nicht von Meetings oder Dokumenten)."
))
def search_emails(query: str) -> str:
    return search_service.search_emails(query)


@mcp.tool(description=(
    "Lädt alle Anhänge einer Gmail-Mail herunter, speichert sie in _inbox/ und indexiert sie sofort. "
    "Die message_id steht im Gmail-Kontext (id-Feld)."
))
def download_attachment(message_id: str) -> dict:
    """Mirrors app.services.tools._download_attachment 1:1."""
    if not gmail_client.is_authenticated():
        return {"ok": False, "error": "Gmail nicht verbunden"}
    try:
        settings = get_settings()
        raw_mails = gmail_client.get_emails(top=50)
        sender = ""
        subject = ""
        for m in raw_mails:
            if m.get("id") == message_id:
                sender = m.get("from", "")
                subject = m.get("subject", "")
                break

        attachments = gmail_client.get_attachments(message_id)
        if not attachments:
            return {"ok": False, "error": "Keine Anhänge in dieser Mail gefunden"}

        settings.inbox_dir.mkdir(parents=True, exist_ok=True)
        saved = []
        for att in attachments:
            data = gmail_client.download_attachment(message_id, att["attachmentId"])
            if not data:
                continue
            dest = settings.inbox_dir / att["filename"]
            dest.write_bytes(data)
            saved.append({"filename": att["filename"], "size": att["size"]})

        classify.run_inbox()
        new_files = rag.reindex_new_files()
        for rel, content in new_files:
            memory.learn_from_file(rel, content)

        return {
            "ok": True, "message_id": message_id, "subject": subject,
            "sender": sender, "attachments": saved, "count": len(saved),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool(description="Pusht die neueste generierte beitraege-*.json (LinkedIn-Posts) sofort nach Buffer, für beide Kanäle (Sebastian + Prozessia).")
def push_to_buffer() -> dict:
    return linkedin_service.push_latest_to_buffer()


@mcp.tool(description="Generiert 10 neue LinkedIn-Ideen (4x Typ A Schmerz-Post, 3x Typ B Karussell, 3x Typ C Story) via Claude und speichert sie.")
def generate_linkedin_ideas(focus: str = "") -> dict:
    return linkedin_service.generate_ideas(focus or "")


@mcp.tool(description=(
    "Schreibt fertige LinkedIn-Post-Texte aus und pusht sie direkt nach Buffer (beide Kanäle). "
    "Spec-Format: 'Thema1/Datum1, Thema2/Datum2, Zielgruppe' - Datum ist optional (YYYY-MM-DD)."
))
def generate_linkedin_posts(spec: str) -> dict:
    result = linkedin_service.generate_posts(spec)
    if not result.get("ok"):
        return result
    push = linkedin_service.push_latest_to_buffer()
    result["push"] = push
    return result


@mcp.tool(description=(
    "Schreibt einen LinkedIn-Post-Text aus einer Idee/einem Thema und speichert ihn NUR als Entwurf - "
    "pusht NICHT nach Buffer. Für die eigentliche Veröffentlichung danach schedule_linkedin_post aufrufen."
))
def write_linkedin_post_draft(spec: str) -> dict:
    return linkedin_service.generate_posts(spec)


@mcp.tool(description="Zeigt die aktuell gespeicherten LinkedIn-Ideen (Titel, Hook, Kategorie, Branche, Format).")
def list_linkedin_ideas() -> str:
    return linkedin_service.list_ideas_text()


@mcp.tool(description="Zeigt die aktuell gespeicherten/geplanten LinkedIn-Posts (id, Tag, Termin, ob schon gepusht, Thema).")
def list_linkedin_posts() -> str:
    return linkedin_service.list_posts_text()


@mcp.tool(description="Überarbeitet den Text eines bestehenden, gespeicherten LinkedIn-Posts per id (siehe list_linkedin_posts).")
def revise_linkedin_post(post_id: str, neuer_text: str) -> dict:
    return linkedin_service.update_post_text(post_id, neuer_text)


@mcp.tool(description=(
    "Plant einen bestehenden, gespeicherten LinkedIn-Post (per id) zu Datum+Uhrzeit in Buffer ein (beide Kanäle). "
    "datum als YYYY-MM-DD, uhrzeit als HH:MM (24h, Berliner Zeit)."
))
def schedule_linkedin_post(post_id: str, datum: str, uhrzeit: str) -> dict:
    return linkedin_service.schedule_post(post_id, datum, uhrzeit)


@mcp.tool(description="Setzt die Richtungsvorgabe, die künftige LinkedIn-Ideen-/Post-Generierung beeinflusst.")
def set_linkedin_direction(prompt: str) -> dict:
    return linkedin_service.set_direction(prompt)


@mcp.tool(description=(
    "Vollständige Karussell-Pipeline: Slides (Claude) -> KI-Bilder (gpt-image-1) -> PDF -> Cloudinary -> Buffer Document-Post. "
    "Entweder post_id (Karussell aus einem bestehenden, gespeicherten Post ableiten) oder hook (freies Thema) angeben. "
    "Datum optional, ohne Datum wird der nächste Di oder Fr 09:30 genommen."
))
def generate_carousel(hook: str = "", branche: str = "Alle", saeule: str = "Wissen", due_date: str = "", post_id: str = "") -> dict:
    due_at = f"{due_date}T09:30:00+02:00" if due_date and re.match(r"\d{4}-\d{2}-\d{2}", due_date) else None
    if post_id:
        return linkedin_service.make_carousel_from_post(post_id, branche=branche or "Alle", saeule=saeule or "Wissen", due_at=due_at)
    if not hook:
        return {"ok": False, "error": "Weder hook noch post_id angegeben."}
    return carousel_service.generate_carousel(hook, branche or "Alle", saeule or "Wissen", due_at=due_at)


@mcp.tool(description="Zeigt hochgeladene NotebookLM-Videos in der YouTube-Pipeline mit Status (Titel gesetzt? schon in Buffer gepusht?).")
def list_youtube_videos() -> dict:
    return youtube_service.list_videos()


@mcp.tool(description="Schreibt Titel + Beschreibung für ein hochgeladenes YouTube-Video via Claude, auf Basis von Stichpunkten zum Videoinhalt (Claude sieht das Video selbst nicht).")
def generate_youtube_metadata(filename: str, topic: str) -> dict:
    return youtube_service.generate_metadata(filename, topic)


@mcp.tool(description="Pusht ein hochgeladenes YouTube-Video (mit gesetztem Titel) nach Buffer zur Veröffentlichung.")
def push_youtube_to_buffer(filename: str, scheduled_at: str = "") -> dict:
    return youtube_service.push_to_buffer(filename, scheduled_at or None)


if __name__ == "__main__":
    mcp.run(transport="stdio")
