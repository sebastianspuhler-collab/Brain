"""LinkedIn-Autoposter-Bridge. Migriert aus brain_server.py (api_linkedin_*).
Liest/schreibt JSON-Output des externen Autoposter-Skripts im Vault."""
import json
import logging
import re
import urllib.request
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import get_settings
from app.constants import Models
from app.services import cache, carousel_service
from app.services.anthropic_client import get_client, get_response_text

BERLIN = ZoneInfo("Europe/Berlin")

logger = logging.getLogger("brain.linkedin")

BUFFER_GRAPHQL = "https://api.buffer.com/graphql"


def _direction_path():
    return get_settings().autoposter_dir / "brain-direction.md"


def _latest_file(prefix: str):
    out = get_settings().autoposter_dir
    if not out.exists():
        return None
    files = sorted(out.glob(f"{prefix}-*.json"), reverse=True)
    return files[0] if files else None


def get_ideas() -> dict:
    cached = cache.get("li_ideas")
    if cached is not None:
        return cached
    path = _latest_file("ideen")
    if not path:
        return {"ideen": [], "datum": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        result = {
            "datum": data.get("generiert_am", "")[:10],
            "ideen": [
                {
                    "typ": i.get("typ", ""),
                    "titel": i.get("titel", ""),
                    "hook": i.get("hook", ""),
                    "kategorie": i.get("kategorie", ""),
                    "branche": i.get("branche", ""),
                    "format": i.get("format_empfehlung", ""),
                    "cta": i.get("cta_vorschlag", ""),
                }
                for i in data.get("ideen", [])
            ],
        }
        cache.set("li_ideas", result)
        return result
    except Exception as e:
        return {"ideen": [], "datum": None, "error": str(e)}


_WEEKDAY_KEYS = ("montag", "dienstag", "mittwoch", "donnerstag", "freitag")


def _normalize_posts(data: dict) -> list[dict]:
    """Liest Posts aus einer beitraege-*.json, egal ob altes Format
    (Wochentag als Key, ein Post pro Tag - kollidiert bei mehreren Posts am
    selben Tag) oder neues Format (Liste mit stabiler id pro Post)."""
    if isinstance(data.get("posts"), list):
        return data["posts"]

    # Altes Format: aus den Wochentag-Keys eine Liste mit abgeleiteter id bauen.
    posts = []
    datum = data.get("generiert_am", "")[:10]
    for key in _WEEKDAY_KEYS:
        p = data.get(key)
        if not p:
            continue
        posts.append({
            "id": f"{datum}-{key}",
            "tag": key.capitalize(),
            "datum": datum,
            "termin": p.get("termin", ""),
            "idee": p.get("idee", ""),
            "typ": p.get("typ", ""),
            "text": p.get("text", ""),
        })
    return posts


def get_posts() -> dict:
    cached = cache.get("li_posts")
    if cached is not None:
        return cached
    path = _latest_file("beitraege")
    if not path:
        return {"posts": [], "datum": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        posts = [
            {
                "id": p.get("id", ""),
                "tag": p.get("tag", ""),
                "termin": p.get("termin", ""),
                "idee": p.get("idee", ""),
                "text_preview": p.get("text", "")[:200],
                "pushed": bool(p.get("pushed")),
            }
            for p in _normalize_posts(data)
        ]
        result = {"datum": path.stem.replace("beitraege-", ""), "posts": posts}
        cache.set("li_posts", result)
        return result
    except Exception as e:
        return {"posts": [], "datum": None, "error": str(e)}


def get_post(post_id: str) -> dict | None:
    """Findet einen einzelnen Post (voller Text) über seine id, für die
    Detail-/Bearbeitungsansicht im Dashboard."""
    path = _latest_file("beitraege")
    if not path:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        for p in _normalize_posts(data):
            if p.get("id") == post_id:
                return p
    except Exception:
        logger.exception("get_post() fehlgeschlagen")
    return None


def _save_post_fields(post_id: str, **fields) -> dict:
    """Aktualisiert beliebige Felder eines einzelnen Posts über seine id, ohne
    die anderen Posts in derselben Datei anzufassen. Gemeinsame Basis für
    Text-Edits, Termin-Änderungen und Push-Status."""
    path = _latest_file("beitraege")
    if not path:
        return {"error": "Keine beitraege-Datei gefunden"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        posts = _normalize_posts(data)
        found = False
        for p in posts:
            if p.get("id") == post_id:
                p.update(fields)
                found = True
                break
        if not found:
            return {"error": f"Post {post_id} nicht gefunden"}
        data["posts"] = posts
        for key in _WEEKDAY_KEYS:
            data.pop(key, None)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        cache.invalidate("li_posts")
        return {"ok": True}
    except Exception as e:
        logger.exception("_save_post_fields() fehlgeschlagen")
        return {"error": str(e)}


def update_post_text(post_id: str, new_text: str) -> dict:
    return _save_post_fields(post_id, text=new_text)


def _to_iso_berlin(datum: str, uhrzeit: str) -> str:
    """Wandelt Datum (YYYY-MM-DD) + Uhrzeit (HH:MM) in Berliner Zeit in ISO-8601
    mit korrektem Offset um (+01:00/+02:00 je nach Sommer-/Winterzeit)."""
    dt = datetime.strptime(f"{datum} {uhrzeit}", "%Y-%m-%d %H:%M").replace(tzinfo=BERLIN)
    return dt.isoformat()


def push_post_to_buffer(post_id: str, scheduled_at: str | None = None) -> dict:
    """Pusht einen einzelnen gespeicherten Post nach Buffer (beide Kanäle) und
    merkt Termin + Status direkt am Post, damit Detailansicht/Chat wissen,
    dass er schon raus ist."""
    post = get_post(post_id)
    if not post:
        return {"error": f"Post {post_id} nicht gefunden"}
    if not post.get("text", "").strip():
        return {"error": "Post hat keinen Text"}
    due = scheduled_at or post.get("termin") or None
    result = buffer_push(post["text"], scheduled_at=due)
    if result.get("ok"):
        _save_post_fields(
            post_id,
            termin=due or post.get("termin", ""),
            pushed=True,
            buffer_post_ids=[p["post_id"] for p in result.get("pushed", [])],
        )
        cache.invalidate("buffer_status")
    return result


def _karusselle_path():
    return get_settings().autoposter_dir / "karusselle.json"


def _load_karusselle() -> list[dict]:
    path = _karusselle_path()
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def get_carousels() -> dict:
    return {"karusselle": _load_karusselle()}


def _save_carousel_record(hook: str, branche: str, result: dict, source_post_id: str | None = None) -> None:
    """Merkt ein erzeugtes Karussell dauerhaft (Thumbnail + PDF-Link), damit es
    im Dashboard sichtbar bleibt statt nur einmalig im Chat aufzutauchen -
    analog zum youtube_service-Metadaten-Sidecar-Muster, hier als eine
    gemeinsame Liste statt einer Datei pro Eintrag."""
    items = _load_karusselle()
    items.insert(0, {
        "id": uuid.uuid4().hex[:8],
        "source_post_id": source_post_id,
        "hook": hook,
        "branche": branche,
        "slide_titles": result.get("slide_titles", []),
        "thumb_url": result.get("thumb_url"),
        "pdf_url": result.get("pdf_url"),
        "due_at": result.get("due_at"),
        "anzahl_gepusht": result.get("anzahl_gepusht", 0),
        "created_at": datetime.now().isoformat(),
    })
    _karusselle_path().parent.mkdir(parents=True, exist_ok=True)
    _karusselle_path().write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def make_carousel(hook: str, branche: str = "Alle", saeule: str = "Wissen",
                   due_at: str | None = None, source_post_id: str | None = None) -> dict:
    """Erstellt ein eigenständiges Karussell (Slides -> Bilder -> PDF ->
    Cloudinary -> Buffer) aus einem Hook/Thema und merkt das Ergebnis dauerhaft."""
    result = carousel_service.generate_carousel(hook=hook, branche=branche or "Alle", saeule=saeule, due_at=due_at)
    if result.get("ok"):
        _save_carousel_record(hook, branche or "Alle", result, source_post_id=source_post_id)
    return result


def make_carousel_from_post(post_id: str, branche: str = "Alle", saeule: str = "Wissen",
                             due_at: str | None = None) -> dict:
    """Erstellt aus einem bestehenden Text-Post ein eigenständiges Karussell -
    läuft unabhängig vom Text-Post als eigener Buffer-Beitrag, der Text-Post
    bleibt unverändert."""
    post = get_post(post_id)
    if not post:
        return {"ok": False, "error": f"Post {post_id} nicht gefunden"}
    hook = (post.get("idee") or "").strip()
    if not hook and post.get("text"):
        hook = post["text"].strip().split("\n")[0].strip()
    if not hook:
        return {"ok": False, "error": "Kein Thema/Hook für das Karussell gefunden"}
    return make_carousel(hook, branche=branche, saeule=saeule, due_at=due_at or post.get("termin"), source_post_id=post_id)


def _format_ideas_for_chat() -> str:
    ideen = get_ideas().get("ideen", [])
    if not ideen:
        return "(keine Ideen vorhanden)"
    return "\n".join(f"- [{i['kategorie']}] {i['titel']} — {i['hook']}" for i in ideen)


def _format_posts_for_chat() -> str:
    posts = get_posts().get("posts", [])
    if not posts:
        return "(keine gespeicherten Posts)"
    return "\n".join(
        f"- id={p['id']} | {p['tag']} {p['termin'][:16].replace('T', ' ')} | "
        f"{'gepusht' if p['pushed'] else 'offen'} | {p['idee']}"
        for p in posts
    )


def list_ideas_text() -> str:
    return _format_ideas_for_chat()


def list_posts_text() -> str:
    return _format_posts_for_chat()


def schedule_post(post_id: str, datum: str, uhrzeit: str) -> dict:
    """MCP-/Chat-Tool-Variante von schedule_post - wandelt Datum+Uhrzeit um und
    pusht den Post. Gibt bei ungültigem Format einen Fehler zurück statt zu
    crashen, mirror von _execute_linkedin_chat_tool's altem schedule_post-Zweig."""
    try:
        scheduled_at = _to_iso_berlin(datum, uhrzeit)
    except Exception:
        return {"error": "Ungültiges Datum/Uhrzeit-Format, bitte YYYY-MM-DD und HH:MM verwenden."}
    return push_post_to_buffer(post_id, scheduled_at)


_LINKEDIN_CHAT_TOOLS = [
    {
        "name": "list_ideas",
        "description": "Zeigt die aktuell gespeicherten LinkedIn-Ideen (Titel, Hook, Kategorie, Branche, Format).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "generate_ideas",
        "description": "Generiert 10 neue LinkedIn-Ideen (4x Typ A, 3x Typ B, 3x Typ C) und speichert sie - ersetzt die alten Ideen.",
        "input_schema": {
            "type": "object",
            "properties": {"focus": {"type": "string", "description": "Optionaler thematischer Fokus"}},
        },
    },
    {
        "name": "list_posts",
        "description": "Zeigt die aktuell gespeicherten/geplanten Posts (id, Tag, Termin, ob schon gepusht, Thema).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "write_post",
        "description": "Schreibt einen vollständigen LinkedIn-Post-Text aus (aus einer Idee oder freiem Thema) und speichert ihn als Entwurf - pusht NICHT automatisch nach Buffer, das braucht einen expliziten schedule_post-Aufruf.",
        "input_schema": {
            "type": "object",
            "properties": {
                "spec": {"type": "string", "description": "Thema, Hook, Format, Zielgruppe, gewünschter Tag/Zeitraum - alles was für den Text gebraucht wird."},
            },
            "required": ["spec"],
        },
    },
    {
        "name": "revise_post",
        "description": "Überarbeitet den Text eines bestehenden, gespeicherten Posts (per id, siehe list_posts) gemäß Sebastians Wunsch.",
        "input_schema": {
            "type": "object",
            "properties": {
                "post_id": {"type": "string"},
                "neuer_text": {"type": "string", "description": "Der komplette überarbeitete Post-Text."},
            },
            "required": ["post_id", "neuer_text"],
        },
    },
    {
        "name": "schedule_post",
        "description": "Plant einen bestehenden, gespeicherten Post (per id) zu einem Datum/Uhrzeit in Buffer ein (beide Kanäle: Sebastian + Prozessia).",
        "input_schema": {
            "type": "object",
            "properties": {
                "post_id": {"type": "string"},
                "datum": {"type": "string", "description": "YYYY-MM-DD - relative Angaben wie 'morgen' anhand des heutigen Datums umrechnen."},
                "uhrzeit": {"type": "string", "description": "HH:MM, 24h, Berliner Zeit."},
            },
            "required": ["post_id", "datum", "uhrzeit"],
        },
    },
    {
        "name": "make_carousel",
        "description": "Erstellt ein Bild-Karussell (mehrere Slides als PDF) und plant es eigenständig in Buffer ein - läuft komplett automatisch (KI-Bilder, PDF, Upload, Buffer-Push), kann 1-2 Minuten dauern. Entweder post_id (Karussell aus einem bestehenden Post ableiten) oder hook (freies Thema) angeben.",
        "input_schema": {
            "type": "object",
            "properties": {
                "post_id": {"type": "string", "description": "Optional: bestehenden Post als Grundlage nehmen."},
                "hook": {"type": "string", "description": "Optional: freier Hook/Thema, falls kein post_id angegeben."},
                "branche": {"type": "string", "enum": ["Werkzeugbau", "Maschinenbau", "Lohnfertiger", "Elektrotechnik", "Allgemein"]},
                "datum": {"type": "string", "description": "YYYY-MM-DD, optional."},
                "uhrzeit": {"type": "string", "description": "HH:MM, optional, nur zusammen mit datum."},
            },
            "required": [],
        },
    },
    {
        "name": "set_direction",
        "description": "Setzt die Richtungsvorgabe, die künftige Ideen-/Post-Generierung beeinflusst.",
        "input_schema": {
            "type": "object",
            "properties": {"prompt": {"type": "string"}},
            "required": ["prompt"],
        },
    },
]

MAX_LINKEDIN_CHAT_ITERATIONS = 6
_LINKEDIN_STATE_CHANGING_TOOLS = {"generate_ideas", "write_post", "revise_post", "schedule_post", "make_carousel", "set_direction"}


def _execute_linkedin_chat_tool(name: str, inp: dict) -> tuple[str, bool]:
    """Dispatcher für die Tools des LinkedIn-Chats. Gibt (content, is_error) zurück."""
    try:
        if name == "list_ideas":
            return _format_ideas_for_chat(), False

        if name == "list_posts":
            return _format_posts_for_chat(), False

        if name == "generate_ideas":
            r = generate_ideas(inp.get("focus", "") or "")
            if not r.get("ok"):
                return f"Fehler: {r.get('error', '?')}", True
            return f"{r.get('anzahl', 0)} neue Ideen generiert.", False

        if name == "write_post":
            r = generate_posts(inp.get("spec", ""))
            if not r.get("ok"):
                return f"Fehler: {r.get('error', '?')}", True
            posts = r.get("posts", [])
            lines = [f"- id={p.get('id')}: {p.get('text', '')[:80]}…" for p in posts]
            return f"{len(posts)} Post(s) geschrieben und als Entwurf gespeichert:\n" + "\n".join(lines), False

        if name == "revise_post":
            post_id = inp.get("post_id", "")
            neuer_text = (inp.get("neuer_text") or "").strip()
            if not neuer_text:
                return "Kein Text übergeben.", True
            r = update_post_text(post_id, neuer_text)
            return ("Text gespeichert." if r.get("ok") else f"Fehler: {r.get('error', '?')}"), not r.get("ok")

        if name == "schedule_post":
            post_id = inp.get("post_id", "")
            try:
                scheduled_at = _to_iso_berlin(inp.get("datum", ""), inp.get("uhrzeit", ""))
            except Exception:
                return "Ungültiges Datum/Uhrzeit-Format, bitte YYYY-MM-DD und HH:MM verwenden.", True
            r = push_post_to_buffer(post_id, scheduled_at)
            return (f"Post {post_id} eingeplant für {scheduled_at}." if r.get("ok") else f"Buffer-Fehler: {r.get('error', '?')}"), not r.get("ok")

        if name == "make_carousel":
            due_at = None
            datum = (inp.get("datum") or "").strip()
            uhrzeit = (inp.get("uhrzeit") or "").strip()
            if datum and uhrzeit:
                try:
                    due_at = _to_iso_berlin(datum, uhrzeit)
                except Exception:
                    due_at = None
            post_id = inp.get("post_id")
            branche = inp.get("branche") or "Alle"
            if post_id:
                r = make_carousel_from_post(post_id, branche=branche, due_at=due_at)
            elif inp.get("hook"):
                r = make_carousel(inp["hook"], branche=branche, due_at=due_at)
            else:
                return "Weder post_id noch hook angegeben.", True
            if r.get("ok"):
                titles = " | ".join((r.get("slide_titles") or [])[:3])
                return f"Karussell fertig — {r.get('slides', 0)} Slides, {r.get('anzahl_gepusht', 0)}x eingeplant. {titles}", False
            return f"Karussell-Fehler: {r.get('error', '?')}", True

        if name == "set_direction":
            r = set_direction(inp.get("prompt", ""))
            return ("Richtung gesetzt." if r.get("ok") else f"Fehler: {r.get('error', '?')}"), not r.get("ok")

        return f"Unbekanntes Tool: {name}", True
    except Exception as e:
        return f"Tool-Fehler ({name}): {e}", True


def _linkedin_system_prompt() -> str:
    now = datetime.now(BERLIN)
    weekday_de = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"][now.weekday()]

    return f"""Du steuerst für Sebastian (Prozessia GbR) die komplette LinkedIn-Content-Pipeline im Chat:
Ideen generieren, Posts schreiben/überarbeiten/einplanen, Karusselle erstellen, Richtung setzen.
Heute ist {weekday_de}, {now.strftime('%Y-%m-%d')}, {now.strftime('%H:%M')} Uhr (Berliner Zeit).

Aktuelle Richtungsvorgabe: {_current_direction() or '(keine gesetzt)'}

Aktuelle Ideen:
{_format_ideas_for_chat()}

Aktuelle gespeicherte Posts:
{_format_posts_for_chat()}

Verfügbare Aktionen (bei Bedarf aufrufen, sonst direkt in Text antworten):
- list_ideas / list_posts (CLI: list_linkedin_ideas / list_linkedin_posts): aktuellen Stand nachladen, falls sich seit obiger Übersicht etwas geändert hat
- generate_ideas (CLI: generate_linkedin_ideas): neue Ideen generieren (ersetzt die alten)
- write_post (CLI: write_linkedin_post_draft): Post-Text aus einer Idee/einem Thema schreiben und als Entwurf speichern - pusht NICHT automatisch
- revise_post (CLI: revise_linkedin_post): Text eines bestehenden Posts (per id) überarbeiten
- schedule_post (CLI: schedule_linkedin_post): bestehenden Post (per id) zu einem Zeitpunkt in Buffer einplanen (rechne relative Angaben wie "morgen" anhand des heutigen Datums oben um)
- make_carousel (CLI: generate_carousel): Bild-Karussell erstellen (aus post_id oder freiem hook) und automatisch in Buffer einplanen
- set_direction (CLI: set_linkedin_direction): Richtungsvorgabe für künftige Generierung setzen

Regeln für Post-Texte (bei write_post/revise_post):
- Max. 15 Wörter pro Satz, Leerzeile nach jeder 2. Zeile
- Max. 3 Hashtags am Ende
- 0 Emojis außer max. 1 ganz am Ende
- Keine Wörter: innovativ, nachhaltig, ganzheitlich, Lösung, Transformation

Sei proaktiv: wenn Sebastian z.B. "schreib mir einen Post über X" sagt, ruf direkt den write_post-Tool auf statt nachzufragen.
Frag nur nach, wenn eine Aktion sonst mehrdeutig wäre (z.B. welcher Post gemeint ist).
Nach jedem Tool-Aufruf kurz bestätigen, was passiert ist."""


_LINKEDIN_STATE_CHANGING_MCP_TOOLS = {
    "mcp__prozessia-tools__generate_linkedin_ideas",
    "mcp__prozessia-tools__write_linkedin_post_draft",
    "mcp__prozessia-tools__revise_linkedin_post",
    "mcp__prozessia-tools__schedule_linkedin_post",
    "mcp__prozessia-tools__generate_carousel",
    "mcp__prozessia-tools__set_linkedin_direction",
}


def _chat_linkedin_cli(messages: list[dict]) -> dict:
    """CLI-Variante von chat_linkedin() (claude_engine="cli") - nutzt dieselben
    Aktionen, aber als MCP-Tools (siehe app.mcp_server) über einen Claude-Code-
    Subprocess statt des Custom-Tool-Loops unten. Abrechnung über
    CLAUDE_CODE_OAUTH_TOKEN statt ANTHROPIC_API_KEY. Wie beim Haupt-Chat
    (chat.py:_stream_chat_cli) wird nur die letzte User-Nachricht als Prompt
    geschickt, nicht die volle messages-History."""
    from app.services import claude_cli
    last_msg = messages[-1].get("content", "") if messages else ""
    if not last_msg:
        return {"error": "Keine Nachricht erhalten"}
    system = _linkedin_system_prompt()
    try:
        text_parts: list[str] = []
        state_changed = False
        for event in claude_cli.stream_chat(last_msg, system_prompt=system, model=Models.SONNET, timeout=180):
            etype = event.get("type")
            if etype == "assistant":
                for block in event.get("message", {}).get("content", []):
                    if block.get("type") == "text" and block.get("text"):
                        text_parts.append(block["text"])
                    elif block.get("type") == "tool_use" and block.get("name") in _LINKEDIN_STATE_CHANGING_MCP_TOOLS:
                        state_changed = True
            elif etype == "result" and event.get("is_error"):
                return {"error": event.get("result", "Unbekannter Fehler")}
        return {"ok": True, "antwort": "".join(text_parts).strip() or "Erledigt.", "state_changed": state_changed}
    except claude_cli.ClaudeCliError as e:
        return {"error": str(e)}


def chat_linkedin(messages: list[dict]) -> dict:
    """Agentischer Chat für die gesamte LinkedIn-Sektion: Ideen generieren,
    Posts schreiben/überarbeiten/einplanen, Karusselle erstellen, Richtung
    setzen - alles über Tool Use (tool_choice=auto, Mehrfach-Turns). Ersetzt
    das frühere chat_about_post(), das auf einen einzelnen Post beschränkt war.
    Bei claude_engine="cli" siehe stattdessen _chat_linkedin_cli()."""
    if get_settings().claude_engine == "cli":
        return _chat_linkedin_cli(messages)

    system = _linkedin_system_prompt()

    try:
        current_messages = list(messages)
        text_parts: list[str] = []
        state_changed = False

        for _ in range(MAX_LINKEDIN_CHAT_ITERATIONS):
            result = get_client().messages.create(
                model=Models.SONNET, max_tokens=3000,
                system=system,
                tools=_LINKEDIN_CHAT_TOOLS,
                tool_choice={"type": "auto"},
                messages=current_messages,
            )
            current_messages.append({
                "role": "assistant",
                # exclude_none: siehe chat.py - vermeidet den "parsed_output"-
                # Extra-Feld-400-Fehler beim Zurücksenden von Content-Blöcken.
                "content": [block.model_dump(exclude_none=True) for block in result.content],
            })
            for block in result.content:
                if block.type == "text" and block.text.strip():
                    text_parts.append(block.text.strip())

            if result.stop_reason != "tool_use":
                break

            tool_result_blocks = []
            for block in result.content:
                if block.type != "tool_use":
                    continue
                content, is_error = _execute_linkedin_chat_tool(block.name, block.input)
                if not is_error and block.name in _LINKEDIN_STATE_CHANGING_TOOLS:
                    state_changed = True
                tool_result_blocks.append({
                    "type": "tool_result", "tool_use_id": block.id,
                    "content": content, "is_error": is_error,
                })
            current_messages.append({"role": "user", "content": tool_result_blocks})
        else:
            text_parts.append("(Maximale Anzahl an Aktionen in diesem Turn erreicht.)")

        return {"ok": True, "antwort": "\n\n".join(text_parts).strip() or "Erledigt.", "state_changed": state_changed}
    except Exception as e:
        logger.exception("chat_linkedin() fehlgeschlagen")
        return {"error": str(e)}


def _current_direction() -> str:
    path = _direction_path()
    if not path.exists():
        return ""
    match = re.search(r"## Aktuelle Richtung\n\n(.+?)(?:\n---|\Z)", path.read_text(encoding="utf-8"), re.DOTALL)
    return match.group(1).strip() if match else ""


def get_direction() -> dict:
    return {"prompt": _current_direction()}


def set_direction(prompt: str) -> dict:
    if not prompt.strip():
        return {"error": "Kein Prompt"}
    path = _direction_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    path.write_text(
        f"""# Brain-Richtungsvorgabe für LinkedIn Autoposter
*Gesetzt am: {ts} von Sebastian via Brain UI*

## Aktuelle Richtung

{prompt.strip()}

---
*Diese Datei wird beim nächsten Autoposter-Run gelesen.*
""",
        encoding="utf-8",
    )
    return {"ok": True, "path": str(path)}


def _next_posting_slot(after: datetime | None = None) -> str:
    """Nächster erlaubter Slot: Dienstag–Donnerstag, 07:00 oder 12:00 Uhr (Berlin)."""
    now = after or datetime.now()
    candidate = (now + timedelta(hours=2)).replace(minute=0, second=0, microsecond=0)
    for _ in range(42):
        if candidate.weekday() in (1, 2, 3):
            for hour in (7, 12):
                slot = candidate.replace(hour=hour, minute=0)
                if slot > now + timedelta(hours=2):
                    return slot.strftime("%Y-%m-%dT%H:00:00+02:00")
        candidate = (candidate + timedelta(days=1)).replace(hour=0)
    return (now + timedelta(days=2)).strftime("%Y-%m-%dT07:00:00+02:00")


_GENERATE_IDEAS_TOOL = {
    "name": "save_linkedin_ideas",
    "description": "Speichert die generierten LinkedIn-Post-Ideen.",
    "input_schema": {
        "type": "object",
        "properties": {
            "ideen": {
                "type": "array",
                "description": "Genau 10 Ideen: 4x Typ A, 3x Typ B, 3x Typ C.",
                "minItems": 10,
                "maxItems": 10,
                "items": {
                    "type": "object",
                    "properties": {
                        "typ": {"type": "string", "enum": ["A", "B", "C"]},
                        "kategorie": {"type": "string", "enum": ["Einkauf", "Industrie", "Compliance", "KI-Tipp", "Kundenstory"]},
                        "titel": {"type": "string", "description": "Max 60 Zeichen."},
                        "hook": {"type": "string", "description": "Erste Zeile, max 80 Zeichen, stoppt den Scroll."},
                        "kern_botschaft": {"type": "string", "description": "Was der Leser mitnimmt."},
                        "branche": {"type": "string", "enum": ["Werkzeugbau", "Maschinenbau", "Lohnfertiger", "Elektrotechnik", "Allgemein"]},
                        "zielgruppe_spezifisch": {"type": "string", "description": "z.B. 'Einkaufsleiter, 45 MA, Werkzeugbau'."},
                        "format_empfehlung": {"type": "string", "enum": ["Text", "Karussell", "Liste"]},
                        "cta_vorschlag": {"type": "string", "description": "Eine spezifische Frage für Kommentare - kein Engagement-Bait."},
                    },
                    "required": ["typ", "kategorie", "titel", "hook", "kern_botschaft", "branche", "zielgruppe_spezifisch", "format_empfehlung", "cta_vorschlag"],
                },
            },
        },
        "required": ["ideen"],
    },
}


def generate_ideas(focus: str = "") -> dict:
    current_direction = _current_direction()
    prompt = f"""Du bist LinkedIn-Content-Stratege für Prozessia.

Zielgruppe: Einkaufsleiter und Geschäftsführer in produzierenden Betrieben, 20–80 MA, DACH.
Prozessia automatisiert Beschaffungsprozesse und Stücklistenprüfung — keine Beratung, konkrete Agenten die Arbeit abnehmen.
Themen insgesamt: KI-Beschaffung, Automatisierung, EU AI Act & KI-Compliance, Produktivität im Mittelstand, allgemeine KI-Tipps für Entscheider — nicht nur das Kernprodukt, sondern die ganze Bandbreite dessen was die Zielgruppe zu KI im Betrieb wissen muss.

{f"Richtungsvorgabe: {current_direction}" if current_direction else ""}
{f"Zusätzlicher Fokus: {focus}" if focus else ""}

Jede Idee bekommt EINEN dieser drei Post-Typen:
- Typ A – Schmerz-Post: Ich-Perspektive, konkreter Alltags-Schmerz der Zielgruppe, keine Lösung im ersten Satz
- Typ B – Carousel/Dokument-Post: Framework, Checkliste oder Schritt-für-Schritt (3–7 Punkte)
- Typ C – Story-Post: anonymes Vorher/Nachher eines Kunden mit konkreten Zahlen (Zeit, Geld, Aufwand)

Jede Idee bekommt außerdem GENAU EINE Kategorie (Themen-Säule), für Mischung sorgen — NICHT alle 10 aus derselben Kategorie:
- Einkauf: konkrete Beschaffungs-/Stücklisten-Schmerzpunkte (Prozessias Kernprodukt)
- Industrie: allgemeinere Produktions-/Mittelstandsthemen, nicht zwingend Beschaffung
- Compliance: EU AI Act, Datenschutz, Haftung bei KI-Einsatz — sachlich, keine Panikmache
- KI-Tipp: praktische, sofort umsetzbare KI-Tipps für Entscheider (Prompts, Tools, Workflows)
- Kundenstory: anonymisiertes Vorher/Nachher

Ziel-Verteilung über die 10 Ideen: mindestens 2× Einkauf, mindestens 2× Compliance, mindestens 2× KI-Tipp, Rest frei gemischt aus Industrie/Kundenstory/Einkauf.

Generiere GENAU 10 Ideen: 4× Typ A, 3× Typ B, 3× Typ C.

VERBOTEN für jeden Hook und Post:
- Statistik oder Prozentzahl als erster Satz
- Wörter: innovativ, nachhaltig, ganzheitlich, Lösungen, Transformation
- Engagement-Bait ("Teile diesen Post", "Tag jemanden")

PFLICHT für jeden Hook:
- Stoppt den Scroll innerhalb von 3 Sekunden
- Ich-Perspektive ODER direkte Du-Ansprache
- Kein vollständiger Satz — eher Fragment oder Frage"""

    try:
        if get_settings().claude_engine == "cli":
            from app.services import claude_cli
            json_prompt = prompt + """

Antworte NUR mit einem JSON-Objekt in genau diesem Format, kein Markdown, keine Erklärung davor/danach:
{"ideen": [{"typ": "A|B|C", "kategorie": "Einkauf|Industrie|Compliance|KI-Tipp|Kundenstory", "titel": "...", "hook": "...", "kern_botschaft": "...", "branche": "Werkzeugbau|Maschinenbau|Lohnfertiger|Elektrotechnik|Allgemein", "zielgruppe_spezifisch": "...", "format_empfehlung": "Text|Karussell|Liste", "cta_vorschlag": "..."}] (genau 10 Einträge)}"""
            raw = claude_cli.run_json(json_prompt, model=Models.SONNET, max_budget_usd=1.00).strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            data = json.loads(raw)
        else:
            result = get_client().messages.create(
                model=Models.SONNET, max_tokens=8000,
                tools=[_GENERATE_IDEAS_TOOL],
                tool_choice={"type": "tool", "name": "save_linkedin_ideas"},
                messages=[{"role": "user", "content": prompt}],
            )
            data = None
            for block in result.content:
                if block.type == "tool_use":
                    data = block.input
                    break
            if data is None:
                return {"error": "Keine Antwort erhalten"}
        data["generiert_am"] = datetime.now().isoformat()
        data["anzahl"] = len(data.get("ideen", []))

        out_path = get_settings().autoposter_dir / f"ideen-{datetime.now().strftime('%Y-%m-%d')}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        cache.invalidate("li_ideas")

        return {"ok": True, "anzahl": data["anzahl"], "ideen": [
            {"titel": i.get("titel", ""), "hook": i.get("hook", ""),
             "kategorie": i.get("kategorie", ""), "branche": i.get("branche", ""),
             "format": i.get("format_empfehlung", ""), "cta": i.get("cta_vorschlag", "")}
            for i in data.get("ideen", [])
        ]}
    except Exception as e:
        logger.exception("generate_ideas() fehlgeschlagen")
        return {"error": str(e)}


_GENERATE_POSTS_TOOL = {
    "name": "save_linkedin_posts",
    "description": "Speichert die ausgeschriebenen LinkedIn-Post-Texte.",
    "input_schema": {
        "type": "object",
        "properties": {
            "posts": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "tag": {"type": "string", "description": "z.B. 'Dienstag'"},
                        "datum": {"type": "string", "description": "YYYY-MM-DD"},
                        "typ": {"type": "string", "enum": ["A", "B", "C"]},
                        "thema": {"type": "string"},
                        "text": {"type": "string", "description": "Vollständiger Post-Text, fertig zum Posten."},
                        "hashtags": {"type": "array", "items": {"type": "string"}},
                        "erster_kommentar": {"type": "string", "description": "Link/weiterführende Info - wird als Kommentar gepostet, nicht im Post."},
                    },
                    "required": ["tag", "datum", "typ", "thema", "text"],
                },
            },
        },
        "required": ["posts"],
    },
}


def generate_posts(spec: str) -> dict:
    current_direction = _current_direction()
    prompt = f"""Du bist LinkedIn-Texter für Prozessia.

Zielgruppe: Einkaufsleiter und Geschäftsführer in produzierenden Betrieben, 20–80 MA, DACH.
Prozessia automatisiert Beschaffungsprozesse und Stücklistenprüfung — konkrete Agenten, keine Beratung.
Themen insgesamt breiter als nur das Produkt: KI-Beschaffung, EU AI Act & KI-Compliance, allgemeine KI-Tipps für Entscheider, Produktivität im Mittelstand — Mischung, nicht nur Beschaffungsagent-Werbung.

{f"Richtungsvorgabe: {current_direction}" if current_direction else ""}

POST-TYPEN (steht in der Spezifikation):
- Typ A – Schmerz-Post: Ich-Perspektive, Alltags-Schmerz der Zielgruppe, keine KI-Lösung im ersten Satz
- Typ B – Karussell/Dokument: Framework, Checkliste oder Schritt-für-Schritt mit 3–7 nummerierten Punkten
- Typ C – Story-Post: anonymes Vorher/Nachher eines Kunden, konkrete Zahlen (Stunden, €, Prozent)

FORMAT-REGELN (ausnahmslos):
- Max. 15 Wörter pro Satz
- Leerzeile nach jeder 2. Zeile (nicht nach jeder Zeile)
- Max. 3 Hashtags, immer am Ende
- VERBOTENE Hashtags: #KI, #AI, #Innovation, #Digitalisierung, #Mittelstand, #Automation (zu groß, zu allgemein)
- Erlaubte Hashtags: #Einkauf, #Beschaffung, #Produktion, #Werkzeugbau, #Lohnfertigung, #ERP, #EUAIAct, #KICompliance
- 0 Emojis, außer maximal 1 in der letzten Zeile (optional)
- Links NIEMALS im Post-Text — nur als separater Kommentar

VERBOTENE WÖRTER: innovativ, nachhaltig, ganzheitlich, Lösung, Transformation, revolutionieren, disruptiv, zukunftsfähig
VERBOTENE NAMEN: konkrete Firmennamen von Kunden (anonymisieren)
VERBOTEN: "In der heutigen Zeit", "Die KI wird", Statistiken als erster Satz, Engagement-Bait

ERSTE ZEILE (Hook):
- Stoppt den Scroll in 3 Sekunden
- Fragment oder kurze Frage, kein vollständiger Satz
- Ich-Perspektive oder Du-Ansprache

Spezifikation für die Posts:
{spec}

Schreibe jeden Post vollständig aus."""

    try:
        if get_settings().claude_engine == "cli":
            from app.services import claude_cli
            json_prompt = prompt + """

Antworte NUR mit einem JSON-Objekt in genau diesem Format, kein Markdown, keine Erklärung davor/danach:
{"posts": [{"tag": "...", "datum": "YYYY-MM-DD", "typ": "A|B|C", "thema": "...", "text": "...", "hashtags": ["..."], "erster_kommentar": "..."}]}"""
            raw = claude_cli.run_json(json_prompt, model=Models.SONNET, max_budget_usd=1.00).strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            posts = json.loads(raw).get("posts", [])
        else:
            result = get_client().messages.create(
                model=Models.SONNET, max_tokens=8000,
                tools=[_GENERATE_POSTS_TOOL],
                tool_choice={"type": "tool", "name": "save_linkedin_posts"},
                messages=[{"role": "user", "content": prompt}],
            )
            posts = []
            for block in result.content:
                if block.type == "tool_use":
                    posts = block.input.get("posts", [])
                    break

        if not posts:
            return {"error": "Keine Posts erhalten"}

        # Stabile id pro Post statt Wochentag-Key als Speicherschlüssel - sonst
        # überschreiben sich zwei Posts am selben Wochentag gegenseitig.
        today = datetime.now().strftime('%Y-%m-%d')
        stored_posts = []
        last_slot = None
        for p in posts:
            slot = _next_posting_slot(after=last_slot)
            last_slot = datetime.fromisoformat(slot.replace("+02:00", "")) + timedelta(hours=1)
            post_id = uuid.uuid4().hex[:8]
            p["id"] = post_id
            stored_posts.append({
                "id": post_id,
                "tag": p.get("tag", ""),
                "datum": p.get("datum", today),
                "termin": slot,
                "idee": p.get("thema", ""),
                "text": p.get("text", ""),
                "typ": p.get("typ", ""),
            })
        out_data = {"generiert_am": datetime.now().isoformat(), "kanaele": [], "planungen": [], "posts": stored_posts}
        out_path = get_settings().autoposter_dir / f"beitraege-{today}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out_data, ensure_ascii=False, indent=2), encoding="utf-8")
        cache.invalidate("li_posts")
        return {"ok": True, "posts": posts}
    except Exception as e:
        logger.exception("generate_posts() fehlgeschlagen")
        return {"error": str(e)}


def push_latest_to_buffer() -> dict:
    """Pusht alle Posts aus dem neuesten beitraege-*.json nach Buffer (beide Kanäle).
    Migriert aus brain_server.py:api_buffer_push() — dort per Subprocess auf
    buffer_manager.py, hier direkt über buffer_push()."""
    path = _latest_file("beitraege")
    if not path:
        return {"error": "Keine generierten Posts gefunden — erst generate_posts aufrufen."}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"error": f"beitraege-Datei nicht lesbar: {e}"}

    pushed = []
    errors = []
    for p in _normalize_posts(data):
        if not p.get("text"):
            continue
        label = p.get("id") or p.get("tag", "")
        result = buffer_push(p["text"], scheduled_at=p.get("termin"))
        if result.get("ok"):
            pushed.append(label)
        else:
            errors.append({"tag": label, "error": result.get("error")})

    cache.invalidate("buffer_status")
    if not pushed:
        return {"error": errors or "Keine Posts zum Pushen gefunden"}
    return {"ok": True, "gepusht": pushed, "errors": errors or None}


def buffer_push(text: str, scheduled_at: str | None = None) -> dict:
    """Pusht einen Post auf beide Buffer-Kanäle (Sebastian + Prozessia) via GraphQL."""
    settings = get_settings()
    token = settings.buffer_api_token
    if not token:
        return {"error": "BUFFER_API_TOKEN nicht gesetzt"}

    channels = [settings.buffer_channel_sebastian, settings.buffer_channel_prozessia]
    pushed = []
    errors = []

    for channel_id in channels:
        # due_at: ISO-8601 mit Z oder leer → Buffer-Default (nächster freier Slot)
        due = scheduled_at or ""
        mutation = """
mutation CreatePost($input: CreatePostInput!) {
  createPost(input: $input) {
    post { id status scheduledAt }
    userErrors { message }
  }
}"""
        variables = {
            "input": {
                "organizationId": "6a15c3685a233c9c16251245",
                "channelId": channel_id,
                "content": {"text": text},
                **({"dueAt": due} if due else {}),
            }
        }
        payload = json.dumps({"query": mutation, "variables": variables}).encode()
        req = urllib.request.Request(
            BUFFER_GRAPHQL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            errs = data.get("data", {}).get("createPost", {}).get("userErrors", [])
            if errs:
                errors.append({"channel": channel_id, "errors": errs})
            else:
                post_id = data.get("data", {}).get("createPost", {}).get("post", {}).get("id", "")
                pushed.append({"channel": channel_id, "post_id": post_id})
        except Exception as exc:
            errors.append({"channel": channel_id, "error": str(exc)})

    if errors and not pushed:
        return {"error": errors}
    return {"ok": True, "pushed": pushed, "errors": errors or None}
