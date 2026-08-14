---
tags: [Meeting, TopDown, Beschaffungsagent, Rechnungsverarbeitung, Schnittstellen]
quelle: Prozessia X TopDown (1).docx
datum: 2026-08-14
kategorie: Kunde
---

# Prozessia X TopDown – Follow-up Angebotsdurchsprache

Meeting am 14.08.2026, 08:02 Uhr, zwischen Sebastian Spuhler und Dominik Nussbaumer (TopDown).
Follow-up zum Termin vom Dienstag (11.08.), bei dem Sebastian die Präsentation/das Angebot verschickt
hatte. Dominik hatte die Präsentation erhalten und intern kurz vorgestellt.

## Wichtigster fachlicher Nachtrag (fehlte in der Präsentation)
- **Kontierung/Verbuchung der Belege** muss Teil des Agenten-Scopes sein: Der Agent soll auf Basis
  der Rechnung einen Buchungsvorschlag machen, sodass der fertig verbuchte Beleg an den Steuerberater
  geht – nicht nur Erkennung/Prüfung.
- Offene Frage von Dominik: An welcher Stelle im Freigabeprozess soll das passieren – vor ERP-Übertragung,
  nach Freigabe, oder schon in der Vorprüfung?
- **Sebastians Empfehlung:** Integration in den bestehenden Freigabeprozess, parallel zur Freigabe durch
  den Projektleiter, vor der Übertragung nach DATEV. Sehr individuell je nach Unternehmensstruktur
  (bei manchen Kunden muss jede Rechnung über den Geschäftsführer, bei anderen läuft es lockerer).

## Schnittstellen (3 identifiziert)
1. **E-Mail-Postfach (Outlook):** unkompliziert, läuft über Microsoft Graph API – Standardprozess bei
   jedem Kunden, TopDown braucht nur einen IT-Ansprechpartner zum Einrichten.
2. **DATEV:** technisch unkompliziert (offene, gängige Schnittstelle), aber für TopDown inhaltlich noch
   Neuland – Umstellung läuft gerade, Abstimmung mit dem Steuerberater zur Kontenübereinstimmung nötig.
   Laut Sebastian unkritisch fürs Projekt, da DATEV der letzte Schritt ist (reiner Übertrag, keine KI-Logik
   mehr) – Verzögerungen dort blockieren das Projekt kaum.
3. **ERP-System "Club Manager" (Club Systems):** die wichtigste und komplexeste Schnittstelle, weil
   zentral im Prozess. Sebastian hat sich das System vorab angeschaut – laut Webseite offene Schnittstellen
   vorhanden. Benötigt wird eine API (POST/GET) zum Lesen und Schreiben von Daten. TopDown hat bereits
   kurz mit ihrem Partner gesprochen – Lösung würde vermutlich über Workflows im ERP laufen; offen ist
   noch, welche Zugänge/Schlüssel genau nötig sind und wer bei TopDown dafür Ansprechpartner ist.

## Infrastruktur
- **Server:** Hetzner (Empfehlung von Sebastian, bereits beim Erstgespräch besprochen) – zwei Optionen,
  finanziell gleichwertig: Prozessia kauft und stellt den Server (dann als offizieller Auftragsverarbeiter,
  Kosten werden weitergegeben) oder TopDown beschafft ihn selbst und gibt Prozessia Zugriff.
- **Sprachmodell:** läuft über Microsoft Azure (OpenAI/Anthropic-Modelle), isoliert auf Servern in
  Frankfurt, verschlüsselt. Da TopDown ohnehin Outlook/Microsoft nutzt, besteht der nötige AVV mit
  Microsoft bereits – kein zusätzlicher Vertrag nötig. Eigenes Hosting des Modells wäre 2026 hardware-
  seitig nicht wirtschaftlich.

## Offene Punkte von TopDown-Seite (Dominiks Fragen)
- Was muss TopDown an Infrastruktur/Schnittstellen bereitstellen – mit ihrem (IT-)Partner parallel
  abstimmen.
- Welche Leistungen bringt Prozessia konkret mit, mit welchem Budget ist zu rechnen – muss TopDown
  intern mit weiteren Partnern abstimmen.
- Ansprechpartner bei TopDown für Club Manager/ERP sowie für DATEV/Steuerberater sind noch zu klären.

## Status
Transkript-Ausschnitt endet mitten im Gespräch (Thema Sprachmodell/Deployment) – ggf. lief das Meeting
danach noch weiter, das ist im vorliegenden Anhang nicht mehr enthalten.

Nächster bekannter Termin: **08.09.2026, 13:00 Uhr – "Angebotsdurchsprache Prozessia X TopDown"** (Teams).
