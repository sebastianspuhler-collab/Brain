# LinkedIn Auto Poster

## Beim Start immer lesen
1. `STRATEGIE.md` — verbindliche Content-Strategie. Bei Widerspruch gewinnt immer diese Datei.
2. `brain-direction.md` — aktuelle Wochen-Richtung von Sebastian via Brain UI
3. `.env` — API-Credentials (Buffer)
4. letzte `ideen-*.json` / `beitraege-*.json` als Referenz

## Workflow
1. **Recherche** → vier Blöcke aus STRATEGIE.md §11, Ergebnis als `focus` einspeisen
2. **Ideen generieren** → `ideen-YYYY-MM-DD.json`
3. **Beiträge ausarbeiten** → `beitraege-YYYY-MM-DD.json`
4. **Karussell produzieren** → `generate_carousel` (Slides + Begleittext + PDF + Buffer)
5. **Planen** → Buffer, **Dienstag und Donnerstag, 09:30 Uhr (Berlin)**
   - Sebastian Spuhler (Profil): `6a25d2578f1d11f9b260c5ee`
   - Prozessia (Seite): `6a25d2578f1d11f9b260c5ef`
6. **60 Minuten nach Go-Live**: Kommentare beantworten (macht Sebastian selbst)

## Zielgruppe
Geschäftsführer und Einkaufsleiter in inhabergeführten, produzierenden Mittelständlern,
20–80 Mitarbeitende, Deutschland.
Branchen: Werkzeugbau, Lohnfertigung, Elektrotechnik, Kunststoff, Metallbau.

Die Fertigungs-Nische ist das Kernargument der Positionierung. Jeder Post muss nach Fertigung
klingen — nach Stücklisten, Ausschreibungen, Zeichnungen, Maschinen. Nie zu „der Mittelstand"
allgemein verwässern.

## Themen-Säulen (genau eine pro Post)
- **Wissensmanagement** — Firmenwissen sichern, KI-gestützte Dokumentation
- **Compliance** — EU-KI-Verordnung, Transparenzpflichten, DSGVO
- **Einkauf** — Ausschreibung, Kalkulation, Lieferantenmanagement, Long-Tail-Spend
- **KI-Nutzung** — Adoption, Hürden, Praxisbeispiele, Stücklisten-/BOM-Automatisierung

Themen-Fingerprint über mehrere Wochen halten, nicht wöchentlich springen.

## Post-Typen (A/B/C-System)
Jeder Post hat genau einen Typ. Verhältnis: 4× A, 3× B, 3× C pro Batch.

**Typ A – Schmerz-Post** — Ich-Perspektive, konkreter Alltags-Schmerz, keine KI-Lösung im
ersten Satz. Fließtext, 3–7 Absätze.

**Typ B – Karussell/Dokument-Post** — Framework, Checkliste oder Schritt-für-Schritt,
3–7 nummerierte Punkte. Leitformat, mindestens die Hälfte der Ideen soll hierhin passen.

**Typ C – Story-Post** — anonymes Vorher/Nachher mit konkreten Zahlen (Stunden, €, Prozent).

## Claim it, Show it, Aim it (ausnahmslos)
- **Claim:** klare Aussage. Keine Frage als These, kein Hedging.
- **Show:** eigene Zahl oder konkrete Beobachtung, kein nacherzähltes fremdes Framework.
- **Aim:** an eine konkrete Person gerichtet, nicht an „alle Unternehmen".

## Aufbau des Post-Textes
1. Kurze Einleitung/Frage, die das Problem umreißt
2. 2–3 konkrete Zahlen oder Fakten
3. Ergebnis-Zeile allein auf einer Zeile: `**Ergebnis: …**`
4. Optional: Fachsystem/Norm für Autorität (SAP, proALPHA, ERP, branchenübliche Normen)
5. Kurzer Einordnungs-Absatz, 2–3 Sätze
6. Abschlussfrage, nur mit echter Berufserfahrung beantwortbar
7. 3–5 Hashtags

`**…**` nur für die Ergebnis-Zeile. Die Umwandlung in LinkedIn-Fettschrift passiert
automatisch beim Push (`carousel_service._linkedin_bold`).

## Format-Regeln (ausnahmslos)
- Max. 15 Wörter pro Satz
- Leerzeile nach jeder 2. Zeile
- **3–5 Hashtags** am Ende, Mischung aus breit und spezifisch
- 0 Emojis (maximal 1 in der letzten Zeile, optional)
- **Links NIE im Post-Text** — immer als erster Kommentar

## Hashtags
Erlaubt und erwünscht ist die Mischung:
- breit: `#KI`, `#Mittelstand`
- spezifisch: `#Werkzeugbau`, `#Beschaffung`, `#Wissensmanagement`, `#Lohnfertigung`,
  `#Einkauf`, `#Produktion`, `#Stückliste`, `#ERP`, `#EUAIAct`

Hashtags dienen Suche und Filter, nicht Reichweite — keine Reichweitenerwartung daran knüpfen.

> Geändert am 2026-08-11: Vorher waren `#KI` und `#Mittelstand` verboten und maximal 3 Hashtags
> erlaubt. Die Strategie verlangt ausdrücklich die Mischung aus breit und spezifisch, siehe
> STRATEGIE.md, Abschnitt „Aufgelöste Widersprüche".

## Beispiele und Kundennamen
Erfundene Beispiele sind erlaubt, wenn sie mitreißend sind — unter drei Bedingungen:
1. Immer ein **erfundener** Firmenname („Elektro Nordstern GmbH", „Nordmetall Fertigung GmbH").
2. Immer als **typisches Szenario** gerahmt, nie als verifizierbares reales Kundenergebnis.
   Sonst ist es irreführende Werbung.
3. Konkret genug, dass die Zielgruppe sich wiedererkennt.

Echte Kundennamen niemals nennen.

## VERBOTENE Wörter
innovativ, nachhaltig, ganzheitlich, Lösung, Transformation, revolutionieren, disruptiv,
zukunftsfähig

## VERBOTEN im Hook (erste Zeile)
- Statistik oder Prozentzahl als erster Satz
- Vollständiger Satz (Fragment oder Frage ist besser)
- Engagement-Bait: „Teile diesen Post", „Tag jemanden"
- „In der heutigen Zeit", „Die KI wird…"

## PFLICHT für den Hook
- Stoppt den Scroll in 3 Sekunden
- Ich-Perspektive ODER direkte Du-Ansprache
- Fragment oder kurze Frage

## VERBOTEN im Abschluss
Generische Zustimmungsfragen: „Stimmt ihr zu?", „Wer kennt das?", „Was denkt ihr?".
Ebenso „Kontaktiert uns"-Floskeln. Die Abschlussfrage muss die Aussage stützen und
Berufserfahrung voraussetzen.

## Ton
Deutsch, direkt, nüchtern-konkret. Keine Superlative ohne Beleg, keine performte Bescheidenheit,
kein Hedging. Aussagen werden getroffen, nicht zur Diskussion gestellt.
