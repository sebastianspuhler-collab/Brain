---
tags: [Zillmer, Prozessskizze, Kalkulation, Ausschreibung, KI-Agent]
datum: 2026-07-28
kategorie: Lead
quelle: Transkript "Update Zillmer X Prozessia" vom 21.07.2026
---

# Prozessskizze: KI-gestützter Kalkulationsprozess für Ausschreibungen
### Zillmer Elektrotechnik – Vorbereitung Termin 28.07.2026, 11:00 Uhr

Diese Skizze basiert 1:1 auf dem, was Dierk Biendarra und Sebastian Spuhler im Meeting am 21.07.2026 besprochen haben.

---

## Ablauf

**1. Ausschreibung geht ein**
→ Ausschreibungstext (z. B. für technische Leuchten) liegt vor

**2. Prüfung: Ist der Hersteller/Typ eindeutig angegeben?**

- **JA, Hersteller steht fest**
  → weiter direkt zu Schritt 4 (Preisanfrage)

- **NEIN, Hersteller/Typ nicht eindeutig**
  → Schritt 3: KI-Recherche

**3. KI-Recherche (nur bei fehlender Angabe)**
- KI liest den Ausschreibungstext und leitet daraus ab, welcher Hersteller/Typ gemeint sein könnte
- Suchraum bewusst eingegrenzt: ca. 50 relevante Hersteller für technische Leuchten in Deutschland
- Ziel der Eingrenzung: Fehleranfälligkeit/Halluzination der KI praktisch auf 0 reduzieren (O-Ton Sebastian: "je spezifischer, desto sicherer das Ergebnis")
→ Ergebnis: identifizierter Hersteller + Typ

**4. Automatisierter Preisvergleich**
- KI sendet automatisiert Anfragen an Großhandel und/oder Hersteller
- Eingehende Preise werden verglichen
→ Ergebnis: günstigster Anbieter/Preis steht fest

**5. Einspeisung in die Kalkulation**
- Der ermittelte Preis fließt direkt in die Angebotskalkulation ein

**6. Bei Auftragserteilung: Weitergabe**
- Ergebnis (Hersteller, Typ, Preis) wird automatisch an weitere am Projekt Beteiligte weitergegeben

---

## Visuelle Kurzfassung (für Folie/PDF)

```
 Ausschreibung
      │
      ▼
 Hersteller/Typ genannt? 
      │
   ┌──┴───┐
  JA      NEIN
   │        │
   │        ▼
   │   KI-Recherche
   │   (eingegrenzt auf
   │    ~50 Hersteller D)
   │        │
   └───┬────┘
       ▼
 Automatischer Preisvergleich
 (Anfragen an Großhandel/Hersteller)
       │
       ▼
 Günstigstes Angebot ermittelt
       │
       ▼
 Einspeisung in Kalkulation
       │
       ▼
 Auftrag erteilt? → Weitergabe an Beauftragte
```

---

## Offene Punkte für den Termin
- Beispiel-Ausschreibung als PDF von Dierk Biendarra ist bislang **nicht** eingegangen (nur mündlich angekündigt am 21.07.) – vor Ort nachfragen bzw. gemeinsam eine Beispielausschreibung durchgehen
- Kostenstruktur laut letztem Gespräch: Projektpreis + Sprachmodellkosten im niedrigen dreistelligen Bereich/Monat, DSGVO-konform über Microsoft-Server Frankfurt – ggf. heute konkretisieren, da laut Biendarra intern noch keine Priorität von seinem Chef gesetzt wurde
