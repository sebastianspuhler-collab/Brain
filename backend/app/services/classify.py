"""Inbox-Verarbeitung: Dateien klassifizieren, Text extrahieren, ablegen.
Migriert aus _agent/heartbeat.py. Als importierbares Modul statt Subprocess-Aufruf,
damit der Chat-Endpoint (/api/inbox_process) es direkt callen kann statt einen
neuen Python-Prozess zu starten.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

from app.config import get_settings
from app.services.anthropic_client import get_client

SKIP_EXTENSIONS = {
    ".js", ".ts", ".map", ".mjs", ".jsx", ".tsx", ".css",
    ".yml", ".yaml", ".eslintrc", ".nycrc", ".npmignore",
    ".enc", ".lock", ".editorconfig", ".orig",
}
SKIP_NAMES = {
    "Thumbs.db", ".DS_Store", "package-lock.json", "package.json",
    "tsconfig.json", "tsdoc-metadata.json", "openai",
}
SKIP_PREFIXES = ("README", "readme", "LICENSE", "license", "CHANGELOG",
                  "HISTORY", "History", "CONTRIBUTING", "contributing")
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".mp4", ".mov", ".mp3"}


def _cache_path() -> Path:
    return get_settings().agent_dir / "logs" / "processed_cache.json"


def _load_cache() -> set:
    path = _cache_path()
    if path.exists():
        try:
            return set(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            return set()
    return set()


def _save_cache(cache: set) -> None:
    _cache_path().write_text(json.dumps(list(cache)), encoding="utf-8")


def extract_text(filepath: Path) -> str | None:
    suffix = filepath.suffix.lower()
    try:
        if suffix == ".pdf":
            import PyPDF2

            with open(filepath, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return " ".join(page.extract_text() or "" for page in reader.pages)[:3000]
        if suffix == ".docx":
            from docx import Document

            doc = Document(filepath)
            return " ".join(p.text for p in doc.paragraphs)[:3000]
        if suffix in (".xlsx", ".xls"):
            import openpyxl

            wb = openpyxl.load_workbook(filepath, read_only=True)
            text = []
            for ws in wb.worksheets:
                for row in ws.iter_rows(values_only=True):
                    text.append(" ".join(str(c) for c in row if c))
            return " ".join(text)[:3000]
        if suffix in (".pptx", ".ppt"):
            from pptx import Presentation

            prs = Presentation(filepath)
            text = []
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text.append(shape.text)
            return " ".join(text)[:3000]
        if suffix == ".html":
            from html.parser import HTMLParser

            class TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.parts: list[str] = []

                def handle_data(self, data):
                    self.parts.append(data)

            p = TextExtractor()
            p.feed(filepath.read_text(encoding="utf-8", errors="ignore"))
            return " ".join(p.parts)[:3000]
        if suffix == ".json":
            raw = filepath.read_text(encoding="utf-8", errors="ignore")[:3000]
            return f"[JSON-Datei] {raw}"
        if suffix in (".txt", ".md", ".markdown", ".csv"):
            return filepath.read_text(encoding="utf-8", errors="ignore")[:3000]
        if suffix in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"):
            return "[Bilddatei, kein Text extrahierbar]"
        if suffix in (".mp4", ".mov", ".avi", ".mkv", ".mp3"):
            return "[Mediendatei, kein Text extrahierbar]"
        if suffix == ".zip":
            return "[ZIP-Archiv]"
        return f"[Unbekanntes Format: {suffix}]"
    except Exception:
        return None


def _load_memory_rules() -> str:
    settings = get_settings()
    if not settings.memory_path.exists():
        return ""
    lines = []
    in_section = False
    for line in settings.memory_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## REGEL") or line.startswith("## PROZESS"):
            in_section = True
        elif line.startswith("## ") and in_section:
            in_section = False
        elif in_section and line.startswith("- "):
            lines.append(line)
    return "\n".join(lines)


def classify(filepath: Path, content: str) -> dict | None:
    settings = get_settings()
    relative = filepath.relative_to(settings.inbox_dir)
    ordner_kontext = str(relative.parent) if str(relative.parent) != "." else ""
    memory_rules = _load_memory_rules()

    prompt = f"""Klassifiziere dieses Dokument für Prozessia GbR (KI-Agentur, Saarbrücken).
Dateiname: {filepath.name}
Unterordner in Inbox: {ordner_kontext or "keiner"}
Inhalt: {content}

Bekannte Kunden: Schaufler, Mundinger, Jochem/nanoSaar, Voigt Salus, Fonio
Bekannte Produkte: Beschaffungsagent, Stücklistenagent, KI-Schulung
Vertrieb: Handelsvertreter, Gegina, Segschneider
{f"Gelernte Ablageregeln:{chr(10)}{memory_rules}" if memory_rules else ""}

Mögliche Zielordner:
- Kunden/Schaufler, Kunden/Mundinger, Kunden/Jochem_nanoSaar, Kunden/[NeuerKunde]
- Leads
- Produkte/Beschaffungsagent, Produkte/Stuecklistenagent
- Vertraege
- Marketing/Flyer, Marketing/LinkedIn, Marketing/Webinar, Marketing/Branding, Marketing/Social-Media
- Sales/Cold_Call, Sales/Praesentationen, Sales/Handelsvertreter
- Finanzen/Rechnungen, Finanzen/Angebote
- Uni
- Memos
- Memos/Medien (für Bilder/Videos ohne klare Kategorie)

Bestimme:
1. kategorie: Kunde/Lead/Produkt/Vertrag/Marketing/Sales/Finanzen/Uni/Memo
2. zusammenfassung: 2-3 Sätze was das Dokument enthält (bei Medien: kurze Beschreibung)
3. tags: 3-5 relevante Tags als JSON-Array
4. zielordner: exakter relativer Pfad aus den Möglichen Zielordnern oben

Antworte NUR als JSON, keine Erklärung."""

    try:
        resp = get_client().messages.create(
            model="claude-sonnet-5", max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception:
        return None


def process_file(filepath: Path) -> tuple[bool, str]:
    settings = get_settings()
    if filepath.suffix.lower() in SKIP_EXTENSIONS:
        return False, "Code-Datei übersprungen"

    content = extract_text(filepath)
    if content is None:
        return False, "Extraktion fehlgeschlagen"

    result = classify(filepath, content)
    if not result:
        return False, "API-Klassifizierung fehlgeschlagen"

    zielordner = settings.vault_path / result.get("zielordner", "Memos")
    zielordner.mkdir(parents=True, exist_ok=True)
    datum = datetime.now().strftime("%Y-%m-%d")

    if filepath.suffix.lower() not in IMAGE_EXTS | {".zip"}:
        tags = result.get("tags", [])
        tags_str = "\n".join(f"  - {t}" for t in tags)
        notiz_path = zielordner / f"{datum}-{filepath.stem}.md"
        notiz_path.write_text(
            f"""---
tags:
{tags_str}
quelle: {filepath.name}
datum: {datum}
kategorie: {result.get("kategorie", "")}
---

# {filepath.stem}

## Zusammenfassung
{result.get("zusammenfassung", "")}

## Vollständiger Inhalt
{content[:6000]}
""",
            encoding="utf-8",
        )

    safe_name = filepath.name.replace("@", "-at-")
    ziel_original = zielordner / safe_name
    ziel = ziel_original if not ziel_original.exists() else zielordner / f"{datum}-{safe_name}"
    try:
        shutil.move(str(filepath), str(ziel))
    except Exception:
        try:
            shutil.copy2(str(filepath), str(ziel))
            filepath.unlink(missing_ok=True)
        except Exception:
            pass

    log_path = settings.agent_dir / "logs" / "inbox_log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(
            f"- {datetime.now().strftime('%Y-%m-%d %H:%M')} | {filepath.name} → "
            f"{result.get('zielordner')} | {result.get('zusammenfassung', '')[:80]}\n"
        )

    return True, result.get("zielordner", "")


def run_inbox() -> dict:
    """Verarbeitet alle neuen Dateien in _inbox/. Entspricht heartbeat.py:run()."""
    settings = get_settings()
    fehler_path = settings.inbox_dir / "_fehler"
    daily_path = settings.agent_dir / "daily"
    fehler_path.mkdir(parents=True, exist_ok=True)
    daily_path.mkdir(parents=True, exist_ok=True)

    dateien = [
        f for f in settings.inbox_dir.rglob("*")
        if f.is_file()
        and not f.name.startswith(".")
        and f.suffix.lower() not in SKIP_EXTENSIONS
        and f.name not in SKIP_NAMES
        and not any(f.name.startswith(p) for p in SKIP_PREFIXES)
        and "node_modules" not in str(f)
        and "_fehler" not in str(f)
    ]

    cache = _load_cache()
    dateien = [d for d in dateien if str(d) not in cache]

    if not dateien:
        return {"processed": 0, "errors": 0, "output": "Inbox leer (alle Dateien bereits verarbeitet)."}

    processed = 0
    errors = 0
    log_lines = []
    for datei in dateien:
        try:
            ok, info = process_file(datei)
        except Exception as e:
            ok, info = False, f"Unerwarteter Fehler: {e}"
        if ok:
            cache.add(str(datei))
            _save_cache(cache)
            processed += 1
            log_lines.append(f"{datei.name} -> {info}")
        else:
            errors += 1
            log_lines.append(f"{datei.name}: FEHLER {info}")
            if info != "Code-Datei übersprungen":
                try:
                    shutil.move(str(datei), str(fehler_path / datei.name))
                except Exception:
                    pass

    daily_file = daily_path / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    with open(daily_file, "a", encoding="utf-8") as f:
        f.write(f"\n## Inbox-Verarbeitung {datetime.now().strftime('%H:%M')}\n")
        f.write(f"- Verarbeitet: {processed}\n")
        f.write(f"- Fehler: {errors}\n")

    return {"processed": processed, "errors": errors, "output": "\n".join(log_lines)}
