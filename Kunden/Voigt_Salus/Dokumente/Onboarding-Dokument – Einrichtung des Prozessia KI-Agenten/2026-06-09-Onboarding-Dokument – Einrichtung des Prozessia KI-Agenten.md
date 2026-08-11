---
tags:
  - Onboarding
  - KI-Agent
  - Azure OpenAI
  - Kanzlei
  - Einrichtung
quelle: Onboarding-Dokument – Einrichtung des Prozessia KI-Agenten.docx
datum: 2026-06-09
kategorie: Kunde
---

# Onboarding-Dokument – Einrichtung des Prozessia KI-Agenten

Technisches Onboarding-Dokument für die Einrichtung des Prozessia KI-Agenten bei der Kanzlei Voigt Salus. Es beschreibt schrittweise die Server-Bereitstellung, Azure OpenAI-Einrichtung, Verbindung von Dokumentenquellen sowie die Konfiguration abteilungsbezogener KI-Modelle und Workflows. Datenschutz und Datenhoheit des Kunden stehen dabei im Mittelpunkt.

## Vollständiger Inhalt
Onboarding-Dokument – Einrichtung des Prozessia KI-Agenten KI-gestützte Automatisierung für Kanzleien Dieses Dokument beschreibt den Ablauf zur technischen Einrichtung Ihres Prozessia KI-Agenten.
 Der Prozess ist so aufgebaut, dass Sie jederzeit die vollständige Kontrolle über Ihre Daten behalten.  1. Bereitstellung des Servers (VPS) Für den Betrieb des Prozessia KI-Agenten benötigen wir Zugang zu einem von Ihnen bereitgestellten Server (VPS). Auf diesem Server installieren und konfigurieren wir: alle technischen Komponenten des Prozessia KI-Agenten
 die Automatisierungsplattform
 die Vektordatenbank
 die RAG-Struktur
 alle benötigten Schnittstellen und Module
 Der Server wird so eingerichtet, dass: wir ausschließlich im technischen Bereich arbeiten
 der Datenbereich der Kanzlei vollständig unter Ihrer Kontrolle bleibt
 wir keine Einsicht in Kanzleidokumente oder Mandantendaten haben
 Damit bleibt die Datenhoheit jederzeit bei Ihnen.  2. Einrichtung von Azure OpenAI Der Prozessia KI-Agent nutzt ein EU-gehostetes Azure-Modell (z. B. GPT-4.1 Mini). Die Einrichtung erfolgt durch Sie, wir führen Sie per Online-Meeting durch: Erstellen der Azure OpenAI-Ressource
 Auswahl und Deployment des Sprachmodells
 Aktivierung der EU Data Boundary
 Erstellen der API-Schlüssel
 Einfügen der Schlüssel in das System Einfügen der Schlüssel im Server für den Microsoft Login
 Die Azure-Zugänge bleiben vollständig in Ihrer Hand;
 wir erhalten keinen Zugang zu Ihrer Microsoft-Organisation.  3. Verbindung Ihrer Dokumentenquellen Damit der Prozessia KI-Agent Ihre kanzleiinternen Dokumente nutzen kann, verbinden Sie selbst Ihre Datenquellen, z. B.: SharePoint
 OneDrive
 Google Drive
 Nextcloud
 interne Ordnerstrukturen
 Die Verbindung erfolgt über vorbereitete Authentifizierungsfenster: Sie melden sich mit Ihren eigenen Kanzleizugangsdaten an
 wir sehen weder Passwörter noch Dokumente
 der Agent erhält Zugriff ausschließlich über die von Ihnen gesetzte Verbindung
 Damit ist sichergestellt, dass sämtliche Daten durchgehend unter Ihrer Kontrolle bleiben.  4. Einrichtung abteilungsbezogener KI-Modelle & Workflows Nach dem Verbinden der Dokumentenquellen richten wir alle module, Modelle und Workflows des Prozessia KI-Agenten ein – ohne Zugriff auf Dokumentinhalte. Beispiele: Gutachten-Assistent: Zugriff auf die von Ihnen definierten Gutachten-Ordner
 Sekretariats-Assistent: Zugriff auf Vorlagen, Schriftverkehr, Standarddokumente
 Fachbereichs-Assistenten: z. B. Steuerrecht, Arbeitsrecht, Zivilrecht
 Interne Wissensdatenbank: Zugriff auf definierte Fachbibliotheken
 Wir nutzen für die Einrichtung: die bereits von Ihnen verbundenen Datenquellen
 Ordnernamen, Pfade oder IDs, die Sie bereitstellen
 keinerlei Einsicht in die tatsächlichen Dokumente
   5. Abschluss & Übergabe Nach Abschluss der technischen Einrichtung: ist der Prozessia KI-Agent vollständig betriebsbereit
 alle abteilungsspezifischen Modelle sind eingerichtet
 alle Workflows sind konfiguriert
 alle Datenquellen sind
