#!/usr/bin/env python3
"""Einmaliger Backfill für Meeting-Notizen, die vor dem Datums-Fix vom
2026-07-19 (classify.py: _resolve_datum) angelegt wurden und deshalb das
Verarbeitungsdatum statt des echten Gesprächsdatums im Frontmatter tragen
(Sebastian, 2026-07-19).

Liest den bereits im Vault liegenden Notiztext (Zusammenfassung + Transkript),
NICHT das Frontmatter (das enthält ja gerade das falsche Datum und würde das
Modell nur dazu verleiten, es unverändert zurückzugeben). Erkennt das Modell
kein plausibles Datum, bleibt die Datei unangetastet - kein Raten.

Ausführen: python scripts/backfill_meeting_dates.py [--dry-run]
"""
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.services.anthropic_client import get_client, get_response_text  # noqa: E402
from app.constants import Models  # noqa: E402

FRONTMATTER_RE = re.compile(r"^---\n(.*?\n)---\n(.*)$", re.S)
DATUM_LINE_RE = re.compile(r"^datum:\s*\d{4}-\d{2}-\d{2}\s*$", re.M)


def _split_frontmatter(text: str) -> tuple[str, str] | None:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    return m.group(1), m.group(2)


def _extract_datum_llm(body: str) -> str | None:
    prompt = f"""Das ist eine Notiz zu einem Kundengespräch für Prozessia GbR
(Zusammenfassung + Transkript, OHNE das Metadaten-Frontmatter).

Inhalt:
{body[:20000]}

Suche nach einem konkreten, im Text genannten Datum des Gesprächs (z.B. im
Transkript-Header "15. Juni 2026, 09:36AM", in der Zusammenfassung "vom
30.06.2026" o.ä.). Antworte NUR als JSON: {{"datum": "YYYY-MM-DD"}} oder
{{"datum": null}} falls kein eindeutiges, vollständiges Datum (inkl. Jahr)
im Text steht."""
    try:
        resp = get_client().messages.create(
            model=Models.SONNET, max_tokens=100,
            thinking={"type": "disabled"},
            messages=[{"role": "user", "content": prompt}],
        )
        raw = get_response_text(resp).strip().replace("```json", "").replace("```", "").strip()
        return json.loads(raw).get("datum")
    except Exception:
        return None


def _plausibel(datum_str: str | None) -> date | None:
    if not datum_str:
        return None
    try:
        geparst = datetime.strptime(datum_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
    if date(2020, 1, 1) <= geparst <= datetime.now().date():
        return geparst
    return None


def main(dry_run: bool) -> None:
    vault = get_settings().vault_path
    changed, unchanged, skipped = [], [], []

    for md_path in sorted(vault.glob("Kunden/*/Meetings/*.md")):
        text = md_path.read_text(encoding="utf-8")
        split = _split_frontmatter(text)
        if not split:
            skipped.append((md_path, "kein Frontmatter erkannt"))
            continue
        frontmatter, body = split
        m = DATUM_LINE_RE.search(f"---\n{frontmatter}---\n")
        if not m:
            skipped.append((md_path, "kein datum:-Feld im Frontmatter"))
            continue
        altes_datum = re.search(r"\d{4}-\d{2}-\d{2}", m.group(0)).group(0)

        neues_datum = _plausibel(_extract_datum_llm(body))
        if neues_datum is None:
            unchanged.append((md_path, "kein Datum im Text erkennbar"))
            continue
        neues_datum_str = neues_datum.strftime("%Y-%m-%d")
        if neues_datum_str == altes_datum:
            unchanged.append((md_path, "Datum stimmt bereits"))
            continue

        changed.append((md_path, altes_datum, neues_datum_str))
        if dry_run:
            continue

        neuer_text = text.replace(f"datum: {altes_datum}", f"datum: {neues_datum_str}", 1)
        md_path.write_text(neuer_text, encoding="utf-8")

        if md_path.name.startswith(f"{altes_datum}-"):
            neuer_name = neues_datum_str + md_path.name[len(altes_datum):]
            ziel = md_path.parent / neuer_name
            if not ziel.exists():
                md_path.rename(ziel)

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Geändert ({len(changed)}):")
    for path, alt, neu in changed:
        print(f"  {path.relative_to(vault)}: {alt} -> {neu}")
    print(f"\nUnverändert, kein Datum erkennbar ({len(unchanged)}):")
    for path, grund in unchanged:
        print(f"  {path.relative_to(vault)}: {grund}")
    if skipped:
        print(f"\nÜbersprungen ({len(skipped)}):")
        for path, grund in skipped:
            print(f"  {path.relative_to(vault)}: {grund}")


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
