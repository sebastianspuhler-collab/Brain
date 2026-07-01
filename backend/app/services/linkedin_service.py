"""LinkedIn-Autoposter-Bridge. Migriert aus brain_server.py (api_linkedin_*).
Liest/schreibt JSON-Output des externen Autoposter-Skripts im Vault."""
import json
import re
from datetime import datetime

from app.config import get_settings
from app.services import cache
from app.services.anthropic_client import get_client


def _direction_path():
    return get_settings().autoposter_dir / "brain-direction.md"


def _latest_file(prefix: str):
    out = get_settings().autoposter_dir / "output"
    if not out.exists():
        return None
    files = sorted(out.glob(f"{prefix}-*.json"), reverse=True)
    return files[0] if files else None


def get_ideas() -> dict:
    cached = cache.get("li_ideas")
    if cached is not None:
        return cached
    path = _latest_file("ideen")
    if not path:
        return {"ideen": [], "datum": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        result = {
            "datum": data.get("generiert_am", "")[:10],
            "ideen": [
                {
                    "titel": i.get("titel", ""),
                    "hook": i.get("hook", ""),
                    "kategorie": i.get("kategorie", ""),
                    "format": i.get("format_empfehlung", ""),
                    "cta": i.get("cta_vorschlag", ""),
                }
                for i in data.get("ideen", [])
            ],
        }
        cache.set("li_ideas", result)
        return result
    except Exception as e:
        return {"ideen": [], "datum": None, "error": str(e)}


def get_posts() -> dict:
    cached = cache.get("li_posts")
    if cached is not None:
        return cached
    path = _latest_file("beitraege")
    if not path:
        return {"posts": [], "datum": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        posts = []
        for key in ("donnerstag", "freitag", "montag", "dienstag", "mittwoch"):
            p = data.get(key)
            if not p:
                continue
            posts.append({
                "tag": key.capitalize(),
                "termin": p.get("termin", ""),
                "idee": p.get("idee", ""),
                "text_preview": p.get("text", "")[:200],
            })
        result = {"datum": path.stem.replace("beitraege-", ""), "posts": posts}
        cache.set("li_posts", result)
        return result
    except Exception as e:
        return {"posts": [], "datum": None, "error": str(e)}


def _current_direction() -> str:
    path = _direction_path()
    if not path.exists():
        return ""
    match = re.search(r"## Aktuelle Richtung\n\n(.+?)(?:\n---|\Z)", path.read_text(encoding="utf-8"), re.DOTALL)
    return match.group(1).strip() if match else ""


def get_direction() -> dict:
    return {"prompt": _current_direction()}


def set_direction(prompt: str) -> dict:
    if not prompt.strip():
        return {"error": "Kein Prompt"}
    path = _direction_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    path.write_text(
        f"""# Brain-Richtungsvorgabe für LinkedIn Autoposter
*Gesetzt am: {ts} von Sebastian via Brain UI*

## Aktuelle Richtung

{prompt.strip()}

---
*Diese Datei wird beim nächsten Autoposter-Run gelesen.*
""",
        encoding="utf-8",
    )
    return {"ok": True, "path": str(path)}


def generate_ideas(focus: str = "") -> dict:
    current_direction = _current_direction()
    prompt = f"""Du bist LinkedIn-Content-Stratege für Prozessia (KI-Automatisierung für produzierende KMU, 20-80 MA, DACH).
Zielgruppe: Einkaufsleiter, Produktionsleiter, Geschäftsführer im Mittelstand.
Themen: KI-Beschaffung, Automatisierung, EU AI Act, Produktivität, Mittelstand.

{f"Richtungsvorgabe von Sebastian: {current_direction}" if current_direction else ""}
{f"Zusätzlicher Fokus: {focus}" if focus else ""}

Generiere genau 10 LinkedIn-Ideen als JSON. Jede Idee muss enthalten:
- kategorie: "Einkauf" | "Industrie" | "Compliance" | "KI-Tipp" | "Kundenstory"
- branche: z.B. "Maschinenbau", "Allgemein", "Werkzeugbau"
- titel: prägnanter Titel (max 60 Zeichen)
- hook: erste Zeile des Posts - neugierig machend (max 80 Zeichen)
- kern_botschaft: was der Leser mitnimmt
- zielgruppe_spezifisch: konkrete Persona (z.B. "Einkaufsleiter Werkzeugbau, 60 MA")
- format_empfehlung: "Text" | "Karussell" | "Liste" | "Story"
- cta_vorschlag: Abschlussfrage oder Call-to-Action

Antworte NUR mit validem JSON, kein Markdown drumherum:
{{"generiert_am": "ISO-DATUM", "anzahl": 10, "ideen": [...]}}"""

    try:
        result = get_client().messages.create(
            model="claude-sonnet-4-6", max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = result.content[0].text.strip()
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {"error": "Kein JSON in Antwort"}
        data = json.loads(match.group())
        data["generiert_am"] = datetime.now().isoformat()
        data["anzahl"] = len(data.get("ideen", []))

        out_path = get_settings().autoposter_dir / "output" / f"ideen-{datetime.now().strftime('%Y-%m-%d')}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        cache.invalidate("li_ideas")

        return {"ok": True, "anzahl": data["anzahl"], "ideen": [
            {"titel": i.get("titel", ""), "hook": i.get("hook", ""),
             "kategorie": i.get("kategorie", ""), "format": i.get("format_empfehlung", ""),
             "cta": i.get("cta_vorschlag", "")}
            for i in data.get("ideen", [])
        ]}
    except Exception as e:
        return {"error": str(e)}


def generate_posts(spec: str) -> dict:
    current_direction = _current_direction()
    prompt = f"""Du bist LinkedIn-Texter für Prozessia (KI-Automatisierung für produzierende KMU, 20-80 MA, DACH).
Zielgruppe: Einkaufsleiter, Produktionsleiter, Geschäftsführer im Mittelstand.
Stil: sachlich, direkt, keine leeren Phrasen, kein "In der heutigen Zeit". Mit konkreten Zahlen.
Max. 1.200 Zeichen pro Post. Keine Emojis außer 1-2 sparsam. Hashtags am Ende (3-5).

{f"Richtungsvorgabe: {current_direction}" if current_direction else ""}

Spezifikation für die Posts:
{spec}

Schreibe jeden Post vollständig aus. Antworte NUR mit validem JSON:
{{
  "generiert_am": "ISO-DATUM",
  "posts": [
    {{
      "tag": "Dienstag",
      "datum": "YYYY-MM-DD",
      "thema": "Themenname",
      "text": "Vollständiger Post-Text fertig zum Kopieren"
    }}
  ]
}}"""

    try:
        result = get_client().messages.create(
            model="claude-sonnet-4-6", max_tokens=6000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = result.content[0].text.strip()

        posts = []
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
                posts = data.get("posts", [])
        except Exception:
            pass

        if not posts:
            blocks = re.split(r"\n#+\s+", raw)
            for block in blocks:
                day_match = re.search(r"(Montag|Dienstag|Mittwoch|Donnerstag|Freitag)", block, re.IGNORECASE)
                date_match = re.search(r"(\d{4}-\d{2}-\d{2})", block)
                if day_match and date_match:
                    posts.append({
                        "tag": day_match.group(1),
                        "datum": date_match.group(1),
                        "thema": block.split("\n")[0].strip()[:80],
                        "text": block.strip()[:1500],
                    })

        if not posts:
            return {"error": "Keine Posts extrahiert", "raw": raw[:500]}

        out_data = {"generiert_am": datetime.now().isoformat(), "kanaele": [], "planungen": []}
        for p in posts:
            key = p.get("tag", "").lower()
            out_data[key] = {
                "termin": f"{p.get('datum', '')}T09:30:00+02:00",
                "idee": p.get("thema", ""),
                "text": p.get("text", ""),
            }
        out_path = get_settings().autoposter_dir / "output" / f"beitraege-{datetime.now().strftime('%Y-%m-%d')}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out_data, ensure_ascii=False, indent=2), encoding="utf-8")
        cache.invalidate("li_posts")
        return {"ok": True, "posts": posts}
    except Exception as e:
        return {"error": str(e)}
