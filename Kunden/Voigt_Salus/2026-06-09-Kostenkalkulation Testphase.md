---
tags:
  - Kostenkalkulation
  - Testphase
  - Voigt Salus
  - GPT-4.1 mini
  - OCR
quelle: Kostenkalkulation Testphase.pdf
datum: 2026-06-09
kategorie: Finanzen
---

# Kostenkalkulation Testphase

Kostenkalkulation für eine Testphase (Pilotprojekt) bei Voigt Salus über einen Monat mit einem Mitarbeiter. Berechnet werden die monatlichen KI-Nutzungskosten für GPT-4.1 mini (Chat), Embeddings und Mistral OCR auf Basis konkreter Token- und Seitenmengen. Gesamtkosten belaufen sich konservativ auf ca. 4,20 USD pro Mitarbeiter und Monat.

## Vollständiger Inhalt
Kostenkalkulation Testphase  1. Rahmen & Annahmen (pro Monat, pro Mitarbeiter) Zeitraum: ca. 4 Wochen / 20 Arbeitstage Nutzung: 1 Mitarbeiter im Pilot 1.1 Chat-Nutzung (GPT-4.1 mini, Azure) • 60 Anfragen pro Tag • 20 Arbeitstage → 1.200 Anfragen pro Monat Pro Anfrage rechnen wir großzügig mit: • 1.800 Tokens Eingabe (Input) • 900 Tokens Ausgabe (Output) Damit ergeben sich: • Gesamter Input: 1.200 × 1.800 = 2.160.000 Tokens • Gesamter Output: 1.200 × 900 = 1.080.000 Tokens 1.2 Aufteilung: Uncached vs. Cached Input Wir unterstellen: • 70 % Uncached Input → 1.512.000 Tokens • 30 % Cached Input → 648.000 Tokens Kurz erklärt für den Kunden: • Uncached Input = „neuer“ Inhalt, den das Modell so noch nicht gesehen hat (neue Fragen, neue Kontextpassagen). → wird zum normalen Input-Preis abgerechnet. • Cached Input = wiederkehrende Teile, z. B. fixer Kanzlei-Systemprompt, Standard-Anweisungen, sich wiederholende Kontexte. → Azure/OpenAI erkennt diese Wiederverwendung und berechnet sie stark rabattiert. Die Annahme „30 % cached“ ist realistisch und eher vorsichtig, d. h. lieber etwas zu viel Kosten einkalkuliert als zu wenig.   1.3 Embeddings (Dokumenten-Vektorisierung) Für die interne Wissensbasis (RAG) rechnen wir: • ca. 800.000 Tokens pro Monat, z. B.: o 500 Dokumente à 1.500 Tokens = 750.000 Tokens o 50 neue/aktualisierte Dokumente à 1.000 Tokens = 50.000 Tokens → Summe Embedding-Tokens: 800.000  1.4 OCR (Mistral OCR) Mistral OCR wird nur dort eingesetzt, wo es nötig ist, z. B.: • gescannte PDFs • bildlastige Anleitungen mit wichtigen Abbildungen Annahme: • 1.000 Seiten pro Monat, die tatsächlich über OCR laufen.  2. Preise (Basis USD) GPT-4.1 mini (Azure, Region Schweden): • Uncached Input: 0,44 $ / 1.000.000 Tokens • Cached Input: 0,11 $ / 1.000.000 Tokens • Output: 1,76 $ / 1.000.000 Tokens Embeddings („ada“): • 0,000121 $ / 1.000 Tokens → 0,121 $ / 1.000.000 Tokens Mistral OCR: • 1,00 $ / 1.000 Seiten Alle Beträge in USD, Wechselkurs- und Mehrwertsteuer-Effekte kommen ggf. noch hinzu.  3. Kostenrechnung (konservativ nach oben gerundet) 3.1 GPT-4.1 mini (Chat)  Uncached Input • 1.512.000 Tokens • 1,512 Mio × 0,44 $ ≈ 0,67 $ → Planwert: 0,70 $ Cached Input • 648.000 Tokens • 0,648 Mio × 0,11 $ ≈ 0,07 $ → Planwert: 0,10 $ Output • 1.080.000 Tokens • 1,08 Mio × 1,76 $ ≈ 1,90 $ → Planwert: 2,10 $ Geplante Chat-Kosten GPT-4.1 mini (1 Monat, 1 Mitarbeiter): ≈ 2,90 $  3.2 Embeddings (Dokumentenbasis) • 800.000 Tokens • 800 × 0,000121 $ = 0,0968 $ → Planwert: 0,12 $ Geplante Embedding-Kosten (1 Monat, 1 Mitarbeiter): ≈ 0,12 $  3.3 Mistral OCR • 1.000 Seiten • 1.000 / 1.000 × 1,00 $ = 1,00 $ (exakt) Wir setzen einen kleinen Puffer an: → Planwert: 1,20 $ Geplante OCR-Kosten (1 Monat, 1 Mitarbeiter): ≈ 1,20 $  4. Gesamtkosten (Pilot pro Mitarbeiter und Monat)  Pro Mitarbeiter, pro Monat (4 Wochen): • GPT-4.1 mini (Chat): ≈ 2,90 $ • Embeddings (Dokumenten-Vektorisierung): ≈ 0,12 $ • Mistral OCR (1.000 Seiten): ≈ 1,20 $   Gesamt (konservativ, inkl. Puffer) ≈ 4,20
