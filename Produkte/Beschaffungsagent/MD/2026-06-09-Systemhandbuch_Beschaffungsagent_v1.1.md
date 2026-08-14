---
tags:
  - Beschaffungsagent
  - Systemhandbuch
  - Schaufler Fischer Group
  - Einkauf
  - Dashboard
quelle: Systemhandbuch_Beschaffungsagent_v1.1.pdf
datum: 2026-06-09
kategorie: Produkt
---

# Systemhandbuch_Beschaffungsagent_v1.1

Systemhandbuch für den Beschaffungsagenten der Schaufler Fischer Group in Version 1.1 (Stand Juni 2026). Es beschreibt die Funktionsweise des Systems zur automatisierten Überwachung von Auftragsbestätigungen, Lieferterminen und Versanddokumenten im Einkauf. Enthalten sind Dashboard-Übersicht, Rollenkonzept und der gesamte Verarbeitungsablauf eingehender E-Mails und Dokumente.

## Vollständiger Inhalt
Systemhandbuch – Beschaffungsagent
Schaufler Fischer Group
Version: 1.1
Stand: 01.06.2026
Seite 1/19 Systemhandbuch – Beschaffungsagent | Schaufler Fischer Group Seite 2
1. Was macht das System?
Der Beschaffungsagent unterstützt den Einkauf bei der Überwachung von Auftragsbestätigungen, Lieferterminen, fehlenden ABs,
Messberichten, Versanddokumenten und laufenden Lieferungen. Ziel ist, Abweichungen und offene Punkte früh zu erkennen und
für den Einkauf nachvollziehbar sichtbar zu machen.
Das System besteht aus drei Teilen:
•  dem Dashboard , in dem die Benutzer arbeiten
•  einem Hintergrunddienst , der E-Mails und Folgeprozesse automatisch verarbeitet
•  einer zentralen Datenspeicherung , in der alle Vorgänge nachvollziehbar abgelegt werden
Kurzablauf:
1. Benutzer melden sich im Dashboard an.
2. Der Hintergrunddienst prüft das angebundene E-Mail-Postfach regelmäßig oder nach manuellem Start.
3. Eingehende Nachrichten werden als Auftragsbestätigung, Messbericht, Versanddokument, T1-Dokument oder Unklarheit
eingeordnet.
4. Auftragsbestätigungen werden mit KI-Unterstützung und zusätzlichen Prüfregeln ausgelesen, im Dokumentenarchiv
abgelegt und mit den Bestelldaten verglichen.
5. Abweichungen bei Termin, Preis, Menge oder Transport führen zu Hinweisen, Eskalationen oder weiteren Folgeaktionen.
6. Fehlende ABs werden über ein 3-Stufen-Erinnerungssystem verfolgt.
7. Messberichte werden auf Vollständigkeit geprüft und an die zuständige Fachabteilung weitergeleitet.
8. Versanddokumente und T1-Dokumente werden separat verarbeitet.
9. Offene Bestellungen werden bei Bedarf durch Lieferstatus-Anfragen oder Anforderungen von Versanddokumenten aktiv
nachverfolgt.
10. Alle Ergebnisse erscheinen im Dashboard, im Aktivitätsverlauf und in den Excel-Exporten.
2. Seitenübersicht im Dashboard
Das Dashboard ist in klar getrennte Seiten aufgeteilt. Je nach Rolle sieht ein Benutzer nur die Seiten, die für seinen
Aufgabenbereich freigegeben sind.
Seite 2/19 Systemhandbuch – Beschaffungsagent | Schaufler Fischer Group Seite 3
 Seite  Aufruf  Standardrollen  Inhalt
 Auftragsbestätigungen  `/auftragsbestaetigung`  Einkauf, Qualität  Auftragsbestätigungen, fehlende ABs und Eskalationen in 3 Tabs
 Messberichte  `/messberichte`  Qualität  Prüfung und Weiterleitung von Messberichten
 Lieferanten  `/lieferanten`  Einkauf  Lieferantenbewertung mit Punktesystem
 Lieferungen  `/lieferungen`  Einkauf, Logistik  Liefertermine, Sendungsverfolgung und Detailansicht
 Unklarheiten  `/unklarheiten`  Einkauf  Nicht zuordenbare E-Mails zur manuellen Prüfung
 Reporting  `/reporting`  Einkauf, Qualität, Logistik  Kennzahlenübersichten und Excel-Exporte
 Aktivität  `/aktivitaet`  Einkauf, Qualität, Logistik  Chronologischer Verlauf aller wichtigen Systemaktionen
 Steuerung  `/steuerung`  Admin  Systemkontrolle, Konfiguration, Sprache und Logs
 Benutzerverwaltung  `/benutzerverwaltung`  Admin  Benutzer, Rollen, Passwörter und Seitenfreigaben
Wichtige Hinweise:
•  Auch die Aufrufe `/bestellunge
