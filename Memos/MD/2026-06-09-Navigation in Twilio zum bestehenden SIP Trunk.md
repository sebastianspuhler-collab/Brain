---
tags:
  - Twilio
  - SIP Trunk
  - Fonio
  - Telefonie
  - Konfiguration
quelle: Navigation in Twilio zum bestehenden SIP Trunk.docx
datum: 2026-06-09
kategorie: Memo
---

# Navigation in Twilio zum bestehenden SIP Trunk

Das Dokument beschreibt die Navigation und Konfiguration eines bestehenden SIP Trunks in Twilio für die Anbindung an Fonio. Es enthält Schritt-für-Schritt-Anleitungen zu den relevanten Einstellungen wie Origination, Termination, Credentials und Phone Numbers. Zusätzlich werden grundlegende Fonio-Konfigurationsschritte wie Assistentenzuweisung, Tools und Outbound-Anleitung erläutert.

## Vollständiger Inhalt
Navigation in Twilio zum bestehenden SIP Trunk  Ireland(IE1) -> Elastic SIP Trunking -> Manage -> Trunks -> Fonio_Agent  (Sie befinden sich jetzt in den Detail-Einstellungen dieses Trunks.  2. Übersicht: Relevante Einstellungen für Fonio Im Trunk sind hauptsächlich diese Bereiche wichtig: 2.1 Allgemeine Einstellungen / General SIP REFER: aktiviert PSTN Transfer: aktiviert    2.2 Origination (eingehende Anrufe → Fonio) Tab Origination öffnen Dort sollte eine Origination URI hinterlegt sein: sip:vojhwtf1hn6.eu.sip.livekit.cloud;edge=frankfurt;transport=tcp Diese sorgt dafür, dass Twilio eingehende Anrufe an Fonio weiterleitet.    2.3 Phone Numbers (zugeordnete Telefonnummern) Tab Phone Numbers öffnen Hier sehen Sie alle Rufnummern, die mit diesem Trunk verbunden sind. Wichtig: Die Nummer, die in Fonio verwendet werden soll, muss hier aufgeführt sein.   2.4 Termination (optional, für ausgehende Anrufe) Tab Termination öffnen Termination SIP URI: Name/URL, die später in Fonio als „Termination“ genutzt wird Darunter: Verknüpfte Credential List (Zugangsdaten) prüfen   2.5 Credentials (Benutzername/Passwort) Unter Credential List (entweder direkt im Trunk oder über den jeweiligen Link): Username und Passwort notieren Diese Daten werden in Fonio bei der Nummer-Konfiguration eingetragen (sofern ausgehende Anrufe genutzt werden).                 2.6 Fonio In Fonio: Telefonnummer -> SIP Nummer bearbeiten/hinzufügen. Twilionummer, Credentials und Termination URL hier eintragen.   2.7 weitere Infos in Fonio:  Assistent zuweisen: Telefonnummern -> Telefonnummer auswählen  -> Assistentzuweisung ändern Tools: Assistenten -> Assistent auswählen -> Tools Transkript einstellen -> Assistenten -> Assistent auswählen -> Nachbearbeitung Outboundanleitung: Assistent -> Outbound 
