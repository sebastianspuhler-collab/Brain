---
tags:
  - Beschaffungsagent
  - Schaufler
  - Umsetzungsplan
  - Auftragsbestätigung
  - Lieferterminverfolgung
quelle: 2025-10_26_Beschaffungs_Agent.pdf
datum: 2026-06-09
kategorie: Kunde
---

# 2025-10_26_Beschaffungs_Agent

Technisches Konzeptdokument für den Beschaffungsagenten im Kundenprojekt Schaufler. Es beschreibt die Funktionen des KI-Agenten zur Verarbeitung von Auftragsbestätigungen, Lieferterminverfolgung und automatisierten E-Mail-Kommunikation mit Lieferanten. Die Integration erfolgt über die Systeme Proleis/Winform, Outlook und ELO.

## Vollständiger Inhalt
Vorstellung Konzept 
Einführung
Technische 
Arbeitsvorbereitung
 1Konzept
2Stakeholder und betroffene IT -Systeme
•Datenformat
3Aufgaben den Agenten
•Auftragsbestätigungen
•Lieferungsterminverfolgung
•Zustellung
2 3Outlook
Datenbank
(Winform /
Proleis )Outlook
ELOAgent
 4Stakeholder und betroffene IT -Systeme
 •Stakeholder
•Lieferanten
•Einkäufer
•Proleis
•ELO
•betroffene IT -Systeme:
•Proleis  bzw. Winform  (wir werden ab dem 02.01.2026 von Winform  auf Proleis  wechseln)
•Outlook
•ELO
•Welche Datenformate können übertragen werden
•Text
•Bilder Auftragsbestätigungen
5Auftragsbestätigungen ablegen und bestätigter Liefertermin eintragen
•Agent prüft das E -Mail -Postfach ob neue Auftragsbestätigungen eingegangen sind
•Agent trägt den bestätigten Liefertermin, die Auftragsbestätigungsreferenz und das Datum 
der Auftragsbestätigung in die Datenbank ein
•Wenn ein Eintrag existiert
•Bei einem früheren bestätigten Liefertermin → alter Eintrag überschreiben
•Bei einem späteren  bestätigten Liefertermin → neuen bestätigten Liefertermin in erwarteten Liefertermin 
eintragen
•Agent legt die Auftragsbestätigung im ELO ab und verschlagen Worten
•Agent prüft ob bestätigter Liefertermin
•vor oder zum geforderten Liefertermin bestätigt worden ist → Keine Aktion notwendig
•nach dem geforderten Liefertermin bestätigt worden ist
1. Schritt
Agent verfasst eine E -Mail an den Lieferanten 
•Emailverteiler
• An: Lieferant
• CC: Verantwortlicher Einkäufer
•Lieferant wird aufgefordert Liefertermin zu prüfen und alle notwendigen Schritte einzuleiten sodass der geforderte 
Liefertermin eingehalten wird. Desweiten wird der Lieferant aufgefordert die korrigierte Auftragsbestätigung zu 
senden
•2. Schritt
Verantwortlicher Einkäufer übernimmt die Thematik
•bestätigter Liefertermin, die Auftragsbestätigungsreferenz und das Datum der Auftragsbestätigung müssen manuell 
in die Datenbank geändert werden Auftragsbestätigungen
6Fehlende Auftragsbestätigungen einfordern
Der Agent überprüft die Datenbank, zu welchen Bestellpositionen Auftragsbestätigungen fehlen. Falls 
Auftragsbestätigungen fehlen, wird je Lieferant eine E -Mail erstellt, in der der Lieferant aufgefordert wird, 
die Auftragsbestätigung zu senden.
1. Erinnerung 
•Ton: nett und höflich
•Inhalt: Bitte um Zusendung der Auftragsbestätigung zur genannten Bestellung
•Frist: 2 Tage Arbeitstage
•Ziel: zeitnahe Reaktion des Lieferanten
2. Erinnerung
•Ton: weiterhin freundlich, aber bestimmter
•CC: zuständiger Einkäufer
•Inhalt: Hinweis auf die erste Erinnerung
•Frist: weitere 2 Tage Arbeitstage
•Ziel: Verdeutlichung der Dringlichkeit
3. Erinnerung
•Ton: verbindlich
•CC: Teamleiter Beschaffung und zuständiger Einkäufer
•Inhalt: Hinweis, dass bei weiterem Ausbleiben der Auftragsbestätigung Maßnahmen eingeleitet werden 
•Ziel: Abschluss des Vorgangs  Lieferungsterminverfolgung
7Lieferungen in der Zukunft
•Der Agent überprüft wöchentlich die Datenbank, um festzustellen, welche Lieferungen je Lieferant in 
Zukunft anstehen oder no
