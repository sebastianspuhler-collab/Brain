---
tags:
  - Seifert
  - Prototyp
  - Stücklistenagent
  - Demo
  - Preisargumentation
quelle: Update Seifert X Prozessia.docx
datum: 2026-07-28
kategorie: Lead
dauer: 28 Min. 30 Sek.
---

# Update Seifert X Prozessia (28.07.2026, 14:35 Uhr)

Folgetermin zum Erstgespräch vom 23.07.2026. Sebastian zeigt Stefan Seifert einen konkreten Prototyp/Demo-Dashboard, das auf Basis der von Seifert per Mail geschickten Anfrage (Stücklisten + Einzelteilzeichnungen, siehe Mail vom 27.07. "Beispiel Anfrage für KI") gebaut wurde.

## Kernpunkte

- **Demo-Datenbasis**: Die von Seifert eingereichte Anfrage enthält 16 Positionen, Kunde dahinter ist Gerhard Rau von Grenzbach.
- **Funktionsweise gezeigt**: Anfrage wird ins System hochgeladen (Status "neu"), das System fasst die Dokumente zusammen und erstellt eine Gesamtübersicht: Positionsnummer, Material und alle relevanten Daten pro Position, automatisch aus Stücklisten/Zeichnungen extrahiert.
- **Warnung-Funktion**: Bei Unsicherheit (z.B. Abbildung nicht lesbar, Wert unklar) markiert das System die Position mit "Warnung" und gibt sie zur manuellen Prüfung frei (Human-in-the-Loop, um Halluzinationen zu vermeiden) – im Beispiel bei Position "Fuß" und "Schwinge".
- **Seiferts konkrete Anforderung** (Anschlussfrage im Meeting): Unterscheidung zwischen bereits zugeschnittenem Material und Material, das laut Zeichnung noch zugeschnitten werden muss (Bleche, Rollprofile, Stabmaterial zusammenfassen) – Sebastian bestätigt, dass der Agent das abbilden kann, wenn es aus den Dokumenten erkennbar ist.
- **Aktueller Ist-Zustand bei Seifert**: Material wird händisch in eine Liste inkl. Norm und Artikelnummer eingetragen und dann als Anfrage an den Material-/Profil-Lieferanten weitergeleitet. Für die Normen nutzt Seifert intern ein kleines Access-Tool.
- **Automatisierungsvorschlag**: Übersicht könnte automatisch als Excel exportiert und direkt weitergeleitet werden; perspektivisch auch automatisches Postfach-Auslesen der Kundenanfrage möglich, sodass der manuelle Upload entfällt.
- **Skalierungsthema**: Aktuelle Demo ist auf eine Anfrage trainiert. Damit es für mehrere/unterschiedlich aufgebaute Kunden(-Stücklisten) von Seifert funktioniert, braucht es ein größeres Projekt mit Training auf mehrere Anfragen/Varianten.
- **Preis**: Sebastian nennt zunächst "niedriger bis mittlerer dreistelliger Bereich", korrigiert sich dann sofort selbst: **richtig ist vierstelliger Bereich**, nicht dreistellig – Projektpreismodell, keine monatlichen Kosten für dieses Projekt (Hosting/Wartung ggf. separat). Projektgröße wird als eher kleineres Projekt für Prozessia eingeordnet, da klar abgegrenzter Scope.
- **Nächster Schritt**: Seifert will das intern mit seinem Team besprechen (wie die Anfrage am besten strukturiert werden könnte). Kein konkreter Folgetermin im Transkript vereinbart – offen.

## Offene Punkte
- Kein fixer Folgetermin vereinbart, sollte nachgefasst werden.
- Unterscheidung Zuschnitt-Material vs. bereits fertiges Material ist als Anforderung explizit dokumentiert – für Angebot/Scope relevant.
- Access-Tool mit Normen bei Seifert als mögliche Datenquelle/Schnittstelle im Hinterkopf behalten.
