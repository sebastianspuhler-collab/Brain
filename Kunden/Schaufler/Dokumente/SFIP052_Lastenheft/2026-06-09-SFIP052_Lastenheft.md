---
tags:
  - Lastenheft
  - Lieferterminverfolgung
  - Beschaffungsagent
  - KI-Automatisierung
  - Einkauf
quelle: SFIP052_Lastenheft.pdf
datum: 2026-06-09
kategorie: Kunde
---

# SFIP052_Lastenheft

Lastenheft für ein KI-gestütztes System zur automatisierten Lieferterminverfolgung und Versandabwicklung beim Kunden Schaufler. Es definiert funktionale Anforderungen für die Verarbeitung von Auftragsbestätigungen, Messberichten und Eskalationslogik im Einkaufsprozess. Das System soll manuelle Aufwände reduzieren und eine durchgängige digitale Prozesskette von der Bestellung bis zur Anlieferung ermöglichen.

## Vollständiger Inhalt
 
Lastenheft  
KI-gestützte Lieferterminverfolgung und Versandabwicklung  
 
1. Zielsetzung  
Ziel dieses Lastenhefts ist die Definition der fachlichen und funktionalen Anforderungen 
an ein KI -gestütztes System zur automatisierten Lieferterminverfolgung, 
Dokumentenverarbeitung und Eskalation im Einkauf.  
Das System soll manuelle Aufwände reduzieren, Transparenz über Liefertermine 
schaffen, Risiken frühzeitig erkennen und eine durchgängige digitale Prozesskette von 
der Bestellung bis zur Anlieferung ermöglichen.  
 
2. Geltungsbereich  
Der Prozess gilt für alle beschafften Materialien und Dienstleistungen mit 
Lieferterminrelevanz, insbesondere:  
• Zukaufteile  
• Rohmaterial  
• Lohnfertigung  
• Internationale Lieferungen inkl. Zollabwicklung  
 
3. Prozessübersicht (Soll -Prozess)  
1. Bestellung wird im ERP -System ausgelöst  
2. Automatisierte Lieferterminverfolgung entlang definierter Events  
3. Dokumentenbasierte KI -Auswertung  
4. Regelbasierte Eskalation an den Einkauf  
5. Abschluss mit Anlieferung der Ware  
 
4. Funktionale Anforderungen  
4.0 Eskalations - und Toleranzlogik (übergreifend)  
Toleranzen  
• Terminabweichung: > +5 Kalendertage  
• Preisabweichung: ≠ 0 %  (jede Abweichung)  
• Mengenabweichung: ≠ 0 (jede Abweichung)  
Eskalationsmechanismus  
• Automatische Benachrichtigung per E -Mail an den zuständigen Einkäufer  
• Zusätzlich automatische Erstellung eines System -Tasks  (To-do / Workflow -
Aufgabe)  
• Statuskennzeichnung der Bestellung (Ampellogik, siehe Kapitel 5.4)  
   
2 / 5 4. Funktionale Anforderungen  
4.1 Auftragsbestätigung (AB)  
Eingang & Monitoring  
• Es wird die zentrale E -Mail-Adresse Order@schaufler.de  verwendet  
• Das Postfach wird stündlich automatisiert überwacht  
Automatische Verarbeitung  
• Eingehende Auftragsbestätigungen werden automatisiert ins System 
übernommen  
• Unterstützte Formate: PDF, E -Mail -Text, gängige Office -Formate  
KI-gestützte Attributprüfung  
Die Auftragsbestätigung wird automatisch auf folgende Attribute geprüft:  
• Liefertermin  
• Position(en)  
• Menge  
• Preis  
• Incoterm  
• Zahlungsbedingungen  
Abgleich & Bewertung  
• Abgleich mit den Bestelldaten aus dem ERP -System  
• Automatische Kennzeichnung von Abweichungen  
• Regelbasierte Eskalation bei Abweichungen an den zuständigen Einkäufer  
 
4.2 Messberichte  
Eingang  
• Messberichte gehen ebenfalls an Order@schaufler.de  
Automatische Weiterleitung & Ablage  
• Automatische Weiterleitung an Quality@schaufler.de  (Messraum)  
• Parallele systemseitige Ablage:  
o Zuordnung zur jeweiligen Bestellung  
o Zuordnung zur konkreten Stücklistenposition  
Vollständigkeitsprüfung  
• KI-gestützte Prüfung der Messberichte auf Vollständigkeit in Bezug auf:  
o Bestellung  
o Bestellposition(en)  
o Geforderte Merkmale  
• Bei nicht vollständigen Messberichten : 
o Automatische Information per E -Mail an den zuständigen Einkäufer  
o Erstellung eines System -Tasks    
3 / 5 Funktionaler Nutzen  
• Frühzeiti
