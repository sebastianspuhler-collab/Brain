---
tags:
  - Angebotsargumentation
  - Scope
  - Messberichte
  - MSSQL-Anbindung
  - Preisargumentation
quelle: messberichte-angebot-argumentation.pdf
datum: 2026-06-25
kategorie: Sales
---

# messberichte-angebot-argumentation

Das Dokument enthält interne Argumentationsunterlagen für Kundengespräche zu zwei Themen: Begründung, warum Messberichte aus dem Projektscope ausgenommen werden sollten (heterogene Kanäle, 2FA, ZIP-Strukturen, Nutzen-Risiko-Verhältnis), sowie eine Preisargumentation für die WinForm-/MSSQL-Anbindung (keine Standard-API, hoher Testaufwand, Sicherheitsanforderungen). Es handelt sich um ein Vertriebsdokument zur Angebotsverteidigung und Scopeabgrenzung.

## Vollständiger Inhalt
Argumentation Messberichte und Angebot
Gründe, warum Messberichte aus dem Scope herausgenom-
men werden sollten
• Heterogene Eingangskanäle:  Die Messberichte kommen über unterschiedliche 
Kanäle wie OneDrive, WeTransfer, Lieferantenportale oder Retransfer. Dadurch 
gibt es keinen einheitlichen, stabil automatisierbaren Prozess.
• 2FA-Authentifizierung:  Bei mehreren Lieferanten ist eine zusätzliche Au-
thentifizierung erforderlich. Diese lässt sich nicht sinnvoll ohne zusätzlichen 
RPA-Aufwand automatisieren, was den Rahmen unverhältnismäßig erweitern 
würde.
• ZIP-Dateien mit unbekannter Ordnerstruktur:  Die Inhalte werden je nach Liefer-
ant unterschiedlich verpackt. Der Agent kann nicht zuverlässig erkennen, wo das 
eigentliche Messprotokoll liegt. Das erhöht die Fehleranfälligkeit deutlich.
• Große Dateimengen inklusive Scandaten:  Neben den Messprotokollen werden 
oft umfangreiche Scandaten mitgeliefert, die vom Agenten ohnehin nicht fachlich 
geprüft werden. Das verursacht nur zusätzlichen technischen Overhead ohne 
echten Mehrwert.
• Change Management / Prozesssicherheit:  Eine Hybrid-Lösung, bei der der 
Agent den Prozess nur in manchen Fällen übernehmen kann, schafft Unsicherheit 
bei den Mitarbeitenden. Es wäre nicht klar, wann der Automatismus greift und wann 
manuell eingegriffen werden muss.
• Unverhältnismäßiges Nutzen-Risiko-Verhältnis:  Der technische Aufwand und 
die Fehleranfälligkeit stehen in keinem sinnvollen Verhältnis zum Nutzen. Gerade 
bei qualitätsrelevanten Dokumenten ist ein robuster, klarer Prozess wichtiger als 
eine nur teilweise funktionierende Automatisierung.
Fazit
Die Verarbeitung von Messberichten sollte vollständig aus dem Scope herausgenom-
men werden. Die Rahmenbedingungen sind zu heterogen, zu fehleranfällig und tech-
nisch zu aufwendig, um hierfür eine verlässliche und wirtschaftliche Lösung im ak-
tuellen Projektkontext bereitzustellen.
Argumente, warum das Angebot für die Win-
Form-/MSSQL-Anbindung entsprechend bepreist ist
•  Keine Standard-API-Anbindung:  Die Anbindung erfolgt nicht über eine klas-
sische, standardisierte API, sondern direkt an einen Microsoft SQL Server. Das 
erfordert eine individuellere technische Umsetzung.
• Individuelle Funktionslogik:  Der Agent muss verschiedene Funktionen speziell 
für diese Umgebung abbilden, zum Beispiel Daten lesen, Status prüfen, Einträge 
schreiben und Felder korrekt auswerten.
• Hoher Testaufwand:  Ein wesentlicher Teil des Aufwands entsteht durch das 
Testen. Gerade bei Datenbankanbindungen muss sichergestellt werden, dass 
Lesen, Schreiben, Statuslogik und Taktung zuverlässig funktionieren.
• Abhängigkeiten zu bestehenden Agentenfunktionen:  Neue Funktionen 
müssen so integriert werden, dass bestehende Abläufe weiterhin stabil funktion-
ieren. Auch diese Prüfung erzeugt zusätzlichen Aufwand.
• Technische Sicherheitsanforderungen:  Die Kommunikation zwischen 
Cloud-Umgebung und internem Server muss sicher umgesetzt werden. Das erhöht 
die Komplexität g
