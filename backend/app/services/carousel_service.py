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


def _generate_image(openai_key: str, slide_context: str) -> bytes | None:
    if not openai_key:
        return None
    prompt = (
        "Professional B2B LinkedIn slide background image, dark navy blue gradient "
        "(#0A0F1E to #1E3A5F), no text, minimalist tech illustration, supply chain / KI / "
        "automation theme, abstract geometric shapes, blue (#3B82F6) and orange (#F97316) "
        f"accents, high quality. Context: {slide_context[:120]}"
    )
    try:
        resp = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {openai_key}"},
            json={"model": "gpt-image-1", "prompt": prompt, "n": 1, "size": "1024x1024", "quality": "low"},
            timeout=60,
        )
        resp.raise_for_status()
        item = resp.json()["data"][0]
        if item.get("b64_json"):
            import base64
            return base64.b64decode(item["b64_json"])
        if item.get("url"):
            img_resp = requests.get(item["url"], timeout=30)
            img_resp.raise_for_status()
            return img_resp.content
    except Exception:
        logger.exception("Karussell-Bildgenerierung fehlgeschlagen")
    return None


def _render_slides(slides: list, images: list) -> list:
    from PIL import Image, ImageDraw, ImageFont

    SIZE = 1080
    PAD = 80
    BG1 = (10, 15, 30)
    BG2 = (30, 58, 95)
    BLUE = (59, 130, 246)
    WHITE = (255, 255, 255)
    GRAY = (148, 163, 184)

    def fn(size):
        try:
            return ImageFont.truetype(FONT_PATH, size)
        except Exception:
            return ImageFont.load_default()

    def gradient():
        img = Image.new("RGB", (SIZE, SIZE), BG1)
        draw = ImageDraw.Draw(img)
        steps = 60
        for i in range(steps):
            t = i / steps
            c = tuple(int(BG1[j] + (BG2[j] - BG1[j]) * t) for j in range(3))
            y0 = int(SIZE * i / steps)
            y1 = int(SIZE * (i + 1) / steps)
            draw.rectangle([(0, y0), (SIZE, y1)], fill=c)
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

    rendered = []
    for i, slide in enumerate(slides):
        img_bytes = images[i] if i < len(images) else None
        if img_bytes:
            bg = Image.open(io.BytesIO(img_bytes)).resize((SIZE, SIZE))
            overlay = Image.new("RGBA", (SIZE, SIZE), (10, 15, 30, int(0.75 * 255)))
            base = bg.convert("RGBA")
            base.paste(overlay, mask=overlay.split()[3])
            img = base.convert("RGB")
        else:
            img = gradient()

        draw = ImageDraw.Draw(img)
        max_w = SIZE - PAD * 2

        draw.text((PAD, PAD), f"{slide['nummer']}/7", font=fn(24), fill=BLUE)

        y = 320
        y = wrap_draw(draw, slide["titel"], PAD, y, fn(64), WHITE, max_w, gap=14)
        y += 24
        if slide.get("untertitel"):
            y = wrap_draw(draw, slide["untertitel"], PAD, y, fn(36), GRAY, max_w, gap=10)
            y += 24
        if slide.get("text"):
            wrap_draw(draw, slide["text"], PAD, y, fn(32), (220, 225, 235), max_w, gap=10)

        by = SIZE - PAD - 48
        draw.rounded_rectangle([(PAD, by), (PAD + 48, by + 48)], radius=8, fill=BLUE)
        pbbox = draw.textbbox((0, 0), "P", font=fn(24))
        draw.text(
            (PAD + (48 - pbbox[2]) // 2, by + (48 - pbbox[3]) // 2),
            "P", font=fn(24), fill=WHITE,
        )
        draw.text((PAD + 64, by + 10), "prozessia.de", font=fn(28), fill=GRAY)

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
    mutation = """
mutation CreatePost($input: CreatePostInput!) {
  createPost(input: $input) {
    post { id status scheduledAt }
    userErrors { message }
  }
}"""
    results = []
    for channel_id, channel_name in (
        (settings.buffer_channel_sebastian, "Sebastian"),
        (settings.buffer_channel_prozessia, "Prozessia"),
    ):
        variables = {
            "input": {
                "organizationId": "6a15c3685a233c9c16251245",
                "channelId": channel_id,
                "content": {"text": post_text},
                "dueAt": due_at,
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
            data = resp.json().get("data", {}).get("createPost", {})
            errs = data.get("userErrors", [])
            if errs:
                results.append({"ok": False, "channel": channel_name, "error": errs[0].get("message", "?")})
            else:
                post = data.get("post", {})
                results.append({"ok": True, "channel": channel_name, "postId": post.get("id", ""), "dueAt": post.get("scheduledAt", "")})
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
        log(f"[1/6] Generiere Slides: \"{hook}\"...")
        slides = _generate_slides(hook, branche, saeule)
        log(f"  {len(slides)} Slides generiert")

        log("[2/6] Generiere KI-Bilder...")
        images = []
        for s in slides:
            ctx = f"{s['titel']} {s.get('text', '')}".strip()[:120]
            img = _generate_image(settings.openai_api_key, ctx)
            images.append(img)

        log("[3/6] Rendere Slides (1080x1080)...")
        rendered = _render_slides(slides, images)

        log("[4/6] Erstelle PDF...")
        pdf_bytes = _make_pdf(rendered)

        log("[5/6] Lade nach Cloudinary hoch...")
        date_slug = due_at[:10].replace("-", "")
        folder = f"carousel/prozessia/{date_slug}"
        thumb_buf = io.BytesIO()
        rendered[0].save(thumb_buf, format="PNG")
        thumb_url = _cloudinary_upload(settings, thumb_buf.getvalue(), "image", f"{date_slug}-thumb", folder)
        pdf_url = _cloudinary_upload(settings, pdf_bytes, "raw", f"{date_slug}-karussell", folder)

        log("[6/6] Pushe nach Buffer...")
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
