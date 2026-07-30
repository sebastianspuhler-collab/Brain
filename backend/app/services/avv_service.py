"""AVV (Auftragsverarbeitungsvertrag) aus einer .docx-Vorlage befüllen.

Ersetzt Platzhalter direkt im XML der .docx (die ist ein ZIP-Archiv) statt
mit einer schweren docx-Library - reicht für reine Text-Platzhalter aus und
bleibt formatierungstreu zur Vorlage."""
import subprocess
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path

from app.config import get_settings

_FALLBACK = "— bitte ergänzen —"

BESCHAFFUNGSAGENT_AVV = {
    "produkt_name": "Beschaffungsagent",
    "produkt_beschreibung": "Beschaffungsdokumenten (Auftragsbestätigungen, Lieferscheine, Versanddokumente)",
    "ki_dienst_beschreibung": "Azure OpenAI Service, Region Sweden Central",
    "unterauftragnehmer_ki_firma": "Microsoft Ireland Operations Limited (Azure OpenAI Service)",
    "unterauftragnehmer_ki_land": "Irland",
    "unterauftragnehmer_ki_region": "Sweden Central (EU)",
    "unterauftragnehmer_ki_leistung": "KI-Sprachmodellen (Azure OpenAI Service) zur automatisierten Dokumentenanalyse/-erkennung der Beschaffungsdokumente",
}

STUECKLISTENAGENT_AVV = {
    "produkt_name": "Stücklistenagent",
    "produkt_beschreibung": "Stücklisten und Fertigungsunterlagen",
    "ki_dienst_beschreibung": "Azure OpenAI Service, Region Sweden Central",
    "unterauftragnehmer_ki_firma": "Microsoft Ireland Operations Limited (Azure OpenAI Service)",
    "unterauftragnehmer_ki_land": "Irland",
    "unterauftragnehmer_ki_region": "Sweden Central (EU)",
    "unterauftragnehmer_ki_leistung": "KI-Sprachmodellen (Azure OpenAI Service) zur automatisierten Dokumentenanalyse/-erkennung der Stücklisten",
}


class AvvTemplateMissing(Exception):
    pass


class PdfConversionError(Exception):
    pass


def docx_bytes_to_pdf_bytes(docx_bytes: bytes, timeout: int = 60) -> bytes:
    """Konvertiert eine befüllte .docx (z.B. fill_avv()'s Rückgabe) 1:1 nach
    PDF, ohne eigenes Layout nachzubauen (Sebastian, 2026-07-30: erster
    Schritt ist die bestehende DOCX-Vorlage exportierbar machen, kein neues
    Design). LibreOffice headless statt einer reinen Python-Lösung, weil
    keine Python-Bibliothek Word-Layout (Tabellen, Absatzformate der Vorlage)
    zuverlässig nachbildet - `soffice --convert-to pdf` rendert dieselbe
    Engine, die auch Word-Dokumente sonst darstellt. Braucht `libreoffice` im
    Docker-Image (siehe Dockerfile)."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        docx_path = tmp_path / "input.docx"
        docx_path.write_bytes(docx_bytes)
        try:
            result = subprocess.run(
                [
                    "soffice", "--headless", "--norestore",
                    "--convert-to", "pdf", "--outdir", str(tmp_path), str(docx_path),
                ],
                capture_output=True, text=True, timeout=timeout,
            )
        except FileNotFoundError as e:
            raise PdfConversionError(
                "LibreOffice (soffice) nicht gefunden - muss im Docker-Image installiert sein."
            ) from e
        except subprocess.TimeoutExpired as e:
            raise PdfConversionError(f"PDF-Konvertierung Timeout nach {timeout}s") from e

        pdf_path = tmp_path / "input.pdf"
        if result.returncode != 0 or not pdf_path.exists():
            raise PdfConversionError(
                f"soffice-Konvertierung fehlgeschlagen (exit {result.returncode}): "
                f"{result.stderr[:500] or result.stdout[:500]}"
            )
        return pdf_path.read_bytes()


def build_replacements(data: dict, avv_data: dict) -> dict[str, str]:
    return {
        "{{KUNDE_FIRMA}}": data.get("kundenname", ""),
        "{{KUNDE_ADRESSE}}": data.get("kunde_adresse") or _FALLBACK,
        "{{PRODUKT_NAME}}": avv_data["produkt_name"],
        "{{PRODUKT_BESCHREIBUNG}}": avv_data["produkt_beschreibung"],
        "{{BESTELLNUMMER}}": data.get("bestellnummer") or _FALLBACK,
        "{{BESTELLDATUM}}": data.get("bestelldatum") or _FALLBACK,
        "{{ANGEBOTSNUMMER}}": data.get("angebotsnummer") or _FALLBACK,
        "{{ANGEBOTSDATUM}}": data.get("angebotsdatum") or _FALLBACK,
        "{{KI_DIENST_BESCHREIBUNG}}": avv_data["ki_dienst_beschreibung"],
        "{{UNTERAUFTRAGNEHMER_KI_FIRMA}}": avv_data["unterauftragnehmer_ki_firma"],
        "{{UNTERAUFTRAGNEHMER_KI_LAND}}": avv_data["unterauftragnehmer_ki_land"],
        "{{UNTERAUFTRAGNEHMER_KI_REGION}}": avv_data["unterauftragnehmer_ki_region"],
        "{{UNTERAUFTRAGNEHMER_KI_LEISTUNG}}": avv_data["unterauftragnehmer_ki_leistung"],
    }


def fill_avv(replacements: dict[str, str]) -> bytes:
    template_path = get_settings().avv_template_path
    if not template_path.exists():
        raise AvvTemplateMissing(
            f"AVV-Vorlage fehlt unter {template_path} - muss einmalig manuell abgelegt werden."
        )

    output = BytesIO()
    with zipfile.ZipFile(template_path, "r") as zin, zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            content = zin.read(item.filename)
            if item.filename == "word/document.xml":
                text = content.decode("utf-8")
                for placeholder, value in replacements.items():
                    text = text.replace(placeholder, value)
                content = text.encode("utf-8")
            zout.writestr(item, content)
    return output.getvalue()
