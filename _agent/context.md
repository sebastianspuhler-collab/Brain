---
updated: 2026-08-17
---

# Aktueller Kontext

## Offene Aufgaben (Woche ab 17.08.2026)
- [ ] Beschaffungsagent überwachen @Amin
- [ ] YouTube: 3 Videos diese Woche erstellen/veröffentlichen @Amin
- [ ] Webseite überarbeiten @Amin
- [ ] Stücklistenkonzept ausarbeiten @Amin @Sebastian
- [ ] LinkedIn: 3 Posts diese Woche @Sebastian
- [ ] Angebot TopDown fertigstellen (Kontierung/Verbuchung ergänzen, siehe Follow-up 14.08.) @Sebastian
- [ ] Close + Twilio verbinden @Sebastian
- [ ] Aufträge vorantreiben @Sebastian
- [ ] Netzwerkausbau fortsetzen @Sebastian

## Erledigt (Woche bis 16.08.2026)
- [x] LinkedIn: 3 Videos posten @Sebastian
- [x] YouTube: 3 Videos erstellen/veröffentlichen @Amin
- [x] Beschaffungsagent überwachen und Bericht für Schaufler vorbereiten @Amin
- [x] Webseite fertigstellen @Amin
- [x] Whitepapers fertigstellen @Amin
- [x] Close-Migration weiterführen @Sebastian
- [x] Kevin (neuer Vertriebler) einarbeiten/einführen @Sebastian
- [x] Netzwerkaufbau und Terminsuche fortsetzen @Sebastian

## Laufende Projekte
- Schaufler Tooling: Beschaffungsagent live (220€/Mon). Nächster Schritt: Lexoffice-Angebot
- Mundinger: KI-Schulung EU AI Act — Termin 29.6.
- Webinar: Vorbereitung bis 5. Juli
- Juchem: Folgetermin 29.07. (14-17 Uhr) mit Thorsten Maas – kompletter Beschaffungsprozess besprochen, siehe Kunden/Juchem/Meetings/2026-07-29-Update Juchem X Prozessia.md. Nächster Schritt: Angebot erstellen

## Notizen
- **12.08.2026, Sebastian:** "das System muss beim nächsten Mal besser abgestimmt werden, es war lange nicht so gut wie gedacht." Grund: an einem Tag mehrere unabhängige, teils schon länger bestehende Lücken gefunden (siehe unten) - nicht durch aktives Testen, sondern weil Sebastian im Alltag draufgestoßen ist. Für die nächste Session: eher eine gezielte Durchsicht der Kernpfade (Buffer-Sync, Git-Sync, Karussell-Pipeline) statt nur auf einzelne Beschwerden zu reagieren.
- **Am 12.08.2026 behoben:**
  - Git-Sync Mac↔VPS war seit dem 04.08. faktisch tot (Ordering-Bug: pull vor lokalem commit) - 82 unpushte VPS-Commits nachgeholt, Reihenfolge in beiden Sync-Skripten gefixt, Fehler jetzt sichtbar statt verschluckt.
  - list_posts zeigte nur lokal generierte Posts, keine direkt in Buffer angelegten Drafts - jetzt live gemischt.
  - Ein Buffer-Karussell-Draft wurde beim "Text überarbeiten" per delete+write_post versehentlich durch einen reinen Text-Post ersetzt (PDF ging verloren, nicht wiederherstellbar) - list_posts erkennt Karussell-Anhänge jetzt und warnt davor.
  - Text-Posts konnten nicht als Buffer-Entwurf gepusht werden (nur Karusselle) - neues draft_post-Tool ergänzt.
  - schedule_post/draft_post meldeten vollen Erfolg, auch wenn nur einer von zwei Kanälen klappte - jetzt sichtbar als Teilerfolg markiert.
- **Noch nicht geprüft / mögliche weitere Baustellen (nächste Session anschauen):** Karussell-Hashtags werden vom Content-Engine unabhängig von der gewählten Themen-Säule generiert (bei „Wissensmanagement“-Post kamen z.B. #Beschaffung #Werkzeugbau-Tags); ob die 6 zuvor versehentlich scheduled statt draft gepushten Text-Posts von Sebastian selbst korrigiert wurden, ist offen.
- **13.08.2026, LinkedIn-Agent-Umbau (Ideen/Entwürfe/Geplant, Karussell als Standard):**
  Sebastian wollte drei klare Stufen statt der alten Vermischung: Ideen (Ideengenerator-Output) →
  Entwürfe (= echte Buffer-Drafts) → Geplant (= Buffer-Queue), Karusselle-Tab weg (läuft als normale
  Post-Karte mit), und ab jetzt Karussell als Standardformat für fast jeden Post, alles im Chat
  steuerbar (Idee→Post→Planen). Umgesetzt und auf brain-vps deployed (docker compose build+up
  backend+web, 13.08.2026 ~13:20):
  - write_post/make_carousel pushen neue Posts jetzt SOFORT als echten Buffer-Entwurf (status draft),
    nicht erst nach zweitem Tool-Call. make_carousel ist jetzt der vom System-Prompt bevorzugte Weg
    (nicht mehr write_post), generate_ideas markiert jetzt mind. 8/10 Ideen als "Karussell".
  - Kritischer Duplikat-Bug gefixt: schedule_post/push_latest_to_buffer legten bei einem bereits
    gedrafteten Post bisher einen ZWEITEN Buffer-Post an, statt den Entwurf umzuschalten - betraf auch
    den auf dem VPS tatsächlich aktiven CLAUDE_ENGINE=cli-Pfad (mcp_server.py), nicht nur die
    API-Chat-Variante. Jetzt promote-statt-duplizieren via neuer _promote_buffer_posts()
    (EditPostInput.saveToDraft live per Introspection verifiziert). Neues Tool schedule_buffer_post für
    Posts ohne lokale id (Karusselle, direkt in Buffer angelegte Drafts).
  - Karussell-Buffer-Post-IDs werden jetzt in karusselle.json gespeichert (vorher nicht) - dadurch
    kann list_posts/das Dashboard Thumbnail+PDF direkt einem Live-Buffer-Post zuordnen.
  - delete_post hat jetzt ein echtes Code-Gate (nicht nur Prompt-Warnung): Löschen eines
    Karussell-Posts schlägt ohne confirm=true ab.
  - Fake-Status "gesendet"/"offen" für unbekannte lokale Posts entfernt (kollidierte mit dem echten
    Buffer-Status "sent") - neue, eindeutige Labels lokal_ungeplant/lokal_verwaist.
  - Frontend (LinkedInPage.tsx): 3 Tabs Ideen/Entwürfe/Geplant, beide Buffer-Tabs ziehen jetzt den
    echten Live-Status über GET /api/linkedin/posts?status=draft|scheduled (neu, Backend:
    get_merged_posts_by_status), Karussell-Thumbnail direkt in der Post-Karte.
  - Root-CLAUDE.md's `_agent/buffer_manager.py`-CLI-Weg (für MICH, Claude Code, außerhalb der
    Web-App) wurde NICHT angefasst - der kann bei "als Entwurf pushen" weiterhin nicht draften
    (kein saveToDraft-Support in cmd_push), das ist eine separate, ältere Schiene und noch offen.
