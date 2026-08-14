---
tags:
  - Schaufler
  - Lastenheft
  - Stücklistenagent
  - Anforderungsdokument
  - MVP
quelle: 19fd0e772e-KI-gestützte Stücklistendatenerfassung_Lastenheft.pdf
datum: 2026-08-05
kategorie: Kunde
firma: Schaufler
---

# 19fd0e772e-KI-gestützte Stücklistendatenerfassung_Lastenheft

## Zusammenfassung
Lastenheft für die KI-gestützte Stücklistendatenerfassung bei Schaufler Tooling GmbH & Co. KG, verfasst von Marvin Wiegner am 05.08.2026. Beschreibt Zweck, Ausgangssituation, Geltungsbereich (inkl. MVP-Abgrenzung), Projektstruktur, Benutzer-/Berechtigungskonzept, Datenintegration, Sollprozess, Statusmodell, Arbeitsoberfläche sowie funktionale Anforderungen und Datenmodell für das Stücklistenprojekt.

## Vollständiger Inhalt
 
   
KI-gestützte Stücklistendatenerfassung  
Lastenheft  
Datum:  05.08.2026  
Verfasser:  Marvin Wiegner    
II 
 
Inhal t  
1 Schaufler Tooling GmbH & Co. KG  ................................ ................................ ...........................  1 
2 Zweck und Zielsetzung  ................................ ................................ ................................ ............  2 
3 Ausgangssituation und Problemstellung  ................................ ................................ .................  3 
4 Geltungsbereich und Abgrenzung  ................................ ................................ ...........................  4 
4.1 Im Geltungsbereich  ................................ ................................ ................................ ........  4 
4.2 Nicht im MVP  ................................ ................................ ................................ .................  4 
5 Systemkontext und Projektstruktur ................................ ................................ .........................  5 
5.1 Anforderungen an die Projektverwaltung  ................................ ................................ ...... 5 
5.2 Projektstruktur  ................................ ................................ ................................ ...............  5 
6 Benutzer - und Berechtigungskonzept  ................................ ................................ .....................  6 
7 Datenintegration und Ablagekonzept ................................ ................................ ......................  7 
7.1 Grundsätze der Datenintegration ................................ ................................ ...................  7 
7.2 Ziel der Integrationslogik ................................ ................................ ................................  7 
8 Sollprozess  ................................ ................................ ................................ ..............................  8 
9 Statusmodell  ................................ ................................ ................................ ...........................  9 
10 Arbeitsoberfläche  ................................ ................................ ................................ .............  10 
10.1 Grundlayout (Ein -Fenster -Konfiguration)  ................................ ................................ ..... 10 
10.2 Funktionale Anforderungen an die Oberfläche  ................................ ............................  11 
10.3 Erwartetes Bedienmuster  ................................ ................................ ............................  11 
11 Funktionale Anforderungen  ................................ ................................ .............................  13 
12 Datenmodell und interne Stücklistenattribute  ................................ ................................ . 15 
13 Konfliktmanagement  ................................ ................................ ................................ ........  17 
14 Regelverwaltung und Lernlogik  ................................ ................................ ........................  18 
15 Kollaboration und Übergabe  ................................ ................................ ............................  19 
16 Export und CadCam -Anbindung  ................................ ................................ .......................  20 
17 Nichtfunktionale Anforderungen ................................ ................................ ......................  21 
18 Ausgrenzungen und spätere Phasen  ................................ ................................ ................  22 
19 Abnahmekriterien  ................................ ................................ ................................ ............  23 
20 Offene Punkte  ................................ ................................ ................................ ..................  24 
   
1 
 
1 Schaufler Tooling  GmbH & Co. KG  
Die SCHAUFLER Tooling GmbH & Co. KG ist ein mittelständische 
Werkzeugbauunternehmen, das für seine Kunden Alluminium -Druckgussformen auf Basis 
selbst erstellter oder beigestellten Produktdaten fertigt. Insbesondere die Fertigung nach 
fremden Produktdaten ist mit einem enormen Aufwand verbunden Informationen seitens 
der Konstruktionsabteilung an die Fertigungsorganisation bereitzustellen.  
Herausforderungen  
Inkonsistente Datenlagen; unterschiedliche Datentypen; wechselnde Nomenklaturen, 
Sprachen, Bezeichnungen, Formate und Schemata  
    
2 
 
2 Zweck und Zielsetzung  
Ziel ist die Entwicklung eines Tools zur KI -gestützten Stücklistendatenerfassung für die 
Konstruktion. Das System soll heterogene Eingangsdaten aufnehmen, die Informationen 
aus den verschiedenen heterogenen Stücklisten extrahieren, transformieren und in eine 
standardisierte Schaufler -Excel -Vorlage regelkonform laden.  
 
Abbildung 1: Zielbild  
Das System ist ein Werkzeug für Konstrukteure. Es ist als Angebot zur 
Arbeitserleichterung gedacht, nicht als Zwangssystem. Die fachliche 
Entscheidungsverantwortung bleibt beim Konstrukteur.  
Zielbild  
• Eingangsdaten aus PDF, Excel, CSV, Zeichnungen, 3D -Daten, E -Mails und 
Protokollen aufnehmen  
• Relevante Inhalte extrahieren und auf Stücklistenpositionen abbilden  
• Technische Stücklistenattribute in das interne Format überführen  
• Quellen, OCR -Fundstellen und Ableitungen nachvollziehbar anzeigen  
• Konflikte auf Dokument -, Zeilen - und Attributebene markieren  
• Konstruktive Entscheidungen dokumentieren und versionieren  
• Befüllte Excel -Vorlage für die Übergabe an CadCam erzeugen   
  
3 
 
3 Ausgangssituation und Problemstellung  
Die Eingangsdaten liegen in der Praxis nicht standardisiert vor. Es gibt Inkonsistente 
Datenlagen , unterschiedliche Dateitypen, kundenspezifische Formate, uneinheitliche 
Benennungen , wechselnde Nomenklaturen , gemischte Tabellenstrukturen (Formate und 
Schemata ) inhaltliche Redundanzen  und unterschiedliche Sprachen . 
Typische Probleme:  
• Daten liegen verteilt über mehrere Dokumente vor  
• Informationen sind in verschiedenen Dokumentklassen enthalten:  
o Stückliste  
o Zeichnung  
o Sammelzeichnung  
o Kundenvorgabe  / Spezifikation  
o Richtlinie  (intern / extern)  
o Herstellerkatalog  
o E-Mail  
o Protokoll  
• Gleiche Bauteile sind unterschiedlich benannt  
• Stückzahlen müssen in flacher Stückliste konsolidiert  werden  
• Attribute können in mehreren Dokumenten widersprüchlich sein  
• Der Konstrukteur muss den fachlich richtigen Zustand ableiten  
Der erste Prioritätsfall ist die PDF -Verarbeitung mit OCR. Digitale Formate wie Excel oder 
CSV sind nachgelagert einfacher umzusetzen. Das System muss aber grundsätzlich alle 
genannten Eingangsdatenarten unterstützen.     
4 
 
4 Geltungsbereich und Abgrenzung  
4.1 Im Geltungsbereich  
 
Abbildung 2: Black -Box-Konzept  
Arbeitsdump:  
• Projektverwaltung und Design -Projektg rupp en 
• Referenz  heterogener Eingangsdaten  
• Dokumentenablage  
Work Desk  (keine Black -Box, sondern transparente Entscheidungslogik ) 
• Extraktion, Konsolidierung und Normalisierung  
• Transparente  Darstellung  der KI -Entscheidungen  
• Quellen - und Konfliktnachweis  
• Manuelle fachliche Korrektur durch den Konstrukteur  
• Regelverwaltung mit Versionierung und Wiederherstellung  
Bearbeitungs stand:  
• Darstellung der aktuellen Ergebnisse  der flachen Stückliste  
• Status der Stücklistenpositionen; offene Punkte  
• Export der befüllten Excel -Vorlage  (Schnittstelle bzw. Übergabevorbereitung für 
CadCam ) 
Ein manu eller Verifikation s- und Validierung smechanismus  wird erwartet.  
4.2 Nicht im MVP  
• Automatische fachliche Verifikation auf Bauteilebene  
• Automatische fachliche Validierung auf Produktebene  
• Vollständiger Ontologieaufbau  
• Vollautomatische Freigabe ohne menschliche Entscheidung   
  
5 
 
5 Systemkontext und Projektstruktur  
Mehrere Fertigungsaufträge können aus einem Design oder einer Design -Gruppierung 
abgeleitet werden. Das System muss eine Projektstruktur abbilden, die diese Hierarchie 
unterstützt.  
5.1 Anforderungen an die Projektverwaltung  
• Neue Projekte müssen angelegt, benannt und gruppiert werden können  
• Projekte müssen nach Kunde und Design -Gruppierung verwaltbar sein  
• Ein Design kann mehreren konkreten Fertigungsaufträgen zugeordnet sein  
• Alle Konstrukteure dürfen jederzeit alle Projekte sehen  
• Projektsichtbeschränkungen sind im Fachsystem nicht vorgesehen  
5.2 Projektstruktur  
Kunde  →  Design -Projekt  → Fertigungsauftrag 1..n  
    
6 
 
6 Benutzer - und Berechtigungskonzept  
Im Fachsystem ist die einzige fachliche Benutzerrolle der Konstrukteur.  
Jeder Konstrukteur hat Lese - und Schreibzugriff auf alle Projekte, Regelsätze und 
Bearbeitungsstände.  
Grundsätze  
• Keine projektbezogenen Sichtbeschränkungen für Konstrukteure  
• Keine Trennung in Fachrollen wie Leser, Reviewer oder Freigeber im MVP  
• Änderungen müssen versioniert und auditierbar sein  
• Das System soll Wissen aus dem Konstruktionsalltag standardisieren , nicht 
isolieren  
    
7 
 
7 Datenintegration und Ablagekonzept  
Das System soll On-Premise  betrieben werden, da unsere Ablagestruktur auf lokalen 
Netzlaufwerken basiert.  
7.1 Grundsätze der Datenintegration  
• Produktdaten und Quelldokumente liegen auf  lokalen Netzlaufwerken . Ein 
Upload wird wegen der große n Datenmengen  im Unternehmensalltag als nicht 
umsetzbar angesehen.  
• Die Anwendung referenziert diese Dokumente on -premise  
• Projektrelevante Bearbeitungsstände, Zuordnungen, Regeln und 
Extraktionsergebnisse werden systemseitig verwaltet  
• Die Quelldokumente verbleiben am Speicherort und werden nicht zwingend 
dupliziert . (→ Abklärung der Datenarchivierung mit It-Support ) 
• Die Anwendung muss auch dann arbeiten können, wenn Dokumente über 
bestehende Netzwerkpfade verfügbar sind  
• Externe Cloud -Abhängigkeiten sind für den MVP ausgeschlossen  
7.2 Ziel der Integrationslogik  
• Ein konsistenter Arbeitsbereich für Konstrukteure  
• Klare Trennung zwischen Quelldokumenten, abgeleiteten Daten und 
Bearbeitungsstand  
• Nachvollziehbarkeit, woher eine Information stammt  
    
8 
 
8 Sollprozess  
Der Prozess ist im Wesentlichen  eine KI -gestützte  ETL-Pipeline  (Extrakt -Transform -Load) , 
der Daten aus verschiedenen Quellen  (Produktdaten)  extrahiert, sie in ein sauberes 
Format umwandelt und in die zentrale  Stücklistenvorlage lädt. 
Tabelle 1: Prozessübersicht  der Datenkonsolidierung  
Schritt  Beschreibung  
1. Eingangsdaten  Eingangsdaten werden in den Arbeitsbereich importiert  
2. Extraktion  Das System analysiert die Daten  und extrahiert Kandidaten für 
Stücklistenpositionen  
3. Transformation 
und 
Normalisierung  Entitäten  werden fachlich identifiziert  und gleiche Entitäten 
erkannt , Benennungen normalisiert  (Abgleich mit Dictionary) , 
Attribute umgewertet , Formate angepasst  
4. Konsolidierung  
und Zuordnung  Quellen werden zusammengeführt, gleiche Bauteile 
unterschiedlicher Entitäten werden konsolidiert und Stückzahlen 
werden aggregiert,  Attribute werden zugeordnet  und abgeglichen , 
Fehler  werden entfernt  
Später:  Ontologie – Abgleich mit Stammdaten, Hersteller - und 
Lieferanten -Katalogen , Online -Datenbanken , Abschätzung anhand 
vorhergehender Projekte  
5. Verifikation  Das System zeigt Quellen, OCR -Ausschnitte und Konflikte 
transparent an ; Der Konstrukteur prüft, korrigiert und überschreibt 
fachlich  
6. Validierung  Technische Gesamtb ewertung  (Funktion und Herstellbarkeit, 
Produkt beschreibung vollständig ), Organisatorische Einordnung und 
Gruppierung (Teilegruppe und Kostenqualifizierer)  
7. Export  Das aktuelle Arbeitsergebnis der Stückliste wird als Excel exportiert    
9 
 
9 Statusmodell  
Verbindliche Zustände  
1. Rohdaten  
2. Erste Konsolidierung  (Entitäten -Konsolidierung)  
3. Normalisierung / Zusammenfassung  (verflachen der Identitäten)  
4. Geprüft / freigegeben  
Exportfähigkeit  
Der Export muss jederzeit möglich sein, also auch nach der ersten Konsolidierung oder 
Normalisierung. Inhaltlich soll der Export über Filter der Bearbeitungsstände 
eingeschränkt werden können. Dabei wird jeweils ein dokumentierter Snapshot des 
aktuellen Bearbeitungsstands erzeugt.     
10 
 
10 Arbeitsoberfläche  
Die Oberfläche wird als hybride Desktopanwendung beschrieben: tabellarische 
Stücklistenarbeit kombiniert mit Formularen, Dokumentenansicht und Detailansicht.  
10.1 Grundlayout  (Ein-Fenster -Konfiguration)  
• Links: Arbeitsdump mit Projektunterlagen  (Dokumenten -Viewer  mit OCR -Spotting -
Frame  in Extrafenster)  
• Mitte:  Darstellung der Transformations - und Entscheidungslogiken mit 
Quellenbezug, OCR -Ausschnitt, Konflikte  und Historie ; differenziert in 
Automatisierte -, KI und manuelle Entscheidungsergebnisse; Entscheidungsregeln 
über eigenes Konfigurationsmenü editierbar  
• Rechts: Stücklistentabelle des aktuellen Arbeitsstands  
 
 
  
11 
 
10.2 Funktionale Anforderungen an die Oberfläche  
Work  Desk  (mitte)  
• Darstellung in der jeweiligen Strukturebene ( Aufträge, Dokumente, 
Aufzeichnungen  / Zeilen , Attribute ) 
• Logikgatter: darstellen der Gesamtt ransformationslogik durch Verknüpfung von 
einzelnen Logikbausteinen  
• KI macht Vorschlag des Logikgatters zu einzelnen Positionen oder Typen  
• Mit Prompt -Feld darunter kann der Konstrukteur auch  die KI anweisen 
Änderungen an der Logik vorzunehmen. (Bedienerfreundlichkeit, kein einarbeiten 
in Logik -Schema nötig)  
Arbeitsdump  (links)  
• Projektstruktur  mit extrahierten Rohdaten  (EDI-Elementen)  
• Dokumentenansicht  auf Quelldokumente  
• OCR -Ausschnitt  (Spotting -Frame  auf EDI -Quelle)  zur visuellen Prüfung  
(Aufzeichnungs - und Attributebene)  
• Detailansicht  auf Transformationslogik pro Ebene  
Stückliste – Arbeitsstand  (rechts)  
• Navigation und Fokus auf ausgewählte Mapping -Logik im Work Desk  
• Konfliktanzeige auf Zeilen - und Attributebene  
• Konfliktbereinigung über Dropdown -Dialog der Auswahlmöglichkeiten ; optionaler 
Kommentar bei Auswahl  
• Historie der Zustandsänderungen  
10.3 Erwartetes Bedienmuster  
Der Konstrukteur soll den Arbeitsbereich wie einen Schreibtisch verwenden können: 
Quellen ablegen, erkannte Inhalte prüfen, Positionen zusammenführen, Konflikte lösen 
und das Ergebnis exportieren.    
12 
 
Entscheidungslogik soll komfortabel über anklicken des gewünschten Datenelements in 
der Ergebnisstückliste im Work Desk in den Fokus gerückt werden.  
Alle Dialogbereich sollen individuell eingerichtet werden. Eindocken in das Hauptfenster , 
ausdocken als eigenes Fenster, flexibles Arbeiten auf einen, zwei oder Widescreen -
Bildschirmen . 
    
13 
 
11 Funktionale Anforderungen  
Tabelle 2: Funktionale Anforderungen  
ID Anforderung  
F01 Das System muss PDF, Excel, CSV und weitere Dokumentarten importieren 
können. PDF -Verarbeitung muss OCR unterstützen.  
F02 Das System muss Projektverwaltung und Design -Gruppierungen 
unterstützen.  
F03 Alle Konstrukteure müssen zu jeder Zeit alle Projekte sehen und bearbeiten 
können.  
F04 Das System muss eine hybride Desktopoberfläche mit Arbeitsdump, 
Stückliste und Detailbereich bereitstellen.  
F05 Das System muss technische Stücklistenattribute aus Eingangsdaten auf das 
interne Format mappen.  
F06 Das System muss Bauteile aus mehreren Quellen konsolidieren können.  
F07 Das System muss Stückzahlen bei eindeutiger Zusammengehörigkeit 
addieren können.  
F08 Das System muss Quellenbezug mindestens auf Dokument -, Seiten - und 
Fundstellenebene anzeigen.  
F09 Das System muss OCR -Ausschnitte zur visuellen Verifikation anzeigen.  
F10 Das System muss Konflikte pro Stücklistenzeile und pro Attribut markieren.  
F11 Der Konstrukteur muss Werte direkt überschreiben dürfen. Die fachliche 
Hoheit liegt beim Konstrukteur.  
F12 Das System muss Entscheidungen speichern und versionieren.  
F13 Das System muss Regeldefinitionen, Regeländerungen und Regelsätze 
versioniert und wiederherstellbar halten.  
F14 Das System muss mehrere Regelsätze parallel verwalten können, mit   
14 
 
ID Anforderung  
kundenspezifischem oder projektspezifischem Geltungsbereich.  
F15 Das System muss den Export der Excel -Vorlage jederzeit zulassen.  
F16 Das System muss den aktuellen Status des Exports mitgeben.  
F17 Das System muss eine Übergabe des Projekts ohne separaten 
Übergabeprozess ermöglichen, da Zustände (Validierung und Frei gaben) und 
Historie im System dokumentiert sind.  
F18 Das System muss implizite  Verifikation s- und Validierung smechanismen  
enthalten.  
F19 Das System muss KI- und Benutzer -Mapping -Entscheidungen transparent 
und vollständig darstellen können.  
F20 Das System muss selbständig  die Daten in d ie aktuell  Export -Vorlage 
mappen und laden . (Excel -Vorlage kann sich über die Zeit ändern ) 
   
15 
 
12 Datenmodell und interne 
Stücklistenattribute  
Das interne Feldmodell orientiert sich an der vorhandenen Richtlinie und der Excel -
Vorlage. Die Feldmenge n und -namen sollen  auf die aktuelle Vorlage flexibel 
konfigurierbar sein . 
Tabelle 3: Kernattribute  
Nr. Deutsch  Englisch  
1 Positionsnummer  Detail Number  
2 Stk. Konstr.  Design Count  
3 Stk. Ersatz  Spare Count  
4 Benennung  Description  
5 Abmaß X/D  Dimensions X/D  
6 Abmaß Y/L  Dimensions Y/L  
7 Abmaß Z  Dimensions Z  
8 Werkstoff  Material  
9 Teilegr p. Parts grp.  
10 Härte  Hardness  
11 Nitr. -Art/ Nitr. -Tiefe  Nitr. Type / Nitr. depth  
12 Beschichtung  Coating  
13 Hersteller  Manufacturer  
14 Hersteller Material -Nr. Manufacturer part no.  
15 Zielkosten -Block Bezeichnung  Target cost block description  
16 besondere Hinweise  Special Notes  
   
16 
 
Wichtige Modellregeln  
• Teilegruppe und Kostenqualifizierer werden im MVP nicht automatisiert fachlich 
bestimmt  
• Technische Attribute sollen aus Quellen extrahiert , normalisiert und der korrekten 
Attributspalte in der  Stücklistenvorlage zugeordnet werden  
• Für bestimmte Angaben, insbesondere Härte, sind Formatregeln zulässig; separate 
Stammdatenlisten sind nicht zwingend erforderlich  
• Das System muss externe Benennungsvarianten auf einen internen Standard 
abbilden  
    
17 
 
13 Konfliktmanagement  
Konflikte sind nicht als Ursachenanalyse zu modellieren, sondern als fachliche 
Auflösungsfälle. Entscheidungsinstanz ist der Konstrukteur.  
Typische Konfliktarten  
• Abweichende Attributwerte (Bezeichnung, Hersteller, Härte, Werkstoff …)  
• Unklare Bauteilzuordnung  
• Doppelte oder widersprüchliche Positionszuordnung  
• Unterschiedliche Stückzahlen in zusammengehörigen Quellen  
Darstellung  
• Konflikte müssen in der Stücklistenzeile farblich hervorgehoben sein  
• Der Konflikt muss auf Attributebene sichtbar sein  
• Der Quellbezug muss bis auf Dokument, Seite und Fundstelle sichtbar sein  
• Die Lösung des Konflikts muss dokumentiert werden  
Fachliche Auflösung  
Der Konstrukteur muss eine fachliche Entscheidung treffen können, zum Beispiel:  
• Wert aus Stückliste verwerfen  
• Wert aus Zeichnung verwerfen  
• Wert aus Kundenspezifikation verwenden  
• Wert aus Herstellerkatalog verwenden  
• Wert aus mehreren Quellen konsolidieren  
• Konflikt akzeptieren und als Ausnahme dokumentieren  
Eine Freitextbegründung soll angeboten werden, aber nicht als starre Pflicht jede einzelne 
Korrektur blockieren.  
    
18 
 
14 Regelverwaltung und Lernlogik  
Die KI soll aus menschlichen Entscheidungen lernen. Die fachliche Steuerung bleibt jedoch 
beim Konstrukteur.  
Anforderungen  
• Jeder Konstrukteur darf Regeln definieren, ergänzen und eingrenzen  
• Regeln müssen versioniert und wiederherstellbar sein  
• Mehrere Regelstände dürfen parallel existieren  
• Regeln müssen einen Geltungsbereich haben:  
o allgemein  
o kundenspezifisch  
o projektspezifisch  
• Das System muss zwischen allgemeingültigen und eingeschränkten Regeln 
unterscheiden können  
Wichtige technische Leitplan
