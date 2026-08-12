---
tags:
  - Schaufler
  - Beschaffungsagent
  - REST API
  - ProLeiS
  - Schnittstellenanforderungen
quelle: Schnittstellenanforderungen_ProLeiS (2).pdf
datum: 2026-06-09
kategorie: Kunde
---

# Schnittstellenanforderungen_ProLeiS (2)

Technisches Dokument der Schaufler Fischer Group, das die Schnittstellenanforderungen an das System ProLeiS für den Beschaffungsagenten von Prozessia beschreibt. Es definiert vier REST-API-Endpoints sowie alle Felder, die pro Bestellposition gelesen und geschrieben werden müssen. Die Logik zur Terminverfolgung, Eskalation und Messberichtsverarbeitung wird detailliert erläutert.

## Vollständiger Inhalt
Schnittstellenanforderungen an ProLeiS
Schaufler Fischer Group | 26.03.2026
Seite 1/4 Systemhandbuch – Beschaffungsagent | Schaufler Fischer Group Seite 2
REST API – 4 Endpoints
1. GET – Liste offener Bestellungen
Alle offenen Bestellungen mit allen Positionen.
2. GET – Einzelne Bestellung
Alle Positionen und Daten zu einer bestimmten Bestellnummer.
3. GET – Einzelne Position
Daten zu einer bestimmten Position innerhalb einer Bestellung.
4. POST – Daten auf Einzelposition schreiben
Liefertermin und AB-Status auf eine Position zurückschreiben.
Warum zwei Termin-Felder zurückgeschrieben werden:
Wenn eine Auftragsbestätigung eingeht, extrahiert der Agent den bestätigten Liefertermin und gleicht ihn mit dem Soll-Termin
aus der Bestellung ab. Liegt der bestätigte Termin innerhalb der Toleranz (≤ 5 Tage), ist die Position termingerecht (Ampel Grün).
Weicht er stärker ab, wird der Einkäufer eskaliert (Ampel Rot). Meldet der Lieferant später per Nachricht oder neuer AB einen
noch späteren Termin, wird dieser als erwarteter Termin erfasst — damit erkennt ProLeiS auf einen Blick, dass sich der Termin
gegenüber der ursprünglichen Bestätigung nochmals verschoben hat, und die Eskalation läuft erneut. Zusätzlich nutzt das System
den erwarteten Termin zur Berechnung des Versandtermins und der Transitzeit.
Felder die geschrieben werden:
 Feld  Wann
 liefertermin_bestaetigt  Bestätigter Termin aus AB (überschreibt bei früherem Termin)
 liefertermin_erwartet  Wenn neuer Termin später als bestätigter Termin
 ab_vorhanden  Auf "Ja" setzen wenn AB eingegangen
 ab_referenz  Referenznummer der Auftragsbestätigung
Felder die wir pro Bestellposition brauchen
Seite 2/4 Systemhandbuch – Beschaffungsagent | Schaufler Fischer Group Seite 3
 Feld  Lesen  Schreiben  Beschreibung
 bestell_nummer  x   Bestellnummer
 position  x   Positionsnummer
 lieferant  x   Lieferantenname
 lieferant_email  x   E-Mail Lieferant (für automatische Mahnungen)
 material  x   Materialbeschreibung
 menge  x   Bestellmenge
 einheit  x   Mengeneinheit
 preis_pro_einheit  x   Einzelpreis
 waehrung  x   Währung
 liefertermin_gefordert  x   Soll-Termin laut Bestellung
 liefertermin_bestaetigt  x  x  Bestätigter Termin (Agent schreibt)
 liefertermin_erwartet  x  x  Erwarteter Termin bei Verzug (Agent schreibt)
 ab_vorhanden  x  x  AB eingegangen? (Agent setzt auf Ja)
 ab_referenz  x  x  AB-Referenznummer (Agent schreibt)
 wareneingang  x   Wareneingang gebucht? (ProLeiS pflegt)
 status  x   Bestellstatus (offen / in Bearbeitung / abgeschlossen)
 einkaufer_email  x   E-Mail Einkäufer (CC bei Eskalationen)
 incoterm  x   Lieferbedingung (für Transitzeit-Berechnung)
 herkunftsland  x   Herkunftsland (steuert Beobachtungsfenster)
 messbericht_eingegangen  x   Messbericht da? (Messraum pflegt in ProLeiS, Agent liest nur)
Messbericht
Der Agent liest aus ProLeiS nur das Feld `messbericht_eingegangen`, um zu prüfen ob der Messbericht für eine Position bereits
vorliegt. Die Ablage und Pflege des Feldes erfolgt d
