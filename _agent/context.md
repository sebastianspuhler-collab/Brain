---
updated: 2026-08-12
---

# Aktueller Kontext

## Offene Aufgaben
- [ ] LinkedIn: 3 Videos diese Woche posten @Sebastian !status(in_progress)
- [ ] YouTube: 3 Videos diese Woche erstellen/veröffentlichen @Amin !status(in_progress)
- [ ] Termin mit Schaufler wegen Stücklistenprojekt vereinbaren (Anschluss an Lastenheft v. 05.08., Angebot/nächste Schritte) @Beide
- [x] Beschaffungsagent überwachen und Bericht für Schaufler vorbereiten @Amin !status(in_progress)
- [ ] Webseite fertigstellen @Amin !status(in_progress)
- [x] Whitepapers fertigstellen @Amin !status(in_progress)
- [ ] Close-Migration weiterführen @Sebastian
- [ ] Kevin (neuer Vertriebler) einarbeiten/einführen @Sebastian
- [ ] Netzwerkaufbau und Terminsuche fortsetzen @Sebastian

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
- **Noch nicht geprüft / mögliche weitere Baustellen (nächste Session anschauen):** MAX_LINKEDIN_CHAT_ITERATIONS=6 könnte bei größeren Batch-Aktionen (z.B. "generiere 9 Posts") zu knapp sein; Karussell-Hashtags werden vom Content-Engine unabhängig von der gewählten Themen-Säule generiert (bei „Wissensmanagement“-Post kamen z.B. #Beschaffung #Werkzeugbau-Tags); ob die 6 zuvor versehentlich scheduled statt draft gepushten Text-Posts von Sebastian selbst korrigiert wurden, ist offen.
