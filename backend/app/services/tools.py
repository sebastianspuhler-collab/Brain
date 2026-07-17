"""Claude Tool Use: Tool-Schemas + Dispatcher für den Chat-Agentic-Loop.
Migriert aus brain_server.py (TOOLS, execute_tool, tool_read_file). Portiert
16 der 17 Legacy-Tools — nur vault_reorganize bewusst zurückgestellt (siehe
Umbau-Plan: höheres Risiko bei KI-geplanter Massen-Reorganisation). generate_carousel
läuft jetzt über den content-engine-Docker-Service statt Mac-lokalem Subprocess.
"""
import json
import re
from pathlib import Path

from app.config import get_settings
from app.services import carousel_service, classify, gmail_client, linkedin_service, memory, rag
from app.services import search_service, tasks_service, vault_service, youtube_service

TOOLS = [
    {
        "name": "read_file",
        "description": (
            "Liest eine Datei aus dem Vault (Verträge, Angebote, Kundendokumente etc.). "
            "Nutze dies wenn eine Datei erwähnt wird, die noch nicht im Kontext steht — "
            "nie 'kann ich nicht einsehen' sagen, sondern dieses Tool nutzen. "
            "Akzeptiert exakten Pfad, reinen Dateinamen oder ein Stichwort im Dateinamen; "
            "der Server sucht automatisch im ganzen Vault danach. PDF/DOCX werden automatisch als Text extrahiert."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Pfad, Dateiname oder Stichwort, z.B. 'Sales/Geginat/Vertriebsvereinbarung.md' oder 'Geginat'"}
            },
            "required": ["path"],
        },
    },
    {
        "name": "search_meetings",
        "description": (
            "Durchsucht Kunden/*/Meetings/ und Kunden/*/Dokumente/ nach Transkripten und Protokollen. "
            "Immer nutzen wenn von Meetings, Besprechungen, Transkripten, Protokollen oder Calls die Rede ist."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Stichwort, z.B. 'winform' oder 'Jochen'"},
                "firma": {"type": "string", "description": "Optional: Firmenname, um die Suche auf Kunden/<Firma>/ einzugrenzen"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_emails",
        "description": (
            "Sucht NUR im E-Mail-Cache (Gmail/Outlook) nach Absender/Betreff/Inhalt. "
            "Nur nutzen wenn explizit von einer E-Mail die Rede ist (nicht von Meetings oder Dokumenten). "
            "NIEMALS vault_list auf _agent/email_cache benutzen — das listet 250+ Dateien ohne Filter, dafür immer dieses Tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Stichwörter mit Leerzeichen getrennt, z.B. 'Mittelstand Digital Michelle'"}
            },
            "required": ["query"],
        },
    },
    {
        "name": "vault_list",
        "description": "Zeigt den Ordnerinhalt eines Vault-Pfads — nur für Struktur-Übersichten, NICHT für E-Mail-Suche (dafür search_emails nutzen).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Ordnerpfad relativ zum Vault-Root, leer = Root"}
            },
        },
    },
    {
        "name": "vault_create",
        "description": "Erstellt einen neuen Ordner im Vault (auch verschachtelt).",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "z.B. 'Kunden/Mueller-GmbH'"}},
            "required": ["path"],
        },
    },
    {
        "name": "vault_move",
        "description": "Verschiebt eine Datei oder einen Ordner im Vault.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "destination": {"type": "string"},
            },
            "required": ["source", "destination"],
        },
    },
    {
        "name": "vault_rename",
        "description": "Benennt eine Datei oder einen Ordner im Vault um.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "aktueller Pfad"},
                "new_name": {"type": "string", "description": "neuer Name"},
            },
            "required": ["path", "new_name"],
        },
    },
    {
        "name": "vault_delete",
        "description": (
            "Löscht eine Datei oder einen Ordner (rekursiv) im Vault, endgültig. "
            "Vor allem für automatisch angelegte Inhalte, die sich als falsch "
            "erweisen (z.B. ein fälschlich erkannter Kalender-Lead in Leads/). "
            "Bei Ordnern oder mehrdeutigen Anfragen vorher kurz den genauen Pfad "
            "bestätigen lassen, bei eindeutigen Einzeldateien direkt ausführen."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Pfad relativ zum Vault-Root"}},
            "required": ["path"],
        },
    },
    {
        "name": "download_attachment",
        "description": (
            "Lädt alle Anhänge einer Gmail-Mail herunter, speichert sie in _inbox/ und indexiert sie sofort. "
            "Die message_id steht im Gmail-Kontext (id-Feld). Niemals 'kann ich nicht' sagen — dieses Tool nutzen."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"message_id": {"type": "string"}},
            "required": ["message_id"],
        },
    },
    {
        "name": "task_add",
        "description": "Fügt eine neue offene Aufgabe in der Sidebar hinzu (context.md). Sidebar aktualisiert sich sofort.",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "task_done",
        "description": "Markiert eine Aufgabe (per Text oder Teiltext) als erledigt. Immer sofort nutzen wenn Sebastian sagt etwas sei erledigt/passiert/fertig — nicht nachfragen.",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "task_remove",
        "description": "Entfernt eine Aufgabe (per Text oder Teiltext) komplett aus der Liste.",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "tasks_set",
        "description": "Ersetzt die gesamte offene Aufgabenliste durch eine neue Liste.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tasks": {"type": "array", "items": {"type": "string"}, "description": "Liste der neuen offenen Aufgaben"}
            },
            "required": ["tasks"],
        },
    },
    {
        "name": "push_to_buffer",
        "description": "Pusht die neueste generierte beitraege-*.json (LinkedIn-Posts) sofort nach Buffer, für beide Kanäle (Sebastian + Prozessia).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "generate_linkedin_ideas",
        "description": "Generiert 10 neue LinkedIn-Ideen (4x Typ A Schmerz-Post, 3x Typ B Karussell, 3x Typ C Story) via Claude und speichert sie.",
        "input_schema": {
            "type": "object",
            "properties": {"focus": {"type": "string", "description": "Optionaler thematischer Fokus"}},
        },
    },
    {
        "name": "generate_linkedin_posts",
        "description": (
            "Schreibt fertige LinkedIn-Post-Texte aus und pusht sie direkt nach Buffer (beide Kanäle). "
            "Spec-Format: 'Thema1/Datum1, Thema2/Datum2, Zielgruppe' — Datum ist optional (YYYY-MM-DD)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"spec": {"type": "string"}},
            "required": ["spec"],
        },
    },
    {
        "name": "generate_carousel",
        "description": (
            "Vollständige Karussell-Pipeline: Slides (Claude) → KI-Bilder (gpt-image-1) → PDF → Cloudinary → Buffer Document-Post. "
            "Datum optional, ohne Datum wird der nächste Di oder Fr 09:30 genommen."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "hook": {"type": "string", "description": "Hook-Text für die erste Slide"},
                "branche": {"type": "string", "description": "z.B. Werkzeugbau, Maschinenbau — Default 'Alle'"},
                "saeule": {"type": "string", "description": "Themen-Säule, Default 'Wissen'"},
                "due_date": {"type": "string", "description": "Optional YYYY-MM-DD"},
            },
            "required": ["hook"],
        },
    },
    {
        "name": "list_youtube_videos",
        "description": "Zeigt hochgeladene NotebookLM-Videos in der YouTube-Pipeline mit Status (Titel gesetzt? schon in Buffer gepusht?). Videos werden über die Brain-UI hochgeladen, nicht über den Chat.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "generate_youtube_metadata",
        "description": "Schreibt Titel + Beschreibung für ein hochgeladenes YouTube-Video via Claude, auf Basis von Stichpunkten zum Videoinhalt (Claude sieht das Video selbst nicht).",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Dateiname des Videos, siehe list_youtube_videos"},
                "topic": {"type": "string", "description": "Stichpunkte/Thema zum Videoinhalt"},
            },
            "required": ["filename", "topic"],
        },
    },
    {
        "name": "push_youtube_to_buffer",
        "description": "Pusht ein hochgeladenes YouTube-Video (mit gesetztem Titel) nach Buffer zur Veröffentlichung.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Dateiname des Videos, siehe list_youtube_videos"},
                "scheduled_at": {"type": "string", "description": "Optional: ISO-8601 Zeitpunkt, leer = nächster freier Slot in Buffer"},
            },
            "required": ["filename"],
        },
    },
]

_TASK_TOOL_NAMES = {"task_add", "task_done", "task_remove", "tasks_set"}


def _read_vault_file_content(path: Path) -> str:
    if path.suffix.lower() in {".md", ".txt"}:
        return path.read_text(encoding="utf-8", errors="ignore")[:6000]
    text = classify.extract_text(path)
    return text if text else "[Kein Textinhalt extrahierbar]"


def _tool_read_file(req_path: str) -> str:
    """Liest exakten Pfad, sonst Dateiname-Suche, sonst Stichwort-Suche im ganzen Vault."""
    vault = get_settings().vault_path
    target = vault / req_path
    if target.exists() and target.is_file():
        return f"Datei: {req_path}\n\n{_read_vault_file_content(target)}"
    fname = Path(req_path).name
    for hit in vault.rglob(fname):
        if hit.is_file():
            rel = str(hit.relative_to(vault))
            return f"Datei: {rel}\n\n{_read_vault_file_content(hit)}"
    kw = req_path.lower().strip()
    for ext in ("*.md", "*.txt", "*.pdf", "*.docx"):
        for hit in vault.rglob(ext):
            if kw in hit.stem.lower():
                rel = str(hit.relative_to(vault))
                return f"Datei: {rel}\n\n{_read_vault_file_content(hit)}"
    return f"Datei nicht gefunden: {req_path}"


def _download_attachment(message_id: str) -> dict:
    """Mirrors brain_server.py:api_gmail_download_attachments — Anhänge laden,
    in _inbox/ speichern, sofort per Inbox-Pipeline einsortieren + reindizieren."""
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


def execute_tool(name: str, tool_input: dict) -> tuple[str, bool]:
    """Führt ein Tool aus. Gibt (text, is_error) zurück, für den tool_result-Block."""
    try:
        if name == "read_file":
            text = _tool_read_file(tool_input.get("path", ""))
            return text, text.startswith("Datei nicht gefunden")

        if name == "search_meetings":
            query = tool_input.get("query", "")
            firma = tool_input.get("firma", "") or ""
            return search_service.search_meetings(query, firma=firma), False

        if name == "search_emails":
            return search_service.search_emails(tool_input.get("query", "")), False

        if name == "vault_list":
            path = tool_input.get("path", "") or ""
            if "email_cache" in path.lower():
                return "vault_list auf email_cache ist deaktiviert (250+ Dateien). Nutze stattdessen search_emails.", True
            return vault_service.vault_list(path), False

        if name == "vault_create":
            result = vault_service.vault_create(tool_input.get("path", ""))
            return json.dumps(result, ensure_ascii=False), not result.get("ok")

        if name == "vault_move":
            result = vault_service.vault_move(tool_input.get("source", ""), tool_input.get("destination", ""))
            return json.dumps(result, ensure_ascii=False), not result.get("ok")

        if name == "vault_rename":
            result = vault_service.vault_rename(tool_input.get("path", ""), tool_input.get("new_name", ""))
            return json.dumps(result, ensure_ascii=False), not result.get("ok")

        if name == "vault_delete":
            result = vault_service.vault_delete(tool_input.get("path", ""))
            return json.dumps(result, ensure_ascii=False), not result.get("ok")

        if name == "download_attachment":
            result = _download_attachment(tool_input.get("message_id", ""))
            if not result.get("ok"):
                return f"Fehler: {result.get('error', '?')}", True
            files_info = "\n".join(f"  - {a['filename']} ({a['size']} Bytes)" for a in result.get("attachments", []))
            return (
                f"{result['count']} Anhang/Anhaenge heruntergeladen aus: {result.get('subject', '?')}\n"
                f"{files_info}\n\nDateien liegen in _inbox/ und wurden einsortiert.",
                False,
            )

        if name == "task_add":
            result = tasks_service.add_task(tool_input.get("text", ""))
            ok = result.get("ok", False)
            return ("Aufgabe hinzugefuegt." if ok else result.get("error", "Fehler beim Hinzufuegen.")), not ok

        if name == "task_done":
            result = tasks_service.toggle_task(tool_input.get("text", ""), done=True)
            ok = result.get("changed", False)
            return ("Aufgabe als erledigt markiert." if ok else "Aufgabe nicht gefunden."), not ok

        if name == "task_remove":
            result = tasks_service.delete_task(tool_input.get("text", ""))
            ok = result.get("removed", False)
            return ("Aufgabe entfernt." if ok else "Aufgabe nicht gefunden."), not ok

        if name == "tasks_set":
            tasks = tool_input.get("tasks", [])
            result = tasks_service.set_tasks(tasks)
            return f"Aufgabenliste aktualisiert: {result.get('count', 0)} offene Aufgaben.", False

        if name == "push_to_buffer":
            result = linkedin_service.push_latest_to_buffer()
            ok = result.get("ok")
            return ("Posts in Buffer eingeplant." if ok else f"Buffer-Fehler: {result.get('error', '?')}"), not ok

        if name == "generate_linkedin_ideas":
            result = linkedin_service.generate_ideas(tool_input.get("focus", "") or "")
            ok = result.get("ok")
            n = result.get("anzahl", 0)
            return (f"{n} neue Ideen generiert und gespeichert." if ok else f"Fehler: {result.get('error', '?')}"), not ok

        if name == "generate_linkedin_posts":
            spec = tool_input.get("spec", "")
            result = linkedin_service.generate_posts(spec)
            if not result.get("ok"):
                return f"Generierung fehlgeschlagen: {result.get('error', '?')}", True
            push = linkedin_service.push_latest_to_buffer()
            if push.get("ok"):
                return f"{len(result.get('posts', []))} Posts generiert und in Buffer eingeplant.", False
            return f"Posts generiert — Buffer Push: {push.get('error', '?')}", False

        if name == "generate_carousel":
            hook = tool_input.get("hook", "")
            branche = tool_input.get("branche") or "Alle"
            saeule = tool_input.get("saeule") or "Wissen"
            due_date = tool_input.get("due_date")
            due_at = f"{due_date}T09:30:00+02:00" if due_date and re.match(r"\d{4}-\d{2}-\d{2}", due_date) else None
            result = carousel_service.generate_carousel(hook, branche, saeule, due_at=due_at)
            if result.get("ok"):
                n = result.get("slides", 0)
                due = (result.get("due_at") or "")[:10]
                pushed = result.get("anzahl_gepusht", 0)
                titles = " | ".join((result.get("slide_titles") or [])[:3])
                return f"Karussell fertig — {n} Slides | Buffer: {pushed}x eingeplant für {due} | {titles}", False
            return f"Karussell-Fehler: {result.get('error', '?')}", True

        if name == "list_youtube_videos":
            result = youtube_service.list_videos()
            videos = result.get("videos", [])
            if not videos:
                return "Keine Videos in der YouTube-Pipeline.", False
            lines = [
                f"- {v['filename']}: {v['title'] or '(kein Titel)'} "
                f"({'gepusht' if v['pushed'] else 'offen'})"
                for v in videos
            ]
            return "\n".join(lines), False

        if name == "generate_youtube_metadata":
            result = youtube_service.generate_metadata(tool_input.get("filename", ""), tool_input.get("topic", ""))
            ok = result.get("ok")
            return (f"Titel: {result.get('title')}\nBeschreibung: {result.get('description')}" if ok else f"Fehler: {result.get('error', '?')}"), not ok

        if name == "push_youtube_to_buffer":
            result = youtube_service.push_to_buffer(tool_input.get("filename", ""), tool_input.get("scheduled_at") or None)
            ok = result.get("ok")
            return ("Video in Buffer eingeplant." if ok else f"Buffer-Fehler: {result.get('error', '?')}"), not ok

        return f"Unbekanntes Tool: {name}", True
    except Exception as e:
        return f"Tool-Fehler ({name}): {e}", True
