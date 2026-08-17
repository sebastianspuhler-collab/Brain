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
    """Aktualisiert den Post-Text lokal - UND in Buffer, falls der Post schon
    gepusht wurde (siehe buffer_edit_post()). Ohne das würde eine Textänderung
    nach dem Push nur lokal ankommen, während der bereits geplante Buffer-Post
    unbemerkt beim alten Text bliebe (live beobachtet, 2026-07-25)."""
    post = get_post(post_id)
    result = _save_post_fields(post_id, text=new_text)
    if not result.get("ok"):
        return result
    buffer_ids = [b for b in (post or {}).get("buffer_post_ids", []) if b]
    if buffer_ids:
        buffer_result = buffer_edit_post(buffer_ids, new_text, due_at=(post or {}).get("termin"))
        result["buffer"] = buffer_result
    return result


def _to_iso_berlin(datum: str, uhrzeit: str) -> str:
    """Wandelt Datum (YYYY-MM-DD) + Uhrzeit (HH:MM) in Berliner Zeit in ISO-8601
    mit korrektem Offset um (+01:00/+02:00 je nach Sommer-/Winterzeit)."""
    dt = datetime.strptime(f"{datum} {uhrzeit}", "%Y-%m-%d %H:%M").replace(tzinfo=BERLIN)
    return dt.isoformat()


def push_post_to_buffer(post_id: str, scheduled_at: str | None = None, draft: bool = False) -> dict:
    """Pusht einen einzelnen gespeicherten Post nach Buffer (beide Kanäle) und
    merkt Termin + Status direkt am Post, damit Detailansicht/Chat wissen,
    dass er schon raus ist.

    Ist der Post schon in Buffer (buffer_post_ids vorhanden, z.B. weil
    write_post ihn per Draft-First schon als Entwurf gepusht hat), wird der
    BESTEHENDE Buffer-Post umgeschaltet (_promote_buffer_posts) statt einen
    zweiten anzulegen. Vorher legte z.B. schedule_post nach einem vorherigen
    Draft-Push immer einen komplett neuen, doppelten Buffer-Post an - der
    alte Entwurf blieb dabei unbemerkt und verwaist in Buffer liegen (live
    beobachtet 2026-08-13, Kern des in context.md offen notierten Problems)."""
    post = get_post(post_id)
    if not post:
        return {"error": f"Post {post_id} nicht gefunden"}
    if not post.get("text", "").strip():
        return {"error": "Post hat keinen Text"}
    due = scheduled_at or post.get("termin") or None
    existing_ids = [b for b in (post.get("buffer_post_ids") or []) if b]
    if existing_ids:
        result = _promote_buffer_posts(existing_ids, due, draft)
        if result.get("ok"):
            _save_post_fields(post_id, termin=due or post.get("termin", ""), pushed=True)
            cache.invalidate("buffer_status")
        return result
    result = buffer_push(post["text"], scheduled_at=due, draft=draft)
    if result.get("ok"):
        _save_post_fields(
            post_id,
            termin=due or post.get("termin", ""),
            pushed=True,
            buffer_post_ids=[p["post_id"] for p in result.get("pushed", [])],
        )
        cache.invalidate("buffer_status")
    return result


def _promote_buffer_posts(buffer_post_ids: list[str], due_at: str | None, draft: bool) -> dict:
    """Ändert Termin/Draft-Status bereits existierender Buffer-Posts per
    editPost, OHNE Text oder Assets (z.B. das Karussell-PDF) anzufassen -
    reines Umschalten Entwurf<->geplant. saveToDraft ist auf EditPostInput
    live per Introspection bestätigt (2026-08-13, s. buffer_edit_post für
    dieselbe Query-Form)."""
    settings = get_settings()
    token = settings.buffer_api_token
    if not token:
        return {"error": "BUFFER_API_TOKEN nicht gesetzt"}
    mutation = """
mutation EditPost($input: EditPostInput!) {
  editPost(input: $input) {
    ... on PostActionSuccess {
      post { id status dueAt }
    }
    ... on InvalidInputError { message }
    ... on UnauthorizedError { message }
    ... on NotFoundError { message }
    ... on UnexpectedError { message }
    ... on RestProxyError { message }
    ... on LimitReachedError { message }
  }
}"""
    updated = []
    errors = []
    for post_id in buffer_post_ids:
        if not post_id:
            continue
        variables = {
            "input": {
                "id": post_id,
                "schedulingType": "automatic",
                "saveToDraft": draft,
                **({"mode": "customScheduled", "dueAt": due_at} if due_at and not draft else {}),
            }
        }
        payload = json.dumps({"query": mutation, "variables": variables}).encode()
        req = urllib.request.Request(
            BUFFER_GRAPHQL, data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            if data.get("errors"):
                errors.append({"post_id": post_id, "errors": data["errors"]})
                continue
            result = data.get("data", {}).get("editPost") or {}
            post = result.get("post")
            if post and post.get("id"):
                updated.append(post_id)
            else:
                errors.append({"post_id": post_id, "errors": [{"message": result.get("message", "Unbekannte Antwort ohne post/message")}]})
        except Exception as exc:
            errors.append({"post_id": post_id, "error": str(exc)})

    if errors and not updated:
        return {"error": errors}
    return {"ok": True, "updated": updated, "errors": errors or None, "partial": bool(errors)}


def schedule_buffer_ids(buffer_post_ids: list[str], datum: str, uhrzeit: str) -> dict:
    """Plant Buffer-Posts OHNE lokale id ein (z.B. Karusselle oder direkt in
    Buffer angelegte Drafts) - Pendant zu schedule_post für Posts, die list_posts
    nur mit buffer_ids statt einer lokalen id zeigt."""
    try:
        scheduled_at = _to_iso_berlin(datum, uhrzeit)
    except Exception:
        return {"error": "Ungültiges Datum/Uhrzeit-Format, bitte YYYY-MM-DD und HH:MM verwenden."}
    result = _promote_buffer_posts(buffer_post_ids, scheduled_at, draft=False)
    if result.get("ok"):
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


def _format_carousels_for_chat() -> str:
    karusselle = get_carousels().get("karusselle", [])
    if not karusselle:
        return "(noch keine Karusselle erstellt)"
    lines = []
    for c in karusselle:
        status = f"{c['anzahl_gepusht']}x gepusht" if c.get("anzahl_gepusht") else "nicht gepusht"
        lines.append(f"- id={c['id']} | {c.get('hook', '')} | {c.get('branche', '')} | {len(c.get('slide_titles') or [])} Slides | {status}")
    return "\n".join(lines)


def _save_carousel_record(hook: str, branche: str, result: dict, source_post_id: str | None = None) -> None:
    """Merkt ein erzeugtes Karussell dauerhaft (Thumbnail + PDF-Link), damit es
    im Dashboard sichtbar bleibt statt nur einmalig im Chat aufzutauchen -
    analog zum youtube_service-Metadaten-Sidecar-Muster, hier als eine
    gemeinsame Liste statt einer Datei pro Eintrag."""
    items = _load_karusselle()
    # buffer_post_ids (2026-08-13): vorher gar nicht gespeichert - ohne die IDs
    # ließ sich ein erzeugtes Karussell später nie wieder gezielt in Buffer
    # wiederfinden (z.B. um es von Entwurf auf geplant zu befördern oder
    # sicher vor delete_post+write_post zu schützen), nur raten über
    # Text-Ähnlichkeit war möglich.
    buffer_post_ids = [b["postId"] for b in (result.get("buffer") or []) if b.get("ok") and b.get("postId")]
    items.insert(0, {
        "id": uuid.uuid4().hex[:8],
        "source_post_id": source_post_id,
        "hook": hook,
        "branche": branche,
        "slide_titles": result.get("slide_titles", []),
        "thumb_url": result.get("thumb_url"),
        "pdf_url": result.get("pdf_url"),
        "due_at": result.get("due_at"),
        "draft": bool(result.get("draft")),
        "buffer_post_ids": buffer_post_ids,
        "anzahl_gepusht": result.get("anzahl_gepusht", 0),
        "created_at": datetime.now().isoformat(),
    })
    _karusselle_path().parent.mkdir(parents=True, exist_ok=True)
    _karusselle_path().write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def make_carousel(hook: str, branche: str = "Alle", saeule: str = "Einkauf",
                   due_at: str | None = None, variante: str = carousel_service.DEFAULT_VARIANTE,
                   draft: bool = False, source_post_id: str | None = None) -> dict:
    """Erstellt ein eigenständiges Karussell (Slides -> Bild -> PDF ->
    Cloudinary -> Buffer) aus einem Hook/Thema und merkt das Ergebnis dauerhaft.

    variante steuert die Farblogik der Serie ("schwarz" oder "weiss", siehe
    Strategie §6) - laut Strategie pro Post-Serie konsistent zu wählen, nicht
    pro Einzelpost zu mischen. draft=True landet als echter Buffer-Entwurf
    (nie automatisch veröffentlicht) - für Testläufe/Review vor dem ersten
    echten Einsatz eines neuen Themas/einer neuen Variante."""
    result = carousel_service.generate_carousel(
        hook=hook, branche=branche or "Alle", saeule=saeule, due_at=due_at, variante=variante, draft=draft
    )
    if result.get("ok"):
        _save_carousel_record(hook, branche or "Alle", result, source_post_id=source_post_id)
    return result


def make_carousel_from_post(post_id: str, branche: str = "Alle", saeule: str = "Einkauf",
                             due_at: str | None = None,
                             variante: str = carousel_service.DEFAULT_VARIANTE,
                             draft: bool = False) -> dict:
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
    return make_carousel(hook, branche=branche, saeule=saeule, due_at=due_at or post.get("termin"),
                         variante=variante, draft=draft, source_post_id=post_id)


def _format_ideas_for_chat() -> str:
    ideen = get_ideas().get("ideen", [])
    if not ideen:
        return "(keine Ideen vorhanden)"
    return "\n".join(f"- [{i['kategorie']}] {i['titel']} — {i['hook']}" for i in ideen)


_BUFFER_STATUS_LABEL = {
    "draft": "Entwurf",
    "scheduled": "geplant",
    "sent": "gesendet",
    # Fallback-Status für lokale Posts ohne Live-Treffer in Buffer - bewusst NICHT
    # "gesendet"/"offen" (kollidierte mit dem echten Buffer-Status "sent" und
    # täuschte einen Buffer-Zustand vor, den es so nie gab). Seit dem Umbau auf
    # Draft-First (write_post/make_carousel pushen sofort als Buffer-Entwurf)
    # sollte "lokal_ungeplant" kaum noch auftreten - "lokal_verwaist" ist ein
    # echtes Drift-Signal (als gepusht markiert, aber Buffer bestätigt es nicht).
    "lokal_ungeplant": "nur lokal, noch nicht in Buffer",
    "lokal_verwaist": "als gepusht markiert, aber kein Live-Treffer in Buffer (bitte prüfen)",
}


def _merge_local_and_buffer_posts() -> list[dict]:
    """Verschmilzt lokal generierte Posts (beitraege-*.json) mit dem
    tatsächlichen Live-Stand in Buffer. Ohne das sieht list_posts nur, was
    diese Pipeline selbst geschrieben hat - Drafts, die Sebastian direkt in
    Buffer anlegt (z.B. über die Buffer-Web-App), blieben sonst komplett
    unsichtbar, weil dafür schlicht kein lokaler Post-Eintrag existiert
    (live beobachtet: 4 Buffer-Drafts, 0 lokale Treffer, 12.08.2026).

    Lokale Posts, die schon gepusht wurden, werden per buffer_post_ids mit
    ihrem Live-Eintrag abgeglichen (echter Buffer-Status statt nur des
    lokalen pushed-Flags). Alles in Buffer, das keinem lokalen Post
    zugeordnet werden kann, wird zusätzlich angehängt und als "nur Buffer"
    markiert - über die zwei Kanäle (Sebastian + Prozessia) hinweg per
    Text+Termin gruppiert, damit nicht derselbe Draft doppelt auftaucht."""
    path = _latest_file("beitraege")
    local_posts = []
    if path:
        try:
            local_posts = _normalize_posts(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            local_posts = []

    buffer_result = get_buffer_status()
    buffer_posts = buffer_result.get("posts", []) if buffer_result.get("ok") else []
    buffer_by_id = {b["id"]: b for b in buffer_posts}

    # Karussell-Design (Thumbnail/PDF) per Buffer-Post-ID zuordnen - präzise
    # statt über Text-/Termin-Heuristik, seit _save_carousel_record() die
    # tatsächlichen Buffer-IDs mitspeichert (2026-08-13).
    carousel_by_buffer_id = {}
    for c in _load_karusselle():
        for bid in c.get("buffer_post_ids") or []:
            carousel_by_buffer_id[bid] = c

    def _carousel_info(buffer_ids: list[str]) -> dict:
        for bid in buffer_ids:
            c = carousel_by_buffer_id.get(bid)
            if c:
                return {"carousel_id": c["id"], "thumb_url": c.get("thumb_url"), "pdf_url": c.get("pdf_url")}
        return {}

    matched_ids = set()
    merged = []
    for p in local_posts:
        buffer_ids = [b for b in (p.get("buffer_post_ids") or []) if b]
        live = [buffer_by_id[b] for b in buffer_ids if b in buffer_by_id]
        matched_ids.update(buffer_ids)
        if live:
            status, due = live[0].get("status"), live[0].get("due_at")
            has_media = any(l.get("has_media") for l in live)
        else:
            status = "lokal_verwaist" if p.get("pushed") else "lokal_ungeplant"
            due = p.get("termin")
            has_media = False
        merged.append({
            "id": p.get("id"),
            "buffer_ids": buffer_ids,
            "text_preview": (p.get("idee") or p.get("text") or "")[:100],
            "status": status,
            "due": due,
            "has_media": has_media,
            "source": "lokal",
            **_carousel_info(buffer_ids),
        })

    grouped = {}
    for b in buffer_posts:
        if b["id"] in matched_ids:
            continue
        key = (b.get("text_preview"), b.get("due_at"))
        g = grouped.setdefault(key, {"buffer_ids": [], "channels": [], "status": b.get("status"), "due": b.get("due_at"), "text_preview": b.get("text_preview"), "has_media": False})
        g["buffer_ids"].append(b["id"])
        g["channels"].append(b.get("channel"))
        g["has_media"] = g["has_media"] or b.get("has_media", False)
    for g in grouped.values():
        merged.append({
            "id": None,
            **_carousel_info(g["buffer_ids"]),
            "buffer_ids": g["buffer_ids"],
            "text_preview": g["text_preview"],
            "status": g["status"],
            "due": g["due"],
            "has_media": g["has_media"],
            "source": "buffer",
        })
    return merged


_DRAFT_STATUS_GROUP = {"draft"}
_SCHEDULED_STATUS_GROUP = {"scheduled"}


def get_merged_posts_by_status(status_group: str) -> dict:
    """Echter Live-Buffer-Stand für die Entwürfe-/Geplant-Tabs im Dashboard
    (status_group 'draft' oder 'scheduled') - Grundlage für GET /api/linkedin/
    posts?status=..., ersetzt das alte, rein lokale pushed-Flag. Nutzt dieselbe
    Merge-Logik, die der Chat über list_posts schon zeigt, inkl. Karussell-
    Thumbnail/PDF-URL wo vorhanden.

    NUR echte Buffer-Treffer (2026-08-13, Bugfix): lokal_ungeplant/lokal_verwaist
    (kein Live-Treffer in Buffer) wurden hier zuerst mit angezeigt, um nichts zu
    verstecken - Sebastian meldete sofort 10 Posts im Entwürfe-Tab ohne
    passenden Buffer-Draft ("wenn kein Karussell-Draft da ist, ist es eine Idee"),
    stammend aus alten, nie gepushten beitraege-*.json-Posts von vor dem
    Draft-First-Umbau. Der Tab zeigt jetzt ausschließlich echte Buffer-Treffer -
    lokal_ungeplant/lokal_verwaist bleiben über list_posts im Chat sichtbar."""
    wanted = _SCHEDULED_STATUS_GROUP if status_group == "scheduled" else _DRAFT_STATUS_GROUP
    posts = [p for p in _merge_local_and_buffer_posts() if p.get("status") in wanted]
    posts.sort(key=lambda p: p.get("due") or "9999")
    return {"posts": posts}


def _format_posts_for_chat() -> str:
    posts = _merge_local_and_buffer_posts()
    if not posts:
        return "(keine gespeicherten Posts)"
    lines = []
    for p in posts:
        due = (p.get("due") or "")[:16].replace("T", " ")
        status_label = _BUFFER_STATUS_LABEL.get(p["status"], p["status"] or "unbekannt")
        medien = " 🖼️KARUSSELL" if p.get("has_media") else ""
        if p["source"] == "buffer":
            hinweis = (
                "ACHTUNG KARUSSELL: NIE delete_post+write_post nutzen, das PDF geht dabei verloren und ist "
                "nicht wiederherstellbar (genau das ist am 12.08.2026 passiert) - Textänderungen an "
                "Karussell-Posts sind hier nicht unterstützt, bei Bedarf Sebastian fragen"
                if p.get("has_media") else
                "nur in Buffer, nicht hier generiert - für Text-/Terminänderung delete_post + write_post nutzen"
            )
            id_part = f"buffer_ids={','.join(p['buffer_ids'])} ({hinweis})"
        else:
            id_part = f"id={p['id']}"
        lines.append(f"- {id_part} | {due} | {status_label}{medien} | {p['text_preview']}")
    return "\n".join(lines)


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


def draft_post(post_id: str) -> dict:
    """MCP-/Chat-Tool-Variante von draft_post - pusht ohne Termin als echten
    Buffer-Entwurf (kein automatisches Veröffentlichen)."""
    return push_post_to_buffer(post_id, scheduled_at=None, draft=True)


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
        "description": "Zeigt alle Posts, die entweder hier lokal geschrieben oder aktuell live in Buffer als Entwurf/geplant hinterlegt sind (auch Drafts, die Sebastian direkt in Buffer angelegt hat) - mit Status (Entwurf/geplant/gesendet/offen) und Termin.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "write_post",
        "description": (
            "Schreibt einen vollständigen LinkedIn-Post-Text aus (aus einer Idee oder freiem Thema) und pusht ihn "
            "SOFORT als echten Buffer-Entwurf (Entwürfe-Tab, kein Termin, wird nie automatisch veröffentlicht). "
            "Nur für reine Text-Ideen nutzen (format_empfehlung 'Text' oder 'Liste', oder Sebastian will ausdrücklich "
            "keinen Karussell-Post) - für alles mit Karussell-Potenzial (Default, siehe make_carousel) NICHT dieses "
            "Tool nutzen. Einplanen danach über schedule_post."
        ),
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
        "description": "Plant einen bestehenden, gespeicherten Post (per id) zu einem Datum/Uhrzeit in Buffer ein (beide Kanäle: Sebastian + Prozessia) - der Post geht zu diesem Termin automatisch live.",
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
        "name": "draft_post",
        "description": (
            "Pusht einen bestehenden, gespeicherten Post (per id) als echten Buffer-Entwurf, OHNE Termin - "
            "wird NIE automatisch veröffentlicht, liegt in Buffer nur zum Anschauen/Auswählen bereit. "
            "Immer dieses Tool nutzen (nicht schedule_post) wenn Sebastian mehrere Posts 'zum Durchschauen', "
            "'als Entwurf', 'unscheduled' oder 'zur Auswahl' haben will, statt sie fest einzuplanen."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"post_id": {"type": "string"}},
            "required": ["post_id"],
        },
    },
    {
        "name": "schedule_buffer_post",
        "description": (
            "Plant einen Post OHNE lokale id (list_posts zeigt id=null, source=buffer - typisch für Karusselle "
            "oder direkt in Buffer angelegte Drafts) zu einem Termin ein - befördert den bestehenden Entwurf zu "
            "'geplant', OHNE einen doppelten Post anzulegen. buffer_post_ids aus list_posts/get_buffer_drafts "
            "übernehmen (alle IDs des Posts, i.d.R. beide Kanäle). Für Posts MIT lokaler id stattdessen schedule_post."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "buffer_post_ids": {"type": "array", "items": {"type": "string"}, "description": "Alle Buffer-Post-IDs dieses Posts (beide Kanäle)."},
                "datum": {"type": "string", "description": "YYYY-MM-DD - relative Angaben wie 'morgen' anhand des heutigen Datums umrechnen."},
                "uhrzeit": {"type": "string", "description": "HH:MM, 24h, Berliner Zeit."},
            },
            "required": ["buffer_post_ids", "datum", "uhrzeit"],
        },
    },
    {
        "name": "make_carousel",
        "description": (
            "STANDARDWEG, um aus einer Idee/einem Thema einen fertigen Post zu machen (Prozessia-Karussell-Design, "
            "siehe STRATEGIE.md §6: Logo, Fließtext, Lila-Akzent, schwarz/weiß) - läuft komplett automatisch "
            "(KI-Bild, Slides, PDF, Upload, Buffer-Push), kann 1-2 Minuten dauern. Entweder post_id (Karussell aus "
            "einem bestehenden Post ableiten) oder hook (freies Thema) angeben. Ohne datum+uhrzeit landet es SOFORT "
            "als Buffer-Entwurf (Entwürfe-Tab) - kein Termin, keine automatische Veröffentlichung. Erst mit "
            "datum+uhrzeit (oder später über schedule_post/schedule_buffer_draft) wird wirklich eingeplant."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "post_id": {"type": "string", "description": "Optional: bestehenden Post als Grundlage nehmen."},
                "hook": {"type": "string", "description": "Optional: freier Hook/Thema, falls kein post_id angegeben."},
                "branche": {"type": "string", "enum": ["Werkzeugbau", "Lohnfertigung", "Elektrotechnik", "Kunststoff", "Metallbau", "Allgemein"]},
                "saeule": {"type": "string", "enum": ["Wissensmanagement", "Compliance", "Einkauf", "KI-Nutzung"]},
                "variante": {"type": "string", "enum": ["schwarz", "weiss"], "description": "Farblogik der Serie: schwarzer oder weißer Hintergrund. Pro Post-Serie konsistent halten, Default schwarz."},
                "datum": {"type": "string", "description": "YYYY-MM-DD, optional - wenn zusammen mit uhrzeit angegeben, wird direkt eingeplant statt als Entwurf zu landen."},
                "uhrzeit": {"type": "string", "description": "HH:MM, optional, nur zusammen mit datum."},
                "entwurf": {
                    "type": "boolean",
                    "description": (
                        "Override des Defaults. Default OHNE datum/uhrzeit ist bereits true (Entwurf), Default MIT "
                        "datum/uhrzeit ist bereits false (eingeplant) - nur explizit setzen, wenn Sebastian das "
                        "Gegenteil vom Default will. entwurf=false OHNE datum/uhrzeit plant automatisch auf den "
                        "nächsten freien Di/Do-9:30-Slot ein (nicht 'sofort live')."
                    ),
                },
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
    {
        "name": "get_insights",
        "description": (
            "Zeigt Performance-Daten der letzten gesendeten Posts direkt aus Buffer: "
            "Impressions, Reach, Engagement-Rate %, Reactions (Likes), Kommentare, Shares. "
            "Immer nutzen bei Fragen zu Performance/Insights/Analytics/Likes/Reichweite der Posts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"n": {"type": "integer", "description": "Anzahl der letzten gesendeten Posts, Default 10"}},
        },
    },
    {
        "name": "get_buffer_status",
        "description": (
            "Live-Abfrage direkt aus Buffer, roh ohne Zusammenführung mit lokalen Posts (list_posts macht "
            "das schon automatisch, ist meist die bessere Wahl). Nur nutzen für den unvermischten "
            "Buffer-Rohstand, z.B. um exakte Buffer-Post-IDs für delete_post/get_insights zu bekommen."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_buffer_drafts",
        "description": "Zeigt nur die Buffer-Entwürfe (status draft), live aus Buffer. Nutzen bei 'Zeig Entwürfe'.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_buffer_ideas",
        "description": (
            "Zeigt Buffers eigenes, organisationsweites Ideas-Feature - NICHT dieselben Ideen wie list_ideas "
            "(das liest die hier im Chat generierten ideen-*.json). Nur nutzen, wenn Sebastian explizit nach "
            "'Buffer-Ideen' fragt, nicht als Ersatz für list_ideas."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "delete_post",
        "description": (
            "Löscht einen Post direkt in Buffer, per Buffer-Post-ID (siehe get_buffer_status/get_insights für die "
            "ID, nicht die lokale Post-id). Bei Posts mit Karussell-PDF (has_media) schlägt der erste Aufruf "
            "OHNE confirm ABSICHTLICH fehl (PDF-Verlust ist unwiderruflich) - erst nach ausdrücklicher Bestätigung "
            "durch Sebastian FÜR GENAU DIESEN Post mit confirm=true erneut aufrufen. NIE delete_post+write_post "
            "als 'Text überarbeiten' nutzen - das ersetzt das Karussell durch einen reinen Text-Post."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "buffer_post_id": {"type": "string"},
                "confirm": {"type": "boolean", "description": "Nur bei Karussell-Posts nötig, nachdem Sebastian das Löschen für genau diesen Post ausdrücklich bestätigt hat."},
            },
            "required": ["buffer_post_id"],
        },
    },
    {
        "name": "reschedule_post",
        "description": (
            "Ändert Datum/Uhrzeit eines bereits in Buffer eingeplanten Posts (per lokaler id, siehe list_posts). "
            "Für noch nicht eingeplante Posts stattdessen schedule_post nutzen - reschedule_post schlägt fehl, "
            "wenn der Post noch nicht gepusht wurde."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "post_id": {"type": "string"},
                "datum": {"type": "string", "description": "YYYY-MM-DD"},
                "uhrzeit": {"type": "string", "description": "HH:MM, 24h, Berliner Zeit."},
            },
            "required": ["post_id", "datum", "uhrzeit"],
        },
    },
    {
        "name": "list_carousels",
        "description": "Zeigt die bisher erstellten Karusselle (Hook, Branche, Slide-Anzahl, Push-Status).",
        "input_schema": {"type": "object", "properties": {}},
    },
]

MAX_LINKEDIN_CHAT_ITERATIONS = 20
_LINKEDIN_STATE_CHANGING_TOOLS = {
    "generate_ideas", "write_post", "revise_post", "schedule_post", "schedule_buffer_post", "draft_post",
    "make_carousel", "set_direction", "delete_post", "reschedule_post",
}


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
            gepusht = r.get("gepusht_als_entwurf", 0)
            hinweis = f"{gepusht}/{len(posts)} als Buffer-Entwurf angelegt (im Entwürfe-Tab sichtbar)."
            if r.get("buffer_errors"):
                hinweis += f" ACHTUNG, nicht alle Buffer-Pushes liefen sauber: {r['buffer_errors']}"
            return f"{len(posts)} Post(s) geschrieben. {hinweis}\n" + "\n".join(lines), False

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
            if not r.get("ok"):
                return f"Buffer-Fehler: {r.get('error', '?')}", True
            if r.get("partial"):
                return f"Post {post_id} nur teilweise eingeplant für {scheduled_at} - ein Kanal ist fehlgeschlagen: {r.get('errors')}. Bitte prüfen, nicht als vollständig erledigt melden.", True
            return f"Post {post_id} eingeplant für {scheduled_at} (beide Kanäle bestätigt).", False

        if name == "draft_post":
            post_id = inp.get("post_id", "")
            r = push_post_to_buffer(post_id, scheduled_at=None, draft=True)
            if not r.get("ok"):
                return f"Buffer-Fehler: {r.get('error', '?')}", True
            if r.get("partial"):
                return f"Post {post_id} nur auf einem Kanal als Entwurf angelegt - der andere ist fehlgeschlagen: {r.get('errors')}. Bitte prüfen.", True
            return f"Post {post_id} als Buffer-Entwurf angelegt (beide Kanäle, kein Termin, wird nicht automatisch veröffentlicht).", False

        if name == "schedule_buffer_post":
            ids = [i for i in (inp.get("buffer_post_ids") or []) if i]
            if not ids:
                return "Keine buffer_post_ids angegeben.", True
            r = schedule_buffer_ids(ids, inp.get("datum", ""), inp.get("uhrzeit", ""))
            if not r.get("ok"):
                return f"Fehler: {r.get('error', '?')}", True
            if r.get("partial"):
                return f"Nur teilweise eingeplant - ein Kanal ist fehlgeschlagen: {r.get('errors')}. Bitte prüfen, nicht als vollständig erledigt melden.", True
            return f"Post eingeplant für {inp.get('datum')} {inp.get('uhrzeit')} (beide Kanäle bestätigt, kein Duplikat angelegt).", False

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
            saeule = inp.get("saeule") or "Einkauf"
            variante = inp.get("variante") or carousel_service.DEFAULT_VARIANTE
            # Draft-first (2026-08-13): ohne explizites datum+uhrzeit landet ein
            # neues Karussell als Buffer-Entwurf (Entwürfe-Tab), nicht automatisch
            # im nächsten Di/Do-Slot eingeplant. Nur wenn Sebastian "entwurf"
            # ausdrücklich angibt, gewinnt das (z.B. um trotz Termin nur einen
            # Entwurf zu wollen, oder umgekehrt explizit entwurf=false + Termin).
            entwurf = bool(inp["entwurf"]) if "entwurf" in inp and inp["entwurf"] is not None else due_at is None
            if post_id:
                r = make_carousel_from_post(post_id, branche=branche, saeule=saeule, due_at=due_at, variante=variante, draft=entwurf)
            elif inp.get("hook"):
                r = make_carousel(inp["hook"], branche=branche, saeule=saeule, due_at=due_at, variante=variante, draft=entwurf)
            else:
                return "Weder post_id noch hook angegeben.", True
            if r.get("ok"):
                titles = " | ".join((r.get("slide_titles") or [])[:3])
                # thumb_url/pdf_url im Klartext mitgeben, nicht nur im Rückgabe-
                # Dict versteckt - der Chat-System-Prompt weist das Modell an,
                # das Bild als Markdown ![...](url) in seine Antwort zu
                # übernehmen, damit Sebastian den Entwurf direkt im Chat sieht
                # statt erst in den Karusselle-Tab wechseln zu müssen.
                bild_zeile = f"\nVorschau-Bild-URL: {r['thumb_url']}" if r.get("thumb_url") else ""
                pdf_zeile = f"\nPDF-URL: {r['pdf_url']}" if r.get("pdf_url") else ""
                return (
                    f"Karussell fertig — {r.get('slides', 0)} Slides, {r.get('anzahl_gepusht', 0)}x als "
                    f"{'Entwurf' if r.get('draft') else 'geplanter Post'} in Buffer. {titles}"
                    f"{bild_zeile}{pdf_zeile}"
                ), False
            return f"Karussell-Fehler: {r.get('error', '?')}", True

        if name == "set_direction":
            r = set_direction(inp.get("prompt", ""))
            return ("Richtung gesetzt." if r.get("ok") else f"Fehler: {r.get('error', '?')}"), not r.get("ok")

        if name == "get_insights":
            text = _format_insights_for_chat(inp.get("n") or 10)
            return text, text.startswith("Fehler")

        if name == "get_buffer_status":
            r = get_buffer_status()
            return _format_buffer_posts_for_chat(r), not r.get("ok")

        if name == "get_buffer_drafts":
            r = get_buffer_drafts()
            return _format_buffer_posts_for_chat(r), not r.get("ok")

        if name == "get_buffer_ideas":
            r = get_buffer_ideas()
            return _format_buffer_ideas_for_chat(r), not r.get("ok")

        if name == "delete_post":
            r = delete_buffer_post(inp.get("buffer_post_id", ""), confirm=bool(inp.get("confirm")))
            if r.get("ok"):
                return f"Post {r.get('id')} gelöscht.", False
            if r.get("needs_confirmation"):
                return r["error"], True
            return f"Fehler: {r.get('error', '?')}", True

        if name == "reschedule_post":
            r = reschedule_post(inp.get("post_id", ""), inp.get("datum", ""), inp.get("uhrzeit", ""))
            return (f"Neuer Termin gesetzt." if r.get("ok") else f"Fehler: {r.get('error', '?')}"), not r.get("ok")

        if name == "list_carousels":
            return _format_carousels_for_chat(), False

        return f"Unbekanntes Tool: {name}", True
    except Exception as e:
        return f"Tool-Fehler ({name}): {e}", True


def _linkedin_system_prompt() -> str:
    now = datetime.now(BERLIN)
    weekday_de = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"][now.weekday()]

    return f"""Du steuerst für Sebastian (Prozessia GbR) die komplette LinkedIn-Content-Pipeline im Chat:
Ideen generieren, Posts schreiben/überarbeiten/einplanen, Karusselle erstellen, Richtung setzen.
Heute ist {weekday_de}, {now.strftime('%Y-%m-%d')}, {now.strftime('%H:%M')} Uhr (Berliner Zeit).

DREI-STUFEN-MODELL (entspricht den drei Tabs im Dashboard - Ideen/Entwürfe/Geplant):
1. IDEE (Tab "Ideen") - Rohmaterial aus generate_ideas, noch kein Post.
2. ENTWURF (Tab "Entwürfe") - ein echter Buffer-Post mit Status "draft": kein Termin, wird NIE automatisch
   veröffentlicht. write_post und make_carousel landen HIER standardmäßig, sobald Sebastian sagt "mach daraus
   einen Post"/"schreib das aus" o.ä. - OHNE dass er extra "als Entwurf" sagen muss, das ist der Default.
3. GEPLANT (Tab "Geplant") - derselbe Buffer-Post, jetzt mit festem Termin (Status "scheduled"), geht zu diesem
   Zeitpunkt automatisch live. Ein Entwurf wird NUR auf ausdrücklichen Wunsch eingeplant ("plane das für Dienstag
   ein", "schick den jetzt raus") - schedule_post/schedule_buffer_post schalten den BESTEHENDEN Entwurf um,
   legen NIE einen zweiten Post an.

KARUSSELL IST DER STANDARD, NICHT DIE AUSNAHME: fast jeder Post soll als Bild-Karussell im Prozessia-Design
raus (STRATEGIE.md §6: Logo, Fließtext, Lila-Akzent, schwarz/weiß je Serie). Wenn Sebastian eine Idee "zum
Post machen" will und sie keine explizite Formatvorgabe "Text"/"Liste" hat, IMMER make_carousel nutzen, NICHT
write_post. write_post ist nur für ausdrückliche Text-only-Wünsche da.

Aktuelle Richtungsvorgabe: {_current_direction() or '(keine gesetzt)'}

Aktuelle Ideen:
{_format_ideas_for_chat()}

Aktuelle gespeicherte Posts:
{_format_posts_for_chat()}

Verfügbare Aktionen (bei Bedarf aufrufen, sonst direkt in Text antworten):
- list_ideas / list_posts (CLI: list_linkedin_ideas / list_linkedin_posts): aktuellen Stand nachladen, falls sich seit obiger Übersicht etwas geändert hat. list_posts zeigt bei jedem Post den echten Buffer-Status (Entwurf/geplant/gesendet) und ob id (lokal) oder nur buffer_ids (nur in Buffer, z.B. Karusselle) vorhanden ist - das entscheidet, welches Tool zum Einplanen passt (siehe unten).
- generate_ideas (CLI: generate_linkedin_ideas): neue Ideen generieren (ersetzt die alten)
- make_carousel (CLI: generate_carousel): STANDARDWEG, um aus einer Idee/einem Thema einen fertigen Post zu machen (Bild-Karussell, Slides+Bild+PDF+Buffer, 1-2 Minuten). post_id ODER hook angeben.
  Ohne datum+uhrzeit landet es SOFORT als Buffer-Entwurf (Tab "Entwürfe") - das ist der Default, nicht "entwurf=true" nötig.
  MIT datum+uhrzeit wird direkt eingeplant (Tab "Geplant").
  WICHTIG: Das Tool-Ergebnis enthält eine Vorschau-Bild-URL (thumb_url) - binde die IMMER unverändert als
  Markdown-Bild in deine Antwort ein: ![Karussell-Vorschau](URL), plus die PDF-URL als Markdown-Link
  [Vollständiges PDF](URL) - Sebastian sieht den fertigen Entwurf so direkt im Chat.
- write_post (CLI: write_linkedin_post_draft): NUR für ausdrückliche Text-only-Ideen (nicht Karussell) - Post-Text schreiben und SOFORT als Buffer-Entwurf pushen (Tab "Entwürfe", Default wie bei make_carousel).
- revise_post (CLI: revise_linkedin_post): Text eines bestehenden Posts MIT lokaler id (per id) überarbeiten - funktioniert NICHT für Karusselle/Buffer-only-Posts (id=null), dafür gibt es keinen Text-Edit-Weg.
- schedule_post (CLI: schedule_linkedin_post): Post MIT lokaler id (per id, aus write_post/list_posts) zu einem Zeitpunkt einplanen (rechne relative Angaben wie "morgen" anhand des heutigen Datums oben um). Schaltet einen bestehenden Entwurf zu "geplant" um, legt KEINEN zweiten Post an.
- schedule_buffer_post: Post OHNE lokale id (list_posts zeigt id=null, buffer_ids=[...] - typisch für Karusselle) zu einem Zeitpunkt einplanen, per buffer_post_ids. Für alles, was make_carousel erzeugt hat, dieses Tool nutzen, nicht schedule_post.
- draft_post: bestehenden Post (per id) OHNE Termin (nochmal) als Entwurf pushen/zurücksetzen - meist nicht nötig, da write_post/make_carousel schon automatisch als Entwurf starten.
- set_direction (CLI: set_linkedin_direction): Richtungsvorgabe für künftige Generierung setzen
- get_insights (CLI: get_buffer_insights): Performance-Daten (Impressions, Reach, Engagement-Rate %, Reactions/Likes, Kommentare, Shares) der letzten gesendeten Posts live aus Buffer abrufen
- get_buffer_status (CLI: get_buffer_status): roher Buffer-Live-Stand ohne Zusammenführung mit lokalen Posts - list_posts zeigt das schon gemischt an, get_buffer_status nur für unvermischte Buffer-Post-IDs (z.B. für delete_post) nutzen
- get_buffer_drafts (CLI: get_buffer_drafts): nur die Buffer-Entwürfe live abrufen
- get_buffer_ideas (CLI: get_buffer_ideas): Buffers eigenes Ideas-Feature - nur auf explizite Nachfrage nach "Buffer-Ideen", nicht als Ersatz für list_ideas
- delete_post (CLI: delete_buffer_post): einen Post direkt in Buffer löschen (Buffer-Post-ID aus get_buffer_status/get_insights, nicht die lokale id). Bei Karussell-Posts (has_media) schlägt der erste Aufruf ABSICHTLICH fehl (PDF-Verlust ist unwiderruflich) - erst nach Sebastians ausdrücklicher Bestätigung FÜR GENAU DIESEN Post mit confirm=true erneut aufrufen. NIE delete_post+write_post als "Text überarbeiten" nutzen, das ersetzt das Karussell durch einen Text-Post.
- reschedule_post (CLI: reschedule_linkedin_post): Termin eines bereits eingeplanten Posts MIT lokaler id ändern - für Posts ohne lokale id stattdessen schedule_buffer_post nutzen, für noch nicht gepushte Posts schedule_post.
- list_carousels (CLI: list_linkedin_carousels): bisher erstellte Karusselle mit Design-Vorschau anzeigen

Regeln für Post-Texte (bei write_post/make_carousel/revise_post), vollständig in Marketing/LinkedIn/STRATEGIE.md:
- Claim it, Show it, Aim it: klare Aussage, eigene Zahl, an eine konkrete Person gerichtet
- Aufbau: Problem-Einstieg, 2–3 Zahlen, Ergebnis-Zeile als **Ergebnis: ...**, optional
  Fachsystem/Norm, kurzer Einordnungs-Absatz, Erfahrungsfrage, 3–5 Hashtags
- Max. 15 Wörter pro Satz, Leerzeile nach jeder 2. Zeile
- 3–5 Hashtags am Ende, breit (#KI, #Mittelstand) plus spezifisch (#Werkzeugbau, #Beschaffung)
- 0 Emojis außer max. 1 ganz am Ende, keine Links im Text
- Erfundene Beispiele nur mit erfundenem Firmennamen und als typisches Szenario gerahmt
- Keine Wörter: innovativ, nachhaltig, ganzheitlich, Lösung, Transformation
- Keine generischen Zustimmungsfragen, kein Hedging, keine performte Bescheidenheit
- Zielgruppe: Geschäftsführer/Einkaufsleiter, produzierende Mittelständler 20–80 MA,
  Werkzeugbau/Lohnfertigung/Elektrotechnik/Kunststoff/Metallbau — Nische nie verwässern

Sei proaktiv: wenn Sebastian z.B. "mach aus Idee X einen Post" sagt, ruf direkt make_carousel (oder bei
ausdrücklichem Textwunsch write_post) auf statt nachzufragen - das Ergebnis landet als Entwurf, Sebastian sieht
es im Tab "Entwürfe" und kann im Chat weiter darauf reagieren ("gefällt mir, plan das für Donnerstag ein",
"mach den Hook schärfer", "lösch das"). Frag nur nach, wenn eine Aktion sonst mehrdeutig wäre (z.B. welcher
Post gemeint ist, oder ob wirklich gelöscht werden soll). Nach jedem Tool-Aufruf kurz bestätigen, was passiert
ist - bei mehreren Aktionen hintereinander (z.B. "generiere 9 Ideen und mach daraus Karusselle") jede einzeln
ausführen, nicht nach der ersten aufhören."""


_LINKEDIN_STATE_CHANGING_MCP_TOOLS = {
    "mcp__prozessia-tools__generate_linkedin_ideas",
    "mcp__prozessia-tools__write_linkedin_post_draft",
    "mcp__prozessia-tools__revise_linkedin_post",
    "mcp__prozessia-tools__schedule_linkedin_post",
    "mcp__prozessia-tools__schedule_buffer_post",
    "mcp__prozessia-tools__generate_carousel",
    "mcp__prozessia-tools__set_linkedin_direction",
    "mcp__prozessia-tools__delete_buffer_post",
    "mcp__prozessia-tools__reschedule_linkedin_post",
    "mcp__prozessia-tools__generate_linkedin_posts",
    "mcp__prozessia-tools__push_to_buffer",
}


def _format_linkedin_history(messages: list[dict], budget_chars: int = 12000) -> str:
    """Baut ein Text-Transkript der bisherigen Unterhaltung (alles außer der
    letzten Nachricht) für den CLI-Pfad - identische Logik zu
    chat.py:_format_history(). Ohne das schickte _chat_linkedin_cli pro Aufruf
    nur die letzte Nachricht an claude -p (--no-session-persistence, kein
    --resume) und vergaß dadurch jeden früheren Turn komplett (Sebastian,
    2026-08-17: "vergisst den Chatverlauf" - z.B. hat er im nächsten Turn
    nicht mehr gewusst, von welchem Post überhaupt die Rede war). Der Haupt-
    Chat hatte genau diesen Bug schon am 2026-07-26 gefixt, der LinkedIn-Chat
    (später als eigener Pfad entstanden) wiederholte ihn unabhängig."""
    if len(messages) <= 1:
        return ""
    picked: list[str] = []
    used = 0
    for m in reversed(messages[:-1]):
        role = "Nutzer" if m.get("role") == "user" else "Assistent"
        line = f"{role}: {m.get('content', '')}"
        if used + len(line) > budget_chars and picked:
            break
        picked.append(line)
        used += len(line)
    picked.reverse()
    return "\n\n".join(picked)


def _chat_linkedin_cli(messages: list[dict]):
    """CLI-Variante von chat_linkedin_stream() (claude_engine="cli") - nutzt
    dieselben Aktionen, aber als MCP-Tools (siehe app.mcp_server) über einen
    Claude-Code-Subprocess statt des Custom-Tool-Loops unten. Abrechnung über
    CLAUDE_CODE_OAUTH_TOKEN statt ANTHROPIC_API_KEY.

    ECHTER Generator (2026-08-13, Bugfix): liefert Chunks/state_changed sofort,
    sobald sie ankommen, statt den kompletten Subprocess-Lauf erst abzuwarten
    und danach EIN einziges Ergebnis zurückzugeben. Bei Batch-Aufträgen mit
    mehreren Karusselen (je 1-2 Min., z.B. "mach zu 4 Ideen Entwürfe") blieb
    die HTTP-Verbindung dadurch mehrere Minuten komplett still - Sebastian
    meldete "Verbindung bricht ab" (13.08.2026), irgendeine Zwischenschicht
    (Traefik/Caddy/Browser) kappte mangels Daten. Mirror von
    chat.py:_stream_chat_cli, das für den Haupt-Chat exakt so schon
    Token-für-Token streamt - dort trat dasselbe Problem deshalb nie auf."""
    from app.services import claude_cli
    last_msg = messages[-1].get("content", "") if messages else ""
    if not last_msg:
        yield {"error": "Keine Nachricht erhalten"}
        return
    system = _linkedin_system_prompt()
    history_block = _format_linkedin_history(messages)
    dynamic_context = (
        f"=== BISHERIGE UNTERHALTUNG (bereits erledigt, nicht erneut ausführen) ===\n{history_block}"
        if history_block else ""
    )
    # Token-für-Token-Text ("stream_event"/"content_block_delta") wird sofort
    # weitergereicht; delta_buffer verhindert, dass derselbe Text beim
    # abschließenden "assistant"-Event (kompletter Block) doppelt geschickt
    # wird, falls eine CLI-Version mal keine Partial-Messages liefert, greift
    # der "assistant"-Zweig als Fallback (identische Logik wie chat.py).
    delta_buffer = ""
    try:
        # mcp_warmup_seconds hochgesetzt (2026-07-25): dieser Pfad läuft bewusst
        # nicht über den warmen Pool (claude_cli_pool.py bäckt nur BASE_PROMPT
        # ein, nicht die LinkedIn-Persona/-Tools aus _linkedin_system_prompt())
        # und kaltstartet daher bei jeder Anfrage. Unter Serverlast (parallele
        # RAG-Embeddings, Inbox-Verarbeitung) reichten die generischen 8s nicht
        # zuverlässig aus, live beobachtet: Modell antwortete bevor MCP verbunden
        # war und hielt write_linkedin_post_draft & Co. für nicht verfügbar.
        for event in claude_cli.stream_chat(
            last_msg, system_prompt=system, dynamic_context=dynamic_context,
            model=Models.SONNET, mcp_warmup_seconds=15.0,
        ):
            etype = event.get("type")
            if etype == "stream_event":
                ev = event.get("event", {})
                ev_type = ev.get("type")
                if ev_type == "content_block_start":
                    delta_buffer = ""
                elif ev_type == "content_block_delta":
                    delta = ev.get("delta", {})
                    if delta.get("type") == "text_delta" and delta.get("text"):
                        delta_buffer += delta["text"]
                        yield {"chunk": delta["text"]}
            elif etype == "assistant":
                for block in event.get("message", {}).get("content", []):
                    if block.get("type") == "text" and block.get("text"):
                        if block["text"] == delta_buffer:
                            continue
                        yield {"chunk": block["text"]}
                    elif block.get("type") == "tool_use" and block.get("name") in _LINKEDIN_STATE_CHANGING_MCP_TOOLS:
                        # Jedes Mal senden, nicht nur beim ersten Mal - bei
                        # mehreren Karusselen in Folge soll das Dashboard nach
                        # JEDEM fertigen Entwurf neu laden, nicht erst am Ende.
                        yield {"state_changed": True}
            elif etype == "result" and event.get("is_error"):
                yield {"error": event.get("result", "Unbekannter Fehler")}
                return
    except claude_cli.ClaudeCliError as e:
        yield {"error": str(e)}


def _chat_linkedin_api(messages: list[dict]):
    """API-Engine-Variante von chat_linkedin_stream() (Anthropic SDK statt
    Claude-Code-Subprocess) - Tool Use mit tool_choice=auto über mehrere
    Turns. Streamt pro Modell-Antwort/Tool-Ergebnis (nicht Token für Token wie
    der CLI-Pfad), reicht aber für dasselbe Ziel: die Verbindung bleibt auch
    bei mehreren langsamen Tool-Aufrufen (z.B. mehrere Karusselle) hintereinander
    aktiv, statt bis zum Abschluss des gesamten Turns komplett still zu sein."""
    system = _linkedin_system_prompt()
    try:
        current_messages = list(messages)

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
                    yield {"chunk": block.text.strip()}

            if result.stop_reason != "tool_use":
                return

            tool_result_blocks = []
            for block in result.content:
                if block.type != "tool_use":
                    continue
                content, is_error = _execute_linkedin_chat_tool(block.name, block.input)
                if not is_error and block.name in _LINKEDIN_STATE_CHANGING_TOOLS:
                    yield {"state_changed": True}
                tool_result_blocks.append({
                    "type": "tool_result", "tool_use_id": block.id,
                    "content": content, "is_error": is_error,
                })
            current_messages.append({"role": "user", "content": tool_result_blocks})
        else:
            yield {"chunk": "\n\n(Maximale Anzahl an Aktionen in diesem Turn erreicht.)"}
    except Exception as e:
        logger.exception("chat_linkedin_stream() fehlgeschlagen")
        yield {"error": str(e)}


def chat_linkedin_stream(messages: list[dict]):
    """Agentischer Chat für die gesamte LinkedIn-Sektion: Ideen generieren,
    Posts schreiben/überarbeiten/einplanen, Karusselle erstellen, Richtung
    setzen - alles über Tool Use, als Generator (yieldet {"chunk": ...} /
    {"state_changed": True} / {"error": ...}, konsumiert vom SSE-Endpunkt in
    routers/linkedin.py). Ersetzt das frühere chat_about_post(), das auf einen
    einzelnen Post beschränkt war, und die alte, komplett blockierende
    chat_linkedin()-Variante (siehe _chat_linkedin_cli-Docstring)."""
    if get_settings().claude_engine == "cli":
        yield from _chat_linkedin_cli(messages)
    else:
        yield from _chat_linkedin_api(messages)


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
    """Nächster erlaubter Slot: Dienstag ODER Donnerstag, 09:30 Uhr Berlin
    (Strategie §5 - verbindlich, war vorher fälschlich Di/Mi/Do 07:00 oder
    12:00). Identische Logik zu carousel_service._next_carousel_slot(), hier
    mit `after` erweitert: ein Post-Batch bekommt so fortlaufend verschiedene
    Slots statt mehrere Posts auf denselben Tag/dieselbe Uhrzeit zu legen."""
    now = after or datetime.now()
    for d in range(1, 15):
        candidate = (now + timedelta(days=d)).replace(hour=9, minute=30, second=0, microsecond=0)
        if candidate.weekday() in (1, 3):  # Dienstag=1, Donnerstag=3
            return candidate.strftime("%Y-%m-%dT%H:%M:%S+02:00")
    return (now + timedelta(days=14)).strftime("%Y-%m-%dT09:30:00+02:00")


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
                        "kategorie": {"type": "string", "enum": ["Wissensmanagement", "Compliance", "Einkauf", "KI-Nutzung"]},
                        "titel": {"type": "string", "description": "Max 60 Zeichen."},
                        "hook": {"type": "string", "description": "Erste Zeile, max 80 Zeichen, stoppt den Scroll."},
                        "kern_botschaft": {"type": "string", "description": "Was der Leser mitnimmt."},
                        "branche": {"type": "string", "enum": ["Werkzeugbau", "Lohnfertigung", "Elektrotechnik", "Kunststoff", "Metallbau", "Allgemein"]},
                        "zielgruppe_spezifisch": {"type": "string", "description": "Die konkrete Person laut Aim-Regel, z.B. 'Einkaufsleiter mit Ausschreibung ohne Herstellerangabe, 45 MA, Werkzeugbau'."},
                        "format_empfehlung": {"type": "string", "enum": ["Karussell", "Text", "Liste"]},
                        "cta_vorschlag": {"type": "string", "description": "Eine Frage, die nur mit echter Berufserfahrung beantwortbar ist - keine generische Zustimmungsfrage, kein Engagement-Bait."},
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
Maßgeblich ist die Content-Strategie in Marketing/LinkedIn/STRATEGIE.md, hier die Kurzfassung.

ZIELGRUPPE (eng halten):
Geschäftsführer und Einkaufsleiter in inhabergeführten, produzierenden Mittelständlern,
20–80 Mitarbeitende, Deutschland. Branchen: Werkzeugbau, Lohnfertigung, Elektrotechnik,
Kunststoff, Metallbau.

POSITIONIERUNG: Generische KI-Agenturen sprechen "den Mittelstand" allgemein an.
Prozessias Fertigungs-Nische ist das Kernargument — sie muss in jeder Idee spürbar sein.
Produkte, um die sich der Content dreht: Beschaffungsagent, Stücklistenagent (BOM-Mapper),
KI-Chatbot, KI-Schulungen.

{f"Richtungsvorgabe: {current_direction}" if current_direction else ""}
{f"Zusätzlicher Fokus: {focus}" if focus else ""}

Jede Idee bekommt EINEN dieser drei Post-Typen:
- Typ A – Schmerz-Post: Ich-Perspektive, konkreter Alltags-Schmerz der Zielgruppe, keine Lösung im ersten Satz
- Typ B – Karussell/Dokument-Post: Framework, Checkliste oder Schritt-für-Schritt (3–7 Punkte)
- Typ C – Story-Post: anonymes Vorher/Nachher mit konkreten Zahlen (Zeit, Geld, Aufwand)

Jede Idee bekommt GENAU EINE der vier Themen-Säulen:
- Wissensmanagement: Firmenwissen sichern, KI-gestützte Dokumentation, Corporate-Wissen strukturieren.
  Konkret: Spezialwissen geht mit der Verrentungswelle verloren; Wissen steckt in Köpfen, E-Mails und
  verstreuten Dateien statt durchsuchbar zu sein; ChatGPT-Uploads skalieren nicht auf echtes Firmenwissen.
- Compliance: EU-KI-Verordnung, Transparenzpflichten für KI-Systeme (z.B. Chatbots), DSGVO-Konformität,
  Schatten-KI als unkontrollierter Wissensabfluss — sachlich, keine Panikmache.
- Einkauf: Ausschreibungsprozesse, Kalkulation, Lieferantenmanagement, Long-Tail-Spend.
- KI-Nutzung: Adoption, Hürden, Praxisbeispiele, Stücklisten-/BOM-Automatisierung.

Ziel-Verteilung über die 10 Ideen: mindestens 2× je Säule, Rest frei.
Den Themen-Fingerprint über Wochen halten — kein abrupter Themenwechsel.

Generiere GENAU 10 Ideen: 4× Typ A, 3× Typ B, 3× Typ C.
Format-Priorität: Dokument-Karussell vor Text vor Video. Karussell ist ab jetzt das
Standardformat für FAST JEDEN Post - mindestens 8 von 10 Ideen bekommen
format_empfehlung "Karussell" (auch Typ A/C-Ideen lassen sich als Karussell umsetzen,
nicht nur Typ B). "Text" oder "Liste" nur, wenn das Thema wirklich nicht als
mehrseitiges Karussell funktioniert (z.B. eine sehr kurze, pointierte Einzelaussage).

CLAIM IT, SHOW IT, AIM IT — gilt für jede Idee:
- Claim: eine klare Aussage, keine Frage als These, kein Hedging.
- Show: eine eigene Zahl oder konkrete Beobachtung, kein nacherzähltes fremdes Framework.
- Aim: an eine konkrete Person gerichtet (Feld zielgruppe_spezifisch), nicht an "alle Unternehmen".

VERBOTEN für jeden Hook und jede Idee:
- Statistik oder Prozentzahl als allererster Satz
- Wörter: innovativ, nachhaltig, ganzheitlich, Transformation, revolutionieren, disruptiv, zukunftsfähig
- Superlative ohne Beleg, performte Bescheidenheit, Hedging
- Generische Zustimmungsfragen als CTA ("Stimmt ihr zu?", "Wer kennt das?")
- Engagement-Bait ("Teile diesen Post", "Tag jemanden")
- Echte Kundennamen — anonymisierte Beispiele bekommen erfundene Firmennamen
  (z.B. "Elektro Nordstern GmbH", "Nordmetall Fertigung GmbH") und werden als typisches
  Szenario gerahmt, nie als verifizierbares reales Kundenergebnis.

PFLICHT für jeden Hook:
- Stoppt den Scroll innerhalb von 3 Sekunden
- Ich-Perspektive ODER direkte Du-Ansprache
- Kein vollständiger Satz — eher Fragment oder Frage"""

    try:
        if get_settings().claude_engine == "cli":
            from app.services import claude_cli
            json_prompt = prompt + """

Antworte NUR mit einem JSON-Objekt in genau diesem Format, kein Markdown, keine Erklärung davor/danach:
{"ideen": [{"typ": "A|B|C", "kategorie": "Wissensmanagement|Compliance|Einkauf|KI-Nutzung", "titel": "...", "hook": "...", "kern_botschaft": "...", "branche": "Werkzeugbau|Lohnfertigung|Elektrotechnik|Kunststoff|Metallbau|Allgemein", "zielgruppe_spezifisch": "...", "format_empfehlung": "Karussell|Text|Liste", "cta_vorschlag": "..."}] (genau 10 Einträge)}"""
            raw = claude_cli.run_json(json_prompt, model=Models.SONNET, max_budget_usd=1.00, timeout=240).strip()
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
Maßgeblich ist die Content-Strategie in Marketing/LinkedIn/STRATEGIE.md, hier die Kurzfassung.

ZIELGRUPPE (eng halten):
Geschäftsführer und Einkaufsleiter in inhabergeführten, produzierenden Mittelständlern,
20–80 Mitarbeitende, Deutschland. Branchen: Werkzeugbau, Lohnfertigung, Elektrotechnik,
Kunststoff, Metallbau. Die Fertigungs-Nische ist das Kernargument der Positionierung und
muss in jedem Post spürbar sein — nie zu "der Mittelstand" allgemein verwässern.

Produkte: Beschaffungsagent, Stücklistenagent (BOM-Mapper), KI-Chatbot, KI-Schulungen.
Themen-Säulen: Wissensmanagement, Compliance (EU-KI-Verordnung, DSGVO), Einkauf/Beschaffung,
allgemeine KI-Nutzung im Mittelstand.

{f"Richtungsvorgabe: {current_direction}" if current_direction else ""}

POST-TYPEN (steht in der Spezifikation):
- Typ A – Schmerz-Post: Ich-Perspektive, Alltags-Schmerz der Zielgruppe, keine KI-Lösung im ersten Satz
- Typ B – Karussell/Dokument: Framework, Checkliste oder Schritt-für-Schritt mit 3–7 nummerierten Punkten
- Typ C – Story-Post: anonymes Vorher/Nachher, konkrete Zahlen (Stunden, €, Prozent)

CLAIM IT, SHOW IT, AIM IT — ausnahmslos in jedem Post:
- Claim: eine klare Aussage. Keine Frage als These, kein "könnte sein", kein "korrigiert mich".
- Show: eine eigene Zahl oder konkrete Beobachtung, kein nacherzähltes fremdes Framework.
- Aim: an eine konkrete Person gerichtet (z.B. "Einkaufsleiter mit Ausschreibung ohne
  Herstellerangabe"), nicht an "alle Unternehmen".

AUFBAU DES POST-TEXTES (in dieser Reihenfolge):
1. Kurze Einleitung oder Frage, die das Problem umreißt
2. 2–3 konkrete Zahlen oder Fakten
3. Eine Ergebnis-Zeile, allein auf einer Zeile, im Format: **Ergebnis: ...**
4. Optional ein Satz mit einem bekannten Fachsystem oder einer Norm (SAP, proALPHA, ERP,
   branchenübliche Normen) — nur wenn es inhaltlich trägt
5. Kurzer Einordnungs-Absatz, 2–3 Sätze
6. Abschlussfrage, die die Aussage stützt und nur mit echter Berufserfahrung beantwortbar ist
7. 3–5 Hashtags

FORMAT-REGELN (ausnahmslos):
- Max. 15 Wörter pro Satz, Leerzeile nach jeder 2. Zeile
- 3–5 Hashtags am Ende, Mischung aus breit (#KI, #Mittelstand) und spezifisch
  (#Werkzeugbau, #Beschaffung, #Wissensmanagement, #Lohnfertigung, #Stückliste, #EUAIAct)
- Nur die Ergebnis-Zeile wird mit **...** markiert, sonst keine Fett-Markierung
- 0 Emojis, außer maximal 1 in der letzten Zeile (optional)
- Links NIEMALS im Post-Text — nur als separater Kommentar

TON: Deutsch, direkt, nüchtern-konkret. Aussagen werden getroffen, nicht zur Diskussion gestellt.

VERBOTENE WÖRTER: innovativ, nachhaltig, ganzheitlich, Lösung, Transformation, revolutionieren, disruptiv, zukunftsfähig
BEISPIELE: erfundene Beispiele sind erlaubt, wenn sie mitreißend sind — aber immer mit
erfundenem Firmennamen (z.B. "Elektro Nordstern GmbH", "Nordmetall Fertigung GmbH"), niemals
mit echtem Kundennamen, und immer als typisches Szenario gerahmt, nie als verifizierbares
reales Kundenergebnis (sonst irreführende Werbung).
VERBOTEN: "In der heutigen Zeit", "Die KI wird", Statistik als allererster Satz,
Engagement-Bait, generische Zustimmungsfragen ("Stimmt ihr zu?", "Wer kennt das?"),
performte Bescheidenheit, Superlative ohne Beleg.

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
            raw = claude_cli.run_json(json_prompt, model=Models.SONNET, max_budget_usd=1.00, timeout=240).strip()
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
            last_slot = datetime.fromisoformat(slot.replace("+02:00", ""))
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

        # Draft-first (2026-08-13): neu geschriebene Posts landen SOFORT als
        # echter Buffer-Entwurf, damit sie im Entwürfe-Tab sichtbar sind, ohne
        # dass ein zweiter Tool-Call (draft_post) nötig ist bzw. vergessen
        # werden kann. Kein Termin -> due bleibt leer, buffer_push() ignoriert
        # scheduled_at bei draft=True ohnehin, geplant wird erst explizit über
        # schedule_post/schedule_buffer_draft.
        buffer_errors = []
        pushed_count = 0
        for p in stored_posts:
            if not p.get("text", "").strip():
                continue
            result = buffer_push(p["text"], scheduled_at=None, draft=True)
            if result.get("ok"):
                pushed_count += 1
                _save_post_fields(
                    p["id"], pushed=True,
                    buffer_post_ids=[x["post_id"] for x in result.get("pushed", [])],
                )
                if result.get("partial"):
                    buffer_errors.append({"id": p["id"], "errors": result.get("errors")})
            else:
                buffer_errors.append({"id": p["id"], "error": result.get("error")})
        cache.invalidate("buffer_status")

        return {"ok": True, "posts": posts, "gepusht_als_entwurf": pushed_count, "buffer_errors": buffer_errors or None}
    except Exception as e:
        logger.exception("generate_posts() fehlgeschlagen")
        return {"error": str(e)}


def push_latest_to_buffer() -> dict:
    """Pusht alle Posts aus dem neuesten beitraege-*.json nach Buffer (beide Kanäle).
    Migriert aus brain_server.py:api_buffer_push() — dort per Subprocess auf
    buffer_manager.py, hier direkt über buffer_push().

    Promote-statt-duplizieren (2026-08-13): generate_posts() pusht seit dem
    Draft-First-Umbau jeden Post SOFORT als Buffer-Entwurf. Ruft danach noch
    jemand push_latest_to_buffer() (z.B. die MCP-/Dashboard-Tool-Varianten von
    generate_linkedin_posts, die historisch beide Schritte kombinieren), legte
    das bisher für JEDEN Post einen ZWEITEN, live geplanten Duplikat-Post an,
    statt den schon existierenden Entwurf einzuplanen - jetzt idempotent."""
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
        existing_ids = [b for b in (p.get("buffer_post_ids") or []) if b]
        if existing_ids:
            result = _promote_buffer_posts(existing_ids, p.get("termin"), draft=False)
        else:
            result = buffer_push(p["text"], scheduled_at=p.get("termin"))
            if result.get("ok") and p.get("id"):
                _save_post_fields(p["id"], pushed=True, buffer_post_ids=[x["post_id"] for x in result.get("pushed", [])])
        if result.get("ok"):
            pushed.append(label)
        else:
            errors.append({"tag": label, "error": result.get("error")})

    cache.invalidate("buffer_status")
    if not pushed:
        return {"error": errors or "Keine Posts zum Pushen gefunden"}
    return {"ok": True, "gepusht": pushed, "errors": errors or None}


def buffer_push(text: str, scheduled_at: str | None = None, draft: bool = False) -> dict:
    """Pusht einen Post auf beide Buffer-Kanäle (Sebastian + Prozessia) via GraphQL.

    draft=True (2026-08-13): landet als echter Buffer-Entwurf (saveToDraft, wie
    carousel_service.generate_carousel es für Karusselle schon konnte) statt
    automatisch eingeplant zu werden. Vorher gab es für reine Text-Posts KEINEN
    Weg, "als Entwurf" zu erfüllen - eine Bitte wie "pushe sie unscheduled als
    Entwürfe" landete zwangsläufig trotzdem scheduled (mode=addToQueue mangels
    Alternative), weil das Tool das schlicht nicht kannte. Live beobachtet
    12.08.2026: 9 angeforderte Entwürfe wurden automatisch im Di/Do-Rhythmus
    eingeplant statt als Entwürfe liegenzubleiben.

    **Ergebnis: ...** wird hier erst beim Push in Unicode-Fettschrift übersetzt
    (siehe carousel_service._linkedin_bold). Gespeichert bleibt der Text mit
    **-Markierung, damit er im Dashboard weiter normal editierbar ist —
    Unicode-Bold ließe sich dort nur mühsam wieder ändern."""
    settings = get_settings()
    token = settings.buffer_api_token
    if not token:
        return {"error": "BUFFER_API_TOKEN nicht gesetzt"}

    text = carousel_service._linkedin_bold(text)

    channels = [settings.buffer_channel_sebastian, settings.buffer_channel_prozessia]
    pushed = []
    errors = []

    for channel_id in channels:
        # due_at: ISO-8601 mit Z oder leer → Buffer-Default (nächster freier Slot)
        due = scheduled_at or ""
        # createPost liefert PostActionPayload zurück - seit einem Buffer-
        # Schema-Update (2026-07, live per Introspection bestätigt) ein UNION
        # aus PostActionSuccess (echter Post) und diversen Fehlertypen
        # (InvalidInputError/UnauthorizedError/NotFoundError/UnexpectedError/
        # RestProxyError/LimitReachedError), alle mit "message". Braucht daher
        # Inline-Fragmente statt direkter post/userErrors-Felder - die alte
        # Query war gegen das aktuelle Schema komplett ungültig
        # (GRAPHQL_VALIDATION_FAILED), lieferte aber trotzdem HTTP 200 mit
        # einem obersten "errors"-Feld statt "data". Der bisherige Code
        # prüfte nur data["data"]["createPost"], fand dort nichts (leeres
        # dict), und markierte den Post fälschlich als erfolgreich gepusht
        # mit leerer post_id - kein einziger Post kam seither wirklich in
        # Buffer an, ohne dass das je auffiel.
        mutation = """
mutation CreatePost($input: CreatePostInput!) {
  createPost(input: $input) {
    ... on PostActionSuccess {
      post { id status dueAt }
    }
    ... on InvalidInputError { message }
    ... on UnauthorizedError { message }
    ... on NotFoundError { message }
    ... on UnexpectedError { message }
    ... on RestProxyError { message }
    ... on LimitReachedError { message }
  }
}"""
        # CreatePostInput-Form ebenfalls live per Introspection bestätigt
        # (2026-07-25): kein organizationId, kein content-Wrapper - text ist
        # ein Top-Level-Feld. mode/schedulingType sind Pflichtfelder (Enums),
        # vorher gar nicht gesetzt. mode=customScheduled für einen festen
        # Termin (dueAt gesetzt), sonst addToQueue (Buffer sucht selbst den
        # nächsten freien Slot). schedulingType=automatic, damit der Post
        # tatsächlich automatisch veröffentlicht wird statt nur eine
        # Erinnerung zu erzeugen (Alternative laut Schema: "notification").
        variables = {
            "input": {
                "channelId": channel_id,
                "text": text,
                "mode": "customScheduled" if due else "addToQueue",
                "schedulingType": "automatic",
                **({"dueAt": due} if due and not draft else {}),
                **({"saveToDraft": True} if draft else {}),
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
            if data.get("errors"):
                errors.append({"channel": channel_id, "errors": data["errors"]})
                continue
            result = data.get("data", {}).get("createPost") or {}
            post = result.get("post")
            if post and post.get("id"):
                pushed.append({"channel": channel_id, "post_id": post["id"]})
            else:
                errors.append({"channel": channel_id, "errors": [{"message": result.get("message", "Unbekannte Antwort ohne post/message")}]})
        except Exception as exc:
            errors.append({"channel": channel_id, "error": str(exc)})

    if errors and not pushed:
        return {"error": errors}
    # "ok" heißt bisher nur "mindestens ein Kanal hat geklappt" - ein Aufrufer,
    # der nur result["ok"] prüft (z.B. der Chat-Tool-Handler für schedule_post),
    # meldet dann fälschlich "in beiden Kanälen eingeplant", obwohl z.B. nur
    # Sebastian klappte und Prozessia mit einem stillen Fehler ausblieb.
    # partial=True macht diesen Fall für Aufrufer unterscheidbar.
    return {"ok": True, "pushed": pushed, "errors": errors or None, "partial": bool(errors)}


_INSIGHTS_ORG_ID = "6a15c3685a233c9c16251245"

_INSIGHTS_QUERY = """
query PostsWithMetrics($orgId: OrganizationId!, $status: [PostStatus!], $after: String) {
  posts(input: { organizationId: $orgId, filter: { status: $status } }, after: $after) {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        id text sentAt
        channel { id name }
        metrics { type value }
      }
    }
  }
}"""


def get_buffer_insights(n: int = 10) -> dict:
    """Liest Performance-Daten (Impressions, Reach, Engagement-Rate %, Reactions,
    Kommentare, Shares) der letzten n gesendeten Posts direkt aus der Buffer-
    GraphQL-API (`posts { metrics { type value } }`, live per Introspection
    verifiziert 2026-08-04) - Portierung von _agent/buffer_manager.py's
    insights()-Befehl in den Chat-Tool-Loop, damit der Web-Chat dieselben
    Zahlen sieht wie das CLI-Tool, statt auf Report-Mails angewiesen zu sein."""
    settings = get_settings()
    token = settings.buffer_api_token
    if not token:
        return {"error": "BUFFER_API_TOKEN nicht gesetzt"}

    variables = {"orgId": _INSIGHTS_ORG_ID, "status": ["sent"]}
    try:
        edges = _gql_all_edges(_INSIGHTS_QUERY, variables, token)
    except Exception as exc:
        return {"error": str(exc)}

    posts = sorted((e["node"] for e in edges), key=lambda p: p.get("sentAt") or "", reverse=True)[:n]

    channel_names = {
        settings.buffer_channel_sebastian: "Sebastian",
        settings.buffer_channel_prozessia: "Prozessia",
    }
    result = []
    for p in posts:
        m = {x["type"]: x["value"] for x in (p.get("metrics") or [])}
        result.append({
            "sent_at": p.get("sentAt"),
            "channel": channel_names.get(p["channel"]["id"], p["channel"]["name"]),
            "text_preview": (p.get("text") or "").replace("\n", " ")[:80],
            "impressions": m.get("impressions"),
            "reach": m.get("reach"),
            "engagement_rate": m.get("engagementRate"),
            "reactions": m.get("reactions"),
            "comments": m.get("comments"),
            "shares": m.get("shares"),
        })
    return {"ok": True, "posts": result}


def _format_insights_for_chat(n: int = 10) -> str:
    result = get_buffer_insights(n)
    if not result.get("ok"):
        return f"Fehler beim Abruf der Buffer-Insights: {result.get('error', '?')}"
    posts = result.get("posts", [])
    if not posts:
        return "(keine gesendeten Posts mit Daten gefunden)"
    lines = []
    for p in posts:
        stats = []
        if p.get("impressions") is not None:
            stats.append(f"{p['impressions']:g} Impr.")
        if p.get("reach") is not None:
            stats.append(f"{p['reach']:g} Reach")
        if p.get("engagement_rate") is not None:
            stats.append(f"{p['engagement_rate']:.1f}% Eng.")
        stats.append(f"{p.get('reactions') or 0:g} Reactions")
        if p.get("comments"):
            stats.append(f"{p['comments']:g} Kommentare")
        if p.get("shares"):
            stats.append(f"{p['shares']:g} Shares")
        sent = (p.get("sent_at") or "")[:16].replace("T", " ")
        lines.append(f"- {sent} | {p['channel']} | " + ", ".join(stats) + f" | {p['text_preview']}…")
    return "\n".join(lines)


def insights_text(n: int = 10) -> str:
    return _format_insights_for_chat(n)


_POSTS_QUERY = """
query Posts($orgId: OrganizationId!, $status: [PostStatus!], $after: String) {
  posts(input: { organizationId: $orgId, filter: { status: $status } }, after: $after) {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        id text status dueAt sentAt
        channel { id name }
        assets { __typename }
      }
    }
  }
}"""


def _gql_all_edges(query: str, variables: dict, token: str) -> list:
    """Paginiert eine Buffer posts()-Query komplett durch. Buffer liefert pro
    Aufruf nur eine Seite (beobachtet: 10 Treffer) und zeigt das nur über
    pageInfo.hasNextPage/endCursor an - ohne dieses Nachfassen wurden reale
    Posts jenseits der ersten Seite verschluckt (2026-08-17: 24 echte Drafts
    in Buffer, list_posts/get_buffer_status zeigten nur die ersten 10 -
    Sebastians EU-AI-Act-Draft lag auf Seite 3 und war dadurch unsichtbar,
    inkl. Folgefehler im Karussell-Löschschutz von delete_buffer_post(), der
    auf get_buffer_status() aufbaut)."""
    edges: list = []
    cursor = None
    while True:
        vars_page = dict(variables, after=cursor)
        payload = json.dumps({"query": query, "variables": vars_page}).encode()
        req = urllib.request.Request(
            BUFFER_GRAPHQL, data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        if data.get("errors"):
            raise RuntimeError(data["errors"][0].get("message", "Unbekannter Fehler"))
        page = data.get("data", {}).get("posts", {})
        edges.extend(page.get("edges", []))
        page_info = page.get("pageInfo") or {}
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")
    return edges


def _query_buffer_posts(status: list[str]) -> dict:
    """Live-Query gegen Buffer (nicht die lokale beitraege-*.json) - Portierung
    von _agent/buffer_manager.py's status()/drafts()-Befehlen in den Chat-Tool-
    Loop. list_posts zeigt nur lokal generierte Posts; das hier zeigt den
    tatsächlichen Buffer-Stand, inkl. Posts, die z.B. manuell in Buffer selbst
    angelegt wurden."""
    settings = get_settings()
    token = settings.buffer_api_token
    if not token:
        return {"error": "BUFFER_API_TOKEN nicht gesetzt"}
    variables = {"orgId": _INSIGHTS_ORG_ID, "status": status}
    try:
        edges = _gql_all_edges(_POSTS_QUERY, variables, token)
    except Exception as exc:
        return {"error": str(exc)}

    channel_names = {
        settings.buffer_channel_sebastian: "Sebastian",
        settings.buffer_channel_prozessia: "Prozessia",
    }
    posts = []
    for e in edges:
        n = e["node"]
        posts.append({
            "id": n["id"],
            "status": n.get("status"),
            "due_at": n.get("dueAt"),
            "sent_at": n.get("sentAt"),
            "channel": channel_names.get(n["channel"]["id"], n["channel"]["name"]),
            "text_preview": (n.get("text") or "").replace("\n", " ")[:100],
            "has_media": bool(n.get("assets")),
        })
    posts.sort(key=lambda p: p.get("due_at") or p.get("sent_at") or "")
    return {"ok": True, "posts": posts}


def get_buffer_status() -> dict:
    """Was ist aktuell in Buffer geplant oder als Entwurf? Live-Abfrage,
    Pendant zu `_agent/buffer_manager.py status`."""
    return _query_buffer_posts(["scheduled", "draft"])


def get_buffer_drafts() -> dict:
    """Nur die Buffer-Entwürfe (status draft) - Pendant zu
    `_agent/buffer_manager.py drafts`. Nicht zu verwechseln mit lokal
    geschriebenen, noch nicht gepushten Posts (list_posts)."""
    return _query_buffer_posts(["draft"])


def _format_buffer_posts_for_chat(result: dict) -> str:
    if not result.get("ok"):
        return f"Fehler: {result.get('error', '?')}"
    posts = result.get("posts", [])
    if not posts:
        return "(keine)"
    lines = []
    for p in posts:
        zeitpunkt = (p.get("due_at") or p.get("sent_at") or "")[:16].replace("T", " ")
        lines.append(f"- id={p['id']} | {p['status']} | {zeitpunkt} | {p['channel']} | {p['text_preview']}…")
    return "\n".join(lines)


_IDEAS_QUERY = """
query Ideas($orgId: OrganizationId!) {
  ideas(input: { organizationId: $orgId }) {
    edges {
      node {
        id
        content { title text date }
        createdAt
      }
    }
  }
}"""


def get_buffer_ideas() -> dict:
    """Buffer-eigenes Ideas-Feature (organisationsweit in Buffer gespeicherte
    Content-Ideen) - NICHT dasselbe wie die lokal generierten Ideen aus
    ideen-*.json (list_ideas/generate_ideas). Pendant zu
    `_agent/buffer_manager.py ideas`."""
    settings = get_settings()
    token = settings.buffer_api_token
    if not token:
        return {"error": "BUFFER_API_TOKEN nicht gesetzt"}
    payload = json.dumps({"query": _IDEAS_QUERY, "variables": {"orgId": _INSIGHTS_ORG_ID}}).encode()
    req = urllib.request.Request(
        BUFFER_GRAPHQL, data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        return {"error": str(exc)}
    if data.get("errors"):
        return {"error": data["errors"][0].get("message", "Unbekannter Fehler")}

    edges = data.get("data", {}).get("ideas", {}).get("edges", [])
    ideas = []
    for e in edges:
        n = e["node"]
        c = n.get("content") or {}
        ideas.append({
            "id": n["id"],
            "title": c.get("title") or (c.get("text") or "")[:60],
            "date": c.get("date"),
            "created_at": n.get("createdAt"),
        })
    return {"ok": True, "ideas": ideas}


def _format_buffer_ideas_for_chat(result: dict) -> str:
    if not result.get("ok"):
        return f"Fehler: {result.get('error', '?')}"
    ideas = result.get("ideas", [])
    if not ideas:
        return "(keine)"
    lines = []
    for i in ideas:
        created = datetime.fromtimestamp(i["created_at"]).strftime("%d.%m.") if i.get("created_at") else ""
        lines.append(f"- id={i['id'][:12]}… | {i['title']} | {i.get('date') or f'erstellt {created}'}")
    return "\n".join(lines)


_DELETE_MUTATION = """
mutation DeletePost($id: PostId!) {
  deletePost(input: { id: $id }) {
    ... on DeletePostSuccess { id }
  }
}"""


def delete_buffer_post(buffer_post_id: str, confirm: bool = False) -> dict:
    """Löscht einen Post direkt in Buffer per Buffer-Post-ID (siehe
    get_buffer_status/get_buffer_insights für die IDs) - Pendant zu
    `_agent/buffer_manager.py delete <id>`. Rührt keine lokale
    beitraege-*.json an, da eine gelöschte Buffer-ID nicht mehr zurückverfolgt
    werden muss.

    Echtes Code-Gate für Karussell-Posts (2026-08-13): vorher gab es nur eine
    Text-Warnung im Chat-Prompt ("ACHTUNG KARUSSELL..."), kein technischer
    Schutz - ein Modell, das die Warnung ignorierte, konnte das PDF trotzdem
    unwiderruflich löschen (genau das ist am 12.08.2026 passiert). Ohne
    confirm=True wird ein Post mit Medien (Karussell-Anhang) jetzt gar nicht
    erst gelöscht, sondern die Anfrage mit einer klaren Rückfrage abgelehnt."""
    if not confirm:
        live = get_buffer_status()
        match = next((p for p in live.get("posts", []) if p.get("id") == buffer_post_id), None)
        if match and match.get("has_media"):
            return {
                "error": (
                    f"Post {buffer_post_id} hat ein Karussell-PDF als Anhang - das geht beim Löschen "
                    "unwiderruflich verloren. Nur löschen, wenn Sebastian das für GENAU diesen Post "
                    "ausdrücklich bestätigt hat, dann mit confirm=true erneut aufrufen."
                ),
                "needs_confirmation": True,
            }
    settings = get_settings()
    token = settings.buffer_api_token
    if not token:
        return {"error": "BUFFER_API_TOKEN nicht gesetzt"}
    payload = json.dumps({"query": _DELETE_MUTATION, "variables": {"id": buffer_post_id}}).encode()
    req = urllib.request.Request(
        BUFFER_GRAPHQL, data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        return {"error": str(exc)}
    if data.get("errors"):
        return {"error": data["errors"][0].get("message", "Unbekannter Fehler")}
    r = data.get("data", {}).get("deletePost") or {}
    if r.get("id"):
        cache.invalidate("buffer_status")
        return {"ok": True, "id": r["id"]}
    return {"error": "Löschen fehlgeschlagen (unbekannte Antwort)"}


def reschedule_post(post_id: str, datum: str, uhrzeit: str) -> dict:
    """Verschiebt einen bereits gepushten, lokal gespeicherten Post (per id,
    siehe list_posts) auf einen neuen Termin - sowohl in Buffer
    (buffer_edit_post) als auch lokal (termin-Feld). Für noch nicht gepushte
    Posts stattdessen schedule_post nutzen. Ohne dieses Tool ließ sich der
    Termin eines schon geplanten Posts über den Chat gar nicht mehr ändern -
    revise_post aktualisiert nur den Text, nicht das Datum."""
    post = get_post(post_id)
    if not post:
        return {"error": f"Post {post_id} nicht gefunden"}
    buffer_ids = [b for b in (post.get("buffer_post_ids") or []) if b]
    if not buffer_ids:
        return {"error": "Post ist noch nicht in Buffer eingeplant - schedule_post nutzen, nicht reschedule_post."}
    try:
        scheduled_at = _to_iso_berlin(datum, uhrzeit)
    except Exception:
        return {"error": "Ungültiges Datum/Uhrzeit-Format, bitte YYYY-MM-DD und HH:MM verwenden."}
    result = buffer_edit_post(buffer_ids, post.get("text", ""), due_at=scheduled_at)
    if result.get("ok"):
        _save_post_fields(post_id, termin=scheduled_at)
        cache.invalidate("li_posts")
        cache.invalidate("buffer_status")
    return result


def buffer_edit_post(buffer_post_ids: list[str], text: str, due_at: str | None = None) -> dict:
    """Aktualisiert bereits in Buffer angelegte Posts (per editPost-Mutation)
    - für Textänderungen NACH dem Push, die sonst nur lokal gespeichert
    würden (update_post_text()) und in Buffer unbemerkt veraltet blieben.
    Gleiches Schema wie buffer_push() (Union-Response, PostActionSuccess),
    live per Introspection verifiziert (2026-07-25)."""
    settings = get_settings()
    token = settings.buffer_api_token
    if not token:
        return {"error": "BUFFER_API_TOKEN nicht gesetzt"}

    text = carousel_service._linkedin_bold(text)

    mutation = """
mutation EditPost($input: EditPostInput!) {
  editPost(input: $input) {
    ... on PostActionSuccess {
      post { id status dueAt }
    }
    ... on InvalidInputError { message }
    ... on UnauthorizedError { message }
    ... on NotFoundError { message }
    ... on UnexpectedError { message }
    ... on RestProxyError { message }
    ... on LimitReachedError { message }
  }
}"""
    updated = []
    errors = []
    for post_id in buffer_post_ids:
        if not post_id:
            continue
        variables = {
            "input": {
                "id": post_id,
                "text": text,
                "schedulingType": "automatic",
                **({"mode": "customScheduled", "dueAt": due_at} if due_at else {}),
            }
        }
        payload = json.dumps({"query": mutation, "variables": variables}).encode()
        req = urllib.request.Request(
            BUFFER_GRAPHQL, data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            if data.get("errors"):
                errors.append({"post_id": post_id, "errors": data["errors"]})
                continue
            result = data.get("data", {}).get("editPost") or {}
            post = result.get("post")
            if post and post.get("id"):
                updated.append(post_id)
            else:
                errors.append({"post_id": post_id, "errors": [{"message": result.get("message", "Unbekannte Antwort ohne post/message")}]})
        except Exception as exc:
            errors.append({"post_id": post_id, "error": str(exc)})

    if errors and not updated:
        return {"error": errors}
    return {"ok": True, "updated": updated, "errors": errors or None}
