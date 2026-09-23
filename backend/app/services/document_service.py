"""PDF-Erzeugung für den Chat (create_pdf-Tool) MIT harter Fakten-Verifikation.

Sebastian, 2026-09-23: das Brain muss wie ein echter Claude-Chat fertige PDFs
erzeugen können (Abnahmeprotokolle, Verträge, Angebote ...) - und jede genannte
Zahl, jedes Datum, jede Nummer, jeder Name muss GENAU stimmen. Deshalb rendert
dieses Modul kein PDF, solange sich ein prüfbarer Fakt aus dem Text nicht in den
angegebenen Quelldateien wiederfindet (Vorfall, der das ausgelöst hat: das Brain
antwortete "ich kann keine PDF-Bytes erzeugen" und lieferte stattdessen eine
.md-Entwurfsdatei, deren Status "Erfüllt" nie gegen den echten Stand geprüft war).

Ablauf create_pdf():
  1. Quellen laden (Vault-Dateien: md/txt/docx/pdf/xlsx ...) -> ein Volltext-Korpus.
  2. Prüfbare Fakten aus dem Markdown extrahieren (Datum, Beträge, Prozent,
     Mengen mit Einheit, Kennungen wie AG0024/BEST-...-124952/HRB 1034,
     E-Mails, Telefon-/Langnummern, Firmen, "Herr/Frau/Dr. X", plus die vom
     Modell explizit gelisteten weiteren Fakten).
  3. Jeden Fakt gegen den Korpus prüfen. Was nicht belegt ist, wird NICHT
     gerendert - es sei denn, das Modell führt es ausdrücklich unter
     `freigegeben` auf (bewusst neue/berechnete Angabe, wird im Ergebnis
     gemeldet, damit Sebastian sie sieht).
  4. PDF rendern, aus dem fertigen PDF den Text zurücklesen und dieselben
     Fakten NOCHMAL dort prüfen (fängt Render-Verluste ab).
  5. Erst dann speichern (+ Markdown-Quelltext unter _agent/documents_src/,
     damit spätere Änderungen nicht aus dem PDF rekonstruiert werden müssen).

Semantische Aussagen ("Modul X ist erfüllt") kann diese Prüfung NICHT beurteilen -
dafür steht die Pflicht im System-Prompt (context.BASE_PROMPT, Abschnitt
DOKUMENTE), Status-/Abnahmeaussagen vorher gegen den echten Stand zu prüfen."""
import io
import re
import threading
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app.config import get_settings
from app.services import classify, rag

# Ordner, in die das Brain keine Dokumente schreiben darf (Systemdaten/App-Code) -
# deckt sich mit dem _SKIP-Set in routers/files.py.
_FORBIDDEN_TARGETS = {
    "_inbox", ".git", ".obsidian", "_fehler", "__pycache__", "_agent",
    "node_modules", ".claude", ".venv", "backend", "frontend", "services",
}

_MONTHS = {
    "januar": 1, "jänner": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4,
    "mai": 5, "juni": 6, "juli": 7, "august": 8, "september": 9,
    "oktober": 10, "november": 11, "dezember": 12,
}
_MONTH_RE = "|".join(sorted(_MONTHS, key=len, reverse=True))

_NUMBER_WORDS = {
    "ein": 1, "eine": 1, "einen": 1, "eins": 1, "zwei": 2, "drei": 3, "vier": 4,
    "fünf": 5, "sechs": 6, "sieben": 7, "acht": 8, "neun": 9, "zehn": 10,
    "elf": 11, "zwölf": 12,
}

# Einheiten -> Stamm (erste 4 Buchstaben reichen: Monat/Monate/Monaten, Tag/Tage ...)
_UNIT_RE = r"(?:Monat\w*|Tag\w*|Woche\w*|Jahr\w*|Stück\w*|Modul\w*|Mitarbeiter\w*|Lizenz\w*|Nutzer\w*|Seite\w*|Stunde\w*)"


@dataclass(frozen=True)
class Fact:
    typ: str          # datum | betrag | prozent | menge | kennung | email | nummer | name
    text: str         # so wie im Dokument geschrieben
    key: object       # normalisierter Vergleichswert


class DocumentError(Exception):
    pass


# ── Normalisierung ──────────────────────────────────────────────────────────

def _fold(s: str) -> str:
    """Casefold + Umlaut-Faltung + Whitespace-Kollaps, damit 'Schäufler' und
    'Schaeufler' bzw. Zeilenumbrüche in PDF-Extrakten nicht zu Fehlalarmen führen."""
    s = s.casefold()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s)


def _alnum(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _fold(s))


def _to_decimal(token: str) -> set[Decimal]:
    """Alle plausiblen Zahlenwerte eines Tokens wie '10.000,00' / '10,000.00' / '19,5'."""
    values: set[Decimal] = set()

    def add(s: str):
        try:
            values.add(Decimal(s).normalize())
        except InvalidOperation:
            pass

    if re.fullmatch(r"\d+", token):
        add(token)
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", token):          # 10.000,50
        add(token.replace(".", "").replace(",", "."))
    elif re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", token):          # 10,000.50
        add(token.replace(",", ""))
    elif re.fullmatch(r"\d+,\d+", token):                            # 19,5
        add(token.replace(",", "."))
    elif re.fullmatch(r"\d+\.\d+", token):                           # 19.5 (oder 4.500)
        add(token)
        if re.fullmatch(r"\d+\.\d{3}", token):
            add(token.replace(".", ""))
    return values


# ── Fakten aus einem Text ziehen (Dokument UND Quellen) ─────────────────────

_DATE_NUM = re.compile(r"\b(\d{1,2})\.\s?(\d{1,2})\.\s?(\d{4}|\d{2})(?!\d)")
_DATE_WORD = re.compile(rf"\b(\d{{1,2}})\.\s*({_MONTH_RE})\b(?:\s+(\d{{4}}))?", re.IGNORECASE)
_DATE_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")


def _dates(text: str) -> list[tuple[str, tuple[int | None, int, int]]]:
    found = []
    for m in _DATE_NUM.finditer(text):
        d, mo, y = int(m.group(1)), int(m.group(2)), m.group(3)
        if 1 <= d <= 31 and 1 <= mo <= 12:
            year = int(y) + 2000 if len(y) == 2 else int(y)
            found.append((m.group(0), (year, mo, d)))
    for m in _DATE_WORD.finditer(text):
        d, mo = int(m.group(1)), _MONTHS[m.group(2).lower()]
        if 1 <= d <= 31:
            found.append((m.group(0), (int(m.group(3)) if m.group(3) else None, mo, d)))
    for m in _DATE_ISO.finditer(text):
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= d <= 31 and 1 <= mo <= 12:
            found.append((m.group(0), (y, mo, d)))
    return found


_MONEY = re.compile(
    r"(?:(?P<pre>€|EUR)\s*(?P<n1>\d[\d.,]*)|(?P<n2>\d[\d.,]*)\s*(?P<post>€|EUR|Euro\b))"
)
_PERCENT = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:%|Prozent\b)")
_QUANTITY = re.compile(rf"\b(\d+)[\s-]*({_UNIT_RE})", re.IGNORECASE)
_WORD_QUANTITY = re.compile(
    rf"\b({'|'.join(_NUMBER_WORDS)})[\s-]+({_UNIT_RE})", re.IGNORECASE
)
_ID = re.compile(
    r"\b(?:(?:HRA|HRB|VR|GnR)\s?\d+"
    r"|(?=[A-Za-z0-9\-/]*\d)(?=[A-Za-z0-9\-/]*[A-Za-z])[A-Za-z0-9][A-Za-z0-9\-/]{3,})\b"
)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_LONG_NUMBER = re.compile(r"(?<![\d.,])\d{5,}(?![\d.,]*\d)")
_PHONE = re.compile(r"\+\d[\d\s/()-]{7,}\d|\b0\d{2,5}[\s/-]\d[\d\s/-]{4,}\d")
_COMPANY = re.compile(
    r"(?:[A-ZÄÖÜ][\w&.\-]*\s+){1,4}(?:GmbH\s*&\s*Co\.\s*KG|GmbH|GbR|AG|KG|SE|UG|e\.\s?K\.)(?![\w])"
)
_PERSON = re.compile(
    r"\b(?:Herr|Herrn|Frau|Dr\.|Prof\.)\s+(?:(?:Dr\.|Prof\.)\s+)?[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?"
)


def _quantity_key(value: int, unit: str) -> tuple[int, str]:
    return value, _fold(unit)[:4]


def extract_facts(text: str) -> list[Fact]:
    """Prüfbare Fakten eines Dokumenttexts. Bewusst nur Dinge, die sich
    mechanisch belegen lassen - keine Semantik."""
    facts: list[Fact] = []
    seen: set[tuple[str, object]] = set()

    def add(typ: str, raw: str, key: object):
        if (typ, key) in seen:
            return
        seen.add((typ, key))
        facts.append(Fact(typ, raw.strip(), key))

    for raw, key in _dates(text):
        add("datum", raw, key)
    for m in _MONEY.finditer(text):
        raw = m.group(0)
        token = (m.group("n1") or m.group("n2")).rstrip(".,")
        for v in _to_decimal(token):
            add("betrag", raw, v)
            break
    for m in _PERCENT.finditer(text):
        for v in _to_decimal(m.group(1)):
            add("prozent", m.group(0), v)
            break
    for m in _QUANTITY.finditer(text):
        add("menge", m.group(0), _quantity_key(int(m.group(1)), m.group(2)))
    for m in _WORD_QUANTITY.finditer(text):
        add("menge", m.group(0), _quantity_key(_NUMBER_WORDS[m.group(1).lower()], m.group(2)))
    for m in _ID.finditer(text):
        add("kennung", m.group(0), _alnum(m.group(0)))
    for m in _EMAIL.finditer(text):
        add("email", m.group(0), m.group(0).casefold())
    for m in _LONG_NUMBER.finditer(text):
        add("nummer", m.group(0), m.group(0))
    for m in _PHONE.finditer(text):
        add("nummer", m.group(0), re.sub(r"\D", "", m.group(0)))
    for m in _COMPANY.finditer(text):
        add("name", m.group(0), _fold(m.group(0)))
    for m in _PERSON.finditer(text):
        add("name", m.group(0), _fold(m.group(0)))
    return facts


class _Corpus:
    """Aus den Quelltexten abgeleitete Nachschlage-Mengen."""

    def __init__(self, text: str):
        self.folded = _fold(text)
        self.alnum = _alnum(text)
        self.digits = re.sub(r"\D", "", text)
        self.dates_full: set[tuple[int, int, int]] = set()
        self.dates_md: set[tuple[int, int]] = set()
        for _, (y, mo, d) in _dates(text):
            self.dates_md.add((mo, d))
            if y is not None:
                self.dates_full.add((y, mo, d))
        self.money: set[Decimal] = set()
        for m in _MONEY.finditer(text):
            self.money |= _to_decimal((m.group("n1") or m.group("n2")).rstrip(".,"))
        # Beträge stehen in Angeboten auch mal ohne Währungszeichen in Tabellen
        self.numbers: set[Decimal] = set()
        for tok in re.findall(r"\d[\d.,]*\d|\d", text):
            self.numbers |= _to_decimal(tok)
        self.percent: set[Decimal] = set()
        for m in _PERCENT.finditer(text):
            self.percent |= _to_decimal(m.group(1))
        self.quantities: set[tuple[int, str]] = set()
        for m in _QUANTITY.finditer(text):
            self.quantities.add(_quantity_key(int(m.group(1)), m.group(2)))
        for m in _WORD_QUANTITY.finditer(text):
            self.quantities.add(_quantity_key(_NUMBER_WORDS[m.group(1).lower()], m.group(2)))

    def has(self, fact: Fact) -> bool:
        k = fact.key
        if fact.typ == "datum":
            y, mo, d = k
            return (y, mo, d) in self.dates_full if y is not None else (mo, d) in self.dates_md
        if fact.typ == "betrag":
            # Betrag muss entweder mit Währung oder zumindest als Zahl in der Quelle stehen
            return k in self.money or k in self.numbers
        if fact.typ == "prozent":
            return k in self.percent
        if fact.typ == "menge":
            return k in self.quantities
        if fact.typ == "kennung":
            return k in self.alnum
        if fact.typ == "email":
            return k in self.folded
        if fact.typ == "nummer":
            return k in self.digits if k.isdigit() else k in self.folded
        if fact.typ == "name":
            return k in self.folded
        return False


# ── Quellen laden ───────────────────────────────────────────────────────────

def _resolve_source(rel: str) -> Path:
    vault = get_settings().vault_path.resolve()
    rel = rel.strip().lstrip("/")
    target = (vault / rel).resolve()
    if str(target).startswith(str(vault)) and target.is_file():
        return target
    hits = [p for p in vault.rglob(Path(rel).name) if p.is_file() and "_agent/trash" not in str(p)]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        raise DocumentError(
            f"Quelle '{rel}' ist mehrdeutig ({len(hits)} Treffer, z.B. "
            f"{hits[0].relative_to(vault)}) - vollständigen Vault-Pfad angeben."
        )
    raise DocumentError(f"Quelle nicht gefunden: {rel}")


def _read_source(path: Path) -> str:
    if path.suffix.lower() in {".md", ".txt", ".csv", ".json"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix.lower() == ".pdf":
        # Erst lokal (kein externer OCR-Call nötig), OCR nur bei gescannten PDFs.
        try:
            import PyPDF2

            with open(path, "rb") as f:
                text = " ".join(p.extract_text() or "" for p in PyPDF2.PdfReader(f).pages)
            if len(text.strip()) > 50:
                return text
        except Exception:
            pass
    text = classify.extract_text(path, max_chars=10_000_000)
    if not text:
        raise DocumentError(f"Quelle nicht lesbar (kein Text extrahierbar): {path.name}")
    return text


def load_corpus(sources: list[str]) -> tuple[_Corpus, list[str]]:
    if not sources:
        raise DocumentError(
            "Keine Quellen angegeben - `quellen` muss die Vault-Dateien nennen, aus denen die Fakten stammen."
        )
    vault = get_settings().vault_path.resolve()
    texts, used = [], []
    for s in sources:
        p = _resolve_source(s)
        texts.append(_read_source(p))
        used.append(str(p.relative_to(vault)))
    return _Corpus("\n".join(texts)), used


# ── Rendering ───────────────────────────────────────────────────────────────

_FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")


def _font_face_css() -> str:
    regular, bold = _FONT_DIR / "DejaVuSans.ttf", _FONT_DIR / "DejaVuSans-Bold.ttf"
    if not (regular.exists() and bold.exists()):
        return "body { font-family: Helvetica, sans-serif; }"
    return (
        f'@font-face {{ font-family: DejaVu; src: url("{regular}"); }}\n'
        f'@font-face {{ font-family: DejaVu; font-weight: bold; src: url("{bold}"); }}\n'
        "body { font-family: DejaVu, sans-serif; }"
    )


_PDF_CSS = """
@page {
  size: A4; margin: 2.2cm 2cm 2.4cm 2cm;
  @frame footer { -pdf-frame-content: footerContent; bottom: 1cm; margin-left: 2cm; margin-right: 2cm; height: 0.8cm; }
}
body { font-size: 10pt; line-height: 1.45; color: #111; }
h1 { font-size: 18pt; margin: 0 0 10pt 0; }
h2 { font-size: 13pt; margin: 16pt 0 4pt 0; border-bottom: 1px solid #bbb; padding-bottom: 2pt; }
h3 { font-size: 11pt; margin: 12pt 0 3pt 0; }
p { margin: 0 0 6pt 0; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 10pt 0; }
th { background-color: #eee; font-weight: bold; }
th, td { border: 1px solid #999; padding: 4pt 6pt; text-align: left; font-size: 9.5pt; vertical-align: top; }
code { font-size: 9pt; background-color: #f2f2f2; }
hr { border: 0; border-top: 1px solid #bbb; margin: 10pt 0; }
table.sig { margin: 34pt 0 2pt 0; }
table.sig td { border: 0; padding: 0; height: 22pt; }
table.sig td.sigline { border-bottom: 1px solid #000; }
#footerContent { font-size: 8pt; color: #666; text-align: right; }
"""


_SIGNATURE_LINE = re.compile(r"^[ \t]*(_{4,}(?:[ \t]+_{4,})*)[ \t]*$", re.MULTILINE)


def _signature_blocks(text: str) -> str:
    """Eine Zeile nur aus Unterstrichen ('_____  _____') wäre für Markdown eine
    horizontale Trennlinie - in Verträgen/Protokollen sind das aber die
    Unterschriftslinien. Pro Unterstrich-Gruppe eine Zelle mit Linie darunter."""
    def repl(m: re.Match) -> str:
        n = len(m.group(1).split())
        w = round((100 - 10 * (n - 1)) / n, 1)
        line = f'<td class="sigline" width="{w}%">&nbsp;</td>'
        cells = line + "".join(f'<td class="siggap" width="10%">&nbsp;</td>{line}' for _ in range(n - 1))
        return f'\n<table class="sig"><tr>{cells}</tr></table>\n'

    return _SIGNATURE_LINE.sub(repl, text)


def _resource_policy():
    """xhtml2pdf >= 0.2.18 sperrt lokale/entfernte Ressourcen außerhalb des
    Basisverzeichnisses (gut: das Modell kann so keine beliebigen Dateien per
    <img src="file://..."> ins PDF ziehen). Nur das Font-Verzeichnis wird
    freigegeben, Remote bleibt aus. Ältere Versionen kennen keine Policy."""
    try:
        from xhtml2pdf.config.resources import ResourceAccessPolicy
    except ImportError:
        return None
    return ResourceAccessPolicy(allow_remote=False, base_dir=_FONT_DIR, allow_local_outside_base=False)


def markdown_to_pdf(markdown_text: str, title: str | None = None) -> bytes:
    # Lazy: dieses Modul wird vom MCP-Server (eigene venv) beim Start importiert -
    # fehlt dort ein PDF-Paket, soll nur create_pdf scheitern, nicht jedes Tool.
    import markdown as md
    from xhtml2pdf import pisa

    body = re.sub(r"^---\n.*?\n---\n", "", markdown_text, count=1, flags=re.DOTALL)
    body = _signature_blocks(body)
    if title and not re.match(r"\s*#\s", body):
        body = f"# {title}\n\n{body}"
    html = md.markdown(body, extensions=["extra", "sane_lists"])
    full = (
        f"<html><head><meta charset='utf-8'><title>{title or ''}</title>"
        f"<style>{_font_face_css()}\n{_PDF_CSS}</style></head><body>{html}"
        '<div id="footerContent">Seite <pdf:pagenumber> von <pdf:pagecount></div></body></html>'
    )
    buf = io.BytesIO()
    policy = _resource_policy()
    kwargs = {"resource_policy": policy} if policy is not None else {}
    result = pisa.CreatePDF(src=full, dest=buf, encoding="utf-8", **kwargs)
    if result.err:
        raise DocumentError(f"PDF-Rendering fehlgeschlagen ({result.err} Fehler)")
    return buf.getvalue()


def _pdf_text(pdf_bytes: bytes) -> tuple[str, int]:
    import PyPDF2

    reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
    return " ".join(p.extract_text() or "" for p in reader.pages), len(reader.pages)


# ── Zielpfad ────────────────────────────────────────────────────────────────

def _resolve_target(rel: str) -> tuple[Path, str]:
    vault = get_settings().vault_path.resolve()
    rel = rel.strip().lstrip("/")
    if not rel.lower().endswith(".pdf"):
        raise DocumentError("Zielpfad muss auf .pdf enden, z.B. 'Kunden/Firma/Vertraege/2026-09-23-Abnahmeprotokoll.pdf'.")
    target = (vault / rel).resolve()
    if not str(target).startswith(str(vault)):
        raise DocumentError("Zielpfad liegt außerhalb des Vaults.")
    parts = target.relative_to(vault).parts
    if len(parts) < 2:
        raise DocumentError("Zielpfad braucht einen Ordner (z.B. 'Kunden/<Firma>/...'), nicht den Vault-Root.")
    if any(p in _FORBIDDEN_TARGETS or p.startswith(".") for p in parts):
        raise DocumentError("In diesen Ordner (System-/App-Verzeichnis) dürfen keine Dokumente geschrieben werden.")
    return target, "/".join(parts)


# ── Hauptfunktion ───────────────────────────────────────────────────────────

def _today_facts_ok(fact: Fact) -> bool:
    if fact.typ != "datum":
        return False
    t = date.today()
    y, mo, d = fact.key
    return (mo, d) == (t.month, t.day) and (y is None or y == t.year)


def _is_freigegeben(fact: Fact, freigegeben: list[str]) -> bool:
    ft = _fold(fact.text)
    return any(ft in _fold(entry) for entry in freigegeben)


def create_pdf(
    pfad: str,
    titel: str,
    markdown_text: str,
    quellen: list[str],
    weitere_fakten: list[str] | None = None,
    freigegeben: list[str] | None = None,
    ueberschreiben: bool = False,
) -> dict:
    weitere_fakten = weitere_fakten or []
    freigegeben = freigegeben or []
    try:
        target, rel = _resolve_target(pfad)
        if target.exists() and not ueberschreiben:
            return {
                "ok": False,
                "error": f"'{rel}' existiert bereits. Anderen Dateinamen wählen (z.B. mit Versionssuffix) - "
                         "ueberschreiben=true nur, wenn Sebastian ausdrücklich diese Datei ändern will.",
            }
        if not markdown_text.strip():
            return {"ok": False, "error": "Leerer Dokumentinhalt."}

        corpus, used_sources = load_corpus(quellen)

        facts = extract_facts(markdown_text)
        folded_doc = _fold(markdown_text)
        for extra in weitere_fakten:
            if _fold(extra) not in folded_doc:
                return {
                    "ok": False,
                    "error": f"weitere_fakten-Eintrag '{extra}' kommt im Dokumenttext nicht wörtlich vor - "
                             "so schreiben, wie er im Dokument steht.",
                }
            facts.append(Fact("name", extra, _fold(extra)))

        unverified = [
            f for f in facts
            if not corpus.has(f) and not _today_facts_ok(f) and not _is_freigegeben(f, freigegeben)
        ]
        if unverified:
            return {
                "ok": False,
                "error": "PDF NICHT erstellt: folgende Angaben stehen in keiner der genannten Quellen. "
                         "Gegen die Originaldokumente prüfen und korrigieren; nur bei bewusst neuen oder "
                         "berechneten Angaben (Sebastian hat sie genannt / Rechnung offenlegen) unter "
                         "`freigegeben` aufführen.",
                "nicht_verifiziert": [{"typ": f.typ, "text": f.text} for f in unverified],
                "geprueft_gegen": used_sources,
            }

        pdf = markdown_to_pdf(markdown_text, titel)

        # Gegenprobe am fertigen PDF: jeder Fakt muss im gerenderten Text stehen.
        pdf_text, pages = _pdf_text(pdf)
        rendered = _Corpus(pdf_text)
        lost = [f for f in facts if not rendered.has(f)]
        if lost:
            return {
                "ok": False,
                "error": "PDF NICHT gespeichert: Gegenprobe am gerenderten PDF fehlgeschlagen "
                         "(Angaben fehlen/sind verändert im PDF-Text).",
                "im_pdf_nicht_auffindbar": [{"typ": f.typ, "text": f.text} for f in lost],
            }

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(pdf)
        src_file = get_settings().vault_path / "_agent" / "documents_src" / (rel[:-4] + ".md")
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text(markdown_text, encoding="utf-8")
        threading.Thread(target=rag.reindex_new_files, daemon=True).start()

        by_type: dict[str, int] = {}
        for f in facts:
            by_type[f.typ] = by_type.get(f.typ, 0) + 1
        return {
            "ok": True,
            "path": rel,
            "download_url": "/api/files/download/" + rel,
            "seiten": pages,
            "quelltext_markdown": "_agent/documents_src/" + rel[:-4] + ".md",
            "verifiziert": {"anzahl": len(facts), "nach_typ": by_type, "gegen": used_sources},
            "freigegeben_nicht_in_quellen": freigegeben,
            "hinweis": "Nur mechanisch prüfbare Fakten (Daten, Beträge, Nummern, Namen) sind belegt. "
                       "Statusaussagen/Bewertungen im Text hast DU zu verantworten - vorher gegen den echten Stand prüfen.",
        }
    except DocumentError as e:
        return {"ok": False, "error": str(e)}
