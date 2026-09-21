# Lead-Agent Playbook

Wird vom Lead-Agenten bei JEDER Recherche-/Scoring-/Priorisierungs-Anfrage
zuerst gelesen (siehe claude_agent.py::SYSTEM_PROMPT) - analog zum
CLAUDE.md-Prinzip im Hauptrepo: einmal hier schreiben, der Agent zieht es
automatisch als Kontext heran, keine Wiederholung in jedem Chat nötig.

**Stand 2026-09-21:** mit 🔲 markierte Abschnitte sind noch nicht festgelegt und
gelten als KEINE Vorgabe - der Agent leitet die Kriterien dann aus der Anfrage
bzw. dem Referenzkunden ab (z.B. "wie F-Tronic") und nennt seine Annahme, statt
zu blockieren oder nachzufragen. Vergibt Scores erst, wenn Scoring-Regeln
(Abschnitt 3) stehen.

---

## 1. Ideal Customer Profile (ICP)

🔲 **Branchen** (Beispiele aus bestehenden Vault-Daten als Ausgangspunkt,
noch zu bestätigen/erweitern): Werkzeugbau, Lohnfertigung, Elektrotechnik,
Kunststoffverarbeitung, Metallbau - siehe Marketing/LinkedIn/STRATEGIE.md §5
für die aktuelle Content-Zielgruppe.

🔲 **Unternehmensgröße** (Mitarbeiterzahl / Umsatz):

✅ **Geografischer Fokus** (Sebastian, 2026-09-21): ganz Deutschland.

✅ **Referenzkunde F-Tronic - belegte Merkmale** (geprüft 2026-09-21):
- Stammdaten (f-tronic.de Impressum/Über uns): f-tronic GmbH, Zum Gerlen 21-25,
  66131 Saarbrücken-Ensheim, HRB 9402, Geschäftsführer Marvin Brück; **rund 250
  Mitarbeiter**, 35+ Jahre am Markt, 1.100+ Produkte (Installationsdosen,
  Verteiler, Zählerschränke, Brandschutz, Befestigung), Lieferung in 33 Länder.
  Umsatz nur als Schätzung aus Firmenverzeichnissen (10-50 Mio €), nicht von
  F-Tronic bestätigt.
- Prozess (Bedarfsanalyse 02.09.2026, `Kunden/F-Tronic/Meetings/`): ERP proAlpha
  inkl. DMS; ca. 600 Auftragsbestätigungen/Rechnungen/Lieferscheine pro Monat;
  500-800 aktive Lieferanten; Liefertermintreue ca. 70 %; manuelle AB-Prüfung
  2-10 Minuten pro Beleg; Kernproblem: abweichende Liefertermine.
- Ähnliche Firmen = Hersteller/Händler mit ERP-gestütztem Einkauf, vielen
  Lieferanten und hohem Belegaufkommen. Stärkstes Einzelsignal: **gleiches ERP
  (proAlpha)** - belegt bei Spelsberg (seit 1998) und apra-norm (seit 2008).
- Früher im Umlauf, aber FALSCH: "F-Tronic 150-220 MA / >50 Mio € / 15 Länder"
  (Lead-Notes vom 06.-15.09.2026 sind korrigiert). Nicht wieder verwenden.

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

**Zwei getrennte Status-Systeme:** Der Vault-Status (oben) bewertet den Lead
aus Vertriebssicht; der Close-Status ist die Pipeline-Stufe in Close
("Nicht erreicht", "Mailbox", "Termin vereinbart", "Rückruf gewünscht",
"Kein Interesse", "Call Status" - Liste live über `close_lead_statuses`).
`update_lead(status=...)` setzt den Vault-Status, `update_lead(close_status=...)`
den Close-Status. Filter `status` in `get_combined_leads`/`export_leads` matcht
beide.
