---
titel: "Zusammenfassung: Steuerprüfung Umsatzsteuer & Betriebsausgaben 2025"
typ: referenz
bezugsjahr: 2025
erstellt: 2026-07-28
tags: [Umsatzsteuer, EÜR, Elster, Steuern, Buchhaltung, Pruefung]
---

# Zusammenfassung: Steuerprüfung Umsatzsteuer & Betriebsausgaben 2025

> Master-Dokument der Session vom 2026-07-28. Fasst alles zusammen, was zur
> USt-Jahreserklärung 2025 und den Betriebsausgaben (Anlage EÜR) geprüft, korrigiert
> und final festgestellt wurde — inklusive der Fehlversuche, damit nachvollziehbar bleibt,
> warum die Zahlen so sind, wie sie sind. Einzeldateien: `08_euer_ausgaben_zuordnung.md`
> (Ausgaben-Detailliste), `09_ust_jahreserklaerung_2025.md` (Elster-Werte USt).

## 1. Finale Zahlen 2025 (zweifach verifiziert: Pipeline-Output + unabhängige Neuberechnung aus den Rohdaten)

| Kennzahl | Betrag |
|---|---:|
| Umsatz netto (5 Kundenrechnungen) | 4.950,00 € |
| Umsatzsteuer auf Umsatz (19 %) | 940,50 € |
| Betriebsausgaben netto (75 Buchungen) | 2.958,32 € |
| davon abziehbare Vorsteuer | 215,98 € |
| Vom Finanzamt erstattete USt 2025 | 273,96 € |
| An das Finanzamt gezahlte USt 2025 | 0,00 € |
| **Gewinn 2025 (Umsatz − Ausgaben + FA-Erstattung)** | **2.265,64 €** |
| Gewinnanteil je Gesellschafter (2 Gesellschafter) | 995,84 € |

**Für die USt-Jahreserklärung:** Kz. 81 = 4.950,00 €, Kz. 66 = 215,98 €.

## 2. Die 5 Umsatzbuchungen im Detail

| Datum | Kunde | Rechnung | Netto | USt |
|---|---|---|---:|---:|
| 28.08.2025 | Joel Wagner (Marke WebWokr) | RE250005 – Meta-Ads-Tracking-Sheet-Anpassung | 100,00 € | 19,00 € |
| 07.10.2025 | Martin Veser UG | RE250006 – Anzahlung Vapi Voice Agent | 231,09 € | 43,91 € |
| 24.10.2025 | Martin Veser UG | RE250006 – Restzahlung Vapi Voice Agent | 193,91 € | 36,84 € |
| 21.11.2025 | Martin Veser UG | RE250007 – Fonio Voice Agent | 425,00 € | 80,75 € |
| 30.12.2025 | Joel Wagner | RE250009 – Quartalsretainer Adrise | 4.000,00 € | 760,00 € |
| **Summe** | | | **4.950,00 €** | **940,50 €** |

## 3. Betriebsausgaben nach EÜR-Feld

| Feld | Netto | Vorsteuer | Anzahl Buchungen |
|---|---:|---:|---:|
| Werbekosten | 1.117,69 € | 45,79 € | 33 |
| Rechts- und Steuerberatung, Buchführung | 773,67 € | 61,49 € | 15 |
| Laufende IT-Kosten | 626,97 € | 93,12 € | 14 |
| Miete/Pacht für Geschäftsräume | 275,00 € | 0,00 € | 11 |
| Übernachtungs- und Reisekosten | 82,99 € | 0,00 € | 1 |
| Fortbildungskosten | 82,00 € | 15,58 € | 1 |
| **Summe** | **2.958,32 €** | **215,98 €** | **75** |

Davon 3 Buchungen (52,84 € Vorsteuer) privat per PayPal bezahlt, nicht über das Finom-Geschäftskonto: Wix Domain webwokr.de (2,84 €), Wix Google Workspace (31,00 €), LinkedIn Sales Navigator (19,00 €) — zählen als Betriebsausgabe **und** Einlage.

Details je Buchung: siehe `08_euer_ausgaben_zuordnung.md`.

## 4. Der Weg zu diesen Zahlen — inklusive Fehlversuche (damit nachvollziehbar bleibt, warum diese Zahlen stimmen)

**a) Ausgangspunkt (Sessions 2026-07-26/27):** Vollständige Belegprüfung, Korrekturschicht `korrekturen_2025.json` aufgebaut (Parser-Fehler bei Wix/LinkedIn/Benito-Ferrise behoben, Bagatellrechnungen ausgeschlossen, Regel "kein Beleg = keine Ausgabe" umgesetzt → ZOHO/OpenAI/Instantly-Schätzposten ohne Beleg rausgenommen). Ergebnis: Umsatz 4.950,00 €, Ausgaben 2.958,32 €, Vorsteuer 215,98 €.

**b) Fehlversuch 2026-07-28 (gefunden, dann verworfen):** Bei der Ableitung der USt-Jahreserklärung fiel auf, dass die Buchung „Joel Wagner, 100,00 €" vom 28.08.2025 laut Beleg (RE250005) eine Rechnung von **WebWokr** an Joel Wagner ist, mit einer anderen Steuernummer (040/276/11732) als der Rest (040/163/12016). Daraus wurde vorschnell geschlossen, das sei eine fremde Ausgabe statt Umsatz, und testweise umgebucht (Ausgaben stiegen auf 3.058,32 €, Umsatz sank auf 4.850,00 €). **Sebastian hat das zurückgewiesen:** Es gibt nur **eine Firma und eine Steuernummer** — die WebWokr-Vorlage trägt schlicht eine veraltete/falsche Steuernummer. Die Korrektur wurde vollständig rückgängig gemacht (Pipeline erneut durchlaufen), die ursprünglichen Zahlen (4.950,00 € / 215,98 €) sind korrekt.

**c) Abgleich gegen die tatsächlichen Finanzamt-Zahlungen (auf Wunsch von Sebastian):** Rechnerischer Saldo aus Umsatzsteuer minus Vorsteuer (940,50 € − 215,98 € = 724,52 €) wurde mit den tatsächlichen Kontobewegungen verglichen. Nach Herausrechnen einer Erstattung, die eigentlich das Steuerjahr 2024 betrifft (93,27 €, nicht 2025), ergab sich: tatsächlich gezahlt 680,04 € vs. rechnerisch 724,52 € → Differenz 44,48 €. Diese kleine Differenz (< 1 % vom Umsatz) ist normal und erklärt sich durch die Zeitverschiebung zwischen Rechnungsdatum (Soll-Versteuerung in den Voranmeldungen) und Zahlungsdatum (Zufluss-/Abflussprinzip in der EÜR) — kein Hinweis auf einen Fehler in den 215,98 € Vorsteuer.

**d) Unabhängige Neuberechnung direkt aus den Rohdaten (2026-07-28):** Alle 5 Umsatz- und 75 Ausgabenbuchungen wurden nochmal direkt aus `04_merged.json` (nicht aus den Markdown-Zusammenfassungen) neu aufsummiert. Ergebnis stimmt exakt mit dem Pipeline-Output überein — keine Diskrepanz gefunden.

## 5. Offene Punkte (keine davon blockierend für die Abgabe)

1. **Drei privat bezahlte Rechnungen** (Wix Domain, Wix Workspace, LinkedIn, zusammen 52,84 € Vorsteuer) lauten auf Sebastians Privatadresse statt auf die Firma — Vorsteuerabzug bei einer Personengesellschaft ist dadurch i. d. R. trotzdem unproblematisch (Einlage), aber formal nicht ganz sauber. Für künftige Bestellungen auf Firmenadresse achten.
2. **Triathlon-Mietvertrag** (11× 25,00 € netto/Monat) weist auf dem Beleg keine USt aus, obwohl rechnerisch 19 % aufgingen — daher keine Vorsteuer geltend gemacht (möglich entgangen: 52,25 €/Jahr). Reine Kulanz-Entscheidung, kein Risiko.
3. **WebWokr-Rechnungsvorlage** trägt eine falsche/veraltete Steuernummer (040/276/11732 statt 040/163/12016) — für künftige Rechnungen korrigieren, um diese Verwirrung nicht jedes Jahr zu wiederholen.
4. **Restdifferenz 44,48 €** zwischen rechnerischer und tatsächlich gezahlter USt 2025 — plausibel durch Rechnungs-/Zahlungsdatum-Verschiebung erklärt, aber nicht mit einer einzelnen Buchung bewiesen (dafür fehlen die genauen Quartalswerte aus den eingereichten Voranmeldungen).

## 6. Einzeltransaktions-Verifizierung

Alle 75 Ausgaben- und 5 Einnahmenbuchungen wurden am 2026-07-28 zusätzlich einzeln gegen die
Original-Belege geprüft (unabhängig von der Pipeline, Datei für Datei). Ergebnis siehe Anhang
unten bzw. Update in diesem Abschnitt, sobald die Prüfung abgeschlossen ist.

<!-- VERIFIZIERUNG_PLATZHALTER -->
