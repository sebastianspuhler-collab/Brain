---
tags: [linkedin, bild-prompts, branding, nano-banana]
datum: 2026-08-11
kategorie: Marketing
---

# Bild-Prompt-Vorlagen (Nano Banana Pro)

Soll laut STRATEGIE.md §5 mindestens **6 Bild-Prompts pro Monat** abdecken:
1× Banner + 1 Cover-Bild je Wochenpost + 1 wiederverwendbare Zitat-Vorlage.

## Immer als Bild-Input mitgeben

Textuelle Beschreibung allein streut zu stark. Diese Dateien als Referenzbilder anhängen:

| Zweck | Datei |
|---|---|
| Logo hell (für dunkle Motive) | `Marketing/Branding/Logo-removebg-preview.png` |
| Logo dunkel (für helle Motive) | `Marketing/Branding/Logo_converted.png` |
| Schrift-Referenz | Screenshot eines fertigen Karussell-Slides aus `carousel/` |
| Farb-/Stil-Referenz | finales Banner |

## Feste Marken-Klausel (an jeden Prompt anhängen)

> Color scheme: pure black and white as the base, with a single restrained purple accent
> (#6B3FA0 to #8B5CF6) covering no more than 10–15% of the image. Headline typography: bold,
> rounded display grotesque with an inflated character, sentence case (never all caps), tight
> letter spacing. German text only, spelled exactly as given. Use the attached logo file as-is,
> do not redraw or reinterpret it. No stock-photo gloss, no generic AI-tech clichés
> (no glowing brains, no circuit boards, no robot hands).

## 1 — Profil-Banner (1584 × 396)

```
LinkedIn profile banner, 1584x396. Black background. Left two thirds: headline
"Fortschritt durch sichere KI." in white, bold rounded display grotesque, sentence case.
Directly beneath, smaller and in a lighter weight: "Wissenssicherung und Prozesseffizienz
für den Mittelstand". Right third: an abstract geometric composition of thin purple lines
suggesting a structured parts list. Prozessia logo top right, from the attached file.
[Marken-Klausel anhängen]
```

Headline und Unterzeile bleiben **produktübergreifend** — nicht auf Einkauf verengen,
Prozessia hat vier Produktlinien.

## 2 — Cover-Bild Wochenpost (1080 × 1080)

```
Square 1080x1080 cover image. Documentary photograph of a German mid-sized precision
manufacturing workshop — CNC machining, tool and die making, sheet metal fabrication —
shot with shallow depth of field, softly out of focus, monochrome and near-black.
Over it a flat black wash at roughly 80% opacity so the photo reads only as texture.
Headline in white, bold rounded display grotesque, sentence case, left aligned in the
upper third: "<HEADLINE>". A short purple horizontal rule above the headline.
Prozessia logo top left, from the attached file. No other text.
[Marken-Klausel anhängen]
```

Für die weiße Serie: `black wash` → `white wash at roughly 88% opacity`, Schrift in Schwarz.

## 3 — Zitat-Vorlage (wiederverwendbar, 1080 × 1080)

```
Square 1080x1080 quote card. Pure white background, no photograph. Large quotation mark
set in purple (#8B5CF6) in the upper left, oversized and partially cropped by the edge.
Quote text in black, bold rounded display grotesque, sentence case, left aligned, centred
vertically: "<ZITAT>". Beneath it, small and in a lighter weight: "Sebastian Spuhler,
Prozessia". Prozessia logo top right, from the attached file. Generous white space.
[Marken-Klausel anhängen]
```

## 4 — Zahlen-Slide / Statistik-Grafik (1080 × 1080)

```
Square 1080x1080. Black background. One very large number set in white, bold rounded
display grotesque, occupying the upper half: "<ZAHL>". Directly beneath, one line of
context in a lighter weight: "<KONTEXTZEILE>". A thin purple rule separates the two.
No chart, no icons, no photograph. Prozessia logo top left, from the attached file.
[Marken-Klausel anhängen]
```

## 5 — Vergleichs-/Prozessbild (1080 × 1080)

```
Square 1080x1080. Black background. Two labelled columns separated by a thin vertical
purple line: left "Heute", right "Mit KI-Agent". Each column holds three short German
phrases in white, sentence case, generous line spacing. No icons, no arrows, no clip art.
Prozessia logo top left, from the attached file.
[Marken-Klausel anhängen]
```

## 6 — Event-/Anlass-Bild (1080 × 1080)

```
Square 1080x1080. White background, black text. Headline in bold rounded display
grotesque, sentence case: "<ANLASS>". Beneath it date and place in a lighter weight.
A single purple geometric shape — a rectangle or a thick rule — anchors the lower left
corner. Prozessia logo top right, from the attached file. Nothing else.
[Marken-Klausel anhängen]
```

## Qualitätsprüfung vor Verwendung

- [ ] Deutscher Text fehlerfrei? (Bildmodelle verdrehen deutsche Wörter regelmäßig —
      der Banner-Tippfehler in der Vergangenheit kam genau daher.)
- [ ] Lila unter 15 % Bildfläche?
- [ ] Logo unverändert übernommen, nicht nachgezeichnet?
- [ ] Versalien vermieden (normale Groß-/Kleinschreibung)?
- [ ] Keine KI-Klischees (Gehirne, Platinen, Roboterhände)?
