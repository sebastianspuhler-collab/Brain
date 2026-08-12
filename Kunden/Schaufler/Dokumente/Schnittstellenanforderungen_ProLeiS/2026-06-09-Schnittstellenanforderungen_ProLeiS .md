---
tags:
  - Schnittstelle
  - REST API
  - ProLeiS
  - Beschaffungsagent
  - Integration
quelle: Schnittstellenanforderungen_ProLeiS .pdf
datum: 2026-06-09
kategorie: Kunde
---

# Schnittstellenanforderungen_ProLeiS 

Technisches Dokument mit den Schnittstellenanforderungen an das ERP-System ProLeiS der Schaufler Fischer Group für den Beschaffungsagenten von Prozessia. Es beschreibt vier REST-API-Endpoints sowie alle Felder, die der Agent lesen und schreiben muss, inklusive Logik zur Terminverfolgung, Eskalation und Messbericht-Prüfung. Das Dokument bildet die technische Grundlage für die Integration des Beschaffungsagenten in die bestehende Systemlandschaft des Kunden.

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
aus der Bestellung ab. Liegt der bestätigte Termin innerhalb der Toleranz (≤ 5 Tage), ist die Position termingerecht. Weicht er
stärker ab, wird der Einkäufer eskaliert (Ampel Rot). Meldet der Lieferant später per Nachricht oder neuer AB einen noch späteren
Termin, wird dieser als erwarteter Termin erfasst — damit erkennt ProLeiS auf einen Blick, dass sich der Termin gegenüber der
ursprünglichen Bestätigung nochmals verschoben hat, und die Eskalation läuft erneut.
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
Der Agent leitet eingehende Messberichte automatisch an den Messraum weiter. Aus ProLeiS liest der Agent nur das Feld
`messbericht_eingegangen`, um zu prüfen ob der Messbericht für eine Position bereits vorliegt. Eine Woche vor dem Liefertermin
prüft der Agent dieses Feld — fehlt der Messbericht
