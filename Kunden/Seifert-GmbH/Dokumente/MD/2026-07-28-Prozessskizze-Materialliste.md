---
tags: [Seifert, Prozessskizze, Stückliste, Materialliste, Zuschnitte, KI-Agent]
datum: 2026-07-28
kategorie: Lead
quelle: Transkript "Stefan Seifert and Sebastian Spuhler" vom 23.07.2026
---

# Prozessskizze: KI-gestützte Material-/Zuschnittliste für Schweißbaugruppen
### Seifert GmbH – Vorbereitung Termin 28.07.2026, 14:30 Uhr

Diese Skizze basiert 1:1 auf dem, was Stefan Seifert und Sebastian Spuhler im Erstgespräch am 23.07.2026 besprochen haben. Es werden ausschließlich Fakten aus dem Transkript verwendet – keine ergänzten Schritte, Zahlen oder Annahmen.

---

## Ausgangslage

Seifert nutzt aktuell **Spanflug** zur Kalkulation von Frästeilen:
- Input: PDF eines Frästeils + 3D-Modell
- Spanflug berechnet daraus: Fräszeit, Anzahl Bohrungen, benötigte Werkzeuge (Grundbohrer, Bohrer, Fräser), sowie einen Vorschlag für die Werktage
- Funktioniert laut Seifert gut bei einteiligen Zerspanungsteilen ("wenn man einen Klotz hat und den komplett zerspant, dann funktioniert das eigentlich ganz gut")

## Das Problem

Bei Seifert sind die Aufträge aber überwiegend **geschweißte Baugruppen aus mehreren Einzelteilen** ("meistens halt immer so geschweißte Baugruppen"). Spanflug erkennt diese Zusammensetzung nicht ("das schluckt das System nicht") – das Tool ist nicht flexibel genug für diesen Regelfall bei Seifert.

## Was Seifert stattdessen braucht

Eine **Gesamtliste**, die automatisiert erstellt wird und zeigt:
- welches Material benötigt wird
- welche Zuschnitte benötigt werden
- zu welchen Positionen diese gehören (Beispiel aus dem Transkript: "das Bauteil gibt es 5 mal zu 5 Positionen")

Diese Zuordnung braucht Seifert, um die **Kosten korrekt auf die einzelnen Positionen aufzuteilen**. Aktuell macht sein Team das handschriftlich ("das schreiben wir momentan handschriftlich zusammen").

## Ablauf (nach Seiferts eigener Beschreibung)

**1. Upload der Unterlagen**
→ Zeichnungen, Daten bzw. Stücklisten werden hochgeladen ("dann lad ich halt die Zeichnungen, Daten oder Stücklisten hoch")

**2. Verarbeitung**
→ Aus den hochgeladenen Unterlagen soll ein Programm/eine Plattform ableiten, welches Material und welche Zuschnitte pro Position benötigt werden

**3. Output: Gesamtliste**
→ Material- und Zuschnittliste, positionsgenau zugeordnet, als Grundlage für die Kostenaufteilung auf die einzelnen Positionen

---

## Visuelle Kurzfassung (für Folie/PDF)

```
 Zeichnungen / Daten / Stücklisten
              │
              ▼
   Verarbeitung: Material- &
   Zuschnittbedarf je Position
   ableiten
              │
              ▼
   Gesamtliste: Material + Zuschnitte
   zugeordnet zu Positionen
              │
              ▼
   Grundlage für Kostenaufteilung
   auf die Positionen
```

---

## Wichtiger Unterschied zu Spanflug

Spanflug kalkuliert **Zeit und Werkzeugbedarf** für einteilige Frästeile. Der hier skizzierte Bedarf ist ein anderer: **Material-/Zuschnittzuordnung für mehrteilige Schweißbaugruppen** zur Kostenaufteilung. Beide Tools würden nebeneinander bestehen, nicht Spanflug ersetzen.

## Offene Punkte für den Termin

- Das Transkript bricht genau an der Stelle ab, an der Seifert beginnt zu beschreiben, wie ein Programm das lösen könnte ("Wenn sowas möglich wäre, wie gesagt, dass ich sag, irgendwie ein Programm oder irgendwie eine Seite, wo halt so die Daten oder halt..."). Die genaue technische Vorstellung ist damit **nicht zu Ende dokumentiert** – im Termin gezielt nachfragen, wie er sich die Eingabe/Ausgabe konkret vorstellt.
- Seifert hat am 27.07. per Mail Stücklisten und Einzelteilzeichnungen zu einer Anfrage (6000017119) geschickt – liegen als PDFs in Memos/ (u.a. Stückliste_-_6000017119, mehrere MATERIAL_*.pdf). Diese wirken bisher wie generische Test-/Beispieldaten ohne eindeutig erkennbaren Bezug zu einem realen Seifert-Kundenauftrag – vor dem Termin gegenchecken, um im Meeting nicht an den falschen Zahlen zu argumentieren.
- Kostenstruktur wurde in diesem Gespräch nicht thematisiert – noch offen, welchen Scope/Preis Sebastian ansetzt.
