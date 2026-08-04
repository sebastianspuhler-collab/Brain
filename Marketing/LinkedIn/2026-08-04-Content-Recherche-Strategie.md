---
tags: [linkedin, content-strategie, recherche, wachstum, claude-auto-poster]
datum: 2026-08-04
kategorie: Marketing
---

# LinkedIn Wachstums- & Recherche-Strategie für Claude (Auto-Poster)

Ziel: maximale Reichweite/Wachstum bei minimalem Zeitaufwand für Sebastian. Claude
übernimmt Recherche + Texterstellung, Sebastian nur noch Freigabe + 5 Min. Engagement
nach Veröffentlichung.

## 1. Wöchentliche Recherche-Routine (bevor neue Ideen generiert werden)

Jeden Montag, bevor `generate_linkedin_ideas` läuft, folgende Recherche durchführen
(via WebSearch) und Ergebnisse als `focus`-Parameter einspeisen:

1. **Trend-Check Zielbranche**: Suche nach aktuellen News/Statistiken zu KI im
   Mittelstand, Einkauf/Beschaffung, Werkzeugbau/Lohnfertigung/Elektrotechnik
   (Prozessia-Zielgruppe). Konkrete Zahlen > generische Aussagen.
2. **Konkurrenz-/Vorbild-Scan**: Was posten andere B2B-/Industrie-KI-Anbieter aktuell
   erfolgreich (Formate, Hooks, Themen)? Nicht kopieren, aber Muster erkennen.
3. **Format-Trend-Check**: 1x im Monat prüfen, ob sich Algorithmus-Empfehlungen
   geändert haben (Suche: "LinkedIn Algorithmus B2B [aktueller Monat/Jahr]").
4. **Event-/Anlass-Check**: Gibt es diese Woche relevante Termine (Webinare,
   Messen, EDIH-Veranstaltungen, Gesetzesänderungen wie EU AI Act-Fristen), an die
   ein Post andocken kann?

Diese vier Punkte fließen als Stichpunkte in den `focus`-Parameter von
`generate_linkedin_ideas` ein, statt dass Sebastian sich das selbst ausdenken muss.

## 2. Was laut aktueller Recherche (Stand 08/2026) wirklich Reichweite bringt

Quellen: Skill-Sprinters, Oktopost, Morphica, Growleads, Socialinsider (LinkedIn
Benchmarks 2026).

- **Karussells sind das stärkste Format**: bis zu 45,85 % Engagement-Rate,
  Dokument-Carousels ca. 600 % mehr Engagement als reine Text-Posts. Grund: Swipen
  erzeugt Dwell Time, die der Algorithmus 2026 am stärksten belohnt.
- **Kommentare zählen 3-5x mehr als Likes.** Ein Post mit 10 echten Kommentaren
  schlägt einen mit 100 Likes. CTA am Ende muss eine echte, leicht beantwortbare
  Frage sein (haben wir bereits, aber konsequenter nutzen).
- **Native Videos unter 90 Sekunden** performen stark (+36 % Videoaufrufe laut
  Adobe), aber nur mit eingebrannten Untertiteln (80 % schauen ohne Ton).
- **Externe Links kosten ca. 60 % Reichweite.** Nie einen Link direkt im Post -
  falls nötig, in den ersten Kommentar.
- **Beste Posting-Zeiten**: Di-Do, morgens oder früher Abend. Unser aktueller
  Rhythmus (Di + Fr 09:30) ist gut, aber Freitag ist laut Daten leicht
  unterdurchschnittlich - Alternative wäre Di + Do.
- **Optimaler Content-Mix**: ca. 50 % Karussell/Video, 30 % Text, 20 %
  Dokument/Bild. Aktuell posten wir fast nur Typ A (Text) und B (Karussell) -
  das passt schon grob, Video fehlt komplett.

## 3. Konkrete Format-Regeln für Claude beim Texten

- Hook muss in den ersten 2 Sekunden/der ersten Zeile eine konkrete Zahl oder ein
  konkretes Problem nennen (kein "Wusstest du, dass...").
  Beispiel: "Freitag, 19 Uhr. Immer noch beim dritten Stücklisten-Abgleich."
- Karussell: Problem → Warum passiert das → konkrete Lösung/Schritt-für-Schritt,
  1080x1350px, max. 8-10 Slides.
- Kein Link im Haupttext, keine Hashtag-Flut (max. 3-5, spezifisch statt generisch).
- CTA = echte Frage, keine "Kontaktiert uns"-Floskel.

## 4. Wie das in die bestehende Pipeline einspeist

- `generate_linkedin_ideas(focus=...)` bekommt wöchentlich die Recherche-Ergebnisse
  aus Punkt 1 als Fokus mitgegeben, statt generisch zu laufen.
- Ideen mit Format "Karussell" bevorzugt über `generate_carousel` produzieren
  (volle Pipeline: Slides → KI-Bilder → PDF → Buffer), da dieses Format laut
  Daten am stärksten zieht.
- Video-Format ist aktuell die einzige Lücke im Mix - dafür bräuchten wir eine
  eigene Produktionsroute (z. B. kurze Screen-/Talking-Head-Clips zu Kundenzahlen).
  Das läuft aktuell nur über die YouTube-Pipeline (NotebookLM), nicht für
  LinkedIn-Feed-Videos - wäre der nächste Ausbauschritt, wenn wir wirklich auf den
  vollen Formatmix wollen.

## 5. Zeitaufwand für Sebastian

- Recherche, Ideen, Texte, Karussells: 100 % Claude, kein Zeitaufwand für Sebastian.
- Einziger Pflicht-Aufwand: nach Veröffentlichung 5-10 Minuten in den ersten
  60 Minuten selbst kommentieren/auf Kommentare antworten - das ist laut Daten der
  größte Hebel, den kein Tool automatisieren kann (Trust-Signal an den Algorithmus).

## Quellen
- https://skill-sprinters.de/blog/social-media/linkedin-algorithmus-2026/
- https://www.oktopost.com/blog/linkedin-carousel-pdf-best-practices/
- https://www.morphica.studio/blog/linkedin-carousel-best-practices-2026
- https://growleads.io/blog/linkedin-algorithm-2026-text-vs-video-reach/
- https://www.socialinsider.io/social-media-benchmarks/linkedin
