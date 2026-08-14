---
tags:
  - Beschaffungsagent
  - Systemhandbuch
  - Schaufler
  - Lieferterminverfolgung
  - KI-Agent
quelle: Systemhandbuch_Beschaffungsagent (2).pdf
datum: 2026-06-09
kategorie: Produkt
---

# Systemhandbuch_Beschaffungsagent (2)

Systemhandbuch des KI-gestützten Beschaffungsagenten, entwickelt für die Schaufler Fischer Group (Stand März 2026). Es beschreibt vollständig den Funktionsumfang des Systems: automatisierte Lieferterminverfolgung, E-Mail-Klassifizierung, ERP-Abgleich, Eskalationslogik sowie alle Dashboard-Seiten und Prüfregeln. Das Dokument dient als technische Referenz für Betrieb und Nutzung des Agenten.

## Vollständiger Inhalt
Systemhandbuch
Beschaffungsagent
Schaufler Fischer Group
Stand: März 2026
Dieses Dokument beschreibt den Funktionsumfang des KI-gestützten
Beschaffungsagenten – alle Seiten, Prüfregeln, Scores und Abläufe.
Seite 1/13 Systemhandbuch – Beschaffungsagent | Schaufler Fischer Group Seite 2
1. Was macht das System?
Der Beschaffungsagent automatisiert die Lieferterminverfolgung im Einkauf. Er überwacht eingehende E-Mails, erkennt
Auftragsbestätigungen (ABs), extrahiert die relevanten Daten per KI und vergleicht sie mit den Bestelldaten aus dem ERP-System.
Bei Abweichungen wird automatisch eskaliert. Alle Ergebnisse werden in einem Dashboard dargestellt.
Kurzablauf:
1. Agent prüft regelmäßig das E-Mail-Postfach (alle 60 Min.)
2. Eingehende E-Mails werden klassifiziert (AB, Messbericht, Versanddokument, Unbekannt)
3. ABs werden per KI ausgelesen und mit ERP-Daten abgeglichen
4. Bei Abweichungen in Preis, Menge oder Termin wird automatisch eskaliert
5. Fehlende ABs werden in 3 Stufen beim Lieferanten angemahnt
6. Überfällige Lieferungen werden erkannt und gemeldet
7. Sendungen auf See werden per Vessel Tracking verfolgt
2. Seitenübersicht im Dashboard
Das Dashboard hat folgende Bereiche:
 Seite  Was findet man dort?
 Auftragsbestätigungen  Alle verarbeiteten ABs mit Prüfergebnis, Eskalationen und fehlende ABs (3 Tabs)
 Messberichte  Weitergeleitete Prüfberichte/Messberichte mit Vollständigkeitsstatus
 Lieferanten  Performance-Übersicht aller Lieferanten mit Score-Berechnung
 Lieferungen  Lieferterminstatus, Sendungsverfolgung (Vessel Tracking)
 Unklarheiten  E-Mails, die keiner Bestellung zugeordnet werden konnten
 Reporting  Kennzahlen, Frühwarnquote und Excel-Exporte
 Aktivität  Chronologisches Protokoll aller Agent-Aktionen
 Steuerung  Agent starten/stoppen, Konfiguration einsehen, Logs
 Benutzerverwaltung  Benutzer anlegen, Rollen zuweisen (nur Admin)
3. Seite „Auftragsbestätigungen"
Seite 2/13 Systemhandbuch – Beschaffungsagent | Schaufler Fischer Group Seite 3
Diese Seite hat 3 Tabs :
Tab 1: Auftragsbestätigungen
Zeigt alle vom Agenten verarbeiteten ABs.
Kennzahlen oben:
•  OK – Anzahl ABs ohne Abweichungen
•  Zur Klärung  – ABs mit leichten Abweichungen (z.B. Termin ≤ 5 Tage verschoben)
•  Eskaliert  – ABs mit kritischen Abweichungen (Preis, Menge oder Termin > 5 Tage)
•  Gesamt  – Gesamtanzahl verarbeiteter ABs
Tabellenspalten:
 Spalte  Bedeutung
 Bestellnr.  Bestellnummer aus dem ERP
 AB-Referenz  Referenznummer der Auftragsbestätigung
 Lieferant  Name des Lieferanten
 Termin  In der AB bestätigter Liefertermin
 Status  Prüfergebnis: OK (grün), Hinweis (gelb), Eskaliert (rot)
 Abweichungen  Konkret erkannte Unterschiede (z.B. „Termin +7 Tage", „Menge abweichend")
 Verarbeitet  Zeitpunkt der Verarbeitung durch den Agenten
Tab 2: Eskalationen
Zeigt alle ausgelösten Eskalationen mit aktuellem Bearbeitungsstatus.
Spalten:
•  Quelle  – Woher die Eskalation kommt: „Fehlende AB" oder „Eingegangene AB"
•  Priorität  – Hoch, Mittel oder Niedrig
•  Status  
