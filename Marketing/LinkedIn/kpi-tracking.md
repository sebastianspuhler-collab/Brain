---
tags: [linkedin, kpi, tracking, reporting]
datum: 2026-08-11
kategorie: Marketing
---

# LinkedIn-Kennzahlen

Kennzahlen-Definition und Prioritäten: `STRATEGIE.md` §10.

## Was automatisch kommt und was nicht

`python3 _agent/buffer_manager.py insights [n]` bzw. das Tool `get_buffer_insights(n)` liefert
aus der Buffer-API pro gesendetem Post:

- Impressions, Reach, Engagement-Rate %, Reactions (Likes), Kommentare, Shares

**Nicht** über Buffer verfügbar — und damit ausgerechnet drei der vier Primär-Kennzahlen:

| Kennzahl | Woher stattdessen |
|---|---|
| **Saves/Post** | LinkedIn-Post → „Analyse anzeigen" → Speicherungen |
| **Profilaufrufe/Woche** | LinkedIn → Ich → Profil-Analysen |
| **DMs/Anfragen** | LinkedIn-Postfach, manuell gezählt |

Diese drei einmal pro Woche von Hand eintragen. Ohne sie misst das Tracking nur das, was leicht
zu messen ist, statt das, was zählt.

## Wochentabelle

Eine Zeile pro Woche. Primär-Kennzahlen fett.

| KW | Zeitraum | **Saves** | **Profilaufrufe** | **DMs/Anfragen** | Impressions | Eng.-Rate | Kommentare | Bester Post (Thema/Säule) |
|---|---|---|---|---|---|---|---|---|
| | | | | | | | | |

## Wöchentliche Auswertung (5 Minuten, montags)

1. Buffer-Insights abrufen: `python3 _agent/buffer_manager.py insights 10`
2. Saves, Profilaufrufe, DMs aus LinkedIn-Analytics nachtragen
3. Besten Post der Vorwoche bestimmen — **nach Saves, nicht nach Likes**
4. Dessen Thema und Säule in der Folgewoche **doppeln**, nicht durch ein neues Thema ersetzen
5. Engagement-Rate gegen den Zielkorridor 5–7 % prüfen
6. Ergebnis als `focus` in die nächste Ideen-Generierung geben

## Interpretationsregeln

- Impressions als **Trend** lesen, nie als Einzelwert. Ein Ausreißer nach oben ist meist ein
  Reichweiten-Zufall, kein Themen-Signal.
- Kommentare zählen algorithmisch mehr als Likes, Qualität vor Menge. Zehn echte Kommentare
  schlagen hundert Likes.
- Ein Themenwechsel ohne Datengrundlage kostet Reichweite — Themen-Fingerprint über mehrere
  Wochen halten (STRATEGIE.md §2).
- Hashtags nicht als Reichweiten-Hebel bewerten. Sie dienen Suche und Filter.
