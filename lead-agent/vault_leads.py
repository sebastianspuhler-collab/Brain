"""Lesen/Schreiben von Leads/*.md im Vault - eigenständige Kopie des
Frontmatter-Musters aus backend/app/services/email_lead_service.py
(_write_lead_stub) und backend/app/services/kunden_status_service.py
(Frontmatter-Auslesen per Zeilen-Regex statt einer YAML-Bibliothek - im
ganzen Repo gibt es keinen einzigen YAML-Parser, dieselbe Konvention wird
hier übernommen statt eine neue Abhängigkeit einzuführen).

NEU gegenüber der bestehenden Konvention (System-Überblick §7: "kein
close_lead_id-Feld, keine Referenz-ID-Konvention"): drei zusätzliche
Frontmatter-Felder, die nur der Lead-Agent liest/schreibt und die die
bestehende Pipeline (classify.py, kunden_status_service.py) unangetastet
lassen, weil sie zusätzliche Zeilen sind, keine Änderung bestehender Felder:
  close_lead_id: <Close-Lead-ID oder leer>
  status: neu | kontaktiert | qualifiziert | heiss | verloren | gewonnen
  score: <Zahl oder leer>
"""
import re
from datetime import datetime
from pathlib import Path

from config import get_settings

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def _sanitize(name: str) -> str:
    return re.sub(r"[^\w\s-]", "", name)[:60].strip().replace(" ", "-")


def leads_dir() -> Path:
    d = get_settings().leads_dir
    d.mkdir(parents=True, exist_ok=True)
    return d


def _all_lead_files() -> list[Path]:
    """Flache Leads/*.md UND Leads/MD/*.md (siehe bestehende Konvention,
    beide Orte kommen im Repo real vor) - bewusst NICHT rekursiv in
    Leads/Sales-Briefs/, sonst tauchen generierte Briefs als eigene "Leads" auf."""
    d = leads_dir()
    files = [p for p in d.glob("*.md") if p.is_file()]
    md_sub = d / "MD"
    if md_sub.exists():
        files += [p for p in md_sub.glob("*.md") if p.is_file()]
    return files


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Gibt (felder, body) zurück. Felder werden zeilenweise per Regex
    gelesen (kein YAML-Parser im Repo, siehe kunden_status_service.py:117)."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    fm_text, body = match.group(1), match.group(2)
    fields: dict[str, str] = {}
    for line in fm_text.splitlines():
        m = re.match(r"^([a-zA-Z_]+):\s*(.*)$", line)
        if m:
            fields[m.group(1)] = m.group(2).strip()
    return fields, body


def read_lead(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="ignore")
    fields, body = parse_frontmatter(text)
    return {"path": str(path), "filename": path.name, "fields": fields, "body": body}


def find_lead(name_or_path: str) -> dict | None:
    """Exakter Pfad zuerst, sonst Stichwortsuche im Dateinamen (wie
    backend/app/services/tools.py::_tool_read_file, gleiches Prinzip)."""
    settings = get_settings()
    direct = settings.vault_path / name_or_path
    if direct.exists() and direct.is_file():
        return read_lead(direct)

    needle = name_or_path.lower().strip()
    for p in _all_lead_files():
        if needle in p.stem.lower():
            return read_lead(p)
    return None


def find_lead_by_close_id(close_lead_id: str) -> dict | None:
    for p in _all_lead_files():
        lead = read_lead(p)
        if lead["fields"].get("close_lead_id") == close_lead_id:
            return lead
    return None


def list_leads(filter_text: str = "") -> list[dict]:
    needle = filter_text.lower().strip()
    result = []
    for p in _all_lead_files():
        lead = read_lead(p)
        if lead["fields"].get("kategorie") == "Archiv":
            continue
        if needle:
            haystack = f"{p.stem} {lead['body']}".lower()
            if needle not in haystack:
                continue
        result.append(lead)
    return result


def write_prospect(firma: str, kontakt_name: str = "", kontakt_email: str = "", notiz: str = "", quelle: str = "Recherche") -> Path:
    """Legt einen neuen Lead an, den der Agent selbst recherchiert hat -
    Gegenstück zu email_lead_service._write_lead_stub()/
    calendar_lead_service._write_lead_stub() für die dritte Quelle
    "Lead-Agent-Recherche". Gleiche Frontmatter-Grundstruktur, ergänzt um die
    drei Sync-Felder aus dem Modul-Docstring."""
    datum = datetime.now().strftime("%Y-%m-%d")
    safe_name = _sanitize(firma) or "Unbekannt"
    path = leads_dir() / f"{datum}-{safe_name}.md"
    kontakt_block = ""
    if kontakt_name or kontakt_email:
        kontakt_block = f"\n## Kontakt\n{kontakt_name}".strip()
        if kontakt_email:
            kontakt_block += f" ({kontakt_email})"
        kontakt_block += "\n"

    body = f"""---
tags:
  - Lead
  - Lead-Agent-Recherche
quelle: {quelle}
datum: {datum}
kategorie: Lead
close_lead_id:
status: neu
score:
---

# {firma}

## Zusammenfassung
{notiz or 'Vom Lead-Agenten recherchierter Prospect, passend zum ICP aus PLAYBOOK.md.'}
{kontakt_block}"""
    path.write_text(body, encoding="utf-8")
    return path


def update_fields(path: Path, updates: dict) -> None:
    """Aktualisiert/ergänzt einzelne Frontmatter-Felder, ohne den restlichen
    Freitext-Body ODER andere Frontmatter-Zeilen anzufassen - genutzt von
    sync_lead_to_close (close_lead_id zurückschreiben) und vom
    Webhook-Handler (status/score bei eingehenden Close-Events aktuell
    halten, siehe webhooks.py). BEWUSST zeilenweises Patchen statt Reparsen+
    Neuschreiben der kompletten Frontmatter (wie eine frühere Version das
    tat): "tags" ist ein mehrzeiliges YAML-Array (tags:\n  - Lead\n  - ...),
    das der einfache Zeilen-Regex-Parser (siehe parse_frontmatter) nicht
    rekonstruieren kann - ein Reparse+Rewrite hätte den Tags-Block bei jedem
    Sync/Webhook-Update stillschweigend auf eine leere Zeile zurückgesetzt."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return
    fm_lines = match.group(1).split("\n")
    body = match.group(2)
    remaining = dict(updates)
    for i, line in enumerate(fm_lines):
        m = re.match(r"^([a-zA-Z_]+):\s*(.*)$", line)
        if m and m.group(1) in remaining:
            fm_lines[i] = f"{m.group(1)}: {remaining.pop(m.group(1))}"
    for key, value in remaining.items():
        fm_lines.append(f"{key}: {value}")
    path.write_text(f"---\n{chr(10).join(fm_lines)}\n---\n{body}", encoding="utf-8")
