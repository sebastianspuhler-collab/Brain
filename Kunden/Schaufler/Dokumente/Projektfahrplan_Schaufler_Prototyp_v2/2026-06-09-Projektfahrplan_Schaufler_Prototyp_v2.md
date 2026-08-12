---
tags:
  - Projektfahrplan
  - Beschaffungsagent
  - Schaufler
  - Prototyp
  - Umsetzungsplan
quelle: Projektfahrplan_Schaufler_Prototyp_v2.pdf
datum: 2026-06-09
kategorie: Kunde
---

# Projektfahrplan_Schaufler_Prototyp_v2

Detaillierter Projektfahrplan für den KI-Beschaffungsagenten der Schaufler Fischer Group mit zwei Phasen: Prototyp (2 Wochen) und Vollversion (10 Wochen). Das Dokument beschreibt die modulare Adapter-Architektur, die Rollenaufteilung zwischen Entwicklung und Frontend/Kommunikation sowie einen Sprint-Plan für die Umsetzung. Zahlungsmeilensteine sind an die Phasenabnahme gekoppelt (50%/50%).

## Vollständiger Inhalt
PROJEKTFAHRPLAN
KI-Beschaffungsagent — Schaufler Fischer Group
Prototyp in 2 Wochen · Vollversion in 10 Wochen
Stand: Februar 2026 · Person A: Entwicklung · Person B: Frontend & Kommunikation
1. Projektziele & Rahmenbedingungen
Das Projekt wird modular gebaut. Jede externe Schnittstelle (ELO, Proleis, Outlook) ist 
austauschbar. Im Prototyp werden ELO und Proleis durch einfache Mocks/Fallbacks ersetzt — die 
echten Adapter kommen in Phase 2.
Phase Ziel Frist / Zahlung
Prototyp AB-Workflow mit Mock-Daten + 
Dashboard4 Wochen (Ziel: 2 Wochen) → 50% 
Zahlung
Vollversion Alle Lastenheft-Anforderungen inkl. 
echter Proleis- & ELO-Anbindung10 Wochen → restliche 50% Zahlung
2. Modulare Architektur — Adapter-Pattern
Jede externe Schnittstelle bekommt einen eigenen Adapter mit fixer interner Schnittstelle. Person A 
entwickelt immer gegen das Interface — nicht gegen das externe System direkt. Dadurch könnt ihr 
Proleis, ELO oder Outlook jederzeit austauschen ohne den Core anzufassen.
Modul Interface (fix) Prototyp (Woche 1-2) Vollversion (Woche 3+)
E-Mail get_new_mails() 
send_mail()mock_adapter.py graph_adapter.py
ERP / Bestelldaten get_order() 
update_delivery_date()mock_adapter.py proleis_adapter.py
DMS / Ablage store_document() 
tag_document()filesystem_adapter.py elo_adapter.py
KI-Extraktion extract_attributes(doc) Claude API Claude API
Projektstruktur:
/agent   /core     orchestrator.py       ← Hauptlogik, kennt keine externen Systeme     
ab_processor.py       ← KI-Extraktion & Abgleichslogik     escalation_engine.py  ← 
Eskalations- & Erinnerungslogik     scheduler.py          ← stündliches Polling   
/adapters     /email    → base.py, graph_adapter.py, mock_adapter.py     /erp      → 
base.py, proleis_adapter.py, mock_adapter.py     /dms      → base.py, elo_adapter.py, 
filesystem_adapter.py   /dashboard             ← Person B (Streamlit)   config.yaml  
← hier Adapter umschalten
config.yaml Beispiel:
# Prototyp email: mock erp: mock dms: filesystem  # Vollversion # email: graph # erp: 
proleis # dms: elo 3. Rollenaufteilung
Bereich Person A — Entwicklung Person B — Frontend & 
Kommunikation
Agent Core orchestrator.py, ab_processor.py, 
escalation_engine.py, scheduler.py—
Adapter Alle Adapter bauen (Mock zuerst, echte 
später)—
KI-Extraktion Claude API Integration, Prompt 
Engineering für AB-DokumenteTestfälle & Beispiel-ABs sammeln und 
aufbereiten
Dashboard API-Endpunkte bereitstellen (FastAPI) 
damit Dashboard Daten hatStreamlit App: Agent-Status, AB-
Übersicht, Eskalationen, Tasks
Kommunikation Technische Fragen an Schaufler IT 
klärenProjekt-Updates, Demo vorbereiten, 
Schaufler-Kontakt managen
Tests Unit Tests für Core-Logik und Adapter End-to-End Tests, Demo-Script, 
Abnahmeprüfung
4. Detaillierter Umsetzungsplan — Prototyp (2 Wochen)
Sprint 0 — Tag 1 (beide zusammen, ~4 Stunden)
Ziel: Alles was den Entwicklungsstart blockiert aus dem Weg räumen.
Aufgabe Wer Deadline
GitHub Repo erstellen, Ordnerstruktur 
anlegen, .env Template, READMEPers
