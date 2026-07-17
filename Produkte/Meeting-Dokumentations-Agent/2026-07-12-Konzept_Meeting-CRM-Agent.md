---
tags:
  - Produktkonzept
  - Meeting-Dokumentation
  - CRM
  - KI-Agent
quelle: Second Brain (Analyse eines YouTube-Videos zu übersehenen KI-Use-Cases)
datum: 2026-07-12
kategorie: Produkt
status: Konzept, noch nicht verkauft
---

# Konzept: Meeting-zu-CRM-Agent

## Ausgangspunkt

Video-Recherche (y0u4-ol8T1I) zeigt: der wirtschaftlich wertvollste, aber am
meisten übersehene KI-Use-Case ist nicht spektakulär — sondern die stille
Umwandlung unstrukturierter Gespräche in strukturierte Daten. Nach jedem
Kundengespräch schreibt ein Agent automatisch Zusammenfassung, Kerndaten und
nächste Schritte ins CRM. Ersparnis: 3–5 Minuten Nacharbeit pro Gespräch —
bei 500 Gesprächen/Monat rund 25–40 Stunden. Firmen zahlen dafür laut Quelle
vier- bis fünfstellige Beträge, weil kaum eine Agentur diesen "langweiligen"
Teil anbietet (Fokus liegt meist auf sichtbareren Use Cases).

**Warum das für Prozessia naheliegend ist:** Genau dieser Mechanismus läuft
bei uns intern bereits produktiv — jeder Kunden-Meeting-Transkript landet im
Vault unter `Kunden/<Firma>/Meetings/`, wird automatisch klassifiziert und
zusammengefasst (`_agent/heartbeat.py` / `classify.py`). Bisher nur als
internes Werkzeug genutzt, nicht als eigenständiges, verkauftes Produkt.

## Produktidee

Ein Agent, der nach jedem Kunden-/Vertriebsgespräch (Zoom/Teams/Telefon)
automatisch:
1. Das Gespräch transkribiert (oder eine bestehende Aufzeichnung einliest)
2. Eine strukturierte Zusammenfassung erstellt (Kernpunkte, Zusagen, offene
   Punkte, nächste Schritte)
3. Die Daten direkt ins CRM des Kunden schreibt (HubSpot, Pipedrive, o.ä. —
   je nach vorhandenem System)
4. Optional: eine Aufgabenliste für den nächsten Schritt generiert

## Zielgruppe

Vertriebsteams und Geschäftsführer in kleinen/mittleren Betrieben (20–80 MA),
die viele wiederkehrende Kundengespräche führen, aber kein Personal für
manuelle CRM-Pflege haben — ähnliche Zielgruppe wie beim Beschaffungsagent
(Einkaufsleiter), hier aber Vertriebs-/Kundenkontakt-Seite.

## Anknüpfungspunkte bei Bestandskunden

- **Schaufler**: Beschaffungsagent bereits live (220€/Mon.) — natürlicher
  Erweiterungsverkauf, kein Neukundengewinn nötig.
- **Mundinger, Voigt Salus**: bestehende Kundenbeziehung, gleiche
  Vertrauensbasis.

## Offene Punkte (vor Verkaufsstart zu klären)

- Welches CRM-System(e) sollen zuerst unterstützt werden (Kunden fragen,
  bevor Integration gebaut wird)
- Preismodell: Pauschale pro Monat vs. pro Gespräch
- Datenschutz: Gesprächsaufzeichnung/-transkription braucht ggf.
  Einwilligung der Gesprächspartner (DSGVO) — genauer prüfen
- Name des Produkts (Arbeitstitel "Meeting-zu-CRM-Agent")
