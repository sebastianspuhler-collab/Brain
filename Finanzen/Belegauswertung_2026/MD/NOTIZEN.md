---
titel: "Belegauswertung 2026 – Notizen & Status"
typ: referenz
erstellt: 2026-07-28
tags: [Buchhaltung, EÜR, Umsatzsteuer, 2026]
---

# Belegauswertung 2026 – Status und Vorgehen

> Angelegt am 2026-07-28 als Vorsorge, damit für 2026 dieselbe strukturierte
> Belegauswertung möglich ist wie für 2025 (siehe `Belegauswertung_2025/`). Enthält alle
> Lehren aus der 2025er-Prüfung, damit die gleichen Fehler nicht wiederholt werden.

## Status (Stand 2026-07-28): Scaffold angelegt, noch nicht final durchgelaufen

- **step1 (Transaktionen) läuft bereits erfolgreich:** 188 Buchungen Jan–Jul 2026 aus dem
  Finom-Kontoauszug extrahiert (27 Umsatz-Kandidaten, 161 Ausgaben-Kandidaten, 58 davon
  „UNKLAR" und müssen manuell geprüft werden — u. a. World Class Marketing LLC, Reisekosten
  (Hotels/Restaurants), diverse SaaS-Abos).
- **step2 (lokale Belege) NICHT lauffähig, bis Vorarbeit gemacht ist:** Braucht
  `_local_text_raw.json` + `_ocr_results.json` (Textextraktion aller PDFs unter
  `Finanzen/2026/*`). Diese Extraktion war 2025 kein eigenes Skript, sondern ein einmaliger
  manueller/Agenten-Durchlauf über alle Belegdateien. Muss für 2026 vor dem ersten echten
  Lauf neu gemacht werden (z. B. per Agent: alle PDFs unter `Finanzen/2026/` einlesen und in
  gleicher Struktur wie die 2025er-Dateien ablegen).
- **step4–step8:** Codeseitig fertig angepasst (Pfade, Jahr, Platzhalter-Konstanten), aber
  noch nicht durchlaufen — macht erst Sinn, sobald step2 lauffähig ist.
- **Finanzamt-Cashflows 2026** (`FA_ERSTATTET_2026`/`FA_GEZAHLT_2026` in
  `step8_euer_zuordnung.py`) stehen noch auf 0,00 € — vor dem ersten echten Lauf aus den
  tatsächlichen 2026er-Finanzamt-Buchungen befüllen (Suche nach "FINANZAMT" in
  `out/_finom_alle_jahre.json`, gefiltert auf 2026-Datumsangaben).
- **Durchlaufposten-Ausschlüsse** (`DURCHLAUFPOSTEN_TX_IDS` in step5/step7) sind aktuell
  leer — 2025 gab es einen Sonderfall (Benito-Ferrise-Rundlauf 4.760 €), 2026-Äquivalente
  bei Bedarf ergänzen.

## Pipeline-Reihenfolge (identisch zu 2025)

```
step1_transaktionen.py → step2_local_belege.py → step4_matching.py →
step4b_korrekturen.py → step5_auswertung.py → step6_output.py →
step7_monatsdateien.py → step8_euer_zuordnung.py
```

`korrekturen_2026.json` ist die manuelle Korrekturschicht (aktuell leer) — analog zu
`Belegauswertung_2025/korrekturen_2025.json`.

## Wichtigste Lehren aus der 2025er-Prüfung (2026-07-28), unbedingt anwenden

1. **Ausländische USt ≠ deutsche Vorsteuer.** Bei jeder Rechnung mit MwSt-/USt-Ausweis
   zuerst die USt-IdNr. des Ausstellers prüfen. Nur bei einer deutschen USt-IdNr. (DE...)
   zählt der ausgewiesene Betrag als abziehbare Vorsteuer. Bei ausländischen USt-IdNrn.
   (NL, CZ, etc.) den vollen Bruttobetrag als Netto-Betriebsausgabe werten, keine
   Vorsteuer ansetzen — außer es liegt ein eindeutiger, korrekt ausgestellter
   Reverse-Charge-Fall vor (0 % USt-Ausweis + Hinweis auf Steuerschuldnerschaft des
   Leistungsempfängers). Konkreter Fall 2025: PNL-Fintech-Rechnung (Amsterdam, NL-USt-ID)
   wurde fälschlich als deutsche Vorsteuer gezählt (−18,47 € Korrektur nötig).
2. **„Kein USt-Ausweis" nicht ungeprüft annehmen.** Die Triathlon-Mietrechnung wurde erst
   für „ohne USt-Ausweis" gehalten, zeigte bei genauem Lesen aber explizit 19 % USt
   (+52,25 € Vorsteuer über das Jahr). Bei jedem Beleg den vollständigen Text lesen, nicht
   nur den Bruttobetrag übernehmen.
3. **Eine abweichende Steuernummer auf einem Beleg ist kein Beweis für eine andere Firma.**
   Bei Sebastian tauchen unter „WebWokr" gelegentlich alte/falsche Steuernummern auf
   Rechnungsvorlagen auf, obwohl es dieselbe Firma ist. Vor einer Umbuchung deswegen erst
   nachfragen, nicht selbst entscheiden.
4. **USt-IdNr. bei Anbietern hinterlegen (To-do, nicht Pipeline-relevant):** Prozessia hat
   eine gültige USt-IdNr., die aber z. B. bei Finom/PNL Fintech nicht hinterlegt ist –
   dadurch verrechnet der Anbieter niederländische statt Reverse-Charge-USt. Wenn Sebastian
   das für 2026 nachträgt, sollten künftige gleichartige Rechnungen automatisch korrekt
   laufen.
5. **„Kein Beleg = keine Ausgabe"** (siehe Brain-Memory [[feedback-kein-beleg-keine-ausgabe]]):
   Buchungen ohne echten Originalbeleg zählen nicht, unabhängig vom Betrag — auch nicht
   geschätzt aus dem Bruttobetrag.
6. **Bei jeder Jahresauswertung: alle Buchungen einzeln gegen den Originalbeleg verifizieren**,
   nicht nur die Pipeline-Summen vertrauen — bei der 2025er-Prüfung wurden dadurch zwei
   materielle Fehler erst im dritten Anlauf gefunden.

## Nächste Schritte, wenn die 2026er-Auswertung ansteht

1. Aktuellen Finom-Kontoauszug besorgen (deckt dann vermutlich Ende 2024 bis zum jeweiligen
   Auswertungsdatum ab) und `Belegauswertung_2025/scripts/parse_finom.py` erneut laufen
   lassen, um `_finom_alle_jahre.json` zu aktualisieren (bleibt bewusst in der
   2025er-Struktur, da jahresübergreifend gepflegt).
2. Alle PDFs/Notizen unter `Finanzen/2026/*` als Text extrahieren (→
   `_local_text_raw.json`/`_ocr_results.json` in `Belegauswertung_2026/out/`).
3. step1 → step2 → step4 → step4b → step5 → step6 → step7 → step8 laufen lassen.
4. FA_ERSTATTET_2026/FA_GEZAHLT_2026 in step8 mit den echten Finanzamt-Buchungen befüllen.
5. Alle Buchungen einzeln gegen Beleg verifizieren (siehe Lehre 6 oben), bevor irgendwas
   ans Finanzamt geht.
