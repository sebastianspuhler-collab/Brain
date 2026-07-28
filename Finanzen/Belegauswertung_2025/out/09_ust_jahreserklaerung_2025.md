---
titel: "Umsatzsteuer-Jahreserklärung 2025 – Zusammenfassung für Elster"
typ: referenz
bezugsjahr: 2025
erstellt: 2026-07-28
tags: [Umsatzsteuer, Elster, Steuern, Buchhaltung]
---

# Umsatzsteuer-Jahreserklärung 2025 – Werte für Elster

> Basis: Finom-Kontoauszüge (einziges Geschäftskonto) + Belegprüfung 2026-07-26/27,
> siehe `08_euer_ausgaben_zuordnung.md` und Brain-Memory
> [[project-euer-2025-finanzamt-zahlungen]] / [[project-euer-2025-ausgaben-korrekturen]].

## Einzutragende Werte (Hauptvordruck USt-Erklärung)

| Kennzahl | Bezeichnung | Betrag |
|---|---|---:|
| **Kz. 81** | Steuerpflichtige Umsätze zum allgemeinen Steuersatz (19 %), netto | **4.950,00 €** |
| **Kz. 66** | Abziehbare Vorsteuerbeträge aus Rechnungen anderer Unternehmer | **215,98 €** |

Elster berechnet die Umsatzsteuer auf Kz. 81 automatisch (19 %):

| | Betrag |
|---|---:|
| Umsatz netto (Kz. 81) | 4.950,00 € |
| Umsatzsteuer darauf (19 %) | 940,50 € |
| Vorsteuer (Kz. 66) | 215,98 € |
| **Zahllast/Erstattungsanspruch 2025** | **724,52 €** (Zahllast) |

Diese Zahllast von 724,52 € ist die **rechnerische Jahressteuer 2025** aus Umsatz und Vorsteuer –
sie ist **nicht identisch** mit den tatsächlichen Finanzamt-Kontobewegungen 2025 (siehe unten),
weil Erklärung und Zahlung zeitversetzt laufen (Voranmeldungen unterjährig, Ausgleich oft erst
im Folgejahr).

## Reverse-Charge (§ 13b UStG)

Betrifft v. a. Instantly/Apify-Ausgaben ohne deutschen USt-Ausweis (ca. 293,80 € netto 2025).
**Bereits in den laufenden Voranmeldungen 2025 routinemäßig erfasst** — für die Jahreserklärung
**nicht neu berechnen oder zusätzlich eintragen**, sonst Doppelzählung.

## Tatsächliche Finanzamt-Kontobewegungen 2025 (zur Kontrolle, nicht für Kz. 81/66)

| Datum | Vorgang | Betrag |
|---|---|---:|
| 28.07.2025 | Erstattung USt 2. Vj. 2025 | +25,59 € |
| 07.08.2025 | Erstattung USt Jahreserklärung 2024 | +93,27 € |
| 09.10.2025 | Erstattung USt 3. Vj. 2025 | +155,10 € |
| **Summe Erstattungen 2025** | | **273,96 €** |
| Zahlungen ans Finanzamt 2025 | | 0,00 € |
| 03.01.2026 | Zahlung USt 4. Vj. 2025 (−860,73 €) | zählt zu **2026**, nicht 2025 |

## Offener Punkt vor Abgabe

**Q1/2025 ist ungeklärt:** Auf dem Finom-Konto findet sich für Q1/2025 keine einzige
Finanzamt-Buchung (weder Zahlung noch Erstattung) — zweifach verifiziert
(Transaktions-JSON + Rohtext-Suche). Mögliche Erklärungen: Zahllast war 0 €, oder die
Verrechnung lief anders. **Vor Abgabe der Jahreserklärung klären** — entweder anhand der
eigenen USt-VA Q1/2025 (falls im Elster-Postfach/Lexoffice auffindbar) oder mit dem
Steuerberater. Keine echten USt-VA-Dokumente im Vault gefunden; Lexoffice-API-Key in
`Finanzen/.env` war zuletzt ungültig (401 Unauthorized).

## Weitere offene Punkte (aus der Belegprüfung, betreffen primär die EÜR, nicht die USt)

- Drei privat bezahlte Rechnungen (Wix Domain, Wix Workspace, LinkedIn Sales Navigator,
  zusammen 52,84 € Vorsteuer) lauten nicht auf die GbR, sondern auf Sebastian Spuhler privat
  bzw. „WebWokr" — Vorsteuerabzug der Gesellschaft mit dem Steuerberater klären.
- Triathlon-Mietvertrag (11× 29,75 € brutto/Monat) weist keine USt aus, obwohl rechnerisch
  19 % aufgingen — mangels USt-Ausweis auf dem Beleg nicht geltend gemacht (möglich entgangene
  Vorsteuer: 52,25 €/Jahr).
- Unklar, welche Gesellschaft (Prozessia GbR vs. „Sebastian Spuhler, Mohamed Douioui GbR")
  die Erklärung für 2025 tatsächlich abgibt — Finom-Kontoinhaber ist die letztere.
