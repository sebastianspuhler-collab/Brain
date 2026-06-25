---
tags:
  - Fachkonzept
  - Beschaffungsagent
  - Angebotsphase
  - Prozessautomatisierung
  - Schaufler
quelle: 📄 Fachkonzept – Beschaffungsagent.docx
datum: 2026-06-09
kategorie: Kunde
---

# 📄 Fachkonzept – Beschaffungsagent

Fachkonzept für einen KI-gestützten Beschaffungsagenten im Rahmen der Angebotsphase beim Kunden Schaufler. Das Dokument beschreibt detailliert die Zielsetzung, beteiligte Systeme (Outlook, Winform/Proleis, ELO) und Prozesse zur Automatisierung von Auftragsbestätigungen, Lieferterminüberwachung und Eskalationslogik. Enthält zusätzlich offene Fragen zur technischen und prozessualen Umsetzung.

## Vollständiger Inhalt
📄 Fachkonzept – Beschaffungsagent (abgeleitet aus der Präsentation, inkl. offener Fragen)  1. Zielsetzung des Beschaffungsagenten Der Beschaffungsagent soll den operativen Beschaffungsprozess automatisieren und unterstützen, insbesondere bei: Verarbeitung von Auftragsbestätigungen
 Überwachung von Lieferterminen
 Eskalation bei Abweichungen
 Verarbeitung von Versanddokumenten
 Tracking der Zustellung
 Kommunikation mit Lieferanten
 Weiterleitung an Zoll / Spedition
 Ziel: Entlastung des Einkaufs
 schnellere Reaktion auf Abweichungen
 bessere Datenqualität
 transparente Nachverfolgung
 strukturierte Dokumentenablage
  2. Beteiligte Stakeholder und Systeme Stakeholder Lieferanten
 Einkäufer
 Teamleiter Beschaffung
 Zoll / Spedition (über Verteiler)
 Systeme Outlook (E-Mail Eingang & Ausgang)
 Datenbank: Winform (ab 02.01.2026 Proleis)
 ELO (Dokumentenmanagement)
 Agent (Automatisierungseinheit)
 Datenformate: Text
 Bilder / Scans
 PDFs
  3. Prozess: Auftragsbestätigungen verarbeiten Beschreibung (laut Präsentation) Agent prüft Outlook-Postfach auf neue Auftragsbestätigungen
 Agent liest aus:
 bestätigten Liefertermin
 Auftragsbestätigungsreferenz
 Datum der Auftragsbestätigung
 Agent trägt diese Daten in die Datenbank ein
 Agent legt die Auftragsbestätigung in ELO ab und verschlagwortet sie
 Entscheidungslogik Existiert bereits ein Eintrag:
 früherer bestätigter Liefertermin → alter Eintrag überschreiben
 späterer bestätigter Liefertermin → neuen Termin in „erwarteter Liefertermin“ eintragen
 Prüfung Liefertermin Liefertermin ≤ geforderter Liefertermin → keine Aktion
 Liefertermin > geforderter Liefertermin → Eskalation
  ❓ Offene Fragen (nicht aus Präsentation ableitbar) Wie erkennt der Agent technisch, dass es sich um eine Auftragsbestätigung handelt?
 Gibt es eindeutige Schlüsselwörter oder Formate?
 Welche Tabellen / Felder genau werden in der Datenbank beschrieben?
 Was passiert, wenn mehrere Positionen in einer Auftragsbestätigung enthalten sind?
 Was passiert bei unleserlichen Scans oder Bildern?
 Wie werden Dokumente in ELO strukturiert (Ordner, Metadaten, Schlagworte)?
  4. Eskalation bei spätem Liefertermin Beschreibung (laut Präsentation) Schritt 1: Agent schreibt E-Mail an Lieferanten
 CC: verantwortlicher Einkäufer
 Lieferant wird aufgefordert:
 Liefertermin zu prüfen
 Maßnahmen einzuleiten
 korrigierte Auftragsbestätigung zu senden
 Schritt 2: Einkäufer übernimmt manuell
 korrigiert bestätigten Liefertermin, Referenz und Datum in der Datenbank
  ❓ Offene Fragen Gibt es standardisierte E-Mail-Vorlagen?
 Darf der Agent rechtlich verbindlich formulieren?
 Muss ein Mensch diese Mails freigeben?
 Ab welcher Abweichung gilt ein Liefertermin als kritisch (1 Tag, 1 Woche, sofort)?
  5. Fehlende Auftragsbestätigungen einfordern Beschreibung (laut Präsentation) Agent prüft Datenbank auf fehlende Auftragsbestätigungen
 Pro Lieferant wird eine E-Mail erstellt
 1. Erinnerung freundlich
 Frist: 2 Arbeitstage
 2. Erinnerung bestimmter
 CC: zuständig
