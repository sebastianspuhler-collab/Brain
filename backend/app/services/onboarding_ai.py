"""KI-Analyse für den Onboarding-Projekttyp 'Neues Projekt': liest hochgeladene
Dokumente + Freitext-Beschreibung, lässt Claude daraus Repo-Namen, Techstack,
Implementierungsplan, Ticket-Plan und AVV-Angaben extrahieren."""
import json
import re
import tempfile
from pathlib import Path

from app.services import classify
from app.services.anthropic_client import get_client, get_response_text

_SYSTEM_PROMPT = """Du bist ein technischer Projektanalyst bei Prozessia, einer AI Process Automation Agentur für deutschen Mittelstand (Fertigung/Industrie).
Analysiere die bereitgestellten Dokumente und Beschreibung und extrahiere folgende Informationen als JSON:
{
  "repo_name": "technischer GitHub-Repo-Name in kebab-case (z.B. 'endin-procurement-agent')",
  "project_title": "lesbarer Projektname auf Deutsch",
  "produkt_name": "kurzer Produktname für Verträge/AVV",
  "produkt_beschreibung": "kurze Beschreibung der verarbeiteten Dokumente/Daten für AVV",
  "tech_stack": ["React", "FastAPI", "..."],
  "features": ["Feature 1", "Feature 2", "..."],
  "ki_dienst_beschreibung": "verwendeter KI-Dienst inkl. Region",
  "unterauftragnehmer_ki_firma": "vollständiger Firmenname des KI-Providers",
  "unterauftragnehmer_ki_land": "Land des KI-Providers",
  "unterauftragnehmer_ki_region": "Rechenzentrumsregion",
  "unterauftragnehmer_ki_leistung": "Beschreibung der KI-Leistung",
  "implementation_plan": [
    {"phase": "Phase 1", "title": "...", "duration": "2 Wochen", "tasks": ["Task 1", "Task 2"]}
  ],
  "ticket_plan": [
    {"title": "Ticket-Titel", "type": "feature|setup", "priority": "high|medium|low", "description": "..."}
  ],
  "contract_description": "2-3 Sätze Projektbeschreibung für den Dienstleistungsvertrag"
}
Antworte NUR mit dem JSON-Objekt, kein weiterer Text, keine Markdown-Backticks."""


def _extract_uploaded_files(files: list[tuple[str, bytes]]) -> str:
    """Extrahiert Text aus hochgeladenen Dateien via die bestehende
    Inbox-Textextraktion (PDF/DOCX/XLSX/PPTX/Bilder/...)."""
    parts = []
    with tempfile.TemporaryDirectory() as tmp:
        for filename, content in files:
            path = Path(tmp) / filename
            path.write_bytes(content)
            text = classify.extract_text(path)
            if text:
                parts.append(f"=== {filename} ===\n{text}")
    return "\n\n".join(parts)


def analyze_new_project(beschreibung: str, files: list[tuple[str, bytes]]) -> dict:
    files_text = _extract_uploaded_files(files)
    user_content = f"Projektbeschreibung:\n{beschreibung}\n\nHochgeladene Dokumente:\n{files_text or '(keine)'}"

    result = get_client().messages.create(
        model="claude-sonnet-5",
        max_tokens=4000,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    text = get_response_text(result).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("KI-Antwort enthielt kein JSON")
    return json.loads(match.group())
