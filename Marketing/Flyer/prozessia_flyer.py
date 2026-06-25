#!/usr/bin/env python3
"""
Prozessia Messe-Flyer – DIN A5 + 3mm Beschnitt (154 x 216 mm)
"""

import io
import math
import random
import qrcode
from PIL import Image, ImageDraw, ImageFilter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

# ── Schriften einbetten (SAXOPRINT verlangt embedded fonts) ──────────────────
_FONT_DIR = "/System/Library/Fonts/Supplemental"
pdfmetrics.registerFont(TTFont("Arial",      f"{_FONT_DIR}/Arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", f"{_FONT_DIR}/Arial Bold.ttf"))
FONT      = "Arial"
FONT_BOLD = "Arial-Bold"

# ---------------------------------------------------------------------------
# Dokument-Dimensionen
# ---------------------------------------------------------------------------
DOC_W = 154 * mm   # 148 + 3mm Beschnitt links/rechts
DOC_H = 216 * mm   # 210 + 3mm Beschnitt oben/unten

OUTPUT = "Prozessia_Flyer_Messe.pdf"

# ---------------------------------------------------------------------------
# Farben
# ---------------------------------------------------------------------------
C_DARK        = HexColor("#111111")
C_WHITE       = HexColor("#FFFFFF")
C_PURPLE      = HexColor("#534AB7")
C_PURPLE_LIGHT= HexColor("#B088FF")
C_GRAY_TEXT   = HexColor("#B8B8C2")
C_GRAY_DARK   = HexColor("#444444")
C_GRAY_MID    = HexColor("#888780")
C_DARK_LINE   = HexColor("#2A2A3A")
C_LIGHT_LINE  = HexColor("#E0DED8")
C_FOOTER_GRAY = HexColor("#5A5A66")
C_BODY_DARK   = HexColor("#C8C7D4")   # Helleres Grau mit Lila-Ton für Rückseite


def hex_with_alpha(hex_color, alpha):
    """Return a Color object with given opacity (0-1)."""
    r = int(hex_color[1:3], 16) / 255
    g = int(hex_color[3:5], 16) / 255
    b = int(hex_color[5:7], 16) / 255
    return Color(r, g, b, alpha=alpha)


STAR_WHITE_18 = hex_with_alpha("#FFFFFF", 0.18)

# ---------------------------------------------------------------------------
# Sternfeld-Positionen (in mm)
# ---------------------------------------------------------------------------
STARS = [
    (12,198),(45,182),(78,205),(112,191),(135,178),
    (22,165),(67,172),(98,160),(140,168),(8,145),
    (55,138),(88,152),(125,143),(30,125),(72,130),
    (105,118),(148,135),(18,108),(62,115),(95,102),
    (138,112),(25,88),(70,95),(108,82),(145,92),
    (40,72),(115,78),
]
STAR_RADIUS = 1.2   # pt


def draw_stars(c):
    c.setFillColor(STAR_WHITE_18)
    for sx, sy in STARS:
        c.circle(sx * mm, sy * mm, STAR_RADIUS, stroke=0, fill=1)


def draw_bullet_square(c, x_mm, y_mm, size_pt, color):
    """Gefülltes Quadrat als Bullet-Symbol."""
    c.setFillColor(color)
    # Quadrat um den Mittelpunkt zentriert
    c.rect(
        x_mm * mm - size_pt / 2,
        y_mm * mm - size_pt / 2,
        size_pt, size_pt,
        stroke=0, fill=1
    )


# Lila #534AB7 als 0-1 float-Werte für Color()-Objekte
_PR, _PG, _PB = 0x53 / 255, 0x4A / 255, 0xB7 / 255   # #534AB7
_LR, _LG, _LB = 0xB0 / 255, 0x88 / 255, 0xFF / 255   # #B088FF


def _gradient_bg(c):
    """Vertikaler Verlauf: #111111 (unten) → #0E0B20 (oben, dunkles Nachtblau)."""
    n = 80
    for i in range(n):
        t = i / (n - 1)
        r = (0x11 + (0x0E - 0x11) * t) / 255
        g = (0x11 + (0x0B - 0x11) * t) / 255
        b = (0x11 + (0x20 - 0x11) * t) / 255
        c.setFillColor(Color(r, g, b))
        c.rect(0, i * DOC_H / n, DOC_W, DOC_H / n + 0.8, stroke=0, fill=1)


def _glow_circle(c):
    """Großer halbsichtbarer Lila-Kreis rechts als Tiefeneffekt."""
    # Äußerer Schein: mehrere Kreise abnehmender Opazität
    layers = [(90 * mm, 0.055), (75 * mm, 0.07), (58 * mm, 0.09),
              (42 * mm, 0.10), (28 * mm, 0.08)]
    cx, cy = 152 * mm, 88 * mm
    for radius, alpha in layers:
        c.setFillColor(Color(_PR, _PG, _PB, alpha=alpha))
        c.circle(cx, cy, radius, stroke=0, fill=1)


def _headline_glow(c):
    """Subtiler lila Schimmer hinter dem Headline-Block."""
    # Breites, weiches Rechteck hinter "KI für die / Industrie."
    c.setFillColor(Color(_PR, _PG, _PB, alpha=0.10))
    c.rect(0, 134 * mm, DOC_W, 46 * mm, stroke=0, fill=1)
    c.setFillColor(Color(_PR, _PG, _PB, alpha=0.05))
    c.rect(0, 124 * mm, DOC_W, 62 * mm, stroke=0, fill=1)


# ---------------------------------------------------------------------------
# SEITE 1 – VORDERSEITE
# ---------------------------------------------------------------------------
def draw_front(c):
    # Hintergrund mit Verlauf
    _gradient_bg(c)

    # Industrie-Foto unten (vorcomposited RGB, kein alpha-Trick nötig)
    ind_buf = create_industrial_image()  # 1820×1040 px = 300 DPI für 154×88 mm
    c.drawImage(ImageReader(ind_buf), 0, 0,
                width=DOC_W, height=88 * mm)

    # Dekorativer Lila-Glow rechts (wie ein Planeten-Schimmer)
    _glow_circle(c)

    # Headline-Glow hinter dem Textbereich
    _headline_glow(c)

    # Sternfeld (über den Glows, damit Sterne leuchten)
    draw_stars(c)

    # --- Logo ---
    c.setFillColor(C_WHITE)
    c.setFont(FONT_BOLD, 15)
    c.drawString(13 * mm, 199 * mm, "Prozessia.")

    # Kleiner Lila-Akzentpunkt hinter dem Logo-Punkt
    c.setFillColor(Color(_LR, _LG, _LB, alpha=0.40))
    c.circle(55.5 * mm, 200.5 * mm, 2.8, stroke=0, fill=1)

    # --- Headline ---
    c.setFillColor(C_WHITE)
    c.setFont(FONT_BOLD, 50)
    c.drawString(13 * mm, 162 * mm, "KI für die")

    c.setFillColor(C_PURPLE_LIGHT)
    c.setFont(FONT_BOLD, 50)
    c.drawString(13 * mm, 140 * mm, "Industrie.")

    # --- Subline: heller für mehr Wirkung ---
    c.setFillColor(C_WHITE)
    c.setFont(FONT_BOLD, 13)
    c.drawString(13 * mm, 128 * mm, "Sicher. Schnell. Skalierbar.")

    # --- Trennlinie: leichter Lila-Verlauf (zwei Segmente) ---
    c.setStrokeColor(C_PURPLE)
    c.setLineWidth(1.2)
    c.line(13 * mm, 122 * mm, 90 * mm, 122 * mm)
    c.setStrokeColor(Color(_PR, _PG, _PB, alpha=0.25))
    c.setLineWidth(0.8)
    c.line(90 * mm, 122 * mm, 141 * mm, 122 * mm)

    # --- Vorteils-Bullets ---
    bullet_data = [
        (114, FONT_BOLD, C_WHITE,
         "Von der Idee zur Kosteneinsparung: KI live in wenigen Wochen."),
        (104, FONT,      C_GRAY_TEXT,
         "Wir bauen Ihnen die Lösung – sicher, auf deutschen Servern, für Ihren Prozess."),
        (94,  FONT,      C_GRAY_TEXT,
         "Bereit für den EU AI Act – ohne Mehraufwand für Sie."),
    ]

    for idx, (y_mm, font, color, text) in enumerate(bullet_data):
        # Erstes Bullet: lila Hintergrund-Row für mehr Gewicht
        if idx == 0:
            c.setFillColor(Color(_PR, _PG, _PB, alpha=0.14))
            c.roundRect(11 * mm, (y_mm - 2.5) * mm, 130 * mm, 8 * mm,
                        radius=2, stroke=0, fill=1)
            # Akzentlinie links auf der Row
            c.setFillColor(C_PURPLE_LIGHT)
            c.rect(11 * mm, (y_mm - 2.5) * mm, 1.5, 8 * mm, stroke=0, fill=1)

        # Bullet-Quadrat
        draw_bullet_square(c, 15.25, y_mm + 0.5, 3.5, C_PURPLE_LIGHT)

        c.setFillColor(color)
        c.setFont(font, 10.5)
        c.drawString(20 * mm, y_mm * mm, text)



# ---------------------------------------------------------------------------
# SEITE 2 – RÜCKSEITE
# ---------------------------------------------------------------------------
def generate_qr_image():
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=20,   # 300 DPI-tauglich: 22 mm QR → ~260 px min
        border=2,
    )
    qr.add_data("https://calendly.com/sebastian-spuhler/30min")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def create_neural_bg():
    """Prozedurales KI-Netzwerk-Bild: Knoten + Verbindungslinien (lila, transparent)."""
    W, H = 1820, 2552        # 154 × 216 mm bei 300 dpi (druckfertig)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    rng = random.Random(2025)

    # 50 zufällige Knoten über die gesamte Seite verteilt
    nodes = [(rng.randint(10, W - 10), rng.randint(10, H - 10)) for _ in range(50)]
    PURPLE = (176, 136, 255)      # #B088FF
    MAX_D  = 790                  # ~66 mm Verbindungsdistanz bei 300 dpi

    # Verbindungslinien zwischen nahen Knoten
    for i, (x1, y1) in enumerate(nodes):
        for j, (x2, y2) in enumerate(nodes):
            if j <= i:
                continue
            d = math.hypot(x2 - x1, y2 - y1)
            if d < MAX_D:
                alpha = int(22 * (1 - d / MAX_D))
                draw.line([(x1, y1), (x2, y2)], fill=(*PURPLE, alpha), width=3)

    # Knoten-Punkte mit kleinem Glow
    for x, y in nodes:
        r = rng.randint(8, 20)
        draw.ellipse([(x - r * 2, y - r * 2), (x + r * 2, y + r * 2)],
                     fill=(*PURPLE, 10))
        draw.ellipse([(x - r, y - r), (x + r, y + r)],
                     fill=(*PURPLE, 38))

    img = img.filter(ImageFilter.GaussianBlur(radius=5))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def create_industrial_image(target_w_px=1820, target_h_px=1040):
    """Industrie-Foto vorcomposited mit passendem Hintergrund-Gradient → RGB,
    kein alpha-Channel nötig. 300 DPI (1820×1040 px für 154×88 mm).
    Vorderseite unten: PIL row 0 = visuelles Oben (y=88 mm), row H-1 = y=0.
    """
    import urllib.request
    from PIL import ImageEnhance

    W, H = target_w_px, target_h_px

    URLS = [
        # Vollautomatische Fertigungsstraße – industrielle Produktion (pWUyHVJgLhg)
        "https://images.unsplash.com/photo-1717386255773-1e3037c81788"
        "?w=2400&q=85&auto=format&fit=crop",
        # Industriemaschinen in einer Fabrik – Fallback (hZ2ULF80dCY)
        "https://images.unsplash.com/photo-1745921204896-c2011440a4e2"
        "?w=2400&q=85&auto=format&fit=crop",
    ]

    # ── Hintergrund-Gradient passend zu _gradient_bg (für pre-compositing) ─
    # PIL row 0 = visuell oben = y=88 mm; row H-1 = visuell unten = y=0 mm
    PHOTO_H_MM = 88
    bg_arr = bytearray()
    for row in range(H):
        y_vis = PHOTO_H_MM * (1.0 - row / max(H - 1, 1))  # mm, von Seitenboden
        t = min(1.0, max(0.0, y_vis / 216.0 * (80.0 / 79.0)))
        bg_arr.extend([
            int(0x11 + (0x0E - 0x11) * t),
            int(0x11 + (0x0B - 0x11) * t),
            int(0x11 + (0x20 - 0x11) * t),
        ] * W)
    bg_img = Image.frombytes("RGB", (W, H), bytes(bg_arr)).convert("RGBA")

    raw = None
    for url in URLS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                raw = io.BytesIO(r.read())
            break
        except Exception:
            continue

    if raw is None:
        buf = io.BytesIO()
        bg_img.convert("RGB").save(buf, format="PNG")
        buf.seek(0)
        return buf

    # ── Cover-Crop: untere Bildhälfte bevorzugen (Funken/Maschinen-Detail) ─
    photo = Image.open(raw).convert("RGB")
    scale = max(W / photo.width, H / photo.height)
    nw    = int(photo.width  * scale)
    nh    = int(photo.height * scale)
    photo = photo.resize((nw, nh), Image.LANCZOS)
    left  = (nw - W) // 2
    # Crop aus dem unteren 60 % des Bildes (mehr Maschinen-/Funken-Detail)
    top   = max(0, int((nh - H) * 0.65))
    photo = photo.crop((left, top, left + W, top + H))

    # ── Darkroom: 65 % Farbe, 70 % Helligkeit, 15 % Lila-Tint ───────────
    desat  = ImageEnhance.Color(photo).enhance(0.65)
    bright = ImageEnhance.Brightness(desat).enhance(0.70)
    purple = Image.new("RGB", (W, H), (70, 55, 140))
    tinted = Image.blend(bright, purple, 0.15)

    # ── Alpha-Maske: obere 40 % des Bildes (nahe Bullets) faden aus ──────
    # row 0 (visuell oben, y=88 mm) → alpha=0; row H-1 (y=0) → alpha=255
    FADE = 0.40
    alpha_arr = bytearray()
    for row in range(H):
        t = row / max(H - 1, 1)
        a = int(min(1.0, t / FADE) * 255)
        alpha_arr.extend([a] * W)
    alpha_mask = Image.frombytes("L", (W, H), bytes(alpha_arr))

    photo_rgba = tinted.convert("RGBA")
    photo_rgba.putalpha(alpha_mask)

    # ── Pre-compositing: Foto über dunklem Gradient (→ reines RGB, kein mask) ─
    composited = Image.alpha_composite(bg_img, photo_rgba)
    final = composited.convert("RGB")
    final = final.filter(ImageFilter.GaussianBlur(radius=0.4))

    buf = io.BytesIO()
    final.save(buf, format="PNG")
    buf.seek(0)
    return buf


def wrap_text(text, max_width_pt, font_name, font_size):
    """Word-wrap text into lines fitting within max_width_pt."""
    from reportlab.pdfbase.pdfmetrics import stringWidth
    words = text.split(' ')
    lines = []
    current = ''
    for word in words:
        candidate = (current + ' ' + word).strip()
        if stringWidth(candidate, font_name, font_size) <= max_width_pt:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_back(c):
    # 1. Gradient-Hintergrund (identisch Vorderseite)
    _gradient_bg(c)

    # 2. KI-Netzwerk-Textur (volle Seite)
    neural_buf = create_neural_bg()
    c.drawImage(ImageReader(neural_buf), 0, 0,
                width=DOC_W, height=DOC_H, mask="auto")

    # 3. Lila Glow oben-links (Gegenpol zum rechten Glow der Vorderseite)
    for radius, alpha in [(72*mm, 0.055), (56*mm, 0.075),
                          (38*mm, 0.09),  (22*mm, 0.07)]:
        c.setFillColor(Color(_PR, _PG, _PB, alpha=alpha))
        c.circle(-8 * mm, 178 * mm, radius, stroke=0, fill=1)

    # 4. Sternfeld
    draw_stars(c)

    # 5. Lila Balken oben
    c.setFillColor(C_PURPLE)
    c.rect(0, 212 * mm, DOC_W, 4 * mm, stroke=0, fill=1)

    # 6. Logo
    c.setFillColor(C_WHITE)
    c.setFont(FONT_BOLD, 13)
    c.drawString(13 * mm, 199 * mm, "Prozessia.")

    TEXT_X  = 13 * mm
    TEXT_W  = 128 * mm
    LINE_13 = 6.0 * mm
    LINE_9  = 3.8 * mm

    # -----------------------------------------------------------------------
    # KERNBOTSCHAFT – subtile Card dahinter
    # -----------------------------------------------------------------------
    core_msg = ("Wir verbinden modernste KI-Technologie mit dem Schutz Ihrer Daten, "
                "damit Sie beides haben.")
    core_lines = wrap_text(core_msg, TEXT_W, FONT_BOLD, 13)
    card_h = len(core_lines) * LINE_13 + 5 * mm
    c.setFillColor(Color(1, 1, 1, alpha=0.04))
    c.roundRect(TEXT_X - 2 * mm, 188 * mm - card_h + 5 * mm,
                TEXT_W + 4 * mm, card_h, radius=2, stroke=0, fill=1)
    c.setFillColor(C_WHITE)
    c.setFont(FONT_BOLD, 13)
    y = 188 * mm
    for line in core_lines:
        c.drawString(TEXT_X, y, line)
        y -= LINE_13

    # -----------------------------------------------------------------------
    # Hilfsfunktion: Content-Block mit lila Akzentbalken links
    # -----------------------------------------------------------------------
    def draw_block(title, body_text, start_y, body_width=None):
        bw = body_width or (TEXT_W - 4.5 * mm)
        body_lines = wrap_text(body_text, bw, FONT, 9)

        # Header
        c.setFillColor(C_PURPLE_LIGHT)
        c.setFont(FONT_BOLD, 11)
        c.drawString(TEXT_X + 4.5 * mm, start_y, title)

        # Body-Text
        by = start_y - 4.5 * mm
        c.setFillColor(C_WHITE)
        c.setFont(FONT, 9)
        for line in body_lines:
            c.drawString(TEXT_X + 4.5 * mm, by, line)
            by -= LINE_9

        # Lila Akzentbalken links (nachträglich, korrekte Höhe)
        bar_bottom = by + LINE_9 - 0.5 * mm
        bar_top    = start_y + 4 * mm
        c.setFillColor(C_PURPLE)
        c.rect(TEXT_X, bar_bottom, 1.5, bar_top - bar_bottom, stroke=0, fill=1)

        return by   # neue y-Position

    # -----------------------------------------------------------------------
    # DREI INHALTSBLÖCKE
    # -----------------------------------------------------------------------
    y -= 5 * mm
    y = draw_block(
        "Einkauf automatisieren",
        ("Auftragsbestätigungen prüfen, Liefertermine im Blick behalten, "
         "Lieferanten bei Abweichungen kontaktieren: Das kostet Ihren Einkauf "
         "täglich wertvolle Zeit. Unsere Lösung übernimmt genau diese Aufgaben "
         "vollautomatisch und hält Ihr Team frei für das Wesentliche."),
        y,
    )

    y -= 5.5 * mm
    y = draw_block(
        "Stücklisten in Stunden statt Tagen",
        ("Was früher Tage gedauert hat, erledigt unsere KI in wenigen Stunden: "
         "Stücklisten automatisch prüfen, Abweichungen sofort erkennen und jeden "
         "Schritt lückenlos dokumentieren. Ihr Team behält die Kontrolle, "
         "ohne den manuellen Aufwand."),
        y,
    )

    y -= 5.5 * mm
    y = draw_block(
        "Datenschutz & Infrastruktur",
        ("Ihre Daten verlassen Ihr Unternehmen nicht – verarbeitet auf deutschen EU-Servern, "
         "vollständig DSGVO-konform, kein US-Datentransfer. Keine Haftungsrisiken durch "
         "Datenschutzverstöße. EU AI Act konform, ohne Mehraufwand für Sie."),
        y,
    )
    y -= 4 * mm

    # -----------------------------------------------------------------------
    # TRENNLINIE vor Kontaktbereich
    # -----------------------------------------------------------------------
    c.setStrokeColor(C_DARK_LINE)
    c.setLineWidth(0.5)
    c.line(13 * mm, y + 2 * mm, 141 * mm, y + 2 * mm)

    # -----------------------------------------------------------------------
    # QR-CODE
    # -----------------------------------------------------------------------
    qr_buf  = generate_qr_image()
    qr_size = 22 * mm
    c.drawImage(ImageReader(qr_buf), 13 * mm, 56 * mm,
                width=qr_size, height=qr_size, mask="auto")

    c.setFillColor(C_PURPLE_LIGHT)
    c.setFont(FONT_BOLD, 8)
    c.drawCentredString((13 + 11) * mm, 52 * mm, "Termin vereinbaren")

    # -----------------------------------------------------------------------
    # KONTAKTBLOCK – Visitenkarten-Card
    # -----------------------------------------------------------------------
    card_x, card_y, card_w, card_h2 = 40 * mm, 49 * mm, 99 * mm, 35 * mm
    # Hintergrund
    c.setFillColor(Color(1, 1, 1, alpha=0.05))
    c.roundRect(card_x, card_y, card_w, card_h2, radius=3, stroke=0, fill=1)
    # Subtiler Rahmen
    c.setStrokeColor(Color(_PR, _PG, _PB, alpha=0.35))
    c.setLineWidth(0.6)
    c.roundRect(card_x, card_y, card_w, card_h2, radius=3, stroke=1, fill=0)
    # Lila Akzentlinie oben auf der Card
    c.setFillColor(C_PURPLE)
    c.rect(card_x, card_y + card_h2 - 2, card_w, 2, stroke=0, fill=1)

    contact = [
        (78, FONT_BOLD, 10,   C_WHITE,        "Sebastian Spuhler"),
        (72, FONT,       9,   C_GRAY_TEXT,    "Prozessia"),
        (66, FONT,       8.5, C_GRAY_TEXT,    "sebastian.spuhler@prozessia.de"),
        (60, FONT,       8.5, C_GRAY_TEXT,    "0151 59473260"),
        (54, FONT_BOLD,  8.5, C_PURPLE_LIGHT, "prozessia.de"),
    ]
    for y_mm, font, size, color, text in contact:
        c.setFillColor(color)
        c.setFont(font, size)
        c.drawString(42 * mm, y_mm * mm, text)

    # -----------------------------------------------------------------------
    # FUßZEILE
    # -----------------------------------------------------------------------
    c.setFillColor(C_GRAY_MID)
    c.setFont(FONT, 7)
    c.drawCentredString(DOC_W / 2, 8 * mm,
                        "Prozessia \u00b7 Saarbrücken \u00b7 prozessia.de")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    c = canvas.Canvas(OUTPUT, pagesize=(DOC_W, DOC_H))
    c.setTitle("Prozessia Messe-Flyer")
    c.setAuthor("Prozessia")

    # Seite 1
    draw_front(c)
    c.showPage()

    # Seite 2
    draw_back(c)
    c.showPage()

    c.save()
    print(f"PDF erstellt: {OUTPUT}")


if __name__ == "__main__":
    main()
