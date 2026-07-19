#!/usr/bin/env python3
"""Bestandsaufnahme: Dateien in Kunden/*/ und Leads/, die nie durch
classify() gelaufen sind - liegen direkt im Kundenwurzelordner statt in
Meetings/Vertraege/Angebote/Dokumente/Praesentationen und haben keine
.md-Begleitnotiz mit demselben Namensstamm (das Zeichen, dass classify()
eine Datei bereits verarbeitet hat). Bewusst nur eine Liste, KEINE
automatische Verschiebung - bei historischen Altdateien lässt sich der
richtige Zielordner nicht immer sicher erraten (Sebastian, 2026-07-19,
Fund: Kunden/Schaufler/Bestelldruck als loses PDF-Duplikat).

Ausführen: python scripts/find_orphan_files.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402

_STANDARD_ORDNER = {"Meetings", "Vertraege", "Angebote", "Dokumente", "Praesentationen"}
_SKIP_NAMES = {".DS_Store", "Thumbs.db"}


def _hat_md_begleitnotiz(datei: Path) -> bool:
    stem = datei.stem
    return any(
        f.suffix == ".md" and (f.stem == stem or f.stem.endswith(f"-{stem}"))
        for f in datei.parent.glob("*.md")
    )


def main() -> None:
    vault = get_settings().vault_path
    treffer = []

    for basis in (vault / "Kunden", vault / "Leads"):
        if not basis.exists():
            continue
        wurzeln = basis.iterdir() if basis.name == "Kunden" else [basis]
        for wurzel in wurzeln:
            if basis.name == "Kunden" and (not wurzel.is_dir() or wurzel.name.startswith((".", "[", "_"))):
                continue
            for datei in wurzel.iterdir():
                if not datei.is_file() or datei.name in _SKIP_NAMES or datei.name.startswith("."):
                    continue
                if datei.suffix == ".md":
                    continue
                if not _hat_md_begleitnotiz(datei):
                    treffer.append(datei)

    print(f"{len(treffer)} unverarbeitete Datei(en) gefunden:\n")
    for f in sorted(treffer):
        groesse = f.stat().st_size
        print(f"  {f.relative_to(vault)}  ({groesse:,} Bytes, .{f.suffix.lstrip('.')  or 'ohne Endung'})")


if __name__ == "__main__":
    main()
