"""YouTube-Buffer-Bridge. Analog zu linkedin_service.py, aber für Videos statt
Text: NotebookLM-Videos werden hochgeladen, liegen lokal auf dem VPS (nicht
git-getrackt), Claude schreibt Titel/Beschreibung, und der Push nach Buffer
übergibt eine öffentliche URL, unter der Buffer das Video selbst abholt
(Buffer akzeptiert keine Datei-Uploads, siehe developers.buffer.com/guides/hosting-media)."""
import json
import logging
import re
import secrets
import urllib.request
from datetime import datetime
from pathlib import Path

from app.config import get_settings
from app.constants import Models
from app.services.anthropic_client import get_client, get_response_text

logger = logging.getLogger("brain.youtube")

BUFFER_GRAPHQL = "https://api.buffer.com/graphql"
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm"}

CATEGORIES = {
    "27": "Bildung",
    "28": "Wissenschaft & Technik",
    "22": "Blogs & Menschen",
    "26": "How-to & Style",
    "24": "Unterhaltung",
}


def _dir() -> Path:
    d = get_settings().youtube_media_dir
    d.mkdir(parents=True, exist_ok=True)
    return d


def _meta_path(filename: str) -> Path:
    return _dir() / f"{filename}.json"


def _load_meta(filename: str) -> dict:
    p = _meta_path(filename)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_meta(filename: str, meta: dict) -> None:
    _meta_path(filename).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def list_videos() -> dict:
    videos = []
    for f in sorted(_dir().glob("*"), reverse=True):
        if f.suffix.lower() not in VIDEO_EXTS:
            continue
        meta = _load_meta(f.name)
        videos.append({
            "filename": f.name,
            "original_name": meta.get("original_name", f.name),
            "size": f.stat().st_size,
            "uploaded_at": meta.get("uploaded_at", ""),
            "title": meta.get("title", ""),
            "description": meta.get("description", ""),
            "category_id": meta.get("category_id", get_settings().youtube_default_category_id),
            "privacy": meta.get("privacy", "public"),
            "topic": meta.get("topic", ""),
            "pushed": meta.get("pushed", False),
            "post_id": meta.get("post_id"),
            "scheduled_at": meta.get("scheduled_at"),
            "error": meta.get("error"),
        })
    return {"videos": videos, "categories": CATEGORIES}


def save_upload(original_name: str, content: bytes) -> dict:
    suffix = Path(original_name).suffix.lower()
    if suffix not in VIDEO_EXTS:
        return {"error": f"Dateityp nicht unterstützt: {suffix or '(keine Endung)'}"}

    # Unrateliches Token statt Klartextnamen im Dateinamen - die Media-Route ist
    # bewusst unauthenticated (Buffer muss sie ohne Session abrufen können).
    token = secrets.token_urlsafe(12)
    filename = f"{token}{suffix}"
    (_dir() / filename).write_bytes(content)

    meta = {
        "original_name": original_name,
        "uploaded_at": datetime.now().isoformat(),
        "title": "",
        "description": "",
        "category_id": get_settings().youtube_default_category_id,
        "privacy": "public",
        "topic": "",
        "pushed": False,
        "post_id": None,
        "scheduled_at": None,
        "error": None,
    }
    _save_meta(filename, meta)
    return {"ok": True, "filename": filename, **meta}


def update_metadata(filename: str, **fields) -> dict:
    meta = _load_meta(filename)
    if not meta:
        return {"error": "Video nicht gefunden"}
    for key in ("title", "description", "category_id", "privacy", "topic"):
        if key in fields and fields[key] is not None:
            meta[key] = fields[key]
    _save_meta(filename, meta)
    return {"ok": True, **meta}


def delete_video(filename: str) -> dict:
    video_path = _dir() / Path(filename).name
    meta_path = _meta_path(Path(filename).name)
    if not video_path.exists():
        return {"error": "Video nicht gefunden"}
    video_path.unlink(missing_ok=True)
    meta_path.unlink(missing_ok=True)
    return {"ok": True}


def generate_metadata(filename: str, topic: str) -> dict:
    """Claude sieht das Video nicht (nur Text-Input) - schreibt Titel + Beschreibung
    auf Basis von Sebastians Stichpunkten zum NotebookLM-Video."""
    meta = _load_meta(filename)
    if not meta:
        return {"error": "Video nicht gefunden"}
    if not topic.strip():
        return {"error": "Kein Thema/Stichpunkte angegeben"}

    prompt = f"""Du schreibst Titel und Beschreibung für ein YouTube-Video von Prozessia
(KI-Automatisierung für den Mittelstand, Fokus Beschaffung/Produktion, DACH-Zielgruppe:
Einkaufsleiter und Geschäftsführer in produzierenden Betrieben).

Das Video wurde mit NotebookLM erstellt. Stichpunkte/Thema zum Inhalt:
{topic}

Titel: max. 70 Zeichen, konkret, ohne Clickbait, ohne die Wörter innovativ/nachhaltig/ganzheitlich/Lösung/Transformation.
Beschreibung: 3-5 Sätze, was der Zuschauer erfährt, dann ein Call-to-Action zu Prozessia (prozessia.de), am Ende 3-5 relevante Hashtags.

Antworte NUR mit validem JSON: {{"title": "...", "description": "..."}}"""

    try:
        result = get_client().messages.create(
            model=Models.SONNET, max_tokens=1000,
            thinking={"type": "disabled"},
            messages=[{"role": "user", "content": prompt}],
        )
        text = get_response_text(result).strip()
        text_clean = text.replace("```json", "").replace("```", "").strip()
        try:
            data = json.loads(text_clean)
        except Exception:
            match = re.search(r"\{.*\}", text_clean, re.DOTALL)
            if not match:
                logger.error("generate_metadata(): kein JSON in Antwort, erste 500 Zeichen: %s", text[:500])
                return {"error": "Kein JSON in Antwort"}
            data = json.loads(match.group())
        meta["title"] = data.get("title", meta.get("title", ""))
        meta["description"] = data.get("description", meta.get("description", ""))
        meta["topic"] = topic
        _save_meta(filename, meta)
        return {"ok": True, "title": meta["title"], "description": meta["description"]}
    except Exception as e:
        logger.exception("generate_metadata() fehlgeschlagen")
        return {"error": str(e)}


def push_to_buffer(filename: str, scheduled_at: str | None = None) -> dict:
    settings = get_settings()
    token = settings.buffer_api_token
    if not token:
        return {"error": "BUFFER_API_TOKEN nicht gesetzt"}
    channel_id = settings.buffer_channel_youtube
    if not channel_id:
        return {"error": "BUFFER_CHANNEL_YOUTUBE nicht gesetzt - YouTube-Kanal-ID fehlt in der Config"}

    meta = _load_meta(filename)
    if not meta:
        return {"error": "Video nicht gefunden"}
    if not (_dir() / filename).exists():
        return {"error": "Videodatei fehlt auf dem Server"}
    if not meta.get("title", "").strip():
        return {"error": "Kein Titel gesetzt - erst generate_metadata oder manuell eintragen"}

    video_url = f"{settings.public_media_base_url}/api/youtube/media/{filename}"

    # Gleiche Mutation-Form wie linkedin_service.buffer_push()/carousel_service -
    # erprobt und funktionierend, im Gegensatz zur älteren Union-Type-Variante
    # ("... on PostActionSuccess"), die hier nie live getestet wurde.
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
            "text": meta.get("description", ""),
            "schedulingType": "automatic",
            "mode": "customScheduled" if scheduled_at else "addToQueue",
            **({"dueAt": scheduled_at} if scheduled_at else {}),
            "assets": [{"video": {"url": video_url}}],
            "metadata": {
                "youtube": {
                    "title": meta["title"][:100],
                    "categoryId": meta.get("category_id") or settings.youtube_default_category_id,
                    "privacy": meta.get("privacy", "public"),
                }
            },
            "saveToDraft": False,
        }
    }
    payload = json.dumps({"query": mutation, "variables": variables}).encode()
    req = urllib.request.Request(
        BUFFER_GRAPHQL, data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        if data.get("errors"):
            err = data["errors"][0]["message"]
            meta["error"] = err
            _save_meta(filename, meta)
            return {"error": err}
        r = data.get("data", {}).get("createPost", {})
        errs = r.get("userErrors") or []
        post = r.get("post")
        if post:
            meta["pushed"] = True
            meta["post_id"] = post["id"]
            meta["scheduled_at"] = post.get("scheduledAt")
            meta["error"] = None
            _save_meta(filename, meta)
            return {"ok": True, "post_id": post["id"], "status": post.get("status")}
        err = errs[0]["message"] if errs else "Unbekannter Buffer-Fehler"
        meta["error"] = err
        _save_meta(filename, meta)
        return {"error": err}
    except Exception as exc:
        meta["error"] = str(exc)
        _save_meta(filename, meta)
        return {"error": str(exc)}
