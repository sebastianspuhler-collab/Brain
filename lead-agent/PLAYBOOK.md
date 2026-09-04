# Lead-Agent Playbook

Wird vom Lead-Agenten bei JEDER Recherche-/Scoring-/Priorisierungs-Anfrage
zuerst gelesen (siehe claude_agent.py::SYSTEM_PROMPT) - analog zum
CLAUDE.md-Prinzip im Hauptrepo: einmal hier schreiben, der Agent zieht es
automatisch als Kontext heran, keine Wiederholung in jedem Chat nötig.

**Dieses Dokument ist ein Gerüst - alle mit 🔲 markierten Abschnitte sind vom
Nutzer (Sebastian) noch inhaltlich zu befüllen.** Ohne befüllte Kriterien
wird der Agent bei Bewertungsfragen nachfragen statt zu raten.

---

## 1. Ideal Customer Profile (ICP)

🔲 **Branchen** (Beispiele aus bestehenden Vault-Daten als Ausgangspunkt,
noch zu bestätigen/erweitern): Werkzeugbau, Lohnfertigung, Elektrotechnik,
Kunststoffverarbeitung, Metallbau - siehe Marketing/LinkedIn/STRATEGIE.md §5
für die aktuelle Content-Zielgruppe.

🔲 **Unternehmensgröße** (Mitarbeiterzahl / Umsatz):

🔲 **Geografischer Fokus**:

🔲 **Erkennbare Schmerzpunkte/Trigger**, die einen Prospect qualifizieren
(z.B. "manuelle Excel-Prozesse in der Angebotserstellung", "kein CRM im
Einsatz", "sichtbares Wachstum ohne Prozess-Digitalisierung"):

🔲 **Ausschlusskriterien** (wen NICHT ansprechen - z.B. Branchen mit
bestehenden Kompetitor-Lösungen, zu kleine Betriebe ohne Budget):

---

## 2. Recherche-Quellen & -Flow

Der Agent nutzt das native WebSearch-Tool für die eigentliche Recherche
(kein separater API-Key nötig, läuft über das Claude-Code-Abo).

🔲 **Bevorzugte Quellen/Verzeichnisse** (z.B. Branchenverzeichnisse,
IHK-Listen, LinkedIn-Suche, bestehende Adresslisten unter
Sales/Cold_Call/Adresslisten/):

🔲 **Typischer Rechercheablauf** (z.B. "Branche + Region googeln ->
Firmenwebsite auf Ansprechpartner/Impressum prüfen -> LinkedIn-Profil des
Ansprechpartners suchen"):

**Ablage:** jeder gefundene, ICP-passende Prospect wird über das
`save_prospect`-Tool angelegt - das schreibt gleichzeitig einen Lead-Stub
nach `Leads/*.md` UND einen Lead in Close CRM (Quelle-Feld
"prozessia-lead-agent"), verknüpft über `close_lead_id`.

---

## 3. Scoring-Kriterien

🔲 **Score-Skala** (z.B. 1-10, oder Kategorien kalt/warm/heiß):

🔲 **Gewichtung der Kriterien** (Beispielgerüst - Zahlen/Kriterien
anpassen):

| Kriterium | Gewicht | Hinweis |
|---|---|---|
| ICP-Branchen-Fit | | |
| Unternehmensgröße passt | | |
| Erkennbarer Schmerzpunkt/Trigger | | |
| Reaktion auf Erstkontakt (Antwort, Terminwunsch, ...) | | |
| Opportunity-Wert in Close (falls vorhanden) | | |

🔲 **Schwelle für "heiß"** (ab welchem Score/welcher Kategorie wird ein
Sales-Brief erzeugt):

---

## 4. Status-Konvention (Vault-Frontmatter `status`-Feld)

Fest im Code verankert (vault_leads.py/mcp_server.py), hier nur zur
Übersicht - bei Bedarf um weitere Werte ergänzen und Code entsprechend
anpassen:

- `neu` - gerade angelegt, noch kein Kontakt
- `kontaktiert` - Outreach/Call/Note vorhanden (auch automatisch per
  Close-Webhook gesetzt, siehe webhooks.py)
- `qualifiziert` - ICP-Fit + Schmerzpunkt bestätigt
- `heiss` - Score über der Schwelle, Sales-Brief wurde/wird erzeugt
- `gewonnen` / `verloren` - aus Close-Opportunity-Status übernommen
