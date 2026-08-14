---
tags:
  - Umsetzungsplan
  - Brain
  - Bugfix
  - RAG
  - Company-Brain
quelle: Everlast-AI-Videoanalyse (81pDusm5nZE, S7yg98I6L7k) + Code-Review Brain-App
datum: 2026-07-16
kategorie: Produkt
---

# Umsetzungsplan: Brain-Bugfixes & Company-Brain-Features

## Status: Kompletter Plan umgesetzt (2026-07-17)

Alle neun Punkte (A1, A2, B1, B2, B3, C1, C2, D1, D2, D3) sind implementiert
und so weit wie in dieser Umgebung möglich verifiziert (Syntax-Checks,
Unit-/Regressionstests gegen den echten Vault, End-to-End-Tests mit
gemocktem Anthropic-Client, `tsc`-Typecheck für das gesamte Frontend, finaler
Nebenläufigkeits-Stresstest für `rag.py`). Noch nichts committed/gepusht/
deployed. Details zu jedem Punkt und was jeweils getestet wurde stehen unten
bei den einzelnen Abschnitten.

## Kohärenz-Review vor Deploy (2026-07-17, zweiter Durchgang)

Auf Sebastians Nachfrage noch mal kritisch geprüft, ob die neuen Teile
technisch sauber ineinandergreifen und ob sie inhaltlich zur tatsächlichen
Situation (Soloselbständiger/kleine Agentur, keine großen Teams) passen —
nicht nur "ist der Code korrekt", sondern "hilft das wirklich und passt die
Architektur". Zwei echte, messbare Probleme gefunden und behoben, plus eine
ehrliche Einschätzung zu zwei Features, deren Passung zur echten Nutzung
fraglich ist.

**Gefundenes Problem 1 — BM25-Rebuild hätte das ursprüngliche Symptom auf
Umwegen zurückgebracht.** C2 (Hybrid Search) baut den BM25-Index bei jedem
einzelnen `add_document()`-Aufruf neu — das hatte ich einzeln getestet, aber
nicht im Zusammenspiel mit dem bereits bestehenden E-Mail-Indexer
(`email_indexer.py`), der bis zu 500 Mails im ersten Deep-Scan und danach alle
5 Minuten bis zu 50 neue über genau diese Funktion einzeln hinzufügt. Gemessen:
ein BM25-Rebuild dauert auf dem aktuellen Vault (~1500 Chunks) ~280ms — bei
50 E-Mails am Stück wären das >5 Sekunden, beim ersten Deep-Scan mit 500
Mails potenziell über eine Minute, in der der eine dedizierte RAG-Worker-Thread
(auf dem A1 jetzt JEDE Chat-Suche laufen lässt) blockiert gewesen wäre — also
im Prinzip eine mildere Neuauflage von "Verbindung unterbrochen", nur durch
meine eigene C2-Änderung neu eingeführt. **Fix:** neue Funktion
`rag.add_documents_batch()` — schreibt den Index und baut BM25 nur EINMAL pro
Batch statt einmal pro Datei. `reindex_new_files()` und `email_indexer.py`
nutzen jetzt diese Batch-Funktion. Gemessen: 50 Dateien vorher ~5,3s, jetzt
~1,0s (dominiert nur noch vom eigentlichen Embedding, nicht mehr von N
Festplatten-Schreibvorgängen und N BM25-Rebuilds). Mit Konkurrenz-Stresstest
(gleichzeitige Chat-Suche während eines 30-50-Datei-Batches) erneut verifiziert
— keine Fehler, keine spürbaren Hänger mehr.

**Gefundenes Problem 2 — Ordner-gefilterte Agenten (D2) konnten leer
zurückkommen.** Der Ordner-Filter für eigene Agenten hat den Kandidatenpool
erst NACH der normalen Top-15-Suche über den ganzen Vault gefiltert. Bei einem
kleinen Kundenordner (wenige Dokumente unter aktuell ~1500 Chunks insgesamt)
tauchen dessen Dokumente in den global besten 15 Treffern oft gar nicht auf —
empirisch nachgestellt: eine generische Frage ("Wie ist der Status?") ohne
Kundennamen, gefiltert auf einen kleinen Kunden, lieferte VOR dem Fix null
Treffer, obwohl passende Dokumente existierten. **Fix:** bei aktivem
Ordner-Filter wird jetzt aus FAISS/BM25 ein deutlich größerer Kandidatenpool
geholt (bis zu 500 statt 15), bevor gefiltert wird — kostenlos bei der
aktuellen Vault-Größe. Nach dem Fix liefert dieselbe Testfrage korrekt alle 3
echten Dokumente des kleinen Testkunden.

**Ehrliche Einschätzung: passen D2 (eigene Agenten) und D3 (Spaces) wirklich
zur Situation?** Beide sind direkt aus Everlast AIs "Company Brain"-Konzept
übernommen, das für Unternehmen mit mehreren Mitarbeitenden gedacht ist
(Agenten pro Abteilung/Mitarbeiter, Vollständigkeits-Tracking fürs
Team-Onboarding). Für einen Soloselbständigen ist der Mehrwert spürbar
kleiner:
- **D2** bringt vor allem zwei echte Vorteile: eine feste Modellwahl pro
  Kontext und (nach dem Fix) einen sauber funktionierenden Ordner-Filter. Der
  Zusatz-Prompt allein bringt wenig, was ein gut formulierter Chat-Prompt
  nicht auch könnte — `get_customer_context()` liefert ja schon automatisch
  alle Kundendateien, sobald der Kundenname in der Frage vorkommt, auch ganz
  ohne Agenten. Nutzt du es nicht, kostet es nichts (Chat verhält sich
  identisch ohne gewählten Agenten) — aber ich würde nicht erwarten, dass es
  viel benutzt wird, solange du alleine arbeitest.
- **D3** ist die fraglichste Ergänzung. Der Vollständigkeits-Score basiert auf
  vier Standardordnern, die aber nicht jedes Engagement tatsächlich braucht
  (manche Kunden laufen ohne formellen Vertrag oder ohne separaten
  Angebots-Ordner) — ein niedriger Score kann also fälschlich nach "hier
  fehlt was" aussehen, obwohl alles in Ordnung ist. Ich habe die Texte in der
  UI entsprechend vorsichtiger formuliert (siehe unten), aber die Kachel
  ersetzt kein echtes Urteil darüber, was bei einem Kunden wirklich fehlt.

**Ähnliches beim Kunden-Status-Widget (B3):** "Tage seit letztem Meeting" als
Ampel zu zeigen, kann bei ruhig laufenden, stabilen Projekten fälschlich nach
Vernachlässigung aussehen, obwohl gerade Funkstille ein gutes Zeichen sein
kann. Texte in `DashboardPage.tsx` jetzt entsprechend präzisiert (zeigt nur
Zeit seit letztem Meeting, keine Bewertung der Beziehung) statt wertender
Begriffe wie "Kontakt verloren".

**Fazit:** A1, A2, B1, B2, C1, C2, D1 sind klar begründet und tragen
unabhängig von Teamgröße. B3/D2/D3 sind funktionsfähig, technisch jetzt
sauber (nach den zwei Fixes oben), aber ihr tatsächlicher Nutzen hängt davon
ab, ob sich dein Arbeitsalltag ändert (z.B. wenn Prozessia wächst und mehrere
Personen mit dem Brain arbeiten) — für den Ist-Zustand als Solo-Setup sind sie
eher "kostet nichts, kann aber warten" als "dringend gebraucht". Kein
Blocker fürs Deployen, aber falls du Zeit sparen willst: B3/D2/D3 könnten
genauso gut erst nach dem Deploy der anderen sechs Punkte kommen.

## Restplan — was Sebastian noch selbst tun muss

1. **Committen & Deployen.** Ich habe noch nichts committed (wie immer, außer
   auf ausdrücklichen Wunsch). Wenn du grünes Licht gibst, committe ich die
   neun Punkte (ggf. in mehreren thematischen Commits) und du deployst wie
   gewohnt: `git pull && docker compose up -d --build` auf dem VPS — das
   `--build` ist diesmal wichtig, weil `requirements.txt` ein neues Paket
   (`rank-bm25`) bekommen hat, ein reines `docker compose up -d` ohne Rebuild
   würde das nicht mitnehmen.
2. **`MISTRAL_API_KEY` (optional, nur für C1/OCR-Vorstufe).** Ohne diesen Key
   läuft alles exakt wie bisher (PyPDF2-Fallback). Falls du die OCR-Vorstufe
   nutzen willst: Account auf console.mistral.ai anlegen, Key in
   `backend/.env` auf dem VPS eintragen (Vorlage steht in
   `backend/.env.example`), danach an einem der PDFs mit bekannt lückenhafter
   Extraktion gegentesten (z.B. Systemhandbuch oder Lastenheft Schaufler).
3. **Nach dem Deploy beobachten: "Verbindung unterbrochen".** Der Fix (A1)
   behebt einen empirisch reproduzierten Absturz, aber ob exakt dieser
   Crash-Mechanismus 1:1 die Ursache auf dem Linux-VPS war, ist nicht zu 100%
   sicher (reproduziert wurde er auf meinem macOS-Testrechner). Wenn das
   Problem danach weiter auftritt, brauche ich doch noch
   `docker compose logs --tail 150 backend` vom nächsten Auftreten.
4. **Die 5 neuen/geänderten UI-Bereiche einmal selbst anschauen.** Ich konnte
   in dieser Umgebung keinen echten Login-Browser-Test fahren (kein
   Browser-Automatisierungstool verfügbar, kein bekanntes Passwort für den
   lokalen Testnutzer) — nur Backend-Endpoints gegen echte Daten und
   TypeScript-Typprüfung. Bitte einmal kurz gegenchecken, ob es optisch passt:
   - **Dashboard** (neue Sidebar-Seite): Kunden-Ampel + LinkedIn-Status
   - **Meetings** (neue Sidebar-Seite): vault-weite Meeting-Übersicht
   - **Agenten** (neue Sidebar-Seite): eigene Chat-Agenten anlegen
   - **Spaces** (neue Sidebar-Seite): Vollständigkeits-Score pro Kunde
   - **Chat**: Verlauf-Liste in der Sidebar, Quellen-Chips unter Antworten,
     Agenten-Auswahl neben der Modellwahl
5. **Zwei Karteileichen im Vault gefunden (kein Blocker, nur Hinweis).**
   `Kunden/[NeuerKunde]/` (lose Dateien ohne Standardstruktur) und
   `Kunden/_Vorlage/` (Vorlagenordner) tauchten beim Testen der neuen
   Dashboard/Spaces-Endpoints als falsche "Kunden mit 0%" auf. Ich habe sie
   nur aus der Anzeige rausgefiltert (Ordnername beginnt mit `[` oder `_`),
   nichts gelöscht oder verschoben — falls das aufräumbare Reste sind, gerne
   Bescheid geben, dann räume ich das auf Zuruf weg.
6. **Eigene Agenten sind opt-in.** Es gibt noch keinen einzigen angelegt —
   falls dir das Feature nützlich erscheint (z.B. ein "Schaufler-Bot" mit
   Ordner-Filter auf `Kunden/Schaufler/`), leg ihn einfach über die neue
   Agenten-Seite an, sonst bleibt der Chat exakt wie bisher.

## Leitplanke

Keine bestehende Funktion der Brain-App darf durch diese Arbeit verloren gehen
oder regredieren. Jeder Punkt unten ist entweder eine **nachweisliche
Verbesserung** eines bereits bestehenden Features (mit konkreter Datei/Zeile
als Beleg) oder eine **reine Ergänzung**, die nichts Bestehendes ersetzt.

Quellen: die zwei Everlast-AI-Videos ("Wieso KI Second Brains scheitern" /
Company-Brain-Vortrag + der RAG-Komplettkurs mit Corporate-LLM-Demo) plus
eigene Code-Analyse von `backend/app/services/rag.py`, `chat.py`,
`context.py`, `classify.py`, `jobs.py`, `dashboard.py` und
`frontend/src/pages/ChatPage.tsx`.

## Abgearbeitete Reihenfolge (alle ✅ erledigt)

1. **A1** – Worker-Thread-Fix in `rag.py` (Verbindungsabbruch)
2. **A2** – Chat-Persistenz
3. **C2** Hybrid Search + **C1** OCR-Vorstufe
4. **D1** Quellenangabe
5. **B1** Decision-Log + **B2** Meeting Cockpit
6. **B3** Dashboard-Erweiterung, **D2** eigene Agenten, **D3** Spaces

---

## Teil A — Die zwei gemeldeten Bugs

### A1. „Verbindung unterbrochen" — wahrscheinliche Ursache gefunden

**Ist-Zustand:** `rag.search()` (`rag.py:69-106`) liest `_index`/`_meta` ohne
jede Sperre. Gleichzeitig mutieren `add_document()` (`rag.py:109-128`) und
`build_full_index()` (`rag.py:169-211`) exakt dieselben Objekte unter einem
`threading.Lock`. Der Inbox-Watcher (`jobs.py:136-162`) ruft alle 30 Sekunden
`rag.reindex_new_files()` auf, sobald irgendeine Datei in `_inbox/` liegt —
das geschieht also nebenläufig zu jeder laufenden Chat-Anfrage, die zeitgleich
`rag.search()` aufruft (`chat.py:52`, im ThreadPoolExecutor). FAISS'
`IndexFlatIP` ist nicht für gleichzeitiges Lesen *und* Schreiben ohne
Synchronisation ausgelegt — das kann zu Exceptions, verfälschten
Suchergebnissen oder im ungünstigen Fall zu einem hängenden Backend-Prozess
führen. Ein hängender/abstürzender Prozess würde sich exakt als plötzlicher
Abbruch **aller** offenen Chat-Verbindungen zeigen, wie gemeldet.

**Status: ✅ Umgesetzt und verifiziert am 2026-07-16.** Der ursprüngliche Plan
(ein einfacher Lock um `search()`) hat sich als unzureichend herausgestellt —
per Stress-Test empirisch nachgewiesen:

- Ein reiner `threading.Lock` um `encode()`+`index.search()` verhindert zwar
  Gleichzeitigkeit, aber schon der **sequenzielle** Aufruf von
  `SentenceTransformer.encode()` aus **wechselnden** Python-Threads (nicht
  einmal zwingend gleichzeitig) konnte den Prozess mit SIGSEGV abschießen —
  ein bekanntes Cross-Thread-Problem von PyTorch/FAISS mit nativen
  BLAS-Backends. Rein sequenzielle Aufrufe von einem einzigen Thread aus
  liefen dagegen beliebig oft crashfrei.
- Deshalb: **dedizierter Worker-Thread** statt reinem Lock. Alle
  Modell-/Index-/BM25-Zugriffe laufen jetzt ausschließlich auf einem einzigen
  Hintergrund-Thread (`_worker_loop` in `rag.py`), egal welcher Thread
  `search()`/`add_document()`/`load()`/`build_full_index()` aufruft — über
  eine interne Queue, für den Aufrufer transparent (`_run_on_worker()`
  blockiert bis das Ergebnis da ist, exakt gleiches Verhalten wie vorher).
- Verifiziert mit einem realistischen Lasttest (3 parallele Chat-Anfragen +
  Inbox-Watcher fügt 5 Dateien hinzu) **und** einem absichtlich überzogenen
  Stresstest (8 parallele Anfragen × 150 Suchen + 60 schnelle Datei-Adds) —
  beide liefen nach dem Fix fehlerfrei durch, vorher beide reproduzierbar
  abgestürzt.

**Aufwand:** M (am Ende mehr als geplant — der einfache Lock reichte nicht)
**Priorität:** Sofort — erledigt

**Wichtiger Vorbehalt bleibt bestehen:** Der reproduzierte Crash trat auf
diesem macOS-Entwicklungsrechner auf (Apple-Silicon-BLAS-Backend). Ob exakt
dieser Crash-Mechanismus 1:1 auch im Linux-Docker-Container auf dem VPS
auftritt, ist nicht zu 100% sicher — der Fix (alles auf einem Thread) behebt
aber ohnehin jede Form von Cross-Thread-Problemen mit dem Modell, unabhängig
von der Plattform, und kostet nichts an Funktionalität. Nach dem Deploy
beobachten, ob "Verbindung unterbrochen" verschwindet — falls nicht, brauchen
wir doch noch `docker compose logs --tail 150 backend` vom nächsten Auftreten.

### A2. Chat-Historie verschwindet beim Neuladen

**Ist-Zustand:** `ChatPage.tsx:31` hält `messages` nur in `useState` — kein
`localStorage`, kein Server-Reload, keine Session-ID. `conversations.log_turn`
(`conversations.py:8-18`) schreibt zwar mit, aber nur als Tages-Logdatei, die
`context.build_system()` am **nächsten** Tag in den System-Prompt einspeist
(`context.py:230-233) — es gibt keinen Endpoint, der eine einzelne
Chat-Session wieder auflädt.

**Status: ✅ Umgesetzt und verifiziert am 2026-07-16.** Neuer Service
`backend/app/services/chat_sessions.py` (eine JSON-Datei pro Session unter
`_agent/chat_sessions/{id}.json`, Titel wird automatisch aus der ersten
Nutzer-Nachricht abgeleitet). Neue Endpoints in `chat.py`:
`GET /api/chat/sessions` (Liste), `GET/POST/DELETE /api/chat/sessions/{id}`.
`/api/chat` bekommt ein optionales `session_id`-Feld — ohne `session_id`
verhält sich der Chat exakt wie zuvor (keine Änderung für bestehende
Aufrufer). Frontend: `ChatPage.tsx` liest/schreibt die Session über
`?session=<id>` in der URL, erzeugt beim ersten Senden automatisch eine neue
ID (`crypto.randomUUID()`). `AppSidebar.tsx` zeigt eine „Verlauf"-Liste mit
„Neuer Chat"-Button, Titel, Zeitangabe und Lösch-Button pro Chat — wie bei
Claude.ai. Backend-Logik (Service + Endpoints) direkt getestet, Frontend
per `tsc` typgeprüft.

**Aufwand:** M
**Priorität:** Hoch — erledigt

---

## Teil B — Company-Brain-Konzepte (Video 2)

### B1. Decision-Log

**Ist-Zustand:** Kein Äquivalent vorhanden. `extract_meeting_structure()`
(`classify.py:208-239`) erfasst bereits Zusagen/Nächste-Schritte pro Meeting,
aber es gibt keine explizite Entscheidungs-Erkennung und kein zentrales,
durchsuchbares Protokoll über alle Meetings/Chats hinweg.

**Status: ✅ Umgesetzt und verifiziert am 2026-07-17.**
`extract_meeting_structure()` in `classify.py` hat jetzt ein fünftes Feld
`entscheidungen` im Prompt/JSON (die bisherigen vier Felder unverändert).
Neue Funktion `_append_decisions_log()` schreibt jede erkannte Entscheidung
nach `_agent/decisions.md` (Format: `- DATUM | QUELLDATEI | Entscheidung`),
aufgerufen aus `process_file()` direkt nach dem bestehenden
`meeting_sections`-Aufbau (neue Sektion „## Entscheidungen" im Meeting-Dokument
selbst kommt zusätzlich dazu, nichts Bestehendes entfällt).

**Verifiziert:** Unit-Test für `_append_decisions_log()` (Formatierung, leere
Liste schreibt nichts, Mehrfach-Einträge korrekt) sowie ein End-to-End-Test
von `process_file()` mit simuliertem Meeting-Transkript (Anthropic-Aufrufe
gemockt, kein echter API-Call) — beide bestanden. Das erzeugte
Meeting-Dokument enthält weiterhin alle bisherigen Felder (Teilnehmer,
Kernpunkte, Zusagen, Nächste Schritte) plus die neue „## Entscheidungen"-
Sektion, und `_agent/decisions.md` wird korrekt mit Datum/Quelldatei/
Entscheidung befüllt. `_agent/decisions.md` liegt außerhalb der RAG-
Skip-Verzeichnisse und wird dadurch automatisch durchsuchbar.

**Nicht umgesetzt (aus dem ursprünglichen Plan zurückgestellt):** optionales
Chat-Tool `log_decision` für explizite Entscheidungen im normalen Chat
("das ist jetzt entschieden: …") — kein Blocker, kann später ergänzt werden,
falls gewünscht.

**Aufwand:** M
**Priorität:** Mittel — erledigt

### B2. Meeting Cockpit

**Ist-Zustand:** Meeting-Notizen liegen verteilt in
`Kunden/[Firma]/Meetings/`, es gibt keine vault-weite Übersicht.

**Status: ✅ Backend verifiziert, Frontend nur typgeprüft (kein Live-Check).**
Neuer Endpoint `GET /api/meetings` in `files.py` (`list_meetings()`): findet
alle `.md`-Dateien vault-weit, deren Pfad ein `Meetings`-Segment enthält,
liest Datum aus dem Frontmatter und den Anfang der „## Zusammenfassung"
(einfaches Parsen, keine neue Klassifizierungslogik), leitet den Kundennamen
aus `Kunden/[Firma]/Meetings/...` ab, sortiert absteigend nach Datum. Neue
eigenständige Seite `MeetingsPage.tsx` (Route `/meetings`, Sidebar-Eintrag
„Meetings") statt Erweiterung von `FilesPage.tsx` — vermeidet jedes Risiko
für die bestehende Dateien-Seite, filterbar nach Kunde (Dropdown) und
Freitext.

**Verifiziert:** `list_meetings()` direkt gegen den echten (nur gelesenen,
nicht veränderten) Vault aufgerufen — 8 Meeting-Notizen korrekt gefunden,
Datum/Kunde/Zusammenfassung korrekt geparst. Route-Registrierung bestätigt.
Frontend per `tsc` typgeprüft. **Nicht gemacht:** echter Browser-Check der
UI — hätte einen vollen lokalen Zwei-Server-Dev-Aufbau (Backend+Vite,
CORS-Konfiguration) plus eine Browser-Automatisierung erfordert, die in
dieser Umgebung nicht verfügbar war. Die Komponente folgt aber 1:1 den
bereits produktiv laufenden Mustern aus `FilesPage.tsx`/`CalendarPage.tsx`
(gleiche Card/Table/Select-Bausteine).

**Aufwand:** S–M
**Priorität:** Mittel — erledigt, UI-Check steht noch aus

### B3. Management-Dashboards (Erweiterung)

**Ist-Zustand:** `dashboard.py:39-63` hat bereits `/api/status`,
`/calendar`, `/gmail`, `/tasks` — das Grundgerüst existiert und bleibt exakt
so bestehen.

**Status: ✅ Umgesetzt und verifiziert am 2026-07-17.** Zwei neue Endpoints in
`dashboard.py`: `GET /api/dashboard/kunden-status` (Ampel je Kunde: grün <30
Tage seit letztem Meeting, gelb 30-90, rot >90, grau ohne erfasstes Meeting;
plus Anzahl offener Aufgaben, deren Text den Kundennamen erwähnt) und
`GET /api/dashboard/linkedin-status` (geplante/gepushte Posts, offene Ideen,
nächster Termin — aus den bereits vorhandenen `linkedin_service`-Daten). Neue
Seite `DashboardPage.tsx` (Route `/dashboard`, Sidebar-Eintrag "Dashboard").
Alle bestehenden Endpoints/Widgets unverändert, nur Ergänzung.

**Bewusst NICHT umgesetzt:** "Offene Rechnungen"-Kachel aus dem
ursprünglichen Plan. Im Vault wird nirgends ein Bezahlt/Offen-Status zu
Rechnungen gepflegt (nur rohe PDFs in `Finanzen/Rechnungen/` ohne
Status-Metadaten) — eine solche Kachel hätte zwangsläufig einen erfundenen
oder geschätzten Status angezeigt, was der Projektregel widerspricht, niemals
Zahlen/Status zu erfinden, wo keine echten Daten vorliegen.

**Nebenbefund:** Beim Testen gegen den echten Vault zwei Platzhalterordner
unter `Kunden/` gefunden — `[NeuerKunde]` (nur lose Dateien, keine
Standardstruktur) und `_Vorlage` (Vorlagen-Kundenordner). Beide wären ohne
Filter fälschlich als "Kunde mit 0% Status" aufgetaucht. Jetzt in
`kunden_status()` und `list_spaces()` (siehe D3) anhand des führenden `[`
bzw. `_` im Ordnernamen ausgeschlossen. Nur eine Anzeige-Filterung, die
Ordner selbst wurden nicht angefasst.

**Verifiziert:** Beide Endpoints direkt gegen den echten (nur gelesenen)
Vault aufgerufen, Ampel-Logik und LinkedIn-Zahlen stimmen mit den
tatsächlichen Daten überein. Frontend per `tsc` typgeprüft, kein
Live-Browser-Check (siehe B2 für den Grund).

**Aufwand:** M
**Priorität:** Niedrig–Mittel — erledigt

---

## Teil C — RAG-Technik-Fundament (Video 1)

### C1. OCR-Vorstufe für PDFs (Mistral)

**Ist-Zustand:** `classify.extract_text()` (`classify.py:46-106`) nutzt
PyPDF2-Seitenextraktion. Funktioniert bei sauberen PDFs, aber in diesem
Projekt wiederholt beobachtet: gescannte/mehrspaltige PDFs liefern
lückenhaften Text (die wiederholt aufgetretenen abgeschnittenen
`.md`-Sidecars bei Systemhandbuch/Lastenheft in diesem Chat waren genau
dieses Problem).

**Status: ✅ Vollständig umgesetzt und mit echtem API-Key verifiziert
(2026-07-17).** `classify._extract_pdf_via_mistral_ocr()` ruft `POST /v1/ocr`
bei Mistral auf (Base64-PDF, Modell `mistral-ocr-latest`), `extract_text()`
nutzt das nur, wenn `MISTRAL_API_KEY` gesetzt ist, und fällt bei jedem Fehler
(kein Key, Netzwerkfehler, unerwartete Antwortstruktur) automatisch auf den
bestehenden PyPDF2-Pfad zurück. Sebastian hat einen Mistral-Key ("Brain")
bereitgestellt, lokal in `backend/.env` eingetragen (gitignored, nicht im
Commit).

**Verifiziert:** Ohne Key verhält sich `extract_text()` nachweislich exakt
wie vorher (Regressionstest bestanden). Mit echtem Key gegen
`Systemhandbuch_Beschaffungsagent (2).pdf` getestet (das Dokument, an dem in
diesem Chat wiederholt lückenhafte Extraktion auffiel): PyPDF2 lieferte
15.499 Zeichen aus 13 Seiten, Mistral OCR 16.898 Zeichen — mehr Inhalt und
sauber strukturiertes Markdown (Überschriften erhalten) statt PyPDF2s
Rohtext-Aneinanderreihung. Der komplette `extract_text()`-Wrapper wurde
end-to-end gegengetestet (nutzt jetzt tatsächlich den OCR-Pfad zuerst).

**Wichtig für den Deploy:** der Key liegt bisher nur lokal in Sebastians
`backend/.env` (Mac) — muss zusätzlich in `backend/.env` **auf dem VPS**
eingetragen werden (dort hat Claude keinen Zugriff), sonst bleibt die
OCR-Vorstufe dort inaktiv (kein Fehler, einfach weiterhin PyPDF2-Fallback).

**Aufwand:** M (neuer API-Key/laufende Kosten, Umbau `extract_text`) — erledigt
**Priorität:** Mittel — vollständig erledigt und verifiziert

### C2. Hybrid Search (semantisch + BM25)

**Ist-Zustand:** `rag.search()` (`rag.py:69-106`) ist reine Vektorsuche
(FAISS) mit Entity-Boost, kein Stichwort-Anteil. Genau die im Video
demonstrierte Schwäche: Eigennamen/IDs (z.B. Kundenname „TPG", Artikel- oder
Bestellnummern) landen bei reiner Vektorsuche nicht zuverlässig auf Platz 1.

**Status: ✅ Umgesetzt und verifiziert am 2026-07-16.** Zusätzlicher
BM25-Kanal (`rank_bm25`, neu in `requirements.txt`) über denselben
Chunk-Metadaten, kombiniert per Reciprocal Rank Fusion mit dem
FAISS-Vektor-Score. BM25-Index wird nur beim Schreiben neu gebaut (in
`load()`/`add_document()`/`build_full_index()`), nicht bei jeder Suche — ein
erster Versuch mit Rebuild direkt im Lese-Pfad hat den Suchpfad unnötig
verlangsamt. Die bestehenden Kunden-/E-Mail-Boosts bleiben erhalten (jetzt
als Faktor >1 statt <1, siehe Randnotiz unten).

**Nebenbefund — echter Bug in der Vorgängerversion gefixt:** Die alte
`search()` hat FAISS-Scores (höher = ähnlicher) **aufsteigend** sortiert und
die ersten 15 genommen — das lieferte bevorzugt die *schlechtesten* Treffer
aus dem Kandidatenpool statt der besten. Nur durch einen ebenfalls
invertierten Boost-Faktor (`*0.80`/`*0.88` statt `*1.25`/`*1.14`) hat sich das
in der Praxis teilweise selbst kompensiert. Jetzt korrekt absteigend sortiert
und empirisch verifiziert: eine Testsuche nach "Schaufler Beschaffungsagent
Auftragsbestätigung" liefert jetzt tatsächlich die drei thematisch
passendsten Dokumente auf den ersten drei Plätzen (vorher wären das die
unpassendsten 15 aus dem Kandidatenpool gewesen).

**Nachtrag 2026-07-17 (Kohärenz-Review):** der "nur beim Schreiben"-Rebuild
war noch nicht das ganze Bild — er passierte pro `add_document()`-Aufruf,
und der bestehende E-Mail-Indexer ruft das bis zu 500x hintereinander auf.
Siehe `rag.add_documents_batch()` im Review-Abschnitt oben: jetzt ein Rebuild
pro Batch statt pro Datei.

**Aufwand:** M
**Priorität:** Hoch — erledigt, hat nebenbei auch A1 (dedizierter Worker-Thread,
siehe oben) und einen echten Sortier-Bug mit gefixt

### C3. Reranking (neu, 2026-07-17 auf Sebastians Nachfrage ergänzt)

**Ist-Zustand vor dieser Ergänzung:** Hybrid Search (C2) lieferte die RRF-
kombinierten Top-Treffer direkt als Endergebnis — die im Video beschriebene
letzte Qualitätsstufe "Reranking" (ein spezialisiertes Modell liest Frage und
Chunk *gemeinsam* statt nur ihre Embeddings zu vergleichen, dadurch präziser)
fehlte noch.

**Status: ✅ Umgesetzt und verifiziert.** Lokaler, mehrsprachiger
Cross-Encoder (`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`, trainiert u.a.
auf Deutsch, passend zum bereits mehrsprachigen Embedding-Modell) über
`sentence-transformers` — **kein neuer API-Key/Account nötig**, läuft wie
das Embedding-Modell komplett lokal. Bewertet die RRF-besten 30 Kandidaten
neu, der Rest bleibt unangetastet dahinter. Fällt lautlos auf die
unveränderte Hybrid-Search-Reihenfolge zurück, falls das Modell beim ersten
Start nicht geladen werden kann (z.B. kurzzeitig kein Internetzugriff) - kein
Fehler, keine Downtime.

**Verifiziert:** Testfrage mit klar relevantem vs. irrelevantem Text zeigt
korrekte Diskriminierung (relevanter Text bekommt spürbar höheren Score).
Ergebnis-Scores werden nach dem Reranking konsistent durch die
Reranker-Scores ersetzt (vorher: Anzeige-Score und tatsächliche Reihenfolge
liefen kurz auseinander, gefixt). Kompletter Konkurrenz-Stresstest (Hybrid
Search + Reranking + Ordner-Filter + Batch-Writes gleichzeitig) erneut
bestanden, keine Fehler. Graceful-Fallback (Reranker absichtlich als
"fehlgeschlagen" simuliert) liefert weiterhin korrekte Ergebnisse.

**Aufwand:** S (kein neues Paket nötig, `CrossEncoder` ist bereits Teil von
`sentence-transformers`)
**Priorität:** Mittel — erledigt

### C4. Bewusst NICHT umgesetzt: GraphRAG / Knowledge Graphs

Auf Sebastians Nachfrage geprüft, ob auch dieser im Video behandelte Ansatz
sinnvoll wäre. **Klare Empfehlung dagegen**, aus drei Gründen:

1. **Das Video selbst rät davon ab** für die meisten Fälle — Leo (Everlast)
   sagt explizit, viele Berater machen KI-Wissensmanagement damit nur
   unnötig kompliziert, und "am Ende gewinnen immer die smarten, aber
   simplen Lösungen".
2. **Hoher Aufwand:** würde eine eigene LLM-Extraktionspipeline (Entitäten +
   Beziehungen aus jedem Dokument ziehen), eine Graph-Datenstruktur/-Datenbank
   und Graph-Traversal-Logik zusätzlich zur bestehenden Vektorsuche
   erfordern — ein Vielfaches des Aufwands von Hybrid Search + Reranking
   zusammen.
3. **Passt nicht zum tatsächlichen Bedarf:** Graph-RAG lohnt sich bei
   Fragen, die mehrere Hops über viele verknüpfte Entitäten brauchen (das
   Video-Beispiel: "welcher Mitarbeiter war 2023 für ein Projekt bei Kunde X
   verantwortlich, in dem eine Force-Majeure-Klausel vorkam"). In allen
   RAG-Tests dieser Session waren Sebastians tatsächliche Fragen einstufige
   Status-/Dokumentenabfragen ("wie ist der Stand bei Schaufler") — genau
   der Fall, für den Hybrid Search + Reranking bereits ausreicht.

Ebenfalls bewusst nicht umgesetzt, aus ähnlichen Kosten-Nutzen-Gründen:
**Contextual Retrieval** (Anthropics Technik, jedem Chunk vor dem Embedding
eine generierte Kontext-Zusammenfassung voranzustellen) würde eine
Neuverarbeitung des kompletten bestehenden Index mit einem LLM-Call pro
Chunk erfordern (~1500 Chunks = echte Kosten) und bringt den größten Nutzen
bei sehr kleinteiligem Chunking — unsere Chunks sind mit 800 Wörtern schon
groß genug, dass der Mehrwert gering wäre. **Late Chunking** ist ein
fortgeschrittenes Nischenverfahren mit ähnlich geringem erwarteten Mehrwert
bei der aktuellen Chunk-Größe.

**Damit ist der komplette RAG-Werkzeugkasten aus Video 1, der für Sebastians
tatsächliche Nutzung sinnvoll ist, jetzt umgesetzt:** Chunking, Embeddings,
Vektorsuche, OCR-Vorstufe (C1), Hybrid Search (C2), Reranking (C3),
Multi-Query (bereits vorhanden über Entitäts-Extraktion), sowie Agentic
Retrieval im weiteren Sinne (Claude kann über bestehende Tools wie
`read_file`/`vault_list`/`search_emails` gezielt nachladen, statt alles
vorab in den Kontext zu stopfen — das eigentliche Kernprinzip aus Video 1).

---

## Teil D — Produktfeatures aus der Corporate-LLM-Demo (Video 1)

### D1. Quellenangabe in Chat-Antworten

**Ist-Zustand:** `rag.search()` gibt einen einzigen zusammengefügten String
zurück (`rag.py:104`), der nur in den System-Prompt eingebettet wird
(`chat.py:69`). Das Modell zitiert Quellen zwar oft im Fließtext (der
System-Prompt fordert das explizit, `context.py:120`), aber es gibt keine
strukturierte, in der UI anklickbare Quellenangabe.

**Status: ✅ Umgesetzt und verifiziert am 2026-07-16.** Neue Funktion
`rag.search_with_sources()` (teilt sich intern `_search_impl` mit dem
unveränderten `rag.search()`) liefert zusätzlich eine strukturierte,
nach Pfad deduplizierte Liste `[{path, score}]` (Top 8). `chat.py` nutzt sie
statt `rag.search()` und sendet ein neues SSE-Event `{"sources": [...]}`
**vor** dem eigentlichen Text-Stream. `client.ts`/`streamChat()` bekommt
einen optionalen `onSources`-Callback, `ChatPage.tsx` zeigt die Quellen als
kleine Datei-Chips (Dateiname, voller Pfad als Tooltip) unter der
Assistant-Antwort. Bewusst **keine** anklickbare Verlinkung zur `FilesPage`
umgesetzt — die bräuchte dort einen neuen Deep-Link-Mechanismus (Datei per
Pfad-Query-Param direkt öffnen), der aktuell nicht existiert und den
eigentlichen Ist-Umfang dieses Punkts gesprengt hätte. Verifiziert: `search()`
liefert bitidentischen String wie vorher (Regressionstest bestanden),
`search_with_sources()` liefert korrekt strukturierte, deduplizierte Quellen;
Frontend per `tsc` typgeprüft.

**Aufwand:** M
**Priorität:** Mittel — erledigt (Datei-Verlinkung als mögliche Folgearbeit offen)

### D2. Eigene benannte Agenten

**Ist-Zustand:** Ein einziger Chat mit festem System-Prompt
(`context.build_system()`, `context.py:141-227`) für alle Zwecke,
Modellwahl nur Sonnet/Opus (`ChatPage.tsx:10-13`).

**Status: ✅ Umgesetzt und verifiziert am 2026-07-17.** Neuer Service
`agents_service.py` (CRUD über `_agent/agents.json`: Name, Zusatz-Prompt,
optionaler Ordner-Filter, optionale feste Modellwahl). Neue Endpoints
`GET/POST /api/agents`, `PUT/DELETE /api/agents/{id}`. `/api/chat` bekommt
ein optionales `agent_id`-Feld — ohne Angabe (Standard) verhält sich der Chat
exakt wie zuvor. Ist ein Agent gewählt: sein Zusatz-Prompt wird an den
bestehenden System-Prompt angehängt (nicht ersetzt), sein Modell überschreibt
bei Bedarf die Chat-Modellwahl, sein Ordner-Filter schränkt die RAG-Suche ein
— dafür hat `rag.search_with_sources()` einen neuen optionalen
`path_prefixes`-Parameter bekommen (Default `None` = unverändertes Verhalten
für alle bestehenden Aufrufer). Neue Seite `AgentsPage.tsx`
(Route `/agenten`, Sidebar-Eintrag "Agenten") zum Anlegen/Bearbeiten/Löschen.
`ChatPage.tsx` bekommt einen Agenten-Dropdown neben der Modellwahl
("Standard" = kein Agent); ist ein Agent mit fester Modellwahl aktiv, wird
der Modell-Dropdown passend deaktiviert, damit nicht angezeigt wird, ein
Modell sei wählbar, das der Server ohnehin überschreibt.

**Verifiziert:** `agents_service.py` per Unit-Test (Anlegen/Lesen/Ändern/
Löschen, Felder bleiben bei Teil-Updates erhalten). `rag.py`-Ordner-Filter
gegen den echten Vault getestet (Suche mit/ohne `path_prefixes`, Treffer
korrekt eingeschränkt, leerer Filter-Pfad liefert korrekt null Treffer). Die
komplette Verdrahtung in `_stream_chat()` mit einem gemockten Anthropic-Client
end-to-end getestet: Agent-Modell überschreibt Request-Modell, Ordner-Filter
wird an die RAG-Suche durchgereicht, Zusatz-Prompt UND Basis-Prompt landen
beide im finalen System-Prompt. Frontend per `tsc` typgeprüft.

**Nachtrag 2026-07-17 (Kohärenz-Review) — echter Bug gefunden und gefixt:**
der Ordner-Filter hat ursprünglich erst NACH der normalen Top-15-Suche über
den ganzen Vault gefiltert. Bei kleinen Kundenordnern kam dadurch bei
generischen Fragen (ohne Kundennamen) leer zurück, obwohl passende Dokumente
existierten — empirisch reproduziert und gefixt (größerer Kandidatenpool bei
aktivem Filter, siehe `_search_impl()` in `rag.py`), erneut verifiziert.
Siehe Review-Abschnitt oben auch für eine ehrliche Einschätzung, wie sehr
dieses Feature für einen Solo-Betrieb aktuell wirklich gebraucht wird.

**Aufwand:** L
**Priorität:** Niedrig — erledigt

### D3. Spaces mit Vollständigkeits-Score

**Ist-Zustand:** `get_customer_context()` (`context.py:60-80`) liefert
bereits automatisch alle Kunden-Dateien, sobald ein Kundenname im Chat erkannt
wird — das ist im Kern schon ein impliziter „Space" pro Kunde, nur ohne UI und
ohne Vollständigkeits-Bewertung.

**Status: ✅ Umgesetzt und verifiziert am 2026-07-17.** Neuer Endpoint
`GET /api/spaces` in `files.py`: pro Kunde, wie viele der vier
Standard-Unterordner (`Vertraege/Angebote/Meetings/Dokumente` — dieselben,
die `classify.classify()` für jeden neuen Kunden ohnehin automatisch anlegt)
tatsächlich Dateien enthalten, als Prozent-Score plus Liste der fehlenden
Ordner. Neue Seite `SpacesPage.tsx` (Route `/spaces`, Sidebar-Eintrag
"Spaces") mit Fortschrittsbalken pro Kunde, aufsteigend nach Score sortiert
(unvollständigste zuerst).

**Bewusst vereinfacht gegenüber dem ursprünglichen Plan:** kein
KI-Vorschlag "was fehlt" per Anthropic-Aufruf. Ein LLM würde hier zwangsläufig
raten oder allgemeine Business-Annahmen treffen, die durch keine echten Daten
gedeckt sind — das hätte gegen die Projektregel verstoßen, nie Zahlen/
Einschätzungen zu erfinden. Stattdessen rein deterministisch: die
Vollständigkeit basiert ausschließlich auf tatsächlicher Dateianzahl pro
Standardordner, keine Kosten pro Seitenaufruf.

**Nebenbefund geteilt mit B3:** dieselben zwei Platzhalterordner
(`[NeuerKunde]`, `_Vorlage`) gefunden und mit demselben Filter ausgeschlossen.

**Verifiziert:** `list_spaces()` direkt gegen den echten Vault aufgerufen —
Scores und fehlende Ordner stimmen mit der tatsächlichen Ordnerstruktur
überein (z.B. Schaufler 100%, mehrere Leads bei 0% ohne jede
Standardstruktur). Frontend per `tsc` typgeprüft.

**Aufwand:** M–L
**Priorität:** Niedrig — erledigt

---

## Nachtrag 2026-07-17 (Token-Verbrauch): Randnotiz war akuter als gedacht

Die Randnotiz unten war ursprünglich "kein akuter Handlungsbedarf" — Sebastian
berichtete danach von sehr hohem Tokenverbrauch bei der letzten Nutzung, also
nachgemessen statt nur vermutet.

**Gemessen:** `context.build_system()` erzeugte ~60.435 Zeichen (~15.100
Tokens) Basis-System-Prompt, auf **jede einzelne Chat-Nachricht**, bevor
überhaupt RAG-Suchergebnisse oder Kunden-Kontext dazukommen. Davon allein
`vault_tree()` ~41.700 Zeichen (~10.400 Tokens, 69% des gesamten
Basis-Prompts) — eine Tiefe-3-Ordnerauflistung des **kompletten Repos**,
inklusive App-Code (`backend/`, `frontend/`, `services/`, `mcp-vnc/`) und
`_agent/`-internen Dateien wie `drive_token.json`, `gmail_token.json`,
`ms_token_cache.bin` (nur Dateinamen, keine Inhalte, aber unnötig in jedem
Modell-Aufruf sichtbar). Genau das „Context Stuffing", vor dem Video 1 warnt.

**Fix (umgesetzt und verifiziert):** `_SKIP_TREE` in `context.py` um
App-Code-/interne Verzeichnisse erweitert (`_agent`, `_inbox`, `backend`,
`frontend`, `services`, `mcp-vnc`, `_fehler`, `.claude`, `.venv` — angelehnt
an das bereits bestehende `_SKIP`-Set in `files.py`), `vault_tree()`
Standardtiefe von 3 auf 2 reduziert. Kein Funktionsverlust: `_agent/`s
Inhalte (Profil, Kontext, Gedächtnis) werden bereits als eigene,
gelabelte Abschnitte direkt aus den Dateien eingelesen — die Baumdarstellung
diente nur der groben Orientierung, und für gezieltes Nachschauen existiert
bereits das `vault_list`-Tool, das Claude bei Bedarf selbst aufrufen kann
(agentisches Nachladen statt alles vorab hineinzustopfen — genau das Muster,
das Video 1 empfiehlt). Gemessen nach dem Fix: `vault_tree()` jetzt ~6.200
Zeichen (~1.550 Tokens, −85%), `build_system()` insgesamt ~25.100 Zeichen
(~6.270 Tokens, −58%). Alle übrigen Abschnitte (Profil, Aufgaben, Gedächtnis,
Kalender, Gmail, LinkedIn) unverändert vorhanden, per Regressionscheck
bestätigt.

**Intelligentere Modellauswahl — umgesetzt und verifiziert (2026-07-17).**
Sebastian hat sich für automatisches Routing entschieden. `chat.py` leitet
jetzt kurze, nicht-komplexe Anfragen (< 80 Zeichen, keine der
`COMPLEX_KEYWORDS`) automatisch an `claude-haiku-4-5-20251001` weiter statt
immer Sonnet zu nutzen — deutlich günstiger ($1/$5 pro 1M Tokens vs. Sonnets
$3/$15). Bewusst konservativ: eine explizite Opus-Wahl (Nutzer oder Agent mit
fester Modellwahl) wird **nie** überschrieben, nur der Sonnet-Default-Fall
wird für kurze Anfragen ersetzt. Frontend zeigt "Haiku (automatisch)" im
Modell-Dropdown an, wenn eine Session so geroutet wurde — kein eigener
manuell wählbarer Menüpunkt, da die Weiterleitung automatisch passiert.

**Verifiziert** mit 5 Testfällen (gemockter Anthropic-Client): kurze Frage +
Standard-Sonnet → Haiku; kurze Frage + explizit gewähltes Opus → bleibt Opus;
lange/komplexe Frage → bleibt Sonnet; Agent mit fest eingestelltem Opus →
bleibt Opus, auch bei kurzer Frage; Agent ohne feste Modellwahl → Auto-Routing
greift trotzdem. Alle fünf Fälle bestanden.

## Randnotiz (kein Task, nur Beobachtung — siehe Nachtrag oben, größtenteils behoben)

`context.build_system()` (`context.py:141-227`) baut auf **jede** Chat-Anfrage
das komplette Profil, Kontext, Gedächtnis, Vault-Baum, Konversationslog,
Kalender, Gmail und LinkedIn-Status in den System-Prompt — genau das
„Context Stuffing", vor dem Video 1 warnt (funktioniert gut bei aktueller
Vault-Größe, wird aber irgendwann teuer/langsam, wenn der Vault deutlich
wächst). Kein akuter Handlungsbedarf, aber ein guter Kandidat für eine
spätere „Space"-basierte Kontext-Auswahl (siehe D3), falls die Antwortzeiten
spürbar leiden.
