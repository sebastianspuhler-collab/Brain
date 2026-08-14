---
tags:
  - Fachkonzept
  - Beschaffungsagent
  - Automatisierung
  - Schaufler
  - Auftragsbestätigung
quelle: Untitled document.pdf
datum: 2026-06-09
kategorie: Produkt
---

# Untitled document

Fachkonzept für den Beschaffungsagenten von Schaufler, abgeleitet aus einer Präsentation. Es beschreibt die Zielsetzung, beteiligte Stakeholder und Systeme (Outlook, Winform/Proleis, ELO) sowie den detaillierten Prozess zur Verarbeitung von Auftragsbestätigungen inklusive Eskalationslogik bei späten Lieferterminen. Zusätzlich sind offene Fragen zur technischen Umsetzung dokumentiert.

## Vollständiger Inhalt
📄
 
Fachkonzept
 
–
 
Beschaffungsagent
 
(abgeleitet
 
aus
 
der
 
Präsentation,
 
inkl.
 
offener
 
Fragen)
 
 
1.
 
Zielsetzung
 
des
 
Beschaffungsagenten
 
Der
 
Beschaffungsagent
 
soll
 
den
 
operativen
 
Beschaffungsprozess
 
automatisieren
 
und
 
unterstützen,
 
insbesondere
 
bei:
 
●
 
Verarbeitung
 
von
 
Auftragsbestätigungen
 
 
●
 
Überwachung
 
von
 
Lieferterminen
 
 
●
 
Eskalation
 
bei
 
Abweichungen
 
 
●
 
Verarbeitung
 
von
 
Versanddokumenten
 
 
●
 
Tracking
 
der
 
Zustellung
 
 
●
 
Kommunikation
 
mit
 
Lieferanten
 
 
●
 
Weiterleitung
 
an
 
Zoll
 
/
 
Spedition
 
 
Ziel:
 
●
 
Entlastung
 
des
 
Einkaufs
 
 
●
 
schnellere
 
Reaktion
 
auf
 
Abweichungen
 
 
●
 
bessere
 
Datenqualität
 
 
●
 
transparente
 
Nachverfolgung
 
 
●
 
strukturierte
 
Dokumentenablage
 
 
  2.
 
Beteiligte
 
Stakeholder
 
und
 
Systeme
 
Stakeholder
 
●
 
Lieferanten
 
 
●
 
Einkäufer
 
 
●
 
Teamleiter
 
Beschaffung
 
 
●
 
Zoll
 
/
 
Spedition
 
(über
 
Verteiler)
 
 
Systeme
 
●
 
Outlook
 
(E-Mail
 
Eingang
 
&
 
Ausgang)
 
 
●
 
Datenbank:
 
Winform
 
(ab
 
02.01.2026
 
Proleis)
 
 
●
 
ELO
 
(Dokumentenmanagement)
 
 
●
 
Agent
 
(Automatisierungseinheit)
 
 
Datenformate:
 
●
 
Text
 
 
●
 
Bilder
 
/
 
Scans
 
 
●
 
PDFs
 
 
 
3.
 
Prozess:
 
Auftragsbestätigungen
 
verarbeiten
 
Beschreibung
 
(laut
 
Präsentation)
 
1.
 
Agent
 
prüft
 
Outlook-Postfach
 
auf
 
neue
 
Auftragsbestätigungen
 
 
2.
 
Agent
 
liest
 
aus:
 
  ○
 
bestätigten
 
Liefertermin
 
 
○
 
Auftragsbestätigungsreferenz
 
 
○
 
Datum
 
der
 
Auftragsbestätigung
 
 
3.
 
Agent
 
trägt
 
diese
 
Daten
 
in
 
die
 
Datenbank
 
ein
 
 
4.
 
Agent
 
legt
 
die
 
Auftragsbestätigung
 
in
 
ELO
 
ab
 
und
 
verschlagwortet
 
sie
 
 
Entscheidungslogik
 
●
 
Existiert
 
bereits
 
ein
 
Eintrag:
 
 
○
 
früherer
 
bestätigter
 
Liefertermin
 
→
 
alter
 
Eintrag
 
überschreiben
 
 
○
 
späterer
 
bestätigter
 
Liefertermin
 
→
 
neuen
 
Termin
 
in
 
„erwarteter
 
Liefertermin“
 
eintragen
 
 
Prüfung
 
Liefertermin
 
●
 
Liefertermin
 
≤
 
geforderter
 
Liefertermin
 
→
 
keine
 
Aktion
 
 
●
 
Liefertermin
 
>
 
geforderter
 
Liefertermin
 
→
 
Eskalation
 
 
 
❓
 
Offene
 
Fragen
 
(nicht
 
aus
 
Präsentation
 
ableitbar)
 
●
 
Wie
 
erkennt
 
der
 
Agent
 
technisch,
 
dass
 
es
 
sich
 
um
 
eine
 
Auftragsbestätigung
 
handelt?
 
 
●
 
Gibt
 
es
 
eindeutige
 
Schlüsselwörter
 
oder
 
Formate?
 
 
●
 
Welche
 
Tabellen
 
/
 
Felder
 
genau
 
werden
 
in
 
der
 
Datenbank
 
beschrieben?
 
 
●
 
Was
 
passiert,
 
wenn
 
mehrere
 
Positionen
 
in
 
einer
 
Auftragsbestätigung
 
enthalten
 
sind?
 
 
●
 
Was
 
passiert
 
bei
 
unleserlichen
 
Scans
 
oder
 
Bildern?
 
 
●
 
Wie
 
werden
 
Dokumente
 
in
 
ELO
 
strukturiert
 
(Ordner,
 
Metadaten,
 
Schlagworte)?
 
   
4.
 
Eskalation
 
bei
 
spätem
 
Liefertermin
 
Beschreibung
 
(laut
 
Präsentation)
 
Schritt
 
1:
 
●
 
Agent
 
schreibt
 
E-Mail
 
an
 
Lieferanten
 
 
●
 
CC:
 
verantwortlicher
 
Einkäufer
 
 
