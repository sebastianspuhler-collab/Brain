---
tags:
  - Hosting
  - Wartungskonzept
  - SLA
  - Infrastruktur
  - Schaufler
quelle: Prozessia_Intern_Schaufler_Hosting.pdf
datum: 2026-06-09
kategorie: Kunde
---

# Prozessia_Intern_Schaufler_Hosting

Internes, vertrauliches Hosting- und Wartungskonzept für den Kunden Schaufler (April 2026). Es beschreibt die Infrastruktur (Hetzner CCX23, Azure OpenAI), das Preismodell mit interner Kalkulation (Pauschale 460 €/Monat, Gesamtkosten ca. 548 €/Monat), SLA-Bedingungen sowie Vertragskonditionen. Das Dokument enthält sensible interne Kosten- und Gewinnmargeninformationen und ist ausschließlich für Prozessia bestimmt.

## Vollständiger Inhalt
INTERNES DOKUMENT – VERTRAULICH
Hosting- & Wartungskonzept
Kunde: Schaufler · Prozessia · April 2026
Internes Dokument – vollständig und transparent. Enthält Kostenstruktur, Infrastruktur, SLA und
Vertragskonditionen.
 1. Was wir liefern
Prozessia richtet einen dedizierten Cloud-Server bei Hetzner ein und betreibt darauf alle KI-Anwendungen
von Schaufler dauerhaft. Schaufler bezahlt Server und Azure direkt – wir verwalten alles, Schaufler hat
keinen Zugriff. Neue Anwendungen werden separat angeboten.
2. Infrastruktur
Server – Hetzner CCX23
– 4 dedizierte vCPU (AMD), 16 GB RAM, 160 GB NVMe SSD
– Deutsches Rechenzentrum – DSGVO-konform
– Läuft dauerhaft – kein Stopp außer geplantem Wartungsfenster
– Kosten: 38,07 €/Monat – Schaufler zahlt direkt an Hetzner
KI-Sprachmodell – Azure OpenAI
– Microsoft Azure, EU-Region – DSGVO-konform
– Kosten variabel nach Verbrauch, aktuell ca. 50 €/Monat
– Steigt mit jeder neuen KI-Anwendung
– Schaufler zahlt direkt – nur Prozessia hat Zugriff
3. Preismodell
Posten
Betrag
Wer zahlt
Wartungs- & Verwaltungspauschale
460 €/Monat fix
Schaufler an Prozessia
Hetzner Server CCX23
38,07 €/Monat
Schaufler direkt
Azure OpenAI
~50 €/Monat variabel
Schaufler direkt
Gesamt monatlich (ca.)
~548 €
Interne Kalkulation der Pauschale
– 4h Aufwand/Monat × 90 €/h = 360 € Kosten
– Gewinn aus Pauschale: ca. 100 €/Monat
– Neuentwicklungen immer separat – nie in Pauschale enthalten
Neue KI-Anwendungen werden immer separat angeboten – nie in der Pauschale enthalten.
4. SLA – Was wir garantieren
Verfügbarkeit & Reaktion
– 99% Uptime pro Monat (max. ~7h Ausfallzeit erlaubt)
– Reaktionszeit bei Ausfall: max. 8h werktags
– Lösungszeit: max. 24h
– Wartungsfenster: 1× monatlich, Sonntag 02–04 Uhr
In der Pauschale enthalten
– 2 Support-Anfragen/Monat
 – Updates & Sicherheitspatches
– Monatlicher Statusbericht
– Zusätzlicher Support: 90 €/Stunde
Wir haften nicht für Ausfälle von Hetzner oder Azure – muss im Vertrag klar ausgeschlossen werden.
5. Vertragskonditionen
– Mindestlaufzeit: 12 Monate
– Kündigung danach: monatlich, 4 Wochen Frist
– Infrastrukturkosten: monatlich variabel, separat ausgewiesen
– Jährliche Preisanpassung: max. 5% p.a.
– Zahlungsziel: 14 Tage nach Rechnungseingang
6. Skalierung – Hetzner Server-Optionen
Jederzeit hochstufbar ohne Datenverlust (Migration ca. 1–2h). Alle Kosten 1:1 an Schaufler.
Modell
vCPU
RAM
SSD
Preis/Monat
Wann sinnvoll
CCX13
2 AMD
8 GB
80 GB
19,62 €
Einzelne leichte Anwendung
CCX23 ✓ aktuell
4 AMD
16 GB
160 GB
38,07 €
1–3 KI-Anwendungen
CCX33
8 AMD
32 GB
240 GB
74,96 €
4–6 Anwendungen / hohe Last
CCX43
16 AMD
64 GB
360 GB
149,33 €
Enterprise / viele Prozesse
CCX53
32 AMD
128 GB
600 GB
298,08 €
Sehr große Workloads
CCX63
48 AMD
192 GB
960 GB
446,24 €
Maximum / Full-Scale
Prozessia · Intern · Vertraulich · April 2026

