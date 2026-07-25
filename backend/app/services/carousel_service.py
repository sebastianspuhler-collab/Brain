"""LinkedIn-Karussell: Slides (Content-Engine) -> KI-Bilder (OpenAI) -> PDF
(PIL) -> Cloudinary -> Buffer Document-Post. Migriert aus
_agent/carousel_push.py — Unterschiede zum Original:
- Content-Engine läuft als eigener Docker-Service (services/content-engine/),
  erreichbar über den internen Docker-DNS-Namen statt localhost:3002; kein
  Subprocess-Start mehr nötig (Container läuft immer).
- Font: DejaVu Sans (per apt im Backend-Image installiert) statt des
  macOS-only /System/Library/Fonts/Helvetica.ttc.
- Credentials kommen aus den zentralen Settings statt aus lokalen .env-Dateien.
- Buffer-Push nutzt dieselbe erprobte Mutation/Antwortform wie
  linkedin_service.buffer_push(), nur mit zusätzlichem document-Asset.
"""
import hashlib
import io
import json
import logging
import time
from datetime import datetime, timedelta

import requests

from app.config import get_settings

logger = logging.getLogger("brain.carousel")

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_PATH_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
BUFFER_GRAPHQL = "https://api.buffer.com/graphql"


def _generate_slides(hook: str, branche: str, saeule: str) -> list:
    settings = get_settings()
    resp = requests.post(
        f"{settings.content_engine_url}/api/karussell/generieren",
        json={"idee": {"hook": hook, "branche": branche, "saeule": saeule}},
        timeout=90,
    )
    resp.raise_for_status()
    return resp.json()["post"]["slides"]


def _logo_path() -> str:
    return str(get_settings().vault_path / "Marketing" / "Branding" / "Logo-removebg-preview.png")


def _render_slides(slides: list, images: list | None = None) -> list:
    """Rendert die Slides im echten Prozessia-Brand-Look (2026-07-25 neu
    gestaltet) - Farben/Typografie 1:1 aus dem Messe-Flyer bzw. der
    tatsächlichen Präsentation Marketing/Präsis/Wissensmanagement_Prozessia.pdf
    übernommen (fast schwarzer Hintergrund, helles Lila #B088FF als Akzent,
    dunkleres Lila #534AB7, dezenter Glow statt generischer KI-Bilder), statt
    der bisherigen, frei erfundenen Navy-Blau/Orange-Palette, die zu Website
    und Präsentationen nicht passte. images-Parameter bleibt aus
    Aufrufer-Kompatibilität erhalten, wird aber nicht mehr genutzt."""
    from PIL import Image, ImageDraw, ImageFont

    SIZE = 1080
    PAD = 80
    BG = (10, 10, 10)
    PURPLE = (83, 74, 183)       # #534AB7 - dunkleres Markenlila
    PURPLE_LIGHT = (176, 136, 255)  # #B088FF - helles Markenlila (Hauptakzent)
    WHITE = (255, 255, 255)
    GRAY = (138, 138, 148)       # entspricht --muted-foreground der Brain-UI

    def fn(size, bold=True):
        try:
            return ImageFont.truetype(FONT_PATH_BOLD if bold else FONT_PATH, size)
        except Exception:
            return ImageFont.load_default()

    def branded_background():
        """Fast schwarzer Hintergrund mit dezentem Lila-Glow unten rechts -
        ruhiger und markenkonformer als ein generisches KI-Bild pro Slide."""
        img = Image.new("RGB", (SIZE, SIZE), BG)
        glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(glow)
        cx, cy, max_r = int(SIZE * 0.86), int(SIZE * 0.88), 520
        steps = 40
        for i in range(steps, 0, -1):
            r = int(max_r * i / steps)
            alpha = int(38 * (1 - i / steps) ** 2)
            gdraw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*PURPLE_LIGHT, alpha))
        img.paste(Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB"))
        return img

    def wrap_draw(draw, text, x, y, font, fill, max_w, gap=10):
        words = str(text).split()
        line = ""
        for word in words:
            test = (line + " " + word).strip()
            w = draw.textbbox((0, 0), test, font=font)[2]
            if w > max_w and line:
                draw.text((x, y), line, font=font, fill=fill)
                y += draw.textbbox((0, 0), line, font=font)[3] + gap
                line = word
            else:
                line = test
        if line:
            draw.text((x, y), line, font=font, fill=fill)
            y += draw.textbbox((0, 0), line, font=font)[3] + gap
        return y

    # Echtes Wordmark (statt gezeichnetem Platzhalter-"P"-Quadrat) einmal
    # geladen und auf Weiß getönt, damit es auf dem dunklen Hintergrund
    # sichtbar ist - Original ist schwarz auf transparent.
    logo_white = None
    try:
        logo_src = Image.open(_logo_path()).convert("RGBA")
        logo_src.thumbnail((280, 90))
        alpha = logo_src.split()[3]
        logo_white = Image.new("RGBA", logo_src.size, (*WHITE, 0))
        logo_white.putalpha(alpha)
    except Exception:
        logger.exception("Logo konnte nicht geladen werden, falle auf Text zurück")

    rendered = []
    total = len(slides)
    for slide in slides:
        img = branded_background()
        draw = ImageDraw.Draw(img)
        max_w = SIZE - PAD * 2

        eyebrow = f"{slide['nummer']:02d} / {total:02d}"
        draw.text((PAD, PAD), eyebrow, font=fn(26), fill=PURPLE_LIGHT)

        y = 300
        y = wrap_draw(draw, slide["titel"], PAD, y, fn(66), WHITE, max_w, gap=16)
        y += 20
        if slide.get("untertitel"):
            y = wrap_draw(draw, slide["untertitel"], PAD, y, fn(34), PURPLE_LIGHT, max_w, gap=10)
            y += 20
        if slide.get("text"):
            wrap_draw(draw, slide["text"], PAD, y, fn(32, bold=False), GRAY, max_w, gap=10)

        by = SIZE - PAD - 40
        if logo_white:
            img.paste(logo_white, (PAD, by - logo_white.height + 40), logo_white)
            draw.text((PAD + logo_white.width + 20, by), "prozessia.de", font=fn(26, bold=False), fill=GRAY)
        else:
            draw.text((PAD, by), "Prozessia. — prozessia.de", font=fn(28), fill=GRAY)

        rendered.append(img)
    return rendered


def _make_pdf(rendered_slides: list) -> bytes:
    buf = io.BytesIO()
    rendered_slides[0].save(
        buf, format="PDF", save_all=True,
        append_images=rendered_slides[1:], resolution=150,
    )
    return buf.getvalue()


def _cloudinary_upload(settings, file_bytes: bytes, resource_type: str, public_id: str, folder: str) -> str:
    ts = str(int(time.time()))
    params = {"folder": folder, "public_id": public_id, "timestamp": ts}
    to_sign = "&".join(f"{k}={v}" for k, v in sorted(params.items())) + settings.cloudinary_api_secret
    sig = hashlib.sha1(to_sign.encode()).hexdigest()

    ext = "pdf" if resource_type == "raw" else "png"
    ct = "application/pdf" if resource_type == "raw" else "image/png"

    resp = requests.post(
        f"https://api.cloudinary.com/v1_1/{settings.cloudinary_cloud_name}/{resource_type}/upload",
        data={**params, "api_key": settings.cloudinary_api_key, "signature": sig},
        files={"file": (f"slide.{ext}", file_bytes, ct)},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["secure_url"]


def _push_carousel_to_buffer(settings, slides: list, pdf_url: str, thumb_url: str, due_at: str) -> list:
    hook = slides[0]["titel"]
    post_text = (
        slides[0]["titel"] + "\n\n"
        + "\n\n".join(
            f"➤ {s['titel']}" + (f"\n{s['text']}" if s.get("text") else "")
            for s in slides[1:]
        )
        + "\n\n#KIAutomatisierung #Einkauf #Mittelstand #Prozessia"
    )
    # Buffer-Schema live per Introspection verifiziert (2026-07-25, siehe
    # linkedin_service.buffer_push()): createPost liefert PostActionPayload,
    # ein UNION aus PostActionSuccess und diversen Fehlertypen - braucht
    # Inline-Fragmente, kein organizationId/content-Wrapper auf
    # CreatePostInput (text ist top-level), mode/schedulingType sind
    # Pflichtfelder, Post hat dueAt statt scheduledAt. Die alte Query
    # validierte serverseitig nie (GRAPHQL_VALIDATION_FAILED, kein "data"-Feld
    # in der Antwort), wurde hier aber mangels Prüfung auf ein oberstes
    # "errors"-Feld fälschlich als Erfolg mit leerer post_id gewertet.
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
    results = []
    for channel_id, channel_name in (
        (settings.buffer_channel_sebastian, "Sebastian"),
        (settings.buffer_channel_prozessia, "Prozessia"),
    ):
        variables = {
            "input": {
                "channelId": channel_id,
                "text": post_text,
                "mode": "customScheduled" if due_at else "addToQueue",
                "schedulingType": "automatic",
                **({"dueAt": due_at} if due_at else {}),
                "assets": [{"document": {"url": pdf_url, "title": hook, "thumbnailUrl": thumb_url}}],
            }
        }
        try:
            resp = requests.post(
                BUFFER_GRAPHQL,
                json={"query": mutation, "variables": variables},
                headers={"Authorization": f"Bearer {settings.buffer_api_token}"},
                timeout=15,
            )
            resp.raise_for_status()
            body = resp.json()
            if body.get("errors"):
                results.append({"ok": False, "channel": channel_name, "error": body["errors"][0].get("message", "?")})
                continue
            data = body.get("data", {}).get("createPost") or {}
            post = data.get("post")
            if post and post.get("id"):
                results.append({"ok": True, "channel": channel_name, "postId": post["id"], "dueAt": post.get("dueAt", "")})
            else:
                results.append({"ok": False, "channel": channel_name, "error": data.get("message", "Unbekannte Antwort ohne post/message")})
        except Exception as exc:
            results.append({"ok": False, "channel": channel_name, "error": str(exc)})
    return results


def _next_carousel_slot(now: datetime | None = None) -> str:
    """Nächster Dienstag oder Freitag 09:30 Uhr Berlin."""
    now = now or datetime.now()
    for d in range(1, 8):
        candidate = (now + timedelta(days=d)).replace(hour=9, minute=30, second=0, microsecond=0)
        if candidate.weekday() in (1, 4):  # Dienstag=1, Freitag=4
            return candidate.strftime("%Y-%m-%dT%H:%M:%S+02:00")
    return (now + timedelta(days=7)).strftime("%Y-%m-%dT09:30:00+02:00")


def generate_carousel(hook: str, branche: str = "Alle", saeule: str = "Wissen",
                       due_at: str | None = None, progress_fn=None) -> dict:
    """Vollständige Karussell-Pipeline: Slides -> KI-Bilder -> PDF -> Cloudinary -> Buffer."""
    settings = get_settings()

    def log(msg: str):
        logger.info(msg)
        if progress_fn:
            try:
                progress_fn(msg)
            except Exception:
                pass

    if not settings.buffer_api_token:
        return {"ok": False, "error": "BUFFER_API_TOKEN nicht gesetzt"}
    if not settings.cloudinary_cloud_name or not settings.cloudinary_api_key or not settings.cloudinary_api_secret:
        return {"ok": False, "error": "Cloudinary-Zugangsdaten (CLOUDINARY_*) nicht vollständig gesetzt"}

    due_at = due_at or _next_carousel_slot()

    try:
        log(f"[1/5] Generiere Slides: \"{hook}\"...")
        slides = _generate_slides(hook, branche, saeule)
        log(f"  {len(slides)} Slides generiert")

        # Kein KI-Bild-Schritt mehr (2026-07-25): generische KI-Hintergrundbilder
        # passten farblich/stilistisch nicht zu Website/Präsentationen. Das
        # gebrandete Design (dunkler Hintergrund, Lila-Glow, echtes Logo) in
        # _render_slides() braucht keine Bilder mehr, kein OpenAI-Aufruf/-Kosten.
        log("[2/5] Rendere Slides im Prozessia-Design (1080x1080)...")
        rendered = _render_slides(slides)

        log("[3/5] Erstelle PDF...")
        pdf_bytes = _make_pdf(rendered)

        log("[4/5] Lade nach Cloudinary hoch...")
        date_slug = due_at[:10].replace("-", "")
        folder = f"carousel/prozessia/{date_slug}"
        thumb_buf = io.BytesIO()
        rendered[0].save(thumb_buf, format="PNG")
        thumb_url = _cloudinary_upload(settings, thumb_buf.getvalue(), "image", f"{date_slug}-thumb", folder)
        pdf_url = _cloudinary_upload(settings, pdf_bytes, "raw", f"{date_slug}-karussell", folder)

        log("[5/5] Pushe nach Buffer...")
        results = _push_carousel_to_buffer(settings, slides, pdf_url, thumb_url, due_at)
        ok_count = sum(1 for r in results if r["ok"])

        return {
            "ok": ok_count > 0,
            "slides": len(slides),
            "slide_titles": [s["titel"] for s in slides],
            "pdf_url": pdf_url,
            "thumb_url": thumb_url,
            "due_at": due_at,
            "buffer": results,
            "anzahl_gepusht": ok_count,
        }
    except Exception as e:
        logger.exception("generate_carousel() fehlgeschlagen")
        return {"ok": False, "error": str(e)}
