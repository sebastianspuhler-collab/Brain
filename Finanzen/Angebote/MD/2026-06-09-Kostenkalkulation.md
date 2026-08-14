---
tags:
  - Kostenkalkulation
  - Azure OpenAI
  - GPT-5.1 mini
  - Embeddings
  - OCR
quelle: Kostenkalkulation.docx
datum: 2026-06-09
kategorie: Finanzen
---

# Kostenkalkulation

Das Dokument enthält eine detaillierte Kostenkalkulation für einen 4-wöchigen KI-Testzeitraum mit einem Mitarbeiter. Es umfasst Berechnungen zu GPT-5.1 mini (Chat-Nutzung via Azure), Embedding-Kosten sowie OCR-Kosten über Mistral OCR. Die Gesamtkosten pro Mitarbeiter für 4 Wochen werden auf Basis konservativer Token- und Nutzungsannahmen ermittelt.

## Vollständiger Inhalt
Kostenkalkulation  2.1 Annahmen zur Nutzung (4 Wochen Test, 20 Arbeitstage) Chat-Nutzung (GPT-5.1 mini): 60 ausführliche Fragen pro Tag 20 Arbeitstage
→ 1.200 Fragen insgesamt Pro Frage (konservativ nach oben): Ø 1.800 Input-Tokens (Prompt + Kontext aus RAG) Ø 900 Output-Tokens Token-Gesamtmengen: Input gesamt:
1.200 Fragen × 1.800 Tokens = 2.160.000 Input-Tokens Output gesamt:
1.200 × 900 = 1.080.000 Output-Tokens Prompt-Caching (Kontext & Systemprompt wiederholen sich): 70 % der Input-Tokens als „normale“ Input-Tokens 30 % als Cached Input Also: Uncached Input: 70 % von 2.160.000 = 1.512.000 Tokens Cached Input: 30 % von 2.160.000 = 648.000 Tokens  Dokumentenbasis / Embeddings: Für den Testzeitraum nehmen wir relativ viele Dokumente, damit wir kostenmäßig eher oben landen: 500 Dokumente initial (Richtlinien, Vorlagen, Wissensartikel) Ø 1.500 Tokens pro Dokument
→ 500 × 1.500 = 750.000 Tokens 50 Updates / neue Dokumente im Zeitraum Ø 1.000 Tokens
→ 50 × 1.000 = 50.000 Tokens Embedding-Tokens gesamt:
750.000 + 50.000 = 800.000 Tokens Umrechnung in 1.000er-Blöcke:
800.000 / 1.000 = 800 Einheiten à 1.000 Tokens.  OCR-Nutzung (Mistral OCR): 800 Seiten gescannte PDFs (z.B. gescannte Akten, alte Verträge, etc.) in 4 Wochen Preis: $1 / 1.000 Seiten → 800 Seiten = 0,8 × $1 = $0,80  2.2 Kostenberechnung im Detail 2.2.1 GPT-5.1 mini (Azure – Sweden Data Zone) a) Uncached Input Tokens: 1.512.000 Preis: $0,28 / 1.000.000 Tokens Kosten:
1.512.000 / 1.000.000 = 1,512 Mio
→ 1,512 × $0,28 = $0,42336 ≈ $0,42  b) Cached Input Tokens: 648.000 Preis: $0,03 / 1.000.000 Tokens Kosten:
0,648 Mio × $0,03 = $0,01944 ≈ $0,02  c) Output Tokens: 1.080.000 Preis: $2,20 / 1.000.000 Tokens Kosten:
1,08 Mio × $2,20 = $2,376 ≈ $2,38  d) Summe GPT-5.1 mini (4 Wochen, 1 Mitarbeiter) Uncached Input: ~ $0,42 Cached Input: ~ $0,02 Output: ~ $2,38 👉 Summe GPT-5.1 mini: $2,82 (gerundet)  2.2.2 Embeddings (Azure OpenAI – text-embedding-3-small) Tokens: 800.000 Abrechnungseinheit: 1.000 Tokens
→ 800.000 / 1.000 = 800 Einheiten Preis (konservativ): $0,000025 / 1.000 Tokens Kosten:
800 × $0,000025 = $0,02 👉 Embedding-Kosten gesamt (4 Wochen): ~ $0,02  2.2.3 Mistral OCR Seiten: 800 Preis: $1,00 / 1.000 Seiten Kosten:
800 / 1.000 × $1 = $0,80 👉 OCR-Kosten gesamt (4 Wochen): $0,80  2.3 Gesamtkosten pro Mitarbeiter (4 Wochen) Jetzt alles zusammen: 
