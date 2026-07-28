---
titel: "Umsatzsteuer-Jahreserklärung 2025 – Zusammenfassung für Elster"
typ: referenz
bezugsjahr: 2025
erstellt: 2026-07-28
tags: [Umsatzsteuer, Elster, Steuern, Buchhaltung]
---

# Umsatzsteuer-Jahreserklärung 2025 – Werte für Elster

> Basis: Finom-Kontoauszüge (einziges Geschäftskonto) + Belegprüfung 2026-07-26/27/28,
> siehe `08_euer_ausgaben_zuordnung.md` und Brain-Memory
> [[project-euer-2025-finanzamt-zahlungen]] / [[project-euer-2025-ausgaben-korrekturen]].

## Korrektur 2026-07-28

Die „Joel Wagner 100,00 €"-Buchung vom 28.08.2025 war fälschlich als Umsatz erfasst
(Pipeline-Fehler: richtung=AUSGANG statt EINGANG). Tatsächlich ist RE250005 eine
**Eingangsrechnung von WebWokr (Joel Wagner)** an Prozessia für eine Meta-Ads-Tracking-Sheet-
Anpassung — also eine Ausgabe, kein Umsatz. Korrigiert in `korrekturen_2025.json`
(`tx_korrektur` FINOM-844f31d5c70f63f1) und in `scripts/step8_euer_zuordnung.py`
(neue Kategorie „Fremdleistungen"). Von Sebastian am 2026-07-28 bestätigt: die drei echten
Einnahmen 2025 sind RE250006 (425,00 €), RE250007 (425,00 €) und RE250009 (4.000,00 €),
zusammen **4.850,00 €** netto.

## Einzutragende Werte (Hauptvordruck USt-Erklärung)

| Kennzahl | Bezeichnung | Betrag |
|---|---|---:|
| **Kz. 81** | Steuerpflichtige Umsätze zum allgemeinen Steuersatz (19 %), netto | **4.850,00 €** |
| **Kz. 66** | Abziehbare Vorsteuerbeträge aus Rechnungen anderer Unternehmer | **234,98 €** |

Elster berechnet die Umsatzsteuer auf Kz. 81 automatisch (19 %):

| | Betrag |
|---|---:|
| Umsatz netto (Kz. 81) | 4.850,00 € |
| Umsatzsteuer darauf (19 %) | 921,50 € |
| Vorsteuer (Kz. 66) | 234,98 € |
| Rechnerische Jahres-USt 2025 | 686,52 € |

**Wichtig – keine zusätzliche Zahllast:** Die 686,52 € sind eine rein rechnerische Kontrollgröße
(Umsatz × 19 % minus Vorsteuer, für das ganze Jahr auf einmal), **keine noch offene Zahlung**.
Sebastian hat 2025 quartalsweise korrekt per USt-Voranmeldung erklärt und bezahlt (Q1+Q2 gemeinsam
in einer Erklärung, dann Q3 und Q4 einzeln) — die Jahreserklärung fasst das nur zusammen, sie
erzeugt keine neue Schuld. Die tatsächlichen Zahlungen/Erstattungen stehen unten; die 686,52 €
sollten sich (ggf. mit kleinen Rundungs-/Periodenabgrenzungsdifferenzen) daraus ergeben, sind
selbst aber **nicht zusätzlich zu zahlen**.

## Reverse-Charge (§ 13b UStG)

Betrifft v. a. Instantly/Apify-Ausgaben ohne deutschen USt-Ausweis (ca. 293,80 € netto 2025).
**Bereits in den laufenden Voranmeldungen 2025 routinemäßig erfasst** — für die Jahreserklärung
**nicht neu berechnen oder zusätzlich eintragen**, sonst Doppelzählung.

## Tatsächliche Finanzamt-Kontobewegungen 2025/2026 (zur Kontrolle, nicht für Kz. 81/66)

| Datum | Vorgang | Betrag |
|---|---|---:|
| 28.07.2025 | Erstattung USt Q1+Q2 2025 (gemeinsame Erklärung) | +25,59 € |
| 07.08.2025 | Erstattung USt Jahreserklärung 2024 | +93,27 € |
| 09.10.2025 | Erstattung USt 3. Vj. 2025 | +155,10 € |
| 03.01.2026 | Zahlung USt 4. Vj. 2025 | −860,73 € |

Q1/2025 ist **kein offener Punkt mehr**: Sebastian hat Q1 und Q2 2025 gemeinsam in einer
Voranmeldung erklärt und gekennzeichnet — die Erstattung vom 28.07.2025 (25,59 €) ist bereits
das Ergebnis von Q1+Q2 zusammen, deshalb gibt es keine separate Q1-Buchung.

## Weitere offene Punkte (aus der Belegprüfung, betreffen primär die EÜR, nicht die USt)

- Drei privat bezahlte Rechnungen (Wix Domain, Wix Workspace, LinkedIn Sales Navigator,
  zusammen 52,84 € Vorsteuer) lauten nicht auf die GbR, sondern auf Sebastian Spuhler privat
  bzw. „WebWokr" — Vorsteuerabzug der Gesellschaft mit dem Steuerberater klären.
- Triathlon-Mietvertrag (11× 29,75 € brutto/Monat) weist keine USt aus, obwohl rechnerisch
  19 % aufgingen — mangels USt-Ausweis auf dem Beleg nicht geltend gemacht (möglich entgangene
  Vorsteuer: 52,25 €/Jahr).
- Unklar, welche Gesellschaft (Prozessia GbR vs. „Sebastian Spuhler, Mohamed Douioui GbR")
  die Erklärung für 2025 tatsächlich abgibt — Finom-Kontoinhaber ist die letztere.
