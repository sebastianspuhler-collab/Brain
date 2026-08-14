---
tags:
  - Lead
  - Juchem
  - Beschaffungsagent
  - Prozessdefinition
quelle: Sebastian Spuhler (mündliche Zusammenfassung nach dem Termin, kein Transkript vorhanden)
datum: 2026-07-29
kategorie: Lead
---

# Update Juchem X Prozessia

## Zusammenfassung
Folgetermin am 29.07.2026, 14:00–17:00 Uhr mit Thorsten Maas (Geschäftsführer Juchem Gruppe, Eppelborn) im Anschluss an das Erstgespräch vom 08.06.2026. Im Termin wurde der komplette End-to-End-Beschaffungsprozess durchgesprochen, den der Prozessia-Agent bei Juchem abdecken soll – deutlich umfangreicher als der bisher bei Schaufler live geschaltete Scope (dort primär AB-Tracking/Eskalation). Ein Transkript liegt noch nicht vor, diese Notiz basiert auf Sebastians eigener Zusammenfassung direkt nach dem Termin.

## Besprochener Gesamtprozess (Ist-Soll für den Agenten)

1. **Preisanfrage:** Der Prozessia-Agent holt eigenständig Preisanfragen bei potenziellen Lieferanten ein, sobald ein Bedarf entsteht. Das ist der einzige Schritt in diesem Prozess, den Sebastian bei keinem bisherigen Kunden (auch nicht Schaufler) in dieser Form skizziert hat – hier übernimmt der Agent aktiv Kommunikation nach außen, nicht nur Prüfung eingehender Dokumente.
2. **Lieferantenauswahl:** Auf Basis der eingeholten Preise trifft der Einkäufer die Entscheidung, bei welchem Lieferanten was bestellt wird. Der Agent liefert hier die Entscheidungsgrundlage (Preisvergleich), ersetzt aber nicht die menschliche Entscheidung – bewusster Human-in-the-loop-Schritt.
3. **Bestellung:** Die eigentliche Bestellung läuft über das ERP-System Info LN. Genau an dieser Stelle hängt die technische Umsetzung: ob und wie der Agent direkt mit Info LN sprechen kann (Schnittstelle/API vs. Postfach-Abgleich wie bei Schaufler), ist bislang nicht geklärt.
4. **Auftragsbestätigungs-Workflow:** Fehlende ABs werden vom Agenten aktiv nachgefordert, eingehende ABs werden automatisch kontrolliert und geprüft (vermutlich analog zu Schaufler: Preis-/Mengenabweichung, AB ohne zugehörige Bestellung).
5. **Dokumenten-/Zertifikatsanforderung:** Lieferscheine sowie sämtliche weiteren Dokumente und Zertifikate werden bereits vorab, also vor Wareneingang, aktiv beim Lieferanten eingefordert – das greift direkt den Wunsch auf, den Maas schon im Erstgespräch vom 08.06. geäußert hatte: automatische Voranforderung von Lieferdokumenten per Mail, die sonst oft erst mit der Lieferung selbst oder gar nicht ankommen.
6. **Wareneingangsprüfung:** Der Agent prüft, ob die Ware wie erwartet und vollständig eingegangen ist. Kommt nichts oder nicht das Erwartete an, löst er automatisch eine Eskalation aus.
7. **Rechnungsprüfung:** Die eingehende Rechnung wird gegen Bestellung/ERP-Daten abgeglichen, um Abweichungen (Preis, Menge, Konditionen) zu erkennen, bevor sie freigegeben wird.
8. **Zertifikats-Monitoring:** Zusätzlich zur einmaligen Anforderung überwacht der Agent laufend die Gültigkeit aller eingesammelten Lieferantenzertifikate und weist rechtzeitig vor Ablauf automatisch darauf hin – ein dauerhafter Überwachungsprozess, kein einmaliger Check.

## Einordnung

Das ist der mit Abstand umfassendste Beschaffungsagent-Scope, den Sebastian bislang mit einem Kunden oder Lead durchgesprochen hat. Er deckt den kompletten Zyklus von der Preisanfrage bis zum laufenden Zertifikats-Monitoring ab – bei Schaufler Tooling (aktuell live für 220€/Monat) beschränkt sich der Agent dagegen im Kern auf AB-Tracking, die drei Eskalationsfälle (fehlende AB, Mengenabweichung, AB ohne Bestellung) und ELO-Ablage, siehe `Kunden/Schaufler/Meetings/2026-07-16-Einführung Beschaffungsagent.md`. Bei Juchem kommen mit der vorgelagerten Preisanfrage/Lieferantenauswahl und der nachgelagerten Rechnungsprüfung plus dauerhaftem Zertifikats-Monitoring gleich mehrere zusätzliche, eigenständige Module hinzu, die im Schaufler-Preismodell (1. Agent 120€, 2. Agent 110€ usw.) so nicht abgebildet sind – das spricht eher für eine Bündelung mehrerer Agenten-Module oder ein individuelles Pilotprojekt-Angebot ab 12.000€ netto statt eines einzelnen Standard-Agenten.

Zwei Punkte aus dem Erstgespräch vom 08.06. sind für dieses Angebot wichtig und noch nicht abschließend geklärt:

- **Info-LN-Schnittstelle:** Maas hatte auf Nachfrage nur genannt, dass Info LN (vermutlich Infor LN, ehemals Baan) das genutzte ERP ist – ob und welche Integrationsmöglichkeiten (z.B. Infor ION, OData/REST) dort lizenziert und aktiv nutzbar sind, wurde bisher in keinem Gespräch technisch geklärt. Das entscheidet maßgeblich, ob Schritt 3 (Bestellung) und die ERP-Rückkopplung in Schritt 4/7 automatisiert oder nur über einen Postfach-Adapter abgebildet werden können.
- **Copilot-Restriktion:** Bei Juchem dürfen Mitarbeiter laut interner Regel ausschließlich Microsoft Copilot als KI-Tool nutzen, keine anderen Chatbots. Für den Beschaffungsagenten selbst ist das unkritisch (kein Chatbot-Interface für Mitarbeiter), sollte aber bei einer eventuellen Nutzeroberfläche oder Rückfragen-Funktion des Agenten mitgedacht werden.

Nicht vergessen werden sollte außerdem die Randnotiz aus dem 08.06.-Transkript, die bisher noch nicht weiterverfolgt wurde: Maas hat von sich aus die Analogie zu Rezepturen gezogen ("Ja, aber wir haben Rezepturen. Das ist so das Gleiche.") als Sebastian das Stücklisten-Thema ansprach. Rezepturen sind bei einem Lebensmittelhersteller wie Juchem strukturell vergleichbar mit Stücklisten – das eröffnet über den Beschaffungsagenten hinaus einen zweiten Produktansatz (Stücklistenagent-Logik auf Rezepturen übertragen), den Sebastian im heutigen Termin ggf. bereits vertieft hat.

## Nächste Schritte
- Prozess in ein detailliertes Angebot überführen – Scope ist deutlich größer als das Schaufler-Standardpaket, Aufwand und Preismodell entsprechend individuell kalkulieren (voraussichtlich Pilotprojekt-Festpreis statt reinem Monats-Agentenpreis)
- Klären, ob die Einkaufsseite bei Juchem (laut 08.06.-Notiz bislang nicht direkt eingebunden) den beschriebenen Prozess in dieser Form bestätigt
- Info-LN-Schnittstellenfrage technisch final klären, falls im heutigen Termin nicht bereits geschehen – das ist Voraussetzung für eine belastbare Aufwandsschätzung
- Rezepturen-/Stücklisten-Analogie als möglichen zweiten Anwendungsfall (Stücklistenagent-Logik) im Angebot oder in einem Folgegespräch aktiv aufgreifen
