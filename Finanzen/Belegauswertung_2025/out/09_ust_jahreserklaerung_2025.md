---
titel: "Umsatzsteuer-Jahreserklärung 2025 – finale Werte für Elster"
typ: referenz
bezugsjahr: 2025
erstellt: 2026-07-28
status: final
tags: [Umsatzsteuer, Elster, Steuern, Buchhaltung]
---

# Umsatzsteuer-Jahreserklärung 2025 – finale Werte für Elster

> **Abgeschlossen am 2026-07-28.** Basis: Finom-Kontoauszüge (einziges Geschäftskonto) +
> vollständige Einzelbeleg-Verifizierung aller 80 Buchungen (75 Ausgaben, 5 Einnahmen).
> Details und Herleitung: `00_zusammenfassung_steuerpruefung_2025.md`,
> `08_euer_ausgaben_zuordnung.md`. Memory: [[project-euer-2025-finanzamt-zahlungen]],
> [[project-euer-2025-ausgaben-korrekturen]].

## Einzutragende Werte

| Feld in Elster (Wortlaut) | Betrag |
|---|---:|
| Steuerpflichtige Umsätze zum allgemeinen Steuersatz (19 %), netto | **4.950,00 €** |
| Abziehbare Vorsteuerbeträge aus Rechnungen anderer Unternehmer | **249,76 €** |
| Vorauszahlungssoll 2025 (Summe der bereits erklärten Voranmeldungen) | **680,04 €** |

Rechnung dahinter:

| | Betrag |
|---|---:|
| Umsatz netto | 4.950,00 € |
| Umsatzsteuer darauf (19 %) | 940,50 € |
| Vorsteuer | 249,76 € |
| Rechnerische Jahressteuer 2025 | 690,74 € |
| − Vorauszahlungssoll 2025 (bereits erklärt/gezahlt) | 680,04 € |
| **= Restzahlung** | **10,70 €** |

**Nur die 10,70 € sind der tatsächlich noch zu zahlende Betrag** — nicht 690,74 €. Der Großteil
der Jahressteuer wurde bereits über die vier Voranmeldungen 2025 (Q1+Q2 gemeinsam, Q3, Q4)
beglichen.

### Herleitung Vorauszahlungssoll 2025 (680,04 €)

| Zeitraum | Erklärt | Betrag |
|---|---|---:|
| Q1+Q2 2025 (gemeinsame Voranmeldung) | Erstattung | −25,59 € |
| Q3 2025 | Erstattung | −155,10 € |
| Q4 2025 | Zahllast (gezahlt 03.01.2026) | +860,73 € |
| **Netto Vorauszahlungssoll 2025** | | **680,04 €** |

Die Erstattung vom 07.08.2025 (93,27 €) ist **nicht** enthalten — die betrifft die
USt-Jahreserklärung 2024, nicht 2025.

## Reverse-Charge (§ 13b UStG)

Betrifft Instantly/Apify-Ausgaben ohne deutschen USt-Ausweis. Bereits in den laufenden
Voranmeldungen 2025 routinemäßig erfasst — für die Jahreserklärung nicht neu berechnen oder
zusätzlich eintragen, sonst Doppelzählung.

## Wie die 249,76 € Vorsteuer zustande kommen

Ausgangswert nach Belegprüfung (26./27.07.): 215,98 €. Zwei Korrekturen nach vollständiger
Einzelverifizierung am 28.07., beide direkt an den Original-Rechnungen geprüft:

- **+52,25 €:** Triathlon-Miete (Vermieter Campus Saarbrücken) weist entgegen der bisherigen
  Annahme ausdrücklich 19 % USt aus (25,00 € netto + 4,75 € USt = 29,75 € brutto/Monat,
  11 Monate 2025) — war fälschlich mit 0 € Vorsteuer geführt.
- **−18,47 €:** PNL-Fintech-Rechnung (3OJ3-0005, Finom-Jahresgebühr) weist niederländische USt
  aus (USt-IdNr. NL859799189B01), keine deutsche — ausländische USt ist nach § 15 UStG nicht
  als deutsche Vorsteuer abzugsfähig. Voller Bruttobetrag (115,67 €) zählt stattdessen als
  Netto-Betriebsausgabe. Ursache: Prozessias eigene USt-IdNr. war bei Finom/PNL Fintech nicht
  hinterlegt, daher keine Reverse-Charge-Behandlung durch den Anbieter. **To-do:** USt-IdNr. bei
  Finom hinterlegen, damit künftige Jahresgebühren-Rechnungen korrekt per Reverse-Charge laufen.

215,98 + 52,25 − 18,47 = **249,76 €**.

## Am 2026-07-28 geprüft und bestätigt (kein weiterer Änderungsbedarf)

- **Q1/2025:** kein offener Punkt — mit Q2 gemeinsam in einer Voranmeldung erklärt, die
  Erstattung vom 28.07.2025 (25,59 €) ist bereits das Ergebnis von Q1+Q2 zusammen.
- **Steuernummer:** Prozessia/WebWokr/das Finom-Konto laufen alle unter einer einzigen
  Steuernummer (040/163/12016) — die abweichende Nummer auf der WebWokr-Vorlage (RE250005,
  040/276/11732) ist ein reiner Vorlagenfehler, kein Hinweis auf eine zweite Firma. Die
  100,00 €-Buchung von RE250005 zählt normal als Umsatz.
- **cyfire (450,00 €, 13.11.2025):** von Sebastian bestätigt netto, so mit dem Anwalt
  vereinbart — bleibt wie erfasst (keine Vorsteuer, da keine Rechnung mit gesondertem
  USt-Ausweis vorliegt).
- **Apify (2× 39 USD, ca. 13 € mögliche Vorsteuer über OSS):** bewusst nicht als Vorsteuer
  angesetzt (Abzugsfähigkeit bei OSS-Rechnungen rechtlich unklar).
- **6 Instantly-Buchungen** mit auffälliger USD/EUR-Umrechnung: von Sebastian bestätigt korrekt
  per Reverse-Charge gebucht, ergibt 0 € Vorsteuer — keine Änderung.

## Für den Steuerberater vermerkt (nicht abgabekritisch)

- Drei privat per PayPal bezahlte Rechnungen (Wix Domain, Wix Workspace, LinkedIn Sales
  Navigator, zusammen 52,84 € Vorsteuer) lauten auf Sebastian Spuhlers Privatadresse statt auf
  die Firma — Vorsteuerabzug ist bei einer Personengesellschaft i. d. R. unproblematisch
  (Einlage), aber formal sauberer wäre die Firmenadresse; für künftige Bestellungen beachten.
