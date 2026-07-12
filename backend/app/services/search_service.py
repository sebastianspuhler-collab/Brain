"""Gezielte Keyword-Suchen für den Chat-Tool-Use-Loop, getrennt von der
allgemeinen semantischen RAG-Suche. Migriert aus brain_server.py
(search_meetings, search_emails)."""
import re

from app.config import get_settings

_SKIP_EMAIL_CACHE_NAMES = {
    "indexed_ids.json", "deep_scan_done.flag", "downloaded_attachments.json",
}


def search_emails(query: str, max_results: int = 5) -> str:
    """Sucht im E-Mail-Cache nach Dateiname (Betreff) + Header (Von/Datum)."""
    keywords = [w.lower() for w in re.split(r"[\s,;/]+", query) if len(w) >= 3]
    if not keywords:
        return "Kein Suchbegriff angegeben."

    settings = get_settings()
    try:
        all_files = sorted(
            (f for f in settings.email_cache_dir.glob("*.md")
             if f.name not in _SKIP_EMAIL_CACHE_NAMES and f.is_file()),
            key=lambda f: f.stat().st_mtime, reverse=True,
        )
    except Exception:
        all_files = []

    results = []
    for f in all_files:
        try:
            content = f.read_text(errors="ignore")
            searchable = f.stem.lower() + "\n" + content[:800].lower()
            if any(kw in searchable for kw in keywords):
                results.append(f"[{f.name}]\n{content[:3500]}")
                if len(results) >= max_results:
                    break
        except Exception:
            pass

    if not results:
        return (
            f"Keine E-Mails gefunden für: '{query}'.\n"
            f"Tipp: Versuche andere Schlüsselwörter (Absender-Nachname, Firmenname, Betreff-Wort)."
        )
    return "\n\n".join(results)


def search_meetings(query: str, firma: str = "", max_results: int = 5) -> str:
    """Sucht in Kunden/*/Meetings/ und Kunden/*/Dokumente/ nach Transkripten und Protokollen."""
    keywords = [w.lower() for w in re.split(r"[\s,;/]+", query) if len(w) >= 2]
    if not keywords:
        return "Kein Suchbegriff angegeben."

    settings = get_settings()
    search_dirs = []
    kunden_dir = settings.vault_path / "Kunden"
    if kunden_dir.exists():
        for firma_dir in sorted(kunden_dir.iterdir()):
            if not firma_dir.is_dir():
                continue
            if firma and firma.lower() not in firma_dir.name.lower():
                continue
            for sub in ("Meetings", "Dokumente"):
                sub_dir = firma_dir / sub
                if sub_dir.exists():
                    search_dirs.append(sub_dir)

    results = []
    for search_dir in search_dirs:
        for f in sorted(search_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                content = f.read_text(errors="ignore")
                searchable = f.stem.lower() + "\n" + content.lower()
                if any(kw in searchable for kw in keywords):
                    rel_path = f.relative_to(settings.vault_path)
                    results.append(f"[{rel_path}]\n{content[:3500]}")
                    if len(results) >= max_results:
                        break
            except Exception:
                pass
        if len(results) >= max_results:
            break

    if not results:
        return f"Keine Meeting-Transkripte gefunden für: '{query}'" + (f" (Firma: {firma})" if firma else "") + "."
    return "\n\n".join(results)
