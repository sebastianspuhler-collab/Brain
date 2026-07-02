"""Generiert den Dienstleistungsvertrag als Markdown aus den Onboarding-Formulardaten."""
from datetime import date

_TEMPLATE = """# Dienstleistungsvertrag

**Auftragnehmer:** Prozessia GbR, Campus Starterzentrum Gebäude A1 1, 66123 Saarbrücken, vertreten durch Mohamed-Amin Douioui und Sebastian Spuhler
**Auftraggeber:** {kunde_firma}, {kunde_adresse}
**Ansprechpartner:** {ansprechpartner_name} ({ansprechpartner_email})
**Datum:** {datum_heute}
**Projektstart:** {projektstart_datum}

---

## 1. Leistungsgegenstand

**Produkt:** {produkt_name}
**Beschreibung:** {produkt_beschreibung}

### Enthaltene Features:
{feature_liste}

---

## 2. Vergütung

| Position | Betrag |
|---|---|
| Einmaliges Setup | {setup_preis} € |
| Monatliche Lizenz & Betrieb | {monatliche_rate} € |

---

## 3. Technische Voraussetzungen

- ERP-System: {erp_system}
- IT-Kontakt: {it_kontakt_name} ({it_kontakt_email})

---

## 4. Referenzdokumente

- Bestellung: {bestellnummer} vom {bestelldatum}
- Angebot: {angebotsnummer} vom {angebotsdatum}

---

## 5. Laufzeit & Kündigung

Der Vertrag beginnt am {projektstart_datum}, hat eine Mindestlaufzeit von 12 Monaten und verlängert sich automatisch um jeweils 12 Monate. Kündigung mit 3 Monaten Frist zum Vertragsende schriftlich.

---

**Saarbrücken, {datum_heute}**

Prozessia GbR ___________________ Mohamed-Amin Douioui / Sebastian Spuhler

{kunde_firma} ___________________ {ansprechpartner_name}
"""

_FALLBACK = "— bitte ergänzen —"


def generate_contract(data: dict, produkt_name: str, produkt_beschreibung: str, features: list[str]) -> str:
    feature_liste = "\n".join(f"- {f}" for f in features) if features else "- (keine Features ausgewählt)"
    return _TEMPLATE.format(
        kunde_firma=data.get("kundenname", ""),
        kunde_adresse=data.get("kunde_adresse") or _FALLBACK,
        ansprechpartner_name=data.get("ansprechpartner_name", ""),
        ansprechpartner_email=data.get("ansprechpartner_email", ""),
        datum_heute=date.today().strftime("%d.%m.%Y"),
        projektstart_datum=data.get("projektstart_datum", ""),
        produkt_name=produkt_name,
        produkt_beschreibung=produkt_beschreibung,
        feature_liste=feature_liste,
        setup_preis=data.get("setup_preis", ""),
        monatliche_rate=data.get("monatliche_rate", ""),
        erp_system=data.get("erp_system") or _FALLBACK,
        it_kontakt_name=data.get("it_kontakt_name") or _FALLBACK,
        it_kontakt_email=data.get("it_kontakt_email") or _FALLBACK,
        bestellnummer=data.get("bestellnummer") or _FALLBACK,
        bestelldatum=data.get("bestelldatum") or _FALLBACK,
        angebotsnummer=data.get("angebotsnummer") or _FALLBACK,
        angebotsdatum=data.get("angebotsdatum") or _FALLBACK,
    )
