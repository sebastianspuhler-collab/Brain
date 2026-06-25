---
tags:
  - Developer Spec
  - Beat Battle Royale
  - Game Development
  - Screen-Flow
  - Spielmodi
quelle: BBR_Developer_Spec.pdf
datum: 2026-06-09
kategorie: Kunde
---

# BBR_Developer_Spec

Technische Entwicklerspezifikation (v1.0) für das Spiel 'Beat Battle Royale', beschreibt Lobby-Aufbau, Screen-Flow, Spielmodi und Implementierungslogik für Frontend & Backend. Enthält detaillierte Anforderungen zu Audio-Test, Spieler-Anmeldung, Jahrzehnt- und Genre-Auswahl. Kein Punktesystem – Fokus auf technische Umsetzung für 1–6 Spieler lokal oder remote.

## Vollständiger Inhalt
Beat Battle Royale  ·  Developer Spec v1.0  ·  Seite 1
 ■
 BEAT BATTLE ROYALE
 Developer Specification · Screens & Modi
 Dieses Dokument beschreibt Lobby-Aufbau, Spielmodi-Abläufe und technische Anforderungen. Kein
 Punktesystem – Fokus auf Screen-Flow und Implementierungslogik.
 
Version
1.0  (Spec-Dokument ohne Scoring)
Zielgruppe
Entwickler  –  Frontend & Backend
Spielerzahl
1–6 Personen  (lokal oder remote via Voicechat)
Neue Modi
7 Spielmodi gesamt (inkl. 2 neuer Modi in diesem Dokument)
 Beat Battle Royale  ·  Developer Spec v1.0  ·  Seite 2
1. LOBBY & ANMELDEMASKE
1.1 Audio-Test (vor allem anderen)
Bevor irgendein Setup-Screen erscheint, wird ein kurzes Audio-Signal abgespielt. Erst wenn der Nutzer
bestätigt, dass er den Ton gehört hat, geht es weiter.
DEV-HINWEIS: Button „Ton gehört ✓" muss aktiv geklickt werden – kein Auto-Skip. Falls kein Ton: Link zu
Browser-Audioeinstellungen anzeigen.
1.2 Spieler-Anzahl & Namen
1
Auswahl der Spieleranzahl: 1 – 6 Personen (Stepper oder Buttons).
2
Für jeden Spieler: Eingabefeld für den Namen (Pflichtfeld, max. 20 Zeichen).
3
Namen erscheinen später im Buzzer-Tracker und Scoreboard.
4
Multiplayer-Hinweis einblenden: „Remote-Modus: Alle Spieler öffnen die App auf ihrem Gerät und
kommunizieren per Voicechat (z.B. Discord)."
DEV-HINWEIS: Namen müssen session-weit als Array gespeichert sein. Bei Remote-Modus: kein Echtzeit-Sync
erforderlich – jeder Spieler sieht seine eigene App-Instanz.
1.3 Jahrzehnt-Auswahl
Mehrfachauswahl möglich. Mindestens ein Jahrzehnt muss gewählt sein.
Auswahl
Zeitraum
Typische Genres (Beispiele – in DB hinterlegen!)
60er
1960–1969
Rock 'n' Roll, Beat, Soul, Folk, Psychedelic Rock
70er
1970–1979
Disco, Funk, Soul, Classic Rock, Prog Rock, Punk
80er
1980–1989
Pop, Synthpop, New Wave, Hair Metal, Hip-Hop (früh), Schlager
90er
1990–1999
Pop, Grunge, R&B;, Eurodance, Hip-Hop, Britpop, Techno
2000er
2000–2009
Pop, R&B;, Hip-Hop, Emo, Rock, Electronic, Schlager
2010er
2010–2019
Pop, EDM, Trap, Indie Pop, K-Pop, Latin Pop
Aktuell
2020–heute
Pop, Afrobeats, Hyperpop, Latin, Hip-Hop, Electronic
DEV-HINWEIS: In der Datenbank muss pro Jahrzehnt eine Liste typischer Genres hinterlegt sein. Wenn der Nutzer
ein Jahrzehnt auswählt, werden im nächsten Screen (Genre-Auswahl) automatisch nur die für dieses Jahrzehnt
relevanten Genres angezeigt. Bei Mehrfachauswahl von Jahrzehnten: UNION der Genre-Listen bilden (Duplikate
entfernen). Genres sind NICHT global fest – sie sind jahrzehntabhängig und kommen aus der DB.
1.4 Genre-Auswahl
Die angezeigten Genres werden dynamisch aus der Jahrzehnt-Selektion (1.3) generiert. Mehrfachauswahl
möglich. Mindestens ein Genre muss aktiv sein.
 Beat Battle Royale  ·  Developer Spec v1.0  ·  Seite 3
Beispiel-Genres (vollständige Liste kommt aus DB):
Pop
Rock
Hip-Hop / Rap
R&B; / Soul
Electronic / Dance
Schlager / Deutsch
Metal / Hard Rock
Indie / Alternative
Latin
Disco / Funk
Grunge
Techno / House
Eurodance
K-Pop
Country / Folk
DEV-HINWEIS: Genre-Filter bestimmt, wel
