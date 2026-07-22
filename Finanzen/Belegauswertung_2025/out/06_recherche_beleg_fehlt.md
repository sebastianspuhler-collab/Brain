# Recherche zu BELEG_FEHLT (21 Transaktionen ohne Beleg)

Stand: 2026-07-22. Quelle der Liste: `04_merged.json`, transaktionen mit `status: "BELEG_FEHLT"`.

**WICHTIG: Gmail-Suche war in dieser Session nicht möglich** (Fehler "insufficient authentication
scopes" bei jeder Anfrage an `mcp__claude_ai_Gmail__search_threads`). Die gesendeten/erhaltenen
Mails aus 2025 sind NICHT durchsucht. Gmail-Verbindung muss neu autorisiert werden, dann Recherche
fortsetzen.

Google Drive wurde vollständig durchsucht (fullText-Suche über alle Dateitypen).

## Gelöst (2)

### Martin Veser UG / WebWokr — beide Buchungen zusammen = 1 Rechnung
- 2025-10-07 | AUSGANG | 275,00 EUR | "WebWokr Angebot AG0011 AZ" (Anzahlung)
- 2025-10-24 | AUSGANG | 230,75 EUR | "Rechnung RE250006"
- **Beleg gefunden**: `Rechnung Vapi Martin Veser.pdf` (Drive-ID `1gcpfii3X0mQJHgZA9amdWPc7msmgnpX1`),
  Rechnungsnr. RE250006, Datum 23.10.2025, Gesamtbetrag **505,75 EUR**.
  → 275,00 (Anzahlung) + 230,75 (Restzahlung) = 505,75 EUR. Exakte Übereinstimmung.
- Datei liegt aktuell nur in Drive, nicht im lokalen `Rechnungen/`-Ordner. Sollte dort abgelegt
  und beiden Transaktionen zugeordnet werden.

### UZR*digistore24.com — 2025-08-28 | EINGANG | 55,93 EUR
- **Beleg gefunden**: Digistore24-Rechnung Nr. 73906478-de vom 27.08.2025, Betrag **55,93 EUR**
  (FunnelCockpit Lite, 27.08.–26.09.2025) — exakter Betrag, Datum passt (Kartenabrechnung 1 Tag später).
- Liegt bereits lokal als `Rechnungen/Funnelcockpit_1.pdf` bzw. `Funnelcockpit_2.pdf` vor —
  wurde vom Matching-Skript nicht erkannt, vermutlich weil "UZR*digistore24.com" (Kartenabrechnungstext)
  nicht als "Digistore24 GmbH" erkannt wurde.

## Plausible Kandidaten gefunden, aber FX-Umrechnung nicht exakt geprüft (Instantly, 9x)

Bank verbucht Instantly-Abbuchungen 1 Tag nach US-Rechnungsdatum, in EUR nach Kartenumrechnung.
Alle Rechnungen liegen (großteils bereits lokal) als `Invoice-BCE54405-00XX.pdf` vor:

| Datum | Betrag EUR | Kandidat (USD-Rechnung) | Bemerkung |
|---|---|---|---|
| 2025-04-05 | 34,13 | Invoice-BCE54405-0002, 37,00 $, bezahlt 4.4. | nur in Drive, fehlt lokal |
| 2025-04-08 | 33,32 | Invoice-BCE54405-0003 ("Instantly 041 25.pdf") | Beleg nennt exakt "Abgebucht 33,32 € (Kurs 0,9520)" — sicherer Treffer, fehlt lokal |
| 2025-05-05 | 32,82 | Invoice-BCE54405-0004 ("Instantly 050 25.pdf") | liegt lokal vor, FX plausibel |
| 2025-06-05 | 85,37 | Invoice-BCE54405-0008 ("Instantly 06 25.pdf") | liegt lokal vor, FX plausibel |
| 2025-07-05 | 82,79 | Invoice-BCE54405-0010 ("Instantly 07 25.pdf") | liegt lokal vor — ACHTUNG: dieselbe Datei ist in PRUEFFAELLE.md bereits einer Buchung vom 2025-07-04 (97,0 EUR) zugeordnet. Bitte prüfen, ob es zwei getrennte Abbuchungen gab oder Dopplung im Datensatz vorliegt. |
| 2025-09-05 | 83,58 | Invoice-BCE54405-0016 | liegt lokal vor, FX plausibel |
| 2025-10-04 | 35,44 | Invoice-BCE54405-0018 | liegt lokal vor, FX plausibel |
| 2025-10-05 | 82,83 | Invoice-BCE54405-0019 | nur in Drive, fehlt lokal |
| 2025-05-19 | 29,54 | Invoice-BCE54405-0007 ("Instantly 05 25.pdf", 32,87 $, bezahlt 18.5.) | liegt lokal vor — ACHTUNG: dieselbe Datei ist in PRUEFFAELLE.md bereits Eintrag #25 (Beleg-Seite, 2025-05-18) — evtl. Doppelverwendung, bitte gegenprüfen |
| 2025-06-30 | 17,12 (BOLT) | Invoice-LRDKYW8R-0002.pdf, 20,00 $, fällig 29.6. | nur in Drive, fehlt lokal, FX plausibel |

→ Diese 9 sind vermutlich reguläre Instantly-Abo-Abbuchungen, deren Belege existieren, aber vom
automatischen Matching wegen der Fremdwährungsumrechnung nicht akzeptiert wurden (gleiches Muster
wie die bereits in PRUEFFAELLE.md dokumentierten Fälle). Menschliche Prüfung/Freigabe empfohlen,
keine neue Recherche nötig.

## Kein Kandidat gefunden — echte Lücken (5)

| Datum | Betrag | Gegenpartei | Anmerkung |
|---|---|---|---|
| 2025-05-16 | 17,91 EUR | INSTANTLY | Keine passende Rechnungsnummer/Datum in Drive gefunden |
| 2025-08-05 | 52,17 EUR | INSTANTLY | Invoice-BCE54405-0014 ($59,42, 4.8.) ist bereits einer anderen Buchung (Apify-Pruefall, 2025-08-07) zugeordnet — für diese Buchung kein eigener Beleg gefunden |
| 2025-12-16 | 21,33 EUR | INSTANTLY | Keine Rechnung für Mitte Dezember in Drive gefunden |
| 2025-05-30 | 17,73 EUR | BOLT (BY STACKBLITZ) | Nur Juni-Rechnung (Invoice-LRDKYW8R-0002, 29.6.) gefunden, keine Mai-Rechnung |
| 2025-07-11 | 28,56 EUR | PADDLE.NET* N8N CLOUD1 | Kein n8n-Cloud-Zahlungsbeleg in Drive gefunden (nur n8n-Workflow-Dateien, keine Rechnungen) — vermutlich nur per Mail zugestellt → Gmail-Suche nötig, aktuell blockiert |

## Kein Einzelbeleg möglich/nötig (3) — Steuererstattungen

| Datum | Betrag | Verwendungszweck |
|---|---|---|
| 2025-07-28 | 25,59 EUR | ERSTATT. UmSt 2. VJ 2025 |
| 2025-08-07 | 93,27 EUR | ERSTATT. UmSt 2024 |
| 2025-10-09 | 155,10 EUR | ERSTATT. UmSt 3. VJ 2025 |

Das sind Rückerstattungen des Finanzamts Saarlouis auf zu hoch gezahlte Umsatzsteuer-Vorauszahlungen
— dafür gibt es keine "Rechnung" im klassischen Sinn. Beleg wäre die jeweilige
Umsatzsteuervoranmeldung/Elster-Bestätigung bzw. ein Steuerbescheid. Das lokal vorhandene
`Finanzamt Bescheid.pdf` betrifft einen anderen Vorgang (gesonderte Feststellung Gewerbebetrieb 2024)
und deckt diese drei Erstattungen nicht ab. Müsste ggf. beim Steuerberater/über Elster nachgereicht werden.

## Nächste Schritte
1. Gmail-Verbindung neu autorisieren, dann Suche nach: Instantly (05-16, 08-05, 12-16), Bolt Mai-Rechnung,
   Paddle/n8n Cloud (07-11) wiederholen.
2. Die unter "Gelöst" und "Plausible Kandidaten" gefundenen Drive-Dateien in den lokalen
   `Rechnungen/`-Ordner herunterladen und in `04_merged.json` als BELEGT nachtragen.
3. Für die 3 Finanzamt-Erstattungen: Umsatzsteuervoranmeldungen 2VJ/3VJ 2025 + Bescheid 2024 besorgen.
