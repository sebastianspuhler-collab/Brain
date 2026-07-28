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

## Klarstellung 2026-07-28 zur Joel-Wagner/WebWokr-Buchung

Die Buchung „Joel Wagner, 28.08.2025, 100,00 €" (RE250005) ist eine Ausgangsrechnung von
**WebWokr an Joel Wagner** über eine Meta-Ads-Tracking-Sheet-Anpassung. Auf dem Belegvordruck
steht eine andere Steuernummer (040/276/11732) als bei den übrigen Prozessia-Rechnungen
(040/163/12016) — laut Sebastian (2026-07-28) ist das **eine Firma**, die Vorlage trägt nur
eine veraltete/falsche Steuernummer. Die 100 € zählen daher normal als Umsatz. (Ein
zwischenzeitlicher Versuch, diese Buchung als Ausgabe umzubuchen, wurde wieder verworfen —
siehe [[project-euer-2025-ausgaben-korrekturen]].)

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
| Rechnerische Jahres-USt 2025 | 724,52 € |

**Keine zusätzliche Zahllast:** Die 724,52 € sind eine rein rechnerische Kontrollgröße
(Umsatz × 19 % minus Vorsteuer, für das ganze Jahr auf einmal), **keine noch offene Zahlung**.
Sebastian hat 2025 quartalsweise korrekt per USt-Voranmeldung erklärt und bezahlt (Q1+Q2
gemeinsam in einer Erklärung, dann Q3 und Q4 einzeln, inkl. 860,73 € am 03.01.2026 für
Q4/2025) — die Jahreserklärung fasst das nur zusammen, sie erzeugt keine neue Schuld.

## Reverse-Charge (§ 13b UStG)

Betrifft v. a. Instantly/Apify-Ausgaben ohne deutschen USt-Ausweis (ca. 293,80 € netto 2025).
**Bereits in den laufenden Voranmeldungen 2025 routinemäßig erfasst** — für die Jahreserklärung
**nicht neu berechnen oder zusätzlich eintragen**, sonst Doppelzählung.

## Tatsächliche Finanzamt-Kontobewegungen 2025/2026 (zur Kontrolle, nicht für Kz. 81/66)

| Datum | Vorgang | Betrag |
|---|---|---:|
| 28.07.2025 | Erstattung USt Q1+Q2 2025 (gemeinsame Erklärung) | +25,59 € |
| 07.08.2025 | Erstattung USt Jahreserklärung 2024 (gehört nicht zu 2025) | +93,27 € |
| 09.10.2025 | Erstattung USt 3. Vj. 2025 | +155,10 € |
| 03.01.2026 | Zahlung USt 4. Vj. 2025 | −860,73 € |

Q1/2025 ist kein offener Punkt: Sebastian hat Q1 und Q2 2025 gemeinsam in einer Voranmeldung
erklärt und gekennzeichnet — die Erstattung vom 28.07.2025 (25,59 €) ist bereits das Ergebnis
von Q1+Q2 zusammen, deshalb gibt es keine separate Q1-Buchung.

## Abgleich 2026-07-28: rechnerischer Saldo vs. tatsächlich gezahlt

Auf Wunsch von Sebastian geprüft, ob Kz. 81/66 mit den tatsächlichen Finanzamt-Zahlungen
zusammenpassen — reine Kontrollrechnung, **ohne** die 93,27 € von 2024 (die gehören nicht
zu 2025):

| | Betrag |
|---|---:|
| Tatsächlich ans Finanzamt gezahlt 2025 (netto: 860,73 € − 25,59 € − 155,10 €) | 680,04 € |
| Rechnerische Jahres-USt 2025 (940,50 € − 215,98 €) | 724,52 € |
| **Differenz** | **44,48 €** |

Die Differenz ist klein und normal — sie erklärt sich durch die Zeitverschiebung zwischen
Rechnungsdatum (Soll-Versteuerung in den Voranmeldungen) und Zahlungsdatum
(Zufluss-/Abflussprinzip in der EÜR), z. B. bei der Martin-Veser-Anzahlung im Oktober vor der
eigentlichen Rechnung. Kein Hinweis auf fehlende/falsche Vorsteuer — **215,98 € bleiben die
korrekte Zahl** für Kz. 66. (Eine erste Kontrollrechnung inkl. der 2024er-Erstattung ergab
noch 133,97 € Differenz, weil ein Teil des Geschäftsjahres 2024 gar nicht in dieser
Finom-basierten Auswertung erfasst ist — nach Herausrechnen der 2024er-Position bleibt nur
noch die oben stehende, plausible 44,48-€-Differenz.)

## Klarstellung 2026-07-28: nur eine Steuernummer

Sebastian bestätigt: **es gibt nur eine Steuernummer und eine Adresse** für die gesamte
Geschäftstätigkeit (Prozessia/WebWokr/Finom-Konto „Sebastian Spuhler, Mohamed Douioui GbR"
sind alle dieselbe Firma unter derselben Steuernummer 040/163/12016). Die abweichende
Steuernummer 040/276/11732 auf der WebWokr-Rechnungsvorlage (RE250005) ist damit endgültig
als reiner Vorlagenfehler eingeordnet — **kein** Hinweis auf eine zweite Rechtsperson oder
Unklarheit, welche Gesellschaft die Erklärung abgibt. Kein offener Punkt mehr.

## Weitere offene Punkte (aus der Belegprüfung, betreffen primär die EÜR, nicht die USt)

- Drei privat bezahlte Rechnungen (Wix Domain, Wix Workspace, LinkedIn Sales Navigator,
  zusammen 52,84 € Vorsteuer) lauten auf Sebastian Spuhlers Privatadresse statt auf die
  Firmenadresse — Vorsteuerabzug ist bei einer Personengesellschaft/Einzelunternehmer i. d. R.
  unproblematisch (Einlage), aber formal sauberer wäre eine Rechnung auf den Firmennamen;
  für künftige Bestellungen beachten.
- Triathlon-Mietvertrag (11× 29,75 € brutto/Monat) weist keine USt aus, obwohl rechnerisch
  19 % aufgingen — mangels USt-Ausweis auf dem Beleg nicht geltend gemacht (möglich entgangene
  Vorsteuer: 52,25 €/Jahr).
- WebWokr-Rechnungen tragen eine andere Steuernummer (040/276/11732) als der Rest
  (040/163/12016) — reiner Vorlagenfehler (siehe oben), für künftige Rechnungen korrigieren,
  um Verwechslungen zu vermeiden.
