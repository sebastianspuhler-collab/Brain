---
tags: [linkedin, content-strategie, positionierung, design, prozessia]
datum: 2026-08-11
kategorie: Marketing
status: verbindlich
---

# LinkedIn-Content-Strategie Prozessia

Verbindliche Grundlage für die gesamte LinkedIn-Pipeline. Wenn eine andere Datei
dieser hier widerspricht, gilt diese Datei.

**Wo das im Code hängt:**

| Was | Datei |
|---|---|
| Ideen- und Post-Generierung | `backend/app/services/linkedin_service.py` |
| Karussell-Slides + Begleittext | `services/content-engine/server/services/claudeService.js` |
| Karussell-Design/Rendering | `backend/app/services/carousel_service.py` |
| Regeln für den Autoposter-Lauf | `Marketing/LinkedIn/CLAUDE.md` |
| Aktuelle Wochen-Richtung | `Marketing/LinkedIn/brain-direction.md` |
| Bild-Prompts | `Marketing/LinkedIn/bild-prompts.md` |
| Kennzahlen | `Marketing/LinkedIn/kpi-tracking.md` |

---

## 1. Zielgruppe & Positionierung

- **Zielunternehmen:** inhabergeführte, produzierende Mittelständler, 20–80 Mitarbeitende, Deutschland
- **Branchen:** Werkzeugbau, Lohnfertigung, Elektrotechnik, Kunststoff, Metallbau
- **Zielpersonen:** Geschäftsführer und Einkaufsleiter
- **Differenzierung:** Generische KI-Agenturen sprechen „den Mittelstand" allgemein an, ohne
  Branchen-Nische. Prozessias klare Fertigungs-Nische ist das Kernargument der Positionierung —
  in jedem Post spürbar, nicht verwässern.

## 2. Themen-Säulen

Content dreht sich um genau diese vier Bereiche:

1. **Wissensmanagement** — Wissen im Unternehmen sichern, KI-gestützte Dokumentation,
   Corporate-Wissen strukturieren
2. **Datenschutz / Compliance** — EU-KI-Verordnung, Transparenzpflichten für KI-Systeme
   (z.B. Chatbots), DSGVO-Konformität von KI-Lösungen
3. **Einkauf / Beschaffung** — Ausschreibungsprozesse, Kalkulation, Lieferantenmanagement,
   Long-Tail-Spend-Problematik
4. **Allgemeine KI-Nutzung im Mittelstand** — Adoption, Hürden, Praxisbeispiele,
   Stücklisten-/BOM-Automatisierung

**Produkte, um die sich Content dreht:** Beschaffungsagent, Stücklistenagent (BOM-Mapper),
KI-Chatbot, KI-Schulungen.

Themen-Fingerprint über mehrere Wochen halten, nicht wöchentlich springen — Accounts, die den
Fokus plötzlich wechseln, verlieren temporär Reichweite.

## 3. Content-Prinzipien (gelten für JEDEN Post ausnahmslos)

Drei Grundprinzipien für jeden Beitrag:

- **Klare Aussage:** eine begründete Aussage statt Frage/Hedging („könnte sein", „korrigiert
  mich", „was denkt ihr?")
- **Eigene Beobachtung:** eigene Erfahrung/eigene Zahl statt fremdes Framework nacherzählt
- **Konkreter Leser:** an eine konkrete Person gerichtet (z.B. „Einkaufsleiter mit Ausschreibung
  ohne Herstellerangabe"), nicht an „alle Unternehmen"

**Weitere feste Regeln:**

- Anonymisierte Beispiele dürfen erfunden sein, sofern sie mitreißend sind — dabei **immer**
  erfundene Firmennamen (z.B. „Elektro Nordstern GmbH", „Nordmetall Fertigung GmbH"),
  **niemals** echte Kundennamen. Beispiele als „typisches Szenario" rahmen, nicht als
  verifizierbares reales Kundenergebnis (rechtliche Vorsicht: irreführende Werbung vermeiden).
- Abschlussfragen nur, wenn sie die Aussage stützen und nur mit echter Erfahrung beantwortbar
  sind. Generische Zustimmungsfragen („Stimmt ihr zu?", „Wer kennt das?") sind tabu.
- 3–5 Hashtags pro Post, Mischung aus breit (#KI, #Mittelstand) und spezifisch (#Werkzeugbau,
  #Beschaffung, #Wissensmanagement). Hashtags dienen Suche/Filter, nicht Reichweite — keine
  Reichweitenerwartung daran knüpfen.

## 4. Text-/Caption-Struktur (pro Karussell-Post)

1. Kurze Einleitung/Frage, die das Problem umreißt
2. 2–3 konkrete Zahlen oder Fakten
3. Eine fett hervorgehobene Ergebnis-Zeile („Ergebnis: …")
4. Optional: Namedropping bekannter Fachsysteme/Standards für Autorität (SAP, proALPHA, ERP,
   branchenübliche Normen)
5. Kurzer Vision-/Einordnungs-Absatz (2–3 Sätze)
6. Abschluss mit spezifischer Erfahrungsfrage (Claim/Show/Aim-konform)
7. 3–5 Hashtags

> **Umsetzungshinweis Fettschrift:** LinkedIn-Beiträge sind reiner Text ohne Markdown. Die
> Generierung markiert die Ergebnis-Zeile als `**Ergebnis: …**`; beim Push nach Buffer wird sie
> in Unicode-Fettbuchstaben übersetzt (`carousel_service._linkedin_bold`). Bewusst nur diese eine
> Zeile: Unicode-Fettschrift ist für Screenreader schlecht lesbar und in der LinkedIn-Suche nicht
> auffindbar. Umlaute und ß haben keine Fett-Entsprechung und bleiben normal.

## 5. Format & Frequenz

**3C-Rhythmus:**

- **Content:** ~2 Std./Woche gebündelt, 1–2 substanzielle Posts/Woche
- **Conversation:** 10–15 Min./Tag, 3–5 durchdachte Kommentare auf Branchen-Posts
- **Conversion:** Featured-Bereich aktuell halten, wöchentlich Saves/Profilaufrufe prüfen
  (nicht Likes), Gewinner-Themen in der Folgewoche doppeln

**Weiteres:**

- Format-Priorität: Dokument-Karussell (1080×1080 px) > Text mit Zahl > Video
- Kanal-Priorität: persönliches Profil (Sebastian) zuerst, Company Page als Zweitverwertung
- Repurposing: bestperformenden Post als 60-Sek-Video (face-to-camera) nachliefern
- Bild-Assets: mindestens 6 Bild-Prompts/Monat (Banner + Cover-Bild pro Wochenpost +
  wiederverwendbare Zitat-Vorlage) — siehe `bild-prompts.md`
- Posting-Slot: Dienstag und Donnerstag, 09:30 Uhr Berlin. Freitag ist laut
  `2026-08-04-Content-Recherche-Strategie.md` leicht unterdurchschnittlich.

## 6. Design-Spezifikation Karussells

**Referenz:** Karussells von Wolfgang Lang (GuidedBuying.com), Originalbilder unter
`Marketing/LinkedIn/Neuer Ordner/`.

**1:1 übernommen:**

- Schriftcharakter und Textrhythmus: große Headline, darunter luftiger Fließtext mit
  großzügiger Zeilenhöhe
- Fett hervorgehobene Kernbegriffe und Zahlen **mitten im Satz**, nicht als eigene Zeile
- Hintergrundoptik: ein Foto, das unter einem flächigen, halbtransparenten Wash nur noch als
  Textur durchscheint
- **Ein einziges Hintergrundfoto über alle Slides** — Lang nutzt durchgehend dasselbe Bild.
  Das hält die Serie ruhig und spart 6 von 7 Bildgenerierungen pro Karussell.
- Proportionen: Logo oben, Textblock ab ca. 28 % Höhe, alles linksbündig am selben Rand
- Slide-Aufbau: Hook → Problem → Zahlen → Vertiefung (3×) → CTA
- Schmale, rotierte Domain-Signatur unten links

**Geändert — nur die Farblogik:**

- Statt Langs Hellblau: **schwarzer ODER weißer Hintergrund**, pro Post-Serie konsistent
  (Parameter `variante`: `schwarz` | `weiss`, Default schwarz)
- Schrift jeweils in der Gegenfarbe
- Dezente Lila/Violett-Akzente (#534AB7–#B088FF, 2026-08-11 pixelgenau aus dem finalen
  Banner nachgemessen — identisch zu C_PURPLE/C_PURPLE_LIGHT in frontend/src/index.css):
  Regel-Strich über der Headline, Seitenzähler, Untertitel. Deutlich unter den
  erlaubten 10–15 % Bildfläche.
- Logo „Prozessia." oben links aus dem eigenen Logo-File, nicht neu generiert
- Hintergrund ohne generiertes Foto (Fallback): Lila-Schimmer rotiert über vier
  Positionen (Hash des Themas), damit nicht jedes Karussell ohne Foto identisch aussieht

> **Beobachtung zur Seitenzahl:** Das „X Seiten"-Label im Vorbild steht nicht im Bild — das
> blendet LinkedIn bei Dokument-Posts selbst ein. Der Renderer setzt trotzdem einen eigenen
> Zähler („3 / 7") oben rechts, damit die Seitenzahl auch im PDF und in der Zweitverwertung
> sichtbar bleibt.

## 7. Bild-/Markenidentität

- **Farbschema:** Schwarz (#0A0A0A) + Weiß (#FFFFFF) als Basis, Lila/Violett
  (#534AB7 dunkel, #B088FF hell) als sparsamer dritter Akzent — alle drei Werte
  2026-08-11 per Pixel-Sampling exakt aus dem finalen Banner übernommen, identisch zur
  Schriftfarbe auf prozessia.de (C_DARK/C_PURPLE/C_PURPLE_LIGHT, siehe frontend/src/index.css)
- **Typografie Headlines:** fette, rundliche Display-Grotesk mit „aufgeblasenem" Charakter,
  normale Groß-/Kleinschreibung statt Versalien, enger Buchstabenabstand.
  Umgesetzt mit **Poppins Bold** (2026-08-13 von Black auf Bold reduziert - Black wirkte
  im Karussell-Rendering gegen das finale Banner spürbar zu fett/aufgeblasen; Poppins war
  in der Marken-Vorgabe als zulässige Variante genannt, neben Baloo 2 ExtraBold und
  Fredoka Bold). Fließtext: Poppins Light, Hervorhebungen Poppins SemiBold.
  Font-Dateien: `Marketing/Branding/fonts/`.
- **Banner-Beispiel (final):** „Fortschritt durch sichere KI." (weiß) /
  „Wissenssicherung und Prozesseffizienz für den Mittelstand" (Unterzeile, kleiner, leichter)
- **Bild-Generierung:** Nano Banana Pro, Logo und Font-Referenz-Screenshots als Bild-Input
  mitgeben statt nur textuell beschreiben — reduziert Zufallsstreuung erheblich
- **Headline/Subline-Regel:** produktübergreifend formulieren, nicht auf ein einzelnes Produkt
  verengen — Prozessia hat vier Produktlinien

## 8. Sprache & Ton

**Geändert 2026-08-20 (Sebastian: Posts klangen zu sehr nach Verkauf/KI-Hype, zu abgehackt,
Überschriften nicht seriös genug):**

- Deutsch, sachlich-professionell, informativ — wie ein fundierter Fachbeitrag, keine
  Verkaufsanzeige. Der Leser soll etwas über sein Fachgebiet mitnehmen, nicht zum Klicken
  verleitet werden.
- Klare, vollständige Sätze in normaler Länge — keine künstliche Wortbegrenzung pro Satz und
  keine erzwungene Fragment-Sprache. Abgehackte "jede Zeile ein Gedanke"-Häppchen vermeiden.
- Überschriften/Hooks sind vollständige, seriöse Sätze oder präzise Fragen — wie bei einem
  Fachartikel, nicht wie ein reißerischer Clickbait-Fragment-Titel.
- KI wird als Werkzeug im Hintergrund erwähnt, wenn es zur Sache gehört — nicht als zentrales
  Verkaufsversprechen. Im Mittelpunkt steht das fachliche Problem der Zielgruppe (Beschaffung,
  Wissensmanagement, Compliance), nicht die Technologie selbst.
- Keine Buzzword-Sprache, keine Superlative ohne Beleg, keine reißerische/marktschreierische
  Zuspitzung
- Keine performte Bescheidenheit („ich war unsicher, ob ich das teilen soll")
- Keine Hedging-Formulierungen
- Aussagen sind klar und gut begründet — bestimmt, aber nicht plakativ oder werblich

## 9. Einmalige Profil-Grundlagen (vor Kampagnenstart)

Nicht automatisierbar, muss Sebastian selbst im LinkedIn-Profil machen:

- [ ] Headline klar formulieren (Muster: „Ich helfe X, Y zu tun")
- [ ] About-Bereich für den Leser geschrieben, nicht als Lebenslauf
- [ ] Featured-Bereich mit stärkstem bisherigem Post pinnen
- [x] Banner-Tippfehler korrigiert (finales Banner ist bereits korrigiert)

## 10. Kennzahlen

| Kennzahl | Priorität | Hinweis |
|---|---|---|
| Saves/Post | primär | wichtiger als Likes |
| Profilaufrufe/Woche | primär | wöchentlich prüfen |
| Engagement-Rate | sekundär | Zielkorridor ca. 5–7 % |
| Kommentare/Post | sekundär | Qualität/Tiefe vor Menge |
| Impressions/Post | sekundär | Trend über Zeit wichtiger als Einzelwert |
| DMs/Anfragen aus LinkedIn | primär (Geschäftsziel) | eigentlicher Erfolgsmaßstab |

Reaktion auf Daten: Gewinner-Themen der Vorwoche in der Folgewoche verstärken/doppeln, nicht
automatisch neue Themen forcieren.

> **Datenlücke:** Die Buffer-API liefert nur Impressions, Reach, Engagement-Rate, Reactions,
> Kommentare und Shares (`linkedin_service.get_buffer_insights`). **Saves, Profilaufrufe und DMs
> gibt es dort nicht** — also ausgerechnet drei der vier Primär-Kennzahlen. Die kommen manuell
> aus LinkedIn-Analytics in `kpi-tracking.md`.

## 11. Wiederkehrender Recherche-Input

Vier Blöcke, die den Content-Ideen laufend zugrunde liegen (fließen als `focus` in die
Ideen-Generierung ein):

1. **Trend-Check Zielbranche** — Studien/Zahlen, max. 4–8 Wochen alt
2. **Konkurrenz-/Vorbild-Scan** — Muster bei vergleichbaren B2B-/Industrie-KI-Anbietern
3. **Format-/Algorithmus-Check** — 1×/Monat ausreichend
4. **Event-/Anlass-Check** — Termine/Fristen der nächsten 2–3 Wochen

---

## Aufgelöste Widersprüche zur bisherigen Konfiguration

Beim Umbau am 2026-08-11 sind drei Stellen aufgefallen, an denen die alte Konfiguration dieser
Strategie widersprach. Aufgelöst wurde jeweils zugunsten dieser Datei:

1. **Hashtags.** `CLAUDE.md` verbot bisher #KI und #Mittelstand ausdrücklich als „zu groß, zu
   allgemein" und erlaubte maximal 3 Hashtags. Diese Strategie verlangt 3–5 Hashtags als
   Mischung aus breit und spezifisch und nennt #KI und #Mittelstand als Beispiele für den
   breiten Teil. Neue Regel gilt. Der Grund für das alte Verbot — Reichweitenerwartung an
   Hashtags — entfällt ohnehin, weil Hashtags hier explizit nur Suche und Filter dienen.
2. **Zielgruppe der Content-Engine.** Der System-Prompt der Content-Engine beschrieb bis dahin
   Automotive/Pharma/Bau/Maschinenbau, 50–500 Mitarbeitende, und ein Produkt „Voice Agents",
   das nicht mehr zum Portfolio gehört. Komplett auf die Zielgruppe und die vier Produkte
   oben umgestellt.
3. **Themen-Säulen.** Es existierten drei verschiedene Säulen-Systeme parallel
   (Schmerz/Wissen/Beweis/Meinung in der Content-Engine, sechs Kategorien im Backend, vier
   Säulen in dieser Strategie). Vereinheitlicht auf die vier Säulen aus Abschnitt 2. Die
   Post-Typen A/B/C (Schmerz/Karussell/Story) bleiben davon unberührt — das ist eine
   Format-Achse, keine Themen-Achse.
4. **Ton (2026-08-20).** Die bisherige Regel "Hook = Fragment, kein vollständiger Satz" plus
   "max. 15 Wörter pro Satz" erzeugte in der Praxis abgehackte, reißerisch wirkende Posts, die
   zu sehr nach Verkauf und KI-Hype klangen statt nach Fachbeitrag (Sebastian, 20.08.2026).
   Ersetzt durch: vollständige, seriöse Sätze/Überschriften, keine künstliche
   Wortbegrenzung, KI als Werkzeug im Hintergrund statt als zentrales Verkaufsargument. Die
   Grundstruktur (Einleitung, Zahlen, Ergebnis-Zeile, Einordnung, Abschlussfrage, Hashtags)
   bleibt unverändert — nur die sprachliche Ausführung wurde professioneller/informativer.
