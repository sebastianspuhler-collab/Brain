"""LinkedIn-Autoposter-Bridge. Migriert aus brain_server.py (api_linkedin_*).
Liest/schreibt JSON-Output des externen Autoposter-Skripts im Vault."""
import json
import logging
import re
import urllib.request
import uuid
from datetime import datetime, timedelta

from app.config import get_settings
from app.services import cache
from app.services.anthropic_client import get_client, get_response_text

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


def update_post_text(post_id: str, new_text: str) -> dict:
    """Überschreibt den Text eines einzelnen Posts über seine id, ohne die
    anderen Posts in derselben Datei anzufassen."""
    path = _latest_file("beitraege")
    if not path:
        return {"error": "Keine beitraege-Datei gefunden"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        posts = _normalize_posts(data)
        found = False
        for p in posts:
            if p.get("id") == post_id:
                p["text"] = new_text
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
        logger.exception("update_post_text() fehlgeschlagen")
        return {"error": str(e)}


_REVISE_POST_TOOL = {
    "name": "revise_post",
    "description": "Gibt den überarbeiteten LinkedIn-Post-Text zurück, plus eine kurze Antwort an Sebastian was geändert wurde.",
    "input_schema": {
        "type": "object",
        "properties": {
            "antwort": {"type": "string", "description": "Kurze Antwort an Sebastian (1-2 Sätze), was am Post geändert wurde oder warum nicht."},
            "neuer_text": {"type": "string", "description": "Der komplette überarbeitete Post-Text, fertig zum Posten - unverändert wenn Sebastian nur eine Frage gestellt hat statt eine Änderung zu verlangen."},
        },
        "required": ["antwort", "neuer_text"],
    },
}


def chat_about_post(post_id: str, messages: list[dict]) -> dict:
    """Ein Chat-Turn über einen bestehenden Post: Claude sieht den aktuellen
    Text + die Konversation, antwortet UND liefert den überarbeiteten Text in
    einem Aufruf (Tool Use statt Freitext-Parsing, für zuverlässige Antworten).
    Speichert das Ergebnis direkt unter derselben post_id."""
    post = get_post(post_id)
    if not post:
        return {"error": f"Post {post_id} nicht gefunden"}

    system = f"""Du hilfst Sebastian (Prozessia GbR), einen bereits generierten LinkedIn-Post zu verfeinern.

Aktueller Post-Text:
---
{post.get('text', '')}
---

Regeln für den überarbeiteten Text (falls Sebastian eine Änderung will):
- Max. 15 Wörter pro Satz, Leerzeile nach jeder 2. Zeile
- Max. 3 Hashtags am Ende
- 0 Emojis außer max. 1 ganz am Ende
- Keine Wörter: innovativ, nachhaltig, ganzheitlich, Lösung, Transformation

Wenn Sebastian nur eine Frage stellt (keine Änderung verlangt), lass neuer_text unverändert (identisch zum aktuellen Text)."""

    try:
        result = get_client().messages.create(
            model="claude-sonnet-5", max_tokens=2000,
            system=system,
            tools=[_REVISE_POST_TOOL],
            tool_choice={"type": "tool", "name": "revise_post"},
            messages=messages,
        )
        data = None
        for block in result.content:
            if block.type == "tool_use":
                data = block.input
                break
        if data is None:
            return {"error": "Keine Antwort erhalten"}

        neuer_text = data.get("neuer_text", "").strip()
        changed = bool(neuer_text) and neuer_text != post.get("text", "")
        if changed:
            update_post_text(post_id, neuer_text)

        return {"ok": True, "antwort": data.get("antwort", ""), "text": neuer_text or post.get("text", ""), "changed": changed}
    except Exception as e:
        logger.exception("chat_about_post() fehlgeschlagen")
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
- Kein vollständiger Satz — eher Fragment oder Frage

Antworte NUR mit validem JSON, kein Markdown:
{{"generiert_am": "ISO-DATUM", "anzahl": 10, "ideen": [
  {{
    "typ": "A",
    "kategorie": "Einkauf|Industrie|Compliance|KI-Tipp|Kundenstory",
    "titel": "max 60 Zeichen",
    "hook": "erste Zeile, max 80 Zeichen, stoppt den Scroll",
    "kern_botschaft": "was der Leser mitnimmt",
    "branche": "Werkzeugbau|Maschinenbau|Lohnfertiger|Elektrotechnik|Allgemein",
    "zielgruppe_spezifisch": "Einkaufsleiter, 45 MA, Werkzeugbau",
    "format_empfehlung": "Text|Karussell|Liste",
    "cta_vorschlag": "eine spezifische Frage für Kommentare — kein Engagement-Bait"
  }}
]}}"""

    try:
        result = get_client().messages.create(
            model="claude-sonnet-5", max_tokens=8000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = get_response_text(result).strip()
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {"error": "Kein JSON in Antwort"}
        data = json.loads(match.group())
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

Schreibe jeden Post vollständig aus. Antworte NUR mit validem JSON:
{{
  "generiert_am": "ISO-DATUM",
  "posts": [
    {{
      "tag": "Dienstag",
      "datum": "YYYY-MM-DD",
      "typ": "A",
      "thema": "Themenname",
      "text": "Vollständiger Post-Text fertig zum Kopieren",
      "hashtags": ["#Einkauf", "#Beschaffung"],
      "erster_kommentar": "Link oder weiterführende Info — wird als Kommentar gepostet, nicht im Post"
    }}
  ]
}}"""

    try:
        result = get_client().messages.create(
            model="claude-sonnet-5", max_tokens=8000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = get_response_text(result).strip()
        raw_clean = raw.replace("```json", "").replace("```", "").strip()

        posts = []
        try:
            posts = json.loads(raw_clean).get("posts", [])
        except Exception:
            match = re.search(r"\{.*\}", raw_clean, re.DOTALL)
            if match:
                try:
                    posts = json.loads(match.group()).get("posts", [])
                except Exception:
                    pass

        if not posts:
            blocks = re.split(r"\n#+\s+", raw)
            for block in blocks:
                day_match = re.search(r"(Montag|Dienstag|Mittwoch|Donnerstag|Freitag)", block, re.IGNORECASE)
                date_match = re.search(r"(\d{4}-\d{2}-\d{2})", block)
                if day_match and date_match:
                    posts.append({
                        "tag": day_match.group(1),
                        "datum": date_match.group(1),
                        "thema": block.split("\n")[0].strip()[:80],
                        "text": block.strip()[:1500],
                    })

        if not posts:
            return {"error": "Keine Posts extrahiert", "raw": raw[:500]}

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
