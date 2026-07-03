#!/usr/bin/env python3
"""
carousel_push.py — Kompletter Karussell-Pipeline für Prozessia Brain.

Ablauf:
  1. Content Engine (Port 3002) → 7 Slide-Texte via Claude
  2. OpenAI gpt-image-1 → Hintergrundbild pro Slide
  3. PIL → Slides rendern (1080×1080, ExportSlide-Design)
  4. PIL → PDF zusammenführen
  5. Cloudinary → PDF + Thumbnail hochladen
  6. Buffer GraphQL → Document-Post einplanen (beide Kanäle)

Aufruf:
  python3 _agent/carousel_push.py "Hook-Text" "Branche" "Säule" "2026-07-02T09:30:00+02:00"
"""

import sys, json, io, time, hashlib, base64, textwrap, urllib.request
from pathlib import Path
from datetime import datetime

# ── Konfiguration ─────────────────────────────────────────────────────────────

VAULT       = Path.home() / "Documents" / "Prozessia-Brain"
AUTOPOSTER  = VAULT / "_inbox" / "Branding" / "claude-linkedin-auto-poster"
CONTENT_ENG = "http://localhost:3002"
BUFFER_API  = "https://api.buffer.com/graphql"
CHANNELS    = ["6a25d2578f1d11f9b260c5ee", "6a25d2578f1d11f9b260c5ef"]
CHANNEL_NAMES = {"6a25d2578f1d11f9b260c5ee": "Sebastian", "6a25d2578f1d11f9b260c5ef": "Prozessia"}

# ── Credentials laden ─────────────────────────────────────────────────────────

def _load_env():
    env = {}
    for path in [
        AUTOPOSTER / ".env",
        Path.home() / "prozessia-content-engine" / ".env",
    ]:
        if path.exists():
            for line in path.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env.setdefault(k.strip(), v.strip())
    return env

# ── Schritt 1: Slides via Content Engine ─────────────────────────────────────

def generate_slides(hook: str, branche: str = "Alle", saeule: str = "KI-Tipp") -> list:
    payload = json.dumps({"idee": {"hook": hook, "branche": branche, "saeule": saeule}}).encode()
    req = urllib.request.Request(
        f"{CONTENT_ENG}/api/karussell/generieren",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        data = json.loads(r.read())
    return data["post"]["slides"]

# ── Schritt 2: KI-Bilder via OpenAI ─────────────────────────────────────────

def gen_image(openai_key: str, slide_context: str):
    if not openai_key or openai_key.startswith("sk-..."):
        return None
    prompt = (
        "Professional B2B LinkedIn slide background image, dark navy blue gradient "
        "(#0A0F1E to #1E3A5F), no text, minimalist tech illustration, supply chain / KI / "
        "automation theme, abstract geometric shapes, blue (#3B82F6) and orange (#F97316) "
        f"accents, high quality. Context: {slide_context[:120]}"
    )
    payload = json.dumps({
        "model": "gpt-image-1",
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
        "quality": "low",
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/images/generations",
        data=payload,
        headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            result = json.loads(r.read())
        item = result["data"][0]
        if item.get("b64_json"):
            return base64.b64decode(item["b64_json"])
        if item.get("url"):
            with urllib.request.urlopen(item["url"], timeout=30) as r:
                return r.read()
    except Exception as e:
        print(f"  Bild-Fehler: {e}", file=sys.stderr)
    return None

# ── Schritt 3: Slides rendern (ExportSlide-Design) ───────────────────────────

def render_slides(slides: list, images: list) -> list:
    from PIL import Image, ImageDraw, ImageFont

    FONT  = "/System/Library/Fonts/Helvetica.ttc"
    SIZE  = 1080
    PAD   = 80
    BG1   = (10, 15, 30)
    BG2   = (30, 58, 95)
    BLUE  = (59, 130, 246)
    WHITE = (255, 255, 255)
    GRAY  = (148, 163, 184)

    def fn(size):
        try: return ImageFont.truetype(FONT, size)
        except: return ImageFont.load_default()

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

        # Slide-Nummer oben links
        draw.text((PAD, PAD), f"{slide['nummer']}/7", font=fn(24), fill=BLUE)

        # Titel + Untertitel + Text in der Mitte
        y = 320
        y = wrap_draw(draw, slide["titel"], PAD, y, fn(64), WHITE, max_w, gap=14)
        y += 24
        if slide.get("untertitel"):
            y = wrap_draw(draw, slide["untertitel"], PAD, y, fn(36), GRAY, max_w, gap=10)
            y += 24
        if slide.get("text"):
            wrap_draw(draw, slide["text"], PAD, y, fn(32), (220, 225, 235), max_w, gap=10)

        # "P"-Box + prozessia.de unten
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

# ── Schritt 4: PDF erstellen ─────────────────────────────────────────────────

def make_pdf(rendered_slides: list) -> bytes:
    buf = io.BytesIO()
    rendered_slides[0].save(
        buf, format="PDF", save_all=True,
        append_images=rendered_slides[1:], resolution=150,
    )
    return buf.getvalue()

# ── Schritt 5: Cloudinary Upload ─────────────────────────────────────────────

def cloudinary_upload(env: dict, file_bytes: bytes, resource_type: str, public_id: str, folder: str) -> str:
    ts = str(int(time.time()))
    params = {"folder": folder, "public_id": public_id, "timestamp": ts}
    to_sign = "&".join(f"{k}={v}" for k, v in sorted(params.items())) + env["CLOUDINARY_API_SECRET"]
    sig = hashlib.sha1(to_sign.encode()).hexdigest()
    boundary = "PyBnd" + ts
    body = b""

    def field(n, v):
        return f"--{boundary}\r\nContent-Disposition: form-data; name=\"{n}\"\r\n\r\n{v}\r\n".encode()

    def file_part(n, fname, data, ct):
        return f"--{boundary}\r\nContent-Disposition: form-data; name=\"{n}\"; filename=\"{fname}\"\r\nContent-Type: {ct}\r\n\r\n".encode() + data + b"\r\n"

    for k, v in params.items():
        body += field(k, v)
    body += field("api_key", env["CLOUDINARY_API_KEY"])
    body += field("signature", sig)
    ext = "pdf" if resource_type == "raw" else "png"
    ct  = "application/pdf" if resource_type == "raw" else "image/png"
    body += file_part("file", f"slide.{ext}", file_bytes, ct)
    body += f"--{boundary}--\r\n".encode()

    url = f"https://api.cloudinary.com/v1_1/{env['CLOUDINARY_CLOUD_NAME']}/{resource_type}/upload"
    req = urllib.request.Request(url, data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["secure_url"]

# ── Schritt 6: Buffer Push ────────────────────────────────────────────────────

CREATE_MUTATION = """
mutation CreatePost($input: CreatePostInput!) {
  createPost(input: $input) {
    ... on PostActionSuccess { post { id status dueAt } }
    ... on InvalidInputError { message }
    ... on UnauthorizedError { message }
    ... on UnexpectedError   { message }
    ... on LimitReachedError { message }
  }
}"""

def buffer_push(env: dict, slides: list, pdf_url: str, thumb_url: str, due_at: str) -> list:
    hook = slides[0]["titel"]
    post_text = (
        slides[0]["titel"] + "\n\n"
        + "\n\n".join(
            f"➤ {s['titel']}" + (f"\n{s['text']}" if s.get("text") else "")
            for s in slides[1:]
        )
        + "\n\n#KIAutomatisierung #Einkauf #Mittelstand #Prozessia"
    )
    results = []
    for ch in CHANNELS:
        payload = json.dumps({"query": CREATE_MUTATION, "variables": {"input": {
            "channelId": ch,
            "text": post_text,
            "schedulingType": "automatic",
            "mode": "customScheduled",
            "dueAt": due_at,
            "assets": [{"document": {"url": pdf_url, "title": hook, "thumbnailUrl": thumb_url}}],
            "saveToDraft": False,
        }}}).encode()
        req = urllib.request.Request(BUFFER_API, data=payload,
            headers={"Authorization": f"Bearer {env['BUFFER_API_TOKEN']}",
                     "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = json.loads(r.read())
        r_data = resp.get("data", {}).get("createPost", {})
        if "post" in r_data:
            p = r_data["post"]
            results.append({"ok": True, "channel": CHANNEL_NAMES.get(ch, ch),
                            "postId": p["id"], "dueAt": p["dueAt"]})
        else:
            results.append({"ok": False, "channel": CHANNEL_NAMES.get(ch, ch),
                            "error": r_data.get("message", "Unbekannter Fehler")})
    return results

# ── Hauptfunktion ─────────────────────────────────────────────────────────────

def run(hook: str, branche: str = "Alle", saeule: str = "KI-Tipp",
        due_at: str = None, verbose: bool = True, progress_fn=None) -> dict:

    def log(msg):
        if verbose:
            print(msg)
        if progress_fn:
            try:
                progress_fn(msg)
            except Exception:
                pass

    if not due_at:
        from datetime import timedelta
        now = datetime.now()
        for d in range(1, 8):
            candidate = (now + timedelta(days=d)).replace(hour=9, minute=30, second=0, microsecond=0)
            if candidate.weekday() in (1, 4):  # Dienstag=1, Freitag=4
                due_at = candidate.strftime("%Y-%m-%dT%H:%M:%S+02:00")
                break

    env = _load_env()

    # 1. Slides generieren
    log(f"[1/6] Generiere Slides: \"{hook}\"...")
    slides = generate_slides(hook, branche, saeule)
    log(f"  ✓ {len(slides)} Slides")

    # 2. Bilder generieren
    log("[2/6] Generiere KI-Bilder...")
    images = []
    for s in slides:
        ctx = f"{s['titel']} {s.get('text', '')}".strip()[:120]
        img = gen_image(env.get("OPENAI_API_KEY", ""), ctx)
        images.append(img)
        log(f"  Slide {s['nummer']}: {'✓ Bild' if img else '○ Gradient'}")

    # 3. Rendern
    log("[3/6] Rendere Slides (1080×1080)...")
    rendered = render_slides(slides, images)
    log(f"  ✓ {len(rendered)} Slides gerendert")

    # 4. PDF
    log("[4/6] Erstelle PDF...")
    pdf_bytes = make_pdf(rendered)
    log(f"  ✓ {len(pdf_bytes)//1024} KB")

    # 5. Cloudinary
    log("[5/6] Lade nach Cloudinary hoch...")
    date_slug = due_at[:10].replace("-", "")
    folder = f"carousel/prozessia/{date_slug}"
    thumb_buf = io.BytesIO()
    rendered[0].save(thumb_buf, format="PNG")
    thumb_url = cloudinary_upload(env, thumb_buf.getvalue(), "image", f"{date_slug}-thumb", folder)
    pdf_url   = cloudinary_upload(env, pdf_bytes, "raw", f"{date_slug}-karussell", folder)
    log(f"  ✓ PDF: {pdf_url}")

    # 6. Buffer
    log("[6/6] Pushe nach Buffer...")
    results = buffer_push(env, slides, pdf_url, thumb_url, due_at)
    for r in results:
        if r["ok"]:
            log(f"  ✓ {r['channel']} → {r['postId']}")
        else:
            log(f"  ✗ {r['channel']}: {r['error']}")

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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 carousel_push.py \"Hook-Text\" [Branche] [Säule] [DueAt]")
        sys.exit(1)
    hook    = sys.argv[1]
    branche = sys.argv[2] if len(sys.argv) > 2 else "Alle"
    saeule  = sys.argv[3] if len(sys.argv) > 3 else "KI-Tipp"
    due_at  = sys.argv[4] if len(sys.argv) > 4 else None
    result  = run(hook, branche, saeule, due_at)
    print(json.dumps(result, ensure_ascii=False, indent=2))
