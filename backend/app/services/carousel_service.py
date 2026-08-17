"""LinkedIn-Karussell: Slides (Content-Engine) -> gebrandetes PDF (PIL) ->
Cloudinary -> Buffer Document-Post. Migriert aus _agent/carousel_push.py —
Unterschiede zum Original:
- Content-Engine läuft als eigener Docker-Service (services/content-engine/),
  erreichbar über den internen Docker-DNS-Namen statt localhost:3002; kein
  Subprocess-Start mehr nötig (Container läuft immer).
- Credentials kommen aus den zentralen Settings statt aus lokalen .env-Dateien.
- Buffer-Push nutzt dieselbe erprobte Mutation/Antwortform wie
  linkedin_service.buffer_push(), nur mit zusätzlichem document-Asset.

Design (2026-08-11, dritte Iteration): Umbau auf die Karussell-Strategie in
Marketing/LinkedIn/STRATEGIE.md, Abschnitt 6. Vorbild sind die Karussells von
Wolfgang Lang (GuidedBuying.com), Referenzbilder in Marketing/LinkedIn/
"Neuer Ordner". Von dort 1:1 übernommen:
- ein EINZIGES Hintergrundfoto über alle Slides hinweg (nicht pro Slide ein
  eigenes — Lang nutzt durchgehend dasselbe Bild, das hält die Serie ruhig und
  spart 6 von 7 Bildgenerierungen),
- darüber ein flächiger, halbtransparenter Wash, der das Foto nur noch als
  Textur durchscheinen lässt,
- Logo oben links, Fließtext links ausgerichtet mit großzügiger Zeilenhöhe,
  fett hervorgehobene Kernbegriffe/Zahlen mitten im Satz,
- schmale, rotierte Domain-Signatur unten links.
Geändert wurde nur die Farblogik (Lang: Hellblau): schwarzer oder weißer
Hintergrund je Serie, Schrift in der Gegenfarbe, Lila (#534AB7–#B088FF) nur als
sparsamer Akzent (Regel-Strich, Seitenzähler, Kernzahl) — deutlich unter den
in der Strategie erlaubten 10–15 % Bildfläche.
Typografie: Poppins (Bold für Headlines, Light/SemiBold für Fließtext) aus
Marketing/Branding/fonts/. Der Vault ist in den Container gemountet, die Fonts
brauchen also keinen Docker-Rebuild. Fällt auf DejaVu zurück, falls sie fehlen.
Headline-Gewicht 2026-08-13 von Black auf Bold reduziert (Black wirkte gegen
das Referenz-Banner spürbar zu fett/aufgeblasen).

Farb-Update (2026-08-11, vierte Iteration): Lila, Weiß und Schwarzton 1:1 aus dem
finalen LinkedIn-Banner (Marketing/LinkedIn/Neuer Ordner/) gemessen (Pixel-Sampling
der Headline "Fortschritt durch sichere KI."), statt der bis dahin generischen
Tailwind-Violet-Töne. #B088FF/#534AB7 sind identisch mit C_PURPLE_LIGHT/C_PURPLE aus
frontend/src/index.css — die Karussell-Farben sind damit erstmals pixelgenau mit dem
Rest der Marke UND dem Banner konsistent, nicht nur "im erlaubten Bereich".
Das Foto-Fallback (_accent_glow, greift nur wenn kein Hintergrundfoto generiert werden
konnte) rotiert jetzt über vier Positionsvarianten statt immer denselben Verlauf zu
zeichnen — sonst sähen alle Karussells ohne Foto identisch aus.
"""
import hashlib
import io
import json
import logging
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

from app.config import get_settings

logger = logging.getLogger("brain.carousel")

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_PATH_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
BUFFER_GRAPHQL = "https://api.buffer.com/graphql"

SIZE = 1080
PAD = 76

# Markenlila laut Strategie §7 — nur als Akzent, nie als Fläche. Exakt aus dem
# finalen Banner gemessen, identisch zu C_PURPLE_LIGHT/C_PURPLE in
# frontend/src/index.css.
PURPLE = (176, 136, 255)      # #B088FF
PURPLE_DEEP = (83, 74, 183)   # #534AB7

# Zwei Serien-Varianten (Strategie §6: "pro Post-Serie konsistent wählbar").
# wash_alpha steuert, wie stark das Hintergrundfoto durchscheint.
VARIANTEN = {
    "schwarz": {
        "base": (10, 10, 10),       # #0A0A0A — exakt der Schwarzton aus dem Banner
        "text": (255, 255, 255),
        "muted": (185, 184, 190),   # exakt aus der Banner-Unterzeile gemessen
        "wash_alpha": 0.82,
        "logo": "Logo-removebg-preview.png",
        # Helle Logo-Variante: cremefarben mit fertigem Alpha-Kanal. Kein
        # Weiß-Keying — die Wortmarke selbst liegt nahe an Weiß und würde
        # dabei ausradiert.
        "logo_key_white": False,
    },
    "weiss": {
        "base": (255, 255, 255),
        "text": (12, 12, 14),
        "muted": (92, 92, 104),
        "wash_alpha": 0.88,
        "logo": "Logo_converted.png",
        # Dunkle Logo-Variante: schwarz auf weißer Fläche, ohne Alpha.
        "logo_key_white": True,
    },
}
DEFAULT_VARIANTE = "schwarz"


def _brand_dir() -> Path:
    return get_settings().vault_path / "Marketing" / "Branding"


def _font(size: int, weight: str = "regular"):
    """Poppins aus dem Vault, sonst DejaVu. Poppins Black ist der in der
    Marken-Identität (Strategie §7) festgelegte Headline-Schnitt: fette,
    rundliche Display-Grotesk, normale Groß-/Kleinschreibung."""
    from PIL import ImageFont

    files = {
        "black": "Poppins-Black.ttf",
        "bold": "Poppins-Bold.ttf",
        "semibold": "Poppins-SemiBold.ttf",
        "regular": "Poppins-Regular.ttf",
        "light": "Poppins-Light.ttf",
    }
    candidate = _brand_dir() / "fonts" / files.get(weight, files["regular"])
    if candidate.exists():
        try:
            return ImageFont.truetype(str(candidate), size)
        except Exception:
            logger.warning("Poppins-Font %s nicht ladbar, nutze DejaVu", candidate)
    fallback = FONT_PATH_BOLD if weight in ("black", "bold", "semibold") else FONT_PATH
    try:
        return ImageFont.truetype(fallback, size)
    except Exception:
        return ImageFont.load_default()


def _tokenize_rich(text: str) -> list:
    """Zerlegt Text mit **fett**-Markierungen in (Wort, ist_fett)-Paare.
    Die Content-Engine markiert damit Kernbegriffe und Zahlen mitten im Satz —
    genau das Muster aus dem Vorbild-Karussell ("Rund **80 Prozent aller
    Beschaffungstransaktionen** entfallen auf...")."""
    runs = []
    for i, segment in enumerate(re.split(r"\*\*", str(text))):
        bold = i % 2 == 1
        for word in segment.split():
            runs.append((word, bold))
    return runs


def _layout_rich(draw, runs, max_w, font_regular, font_bold):
    """Bricht (Wort, fett)-Runs auf max_w um. Gibt Zeilen als Listen von
    (Wort, Font) zurück, damit Fett-Passagen mitten in der Zeile stehen können —
    ein reiner Zeilenumbruch pro Font ginge dafür nicht."""
    space_w = draw.textlength(" ", font=font_regular)
    lines, current, current_w = [], [], 0.0
    for word, bold in runs:
        font = font_bold if bold else font_regular
        w = draw.textlength(word, font=font)
        extra = w if not current else space_w + w
        if current and current_w + extra > max_w:
            lines.append(current)
            current, current_w = [(word, font)], w
        else:
            current.append((word, font))
            current_w += extra
    if current:
        lines.append(current)
    return lines


def _draw_rich(draw, lines, x, y, fill, line_height, space_w):
    for line in lines:
        cursor = x
        for word, font in line:
            draw.text((cursor, y), word, font=font, fill=fill)
            cursor += draw.textlength(word, font=font) + space_w
        y += line_height
    return y


def _fit_headline(draw, text, max_w, max_lines, start_size, min_size):
    """Verkleinert die Headline schrittweise, bis sie in max_lines passt.
    Ohne das reißt eine lange Slide-Überschrift das Layout auf oder läuft aus
    dem Bild — die Slide-Titel kommen aus einem Sprachmodell, ihre Länge ist
    also nicht garantiert.

    Gewicht "bold", nicht "black" (2026-08-13, zweiter Anlauf): Poppins Black
    wirkte gegen das Referenz-Banner (Marketing/Branding/
    Gemini_Generated_Image_z5n18vz5n18vz5n1.png) zu fett/aufgeblasen - auch mit
    zusätzlichem Stroke (verworfen). Sebastian direkt: "das banner hat ja
    dünner schrift". Poppins Bold liegt sichtbar näher an der Banner-Schriftstärke."""
    size = start_size
    while size > min_size:
        font = _font(size, "bold")
        lines = _layout_rich(draw, _tokenize_rich(text), max_w, font, font)
        if len(lines) <= max_lines:
            return font, lines
        size -= 4
    font = _font(min_size, "bold")
    return font, _layout_rich(draw, _tokenize_rich(text), max_w, font, font)


def _load_logo(variante: dict, target_h: int):
    """Lädt das echte Logo-File (Strategie §6: "eigenes Logo-File als Referenz
    nutzen, nicht neu generieren"). Die dunkle Variante liegt als Schwarz-auf-
    Weiß-PNG ohne Alpha vor, dort wird Weiß zu Transparenz gekeyt.
    Gibt None zurück, wenn das File fehlt — dann zeichnet _draw_logo() die
    Wortmarke als Text. Relevant, weil *.png im Vault-Repo gitignored ist und
    das File auf dem VPS fehlen kann."""
    from PIL import Image

    path = _brand_dir() / variante["logo"]
    if not path.exists():
        return None
    try:
        logo = Image.open(path).convert("RGBA")
        if variante.get("logo_key_white"):
            pixels = logo.load()
            for px in range(logo.width):
                for py in range(logo.height):
                    r, g, b, a = pixels[px, py]
                    if r > 244 and g > 244 and b > 244:
                        pixels[px, py] = (r, g, b, 0)
        logo = logo.crop(logo.getbbox() or (0, 0, logo.width, logo.height))
        ratio = target_h / logo.height
        return logo.resize((max(1, int(logo.width * ratio)), target_h), Image.LANCZOS)
    except Exception:
        logger.exception("Logo konnte nicht geladen werden: %s", path)
        return None


def _draw_logo(img, draw, variante: dict, logo):
    """Logo oben links (Strategie §6). Fallback ist die Wortmarke als Text in
    Poppins Black — dieselbe geometrische Grotesk wie im Original-Logo."""
    if logo is not None:
        img.paste(logo, (PAD, PAD), logo)
        return
    font = _font(44, "black")
    draw.text((PAD, PAD), "Prozessia.", font=font, fill=variante["text"])
    sub = _font(15, "semibold")
    draw.text((PAD + 3, PAD + 52), "A I   A G E N C Y", font=sub, fill=variante["muted"])


# Vier Positionen für den Lila-Schimmer im Foto-Fallback (siehe _accent_glow).
# Ohne Rotation sah jedes Karussell ohne generiertes Hintergrundfoto exakt
# gleich aus (immer derselbe Verlauf unten rechts) — das hier gibt sichtbar
# unterschiedliche Ergebnisse, ausgewählt über einen stabilen Hash des Themas,
# statt einer festen Position oder echtem Zufall (reproduzierbar bei erneutem
# Rendern desselben Themas).
GLOW_POSITIONS = [
    ((0.55, 0.62), (1.25, 1.32)),    # unten rechts (Original)
    ((-0.25, 0.60), (0.45, 1.30)),   # unten links
    ((0.55, -0.32), (1.25, 0.38)),   # oben rechts
    ((-0.25, -0.32), (0.45, 0.38)),  # oben links
]


def _background(variante: dict, photo_bytes: bytes | None, seed: str = ""):
    """Hintergrundfoto unter flächigem Wash — die Optik des Vorbilds, nur in
    Schwarz bzw. Weiß statt Langs Hellblau. Ohne Foto bleibt eine ruhige
    Fläche mit dezentem Lila-Verlauf, dessen Position über `seed` rotiert."""
    from PIL import Image

    base = Image.new("RGB", (SIZE, SIZE), variante["base"])
    if not photo_bytes:
        return _accent_glow(base, variante, seed)
    try:
        photo = Image.open(io.BytesIO(photo_bytes)).convert("RGB").resize((SIZE, SIZE), Image.LANCZOS)
    except Exception:
        logger.exception("Hintergrundfoto nicht lesbar")
        return _accent_glow(base, variante, seed)
    wash = Image.new("RGBA", (SIZE, SIZE), (*variante["base"], int(variante["wash_alpha"] * 255)))
    canvas = photo.convert("RGBA")
    canvas.alpha_composite(wash)
    return canvas.convert("RGB")


def _accent_glow(base, variante: dict, seed: str = ""):
    """Dezenter Lila-Schimmer als Ersatz für das Foto, Position rotiert über
    GLOW_POSITIONS (siehe dort). Bewusst schwach — Lila ist laut Strategie
    Akzent, nicht Fläche."""
    from PIL import Image, ImageDraw, ImageFilter

    idx = int(hashlib.sha1(seed.encode()).hexdigest(), 16) % len(GLOW_POSITIONS) if seed else 0
    (x0, y0), (x1, y1) = GLOW_POSITIONS[idx]

    glow = Image.new("RGB", (SIZE, SIZE), variante["base"])
    ImageDraw.Draw(glow).ellipse(
        [(SIZE * x0, SIZE * y0), (SIZE * x1, SIZE * y1)], fill=PURPLE_DEEP
    )
    glow = glow.filter(ImageFilter.GaussianBlur(180))
    return Image.blend(base, glow, 0.30)


def _render_slides(slides: list, photo_bytes: bytes | None = None, variante_name: str = DEFAULT_VARIANTE, seed: str = "") -> list:
    """Rendert alle Slides im Prozessia-Karussell-Design (Strategie §6).
    Aufbau je Slide: Logo oben links, Seitenzähler oben rechts, Lila-Regel,
    Headline, Fließtext mit Fett-Hervorhebungen, rotierte Domain unten links."""
    from PIL import ImageDraw

    variante = VARIANTEN.get(variante_name, VARIANTEN[DEFAULT_VARIANTE])
    background = _background(variante, photo_bytes, seed)
    logo = _load_logo(variante, target_h=54)
    max_w = SIZE - PAD * 2
    total = len(slides)

    rendered = []
    for i, slide in enumerate(slides):
        img = background.copy()
        draw = ImageDraw.Draw(img)

        _draw_logo(img, draw, variante, logo)

        # Seitenzähler oben rechts. Im Vorbild blendet LinkedIn "X Seiten"
        # selbst über Dokument-Posts ein — das steht nicht im Bild. Hier
        # trotzdem als eigener Zähler, damit die Seitenzahl auch im PDF und in
        # der Zweitverwertung sichtbar bleibt.
        counter = f"{i + 1} / {total}"
        counter_font = _font(24, "semibold")
        counter_w = draw.textlength(counter, font=counter_font)
        draw.text((SIZE - PAD - counter_w, PAD + 14), counter, font=counter_font, fill=PURPLE)

        y = 300
        # Lila-Regel über der Headline: der einzige feste Farbakzent pro Slide.
        draw.rectangle([(PAD, y - 34), (PAD + 88, y - 27)], fill=PURPLE)

        headline_font, headline_lines = _fit_headline(
            draw, slide.get("titel", ""), max_w, max_lines=3, start_size=78, min_size=44
        )
        space_w = draw.textlength(" ", font=headline_font)
        y = _draw_rich(
            draw, headline_lines, PAD, y, variante["text"],
            line_height=int(headline_font.size * 1.16), space_w=space_w,
        )

        if slide.get("untertitel"):
            y += 26
            sub_font = _font(34, "semibold")
            sub_lines = _layout_rich(draw, _tokenize_rich(slide["untertitel"]), max_w, sub_font, sub_font)
            y = _draw_rich(
                draw, sub_lines, PAD, y, PURPLE,
                line_height=int(sub_font.size * 1.38), space_w=draw.textlength(" ", font=sub_font),
            )

        if slide.get("text"):
            y += 34
            body_font = _font(36, "light")
            body_bold = _font(36, "semibold")
            body_space = draw.textlength(" ", font=body_font)
            line_height = int(body_font.size * 1.52)
            # Absätze getrennt umbrechen, damit "\n\n" im Slide-Text erhalten
            # bleibt statt zu einem Block zusammenzulaufen.
            for paragraph in [p for p in str(slide["text"]).split("\n\n") if p.strip()]:
                lines = _layout_rich(draw, _tokenize_rich(paragraph), max_w, body_font, body_bold)
                y = _draw_rich(draw, lines, PAD, y, variante["text"], line_height, body_space)
                y += 26

        _draw_signature(img, draw, variante)
        rendered.append(img)
    return rendered


def _draw_signature(img, draw, variante: dict):
    """Rotierte Domain-Signatur unten links — Detail aus dem Vorbild
    (dort "©guidedbuying.com" vertikal am linken Rand)."""
    from PIL import Image, ImageDraw

    text = "prozessia.de"
    font = _font(20, "regular")
    tmp = Image.new("RGBA", (280, 40), (0, 0, 0, 0))
    ImageDraw.Draw(tmp).text((0, 0), text, font=font, fill=(*variante["muted"], 255))
    tmp = tmp.crop(tmp.getbbox() or (0, 0, 280, 40)).rotate(90, expand=True)
    img.paste(tmp, (PAD - 46, SIZE - PAD - tmp.height), tmp)


def _generate_photo(openai_key: str, thema: str, variante_name: str) -> bytes | None:
    """EIN Hintergrundfoto für das gesamte Karussell (siehe Modul-Docstring).
    Motivwelt ist die Fertigungs-Nische der Zielgruppe — Werkzeugbau,
    Lohnfertigung, Metallbau —, nicht generische Tech-Grafik: die Nische ist
    laut Strategie §1 das Kernargument der Positionierung und soll auch im
    Bild spürbar sein. Bewusst monochrom und unscharf, weil das Bild unter dem
    Wash ohnehin nur noch Textur ist."""
    if not openai_key:
        return None
    tonung = "cool near-black monochrome" if variante_name == "schwarz" else "bright airy high-key monochrome"
    prompt = (
        f"Documentary photograph, {tonung}, shallow depth of field, softly out of focus. "
        "German mid-sized precision manufacturing workshop: CNC machining, tool and die making, "
        "sheet metal fabrication, workbenches, technical drawings. No text, no logos, no faces in focus. "
        f"Calm, premium, understated industrial atmosphere. Context: {thema[:120]}"
    )
    try:
        resp = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {openai_key}"},
            json={"model": "gpt-image-1", "prompt": prompt, "n": 1, "size": "1024x1024", "quality": "medium"},
            timeout=90,
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
        logger.exception("Karussell-Hintergrundbild fehlgeschlagen")
    return None


def _generate_slides(hook: str, branche: str, saeule: str) -> tuple[list, str]:
    """Holt Slides UND Begleittext von der Content-Engine. Der Begleittext folgt
    der Caption-Struktur aus Strategie §4 und wird dort mitgeneriert, statt hier
    aus Slide-Titeln zusammengesetzt zu werden."""
    settings = get_settings()
    resp = requests.post(
        f"{settings.content_engine_url}/api/karussell/generieren",
        json={"idee": {"hook": hook, "branche": branche, "saeule": saeule}},
        timeout=120,
    )
    resp.raise_for_status()
    post = resp.json()["post"]
    return post["slides"], (post.get("caption") or "").strip()


def _fallback_caption(slides: list) -> str:
    """Notfall-Begleittext, falls die Content-Engine keine Caption liefert.
    Bewusst knapp und ohne erfundene Zahlen — die gehören laut Strategie §3 in
    den generierten Text, nicht in einen mechanischen Zusammenbau.

    Die frühere statische Zeile "Das ganze Karussell im Dokument oben." wurde
    entfernt (Sebastian, 2026-08-17) - sie stand als reiner Lückenfüller in
    jedem Fallback-Post und wirkte generisch/unpersönlich, unabhängig vom
    eigentlichen Inhalt."""
    blocks = []
    for s in slides[1:-1][:3]:
        block = s.get("titel", "")
        if s.get("text"):
            block += "\n" + s["text"].replace("**", "")
        blocks.append(block)
    kern = "\n\n".join(blocks)
    return f"{slides[0].get('titel', '')}\n\n{kern}\n\n#Beschaffung #Werkzeugbau #KI"


def _linkedin_bold(text: str) -> str:
    """Wandelt **fett**-Markierungen in Unicode-Fettbuchstaben um.

    LinkedIn-Beiträge sind reiner Text ohne Markdown - die in Strategie §4
    geforderte "fett hervorgehobene Ergebnis-Zeile" geht dort nur über
    Unicode-Sans-Bold. Ohne diese Umwandlung stünden im Post sichtbare
    Sternchen. Bewusst nur auf die Ergebnis-Zeile angewandt (die Content-Engine
    markiert auch nur diese): Unicode-Bold ist für Screenreader schlecht
    lesbar und in der LinkedIn-Suche nicht auffindbar, taugt also nur als
    sparsames Stilmittel.
    Umlaute und ß haben keine Unicode-Bold-Entsprechung und bleiben unverändert.
    """
    def convert(match):
        out = []
        for ch in match.group(1):
            if "A" <= ch <= "Z":
                out.append(chr(0x1D5D4 + ord(ch) - ord("A")))
            elif "a" <= ch <= "z":
                out.append(chr(0x1D5EE + ord(ch) - ord("a")))
            elif "0" <= ch <= "9":
                out.append(chr(0x1D7EC + ord(ch) - ord("0")))
            else:
                out.append(ch)
        return "".join(out)

    return re.sub(r"\*\*(.+?)\*\*", convert, text, flags=re.DOTALL)


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


def _push_carousel_to_buffer(
    settings, slides: list, caption: str, pdf_url: str, thumb_url: str, due_at: str, draft: bool = False,
) -> list:
    hook = slides[0]["titel"]
    post_text = _linkedin_bold(caption or _fallback_caption(slides))
    # Buffer-Schema live per Introspection verifiziert (2026-07-25, siehe
    # linkedin_service.buffer_push()): createPost liefert PostActionPayload,
    # ein UNION aus PostActionSuccess und diversen Fehlertypen - braucht
    # Inline-Fragmente, kein organizationId/content-Wrapper auf
    # CreatePostInput (text ist top-level), mode/schedulingType sind
    # Pflichtfelder, Post hat dueAt statt scheduledAt. Die alte Query
    # validierte serverseitig nie (GRAPHQL_VALIDATION_FAILED, kein "data"-Feld
    # in der Antwort), wurde hier aber mangels Prüfung auf ein oberstes
    # "errors"-Feld fälschlich als Erfolg mit leerer post_id gewertet.
    #
    # draft (2026-08-11, für Testläufe): saveToDraft=true - live per
    # Introspection auf CreatePostInput bestätigtes Feld ("If true, saves the
    # post as a draft instead of scheduling it. Post status will be 'draft'
    # ... will not be published until explicitly scheduled"). Damit landet ein
    # Testkarussell sichtbar in Buffer, ohne je automatisch zu veröffentlichen
    # - mode/schedulingType bleiben Pflichtfelder, ihr Wert ist bei
    # saveToDraft=true aber irrelevant (kein Scheduling findet statt).
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
                **({"dueAt": due_at} if due_at and not draft else {}),
                **({"saveToDraft": True} if draft else {}),
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
    """Nächster Dienstag oder Donnerstag 09:30 Uhr Berlin. Freitag ist laut der
    Format-Recherche in Marketing/LinkedIn/2026-08-04-Content-Recherche-
    Strategie.md leicht unterdurchschnittlich."""
    now = now or datetime.now()
    for d in range(1, 8):
        candidate = (now + timedelta(days=d)).replace(hour=9, minute=30, second=0, microsecond=0)
        if candidate.weekday() in (1, 3):  # Dienstag=1, Donnerstag=3
            return candidate.strftime("%Y-%m-%dT%H:%M:%S+02:00")
    return (now + timedelta(days=7)).strftime("%Y-%m-%dT09:30:00+02:00")


def generate_carousel(hook: str, branche: str = "Alle", saeule: str = "Einkauf",
                       due_at: str | None = None, variante: str = DEFAULT_VARIANTE,
                       draft: bool = False, progress_fn=None) -> dict:
    """Vollständige Karussell-Pipeline: Slides + Caption -> ein Hintergrundfoto
    -> Rendering -> PDF -> Cloudinary -> Buffer.

    draft=True (2026-08-11, für Testläufe/Review): landet über Buffers
    saveToDraft-Feld als echter Entwurf (Status "draft"), wird NIE automatisch
    veröffentlicht - sichtbar in Buffer, aber ungefährlich."""
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
    variante = variante if variante in VARIANTEN else DEFAULT_VARIANTE

    try:
        log(f"[1/6] Generiere Slides + Begleittext: \"{hook}\"...")
        slides, caption = _generate_slides(hook, branche, saeule)
        log(f"  {len(slides)} Slides generiert")

        log("[2/6] Generiere Hintergrundfoto (einmal für alle Slides)...")
        photo = _generate_photo(settings.openai_api_key, hook, variante)

        log(f"[3/6] Rendere Slides (1080x1080, Variante {variante})...")
        rendered = _render_slides(slides, photo, variante_name=variante, seed=f"{hook}-{due_at}")

        log("[4/6] Erstelle PDF...")
        pdf_bytes = _make_pdf(rendered)

        log("[5/6] Lade nach Cloudinary hoch...")
        date_slug = due_at[:10].replace("-", "")
        folder = f"carousel/prozessia/{date_slug}"
        thumb_buf = io.BytesIO()
        rendered[0].save(thumb_buf, format="PNG")
        thumb_url = _cloudinary_upload(settings, thumb_buf.getvalue(), "image", f"{date_slug}-thumb", folder)
        pdf_url = _cloudinary_upload(settings, pdf_bytes, "raw", f"{date_slug}-karussell", folder)

        log("[6/6] Pushe nach Buffer" + (" (als Entwurf)" if draft else "") + "...")
        results = _push_carousel_to_buffer(settings, slides, caption, pdf_url, thumb_url, due_at, draft=draft)
        ok_count = sum(1 for r in results if r["ok"])

        return {
            "ok": ok_count > 0,
            "slides": len(slides),
            "slide_titles": [s["titel"] for s in slides],
            "caption": caption or _fallback_caption(slides),
            "variante": variante,
            "pdf_url": pdf_url,
            "thumb_url": thumb_url,
            "due_at": due_at,
            "draft": draft,
            "buffer": results,
            "anzahl_gepusht": ok_count,
        }
    except Exception as e:
        logger.exception("generate_carousel() fehlgeschlagen")
        return {"ok": False, "error": str(e)}
