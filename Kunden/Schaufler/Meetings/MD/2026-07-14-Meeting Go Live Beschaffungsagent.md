---
tags:
  - Go-Live
  - Beschaffungsagent
  - WinForm
  - Testsystem
  - Schaufler
quelle: Meeting Go Live Beschaffungsagent (2).pdf
datum: 2026-07-14
kategorie: Kunde
---

# Meeting Go Live Beschaffungsagent (Schaufler)

## Zusammenfassung
Vorbereitungsgespräch am 14.07.2026 für den Go-Live des Beschaffungsagenten bei Schaufler, mit Sebastian Spuhler und Amin Douioui (Prozessia) sowie Jochen Hettmer (WinForm/IT-Dienstleister). Thema: technische Abstimmung zum WinForm-Testsystem (kein separates Testsystem vorhanden, nur eine Testdatenbank mit Select-Zugriff), Kommentar-Kennzeichnung bei Datensatz-Aktualisierungen zur Nachverfolgbarkeit für Schaufler.

## Teilnehmer
- Sebastian Spuhler (Prozessia)
- Amin Douioui (Prozessia)
- Jochen Hettmer (WinForm/IT-Dienstleister)
- (weitere Teilnehmer laut Gespräch "zu fünft" anwesend, u.a. vermutlich Benjamin Schmohl/Schaufler)

## Kernpunkte
- Jochen Hettmer bestätigt technische Umsetzung: bei Aktualisierung von Datensätzen wird ein Kommentar/Suchbegriff in einem Textfeld hinterlegt
- Es gibt kein separates WinForm-Testsystem, nur eine WinForm-Testdatenbank ohne direkten Zugriff für Schaufler - Hettmer kann für Schaufler per Select-Abfrage im Testsystem nach markierten Datensätzen suchen
- Gespräch dient der Klärung offener technischer Punkte vor dem eigentlichen Go-Live

## Zusagen
- (keine expliziten neuen Zusagen über die bereits laufende technische Abstimmung hinaus)

## Nächste Schritte
- Team teilt Hettmer den verwendeten Suchbegriff/Kommentar mit, damit er die entsprechenden Testsystem-Datensätze für Schaufler selektieren kann

## Entscheidungen
- (keine)

## Vollständiger Inhalt
Meeting Go Live Beschaffungsagent-20260714_110028-Besprechungstranskript
14. Juli 2026, 09:00AM, 35 Min. 0 Sek.

Hettmer, Jochen 0:11: Sebastian, kurz technisch, du hast es jetzt so gemacht, wie von mir vorgeschlagen, wenn du Datensätze aktualisierst, dass du in diesem Textfeld irgendeinen Kommentar hinterlegst.
Sebastian Spuhler 0:12: Ja, das ist Amins Part, aber das haben wir so gemacht, oder?
Amin Douioui 0:25: Ja.
Hettmer, Jochen 0:32: Wenn ihr mir mitteilt, was ihr reinschreibt als Suchbegriff, kann ich für Schaufler mal alle Datensätze selektieren, wo irgendwas drinsteht im Testsystem, weil die können auf das Testsystem nicht zugreifen. Es gibt kein WinForm-Testsystem in der Form, es gibt nur eine WinForm-Testdatenbank. Das heißt, Sie können da selber nichts gucken - Sie können da einfach mal ein Select drauf machen, mir ist das egal, das kannst du genauso machen.
Sebastian Spuhler 1:08: Ja genau, also ich hab jetzt hier noch - wir sind jetzt alle da zu fünft, wir haben paar Punkte aufgeschrieben, die wir von euch noch br[auchen]...
