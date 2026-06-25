---
tags:
  - Twilio
  - Anruftransfer
  - Warm-Transfer
  - Vapi
  - Telefonie
quelle: Dokumentation Twilio Anruftransfer.docx
datum: 2026-06-09
kategorie: Produkt
---

# Dokumentation Twilio Anruftransfer

Technische Dokumentation eines Twilio-basierten Warm-Transfer-Systems für eingehende Anrufe, entwickelt im Twilio-Projekt 'vapi-xfer-ie1' (Irland). Beschreibt den Ablauf mit Konferenzparken, Whisper-Ansage und Zielperson-Akzeptanz/Ablehnung über zwei Twilio Functions (/transfer und /warm_accept). Enthält alle erforderlichen Umgebungsvariablen für die Konfiguration.

## Vollständiger Inhalt
  Develop->Ireland (IE1)-> Functions and Assets-> Services -> vapi-xfer-ie1   Eingehende Anrufe werden immer als Warm-Transfer behandelt: Kunde wird kurz geparkt (Konferenz/Hold). Zielperson (feste Nummer) erhält einen Whisper („Ein Kunde wartet… Drücken Sie 1 zum Übernehmen, 2 zum Ablehnen“). 1 → Zielperson tritt bei, beide sind verbunden. 2 → Kunde hört: „Der gewünschte Ansprechpartner steht derzeit nicht zur Verfügung. Vielen Dank für Ihren Anruf.”, dann Auflegen. Bausteine Twilio Function /transfer (PUBLIC, mit Bearer) Einstiegspunkt für Vapi-Tool transfer_call. Erkennt den laufenden Customer-Call (CallSid CA…). Legt Konferenz conf_<CA…> an und parkt den Kunden dort. Ruft die feste Zielnummer mit Whisper & <Gather> an. action des Gather zeigt auf /warm_accept?conf=conf_<CA…>. Twilio Function /warm_accept (PUBLIC, ohne Bearer) Wird aufgerufen, wenn Zielperson 1 oder 2 drückt. 1 → Zielperson tritt der Konferenz conf_<CA…> bei (Verbindung). 2 → extrahiert CA… aus conf_<CA…> und updated den Kunden-Call mit der „nicht verfügbar“-Ansage + Auflegen. Verbindliche Umgebungsvariablen  Pflicht: ACCOUNT_ID → Twilio Account SID (AC…) TWILIO_API_KEY_SID → IE1 API Key SID (SK… aus Irland) TWILIO_API_KEY_SECRET → Secret zu obigem Key DEFAULT_TO → feste Zielnummer (Zielperson), E.164 (z. B. +49…) DEFAULT_CALLER_ID → eure Twilio-Absendernummer, E.164 (z. B. +353…) VAPI_BEARER → Secret, das Vapi im Header mitschickt WARM_MODE → true (Warm-Transfer ist Pflicht) 
