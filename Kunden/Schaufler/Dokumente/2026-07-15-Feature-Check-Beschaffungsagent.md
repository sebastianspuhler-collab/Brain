---
tags:
  - Feature-Check
  - Beschaffungsagent
  - Schaufler
  - Status
datum: 2026-07-15
kategorie: Kunde
---

# Feature-Check Beschaffungsagent — Schaufler Tooling GmbH

## 1. Auftragsbestätigung (AB)

**Anforderung** (Lastenheft 4.1): zentrales Postfach `Order@schaufler.de`, stündliche
Überwachung, KI-Prüfung auf Liefertermin/Position/Menge/Preis/Incoterm/Zahlungsbedingungen.

**Umsetzung** (Systemhandbuch Kap. 3, Tab "Auftragsbestätigungen"): zeigt alle
verarbeiteten ABs inkl. Abgleichsergebnis. Kennzahlen: Gesamt / OK (ohne relevante
Abweichung) / Hinweis (tolerierte, aber sichtbare Abweichung) / Eskaliert (kritische
Abweichung). Weitere Funktionen: Verteilungsübersicht, Eskalationsauswertung nach Typ,
Filter (Ampelstatus, Lieferant, Zeitraum, Bestellnummer), Excel-Export, Klick öffnet
Bestellhistorie.

Tabellenspalten: Bestellnr., AB-Referenz, Lieferant, Termin, Status (OK/Hinweis/Eskaliert),
Abweichungen (z. B. Termin/Preis/Menge), Verarbeitet (Zeitstempel).

Toleranzlogik: Termin ≤ 5 Tage Abweichung = Hinweis, > 5 Tage = Eskalation; jede
Preis-/Mengenabweichung eskaliert sofort.

**Realer Stand aus den Mails**: Benjamin hat am 07.07. den Top-100-Lieferanten eine Mail
geschickt, ABs künftig an `Order@` zu senden — laut seiner Mail vom 08.07. ist das
"Großteil der Lieferanten" bereits umgesetzt. Ein Beispiel-Bestellschreiben liegt vor
(*Bestellung 127412*, 15.06.).

**Rollout**: Ab Freitag, 17.07. geht zunächst nur die AB-Prüfung live, mit den ersten
**10 Lieferanten** als Pilotgruppe. Ab nächster Woche kommen Lieferverfolgung,
Messberichte und Vessel Tracking dazu.

## 2. Abweichung vom geforderten Liefertermin

**Prüfregeln** (Systemhandbuch Kap. 11):

| Situation | Reaktion |
|---|---|
| Termin im Soll | OK (grün) |
| Termin später, bis 5 Tage Abweichung | Hinweis (gelb) |
| Termin später, mehr als 5 Tage Abweichung | Eskalation (rot) |

Preis: jede Abweichung ≠ 0 → sofortige Eskalation. Menge: jede Abweichung ≠ 0 → sofortige
Eskalation.

**Konfidenz-Prüfung** (zusätzliche Absicherung, nicht in Lastenheft/Fachkonzept gefordert):

| Einschätzung | Reaktion |
|---|---|
| hoch | normal verarbeiten |
| mittel | verarbeiten, aber als prüfungswürdig markieren |
| sehr niedrig | KI-Ergebnis verwerfen, mit einfacheren Erkennungsmustern weiterarbeiten |

Zusatzlogiken: Transport-/Versandterminprüfung (Trackingdaten vs. bestätigter Termin +
tatsächliches Verfügbarkeitsdatum), Messbericht-Vollständigkeit, Dokumentenlogik (fehlende
Versanddokumente/ABs erzeugen eigene Folgeprozesse).

**Geklärt (Sebastian, 15.07.)**: Der Agent schreibt vorerst nur Entwürfe, kein
automatischer Versand an Lieferanten — Mensch-in-the-loop.

## 3. Fehlende Auftragsbestätigungen

**Anforderung**: Fristenkaskade mit Eskalationsstufen (Workshop-Agenda Pkt. 4).

**Umsetzung** (Systemhandbuch, Tab "Fehlende AB"): zeigt offene Bestellungen ohne
registrierte AB. Kennzahlen: Gesamt Bestellungen / Fehlende AB. Tabellenspalten:
Bestellnummer, Lieferant, Soll-Termin, Erinnerungsstufe, Letzte Erinnerung, Nächste
Erinnerung.

**3-Stufen-Erinnerung**:

| Stufe | Frist | Ton | Empfänger |
|---|---|---|---|
| 1 | 2 Arbeitstage | Höfliche Erinnerung | Nur Lieferant |
| 2 | 2 Arbeitstage nach Stufe 1 | Bestimmter und konkreter | Lieferant + Einkäufer (CC) |
| 3 | 2 Arbeitstage nach Stufe 2 | Verbindlich, mit Konsequenzhinweis | Lieferant + Einkäufer + Teamleitung (CC) |

Nach Stufe 3 stoppt die Automatik bewusst zur manuellen Bearbeitung. Erinnerungen werden
historisiert und in der Bestell-/Eskalationshistorie sichtbar.

**Geklärt**: Eine Mitschrift (05.02.) nennt eine abweichende Taktung (5/8/10 Tage statt
2/2/2 Arbeitstage) — nach der Systemhandbuch-Vorrang-Regel gilt die im Systemhandbuch
dokumentierte 2/2/2-Taktung als aktueller Stand, die Mitschrift-Angabe als überholt.

**Tab "Eskalationen"** (Systemhandbuch): zeigt alle ausgelösten Eskalationen — nicht nur
aus fehlenden ABs, sondern auch aus Abweichungen in eingegangenen ABs und weiteren
Folgeprozessen. Kennzahlen: Gesamt / Eskalierungen aus AB / davon fehlende AB / Offene
Fälle. Tabellenspalten: ID, Bestellnr., Quelle, Beschreibung, Priorität, Status, Erstellt
am. Manueller Statuswechsel auf Offen/In Bearbeitung/Gelöst möglich.

## 4. Überwachung zukünftiger Lieferungen

**Anforderung** (Workshop-Agenda Pkt. 5): wöchentliche Prüfung nach Herkunftsland,
Statusabfrage an Lieferanten.

**Umsetzung** (Systemhandbuch Kap. 13, "Lieferstatus-Abfragen"): läuft automatisch,
zusätzlich manuell auslösbar. Beobachtungsfenster nach Herkunftsland:

| Herkunft | Beobachtungsfenster |
|---|---|
| China | 14 Wochen vor Liefertermin |
| USA | 14 Wochen vor Liefertermin |
| Europa | 10 Wochen vor Liefertermin |
| Deutschland | 4 Wochen vor Liefertermin |

Der Lieferant wird gebeten, innerhalb von 2 Arbeitstagen zu antworten:
Produktionsstatus/Qualitätsprüfung/Versandbereitschaft/bereits versandt, Transportweg
(Schiff/Zug/LKW/Flug), ggf. neuer Liefertermin. Die Anfragen erscheinen im
Aktivitätsverlauf als eigene Systemaktionen.

**Geklärt**: Eine frühere Konzept-Präsentation nennt für Europa 6 statt 10 Wochen
Betrachtungszeitraum — nach der Systemhandbuch-Vorrang-Regel gelten die 10 Wochen als
aktueller Stand, die Präsentations-Angabe als überholter Konzeptstand.

**Statusabfrage-Frequenz — geklärt (Sebastian, 15.07.)**: pauschal **alle 2 Wochen**,
unabhängig von der Lieferzeit — die Mitschrift hatte hier noch nach langer/kurzer
Lieferzeit unterschieden (2 bzw. 1 Woche), das gilt nicht mehr. Agent fragt dabei nach
offenen Positionen, ausstehenden Lieferungen, Bestellungen ohne AB, und fasst den Stand
zusammen.

## 5. Überfällige Lieferungen & Ampellogik

**Verbindliche Quelle laut Sebastian (15.07.): Lastenheft 4.0 + 5.4, nicht das
Systemhandbuch.** Die Ampellogik ist einfacher als bisher dargestellt — genau drei
Zustände, direkt an die Toleranzlogik aus 4.0 gekoppelt:

| Farbe | Bedeutung |
|---|---|
| Grün | Keine Abweichungen, Prozess läuft automatisiert |
| Gelb | Abweichung innerhalb der Toleranz oder in Klärung |
| Rot | Eskalation ausgelöst (Termin > 5 Tage, Preis- oder Mengenabweichung) |

Das ist die einzige Ampel, an der wir uns orientieren — die im Systemhandbuch beschriebenen
zusätzlichen Ampel-Varianten (separate Werte mit/ohne Tracking, eigene AB-Prüfung-Ampel)
sind für diesen Report nicht mehr maßgeblich.

**Geklärt (Sebastian, 15.07.)**: Eine Bestellung erscheint **von Anfang an** in
`/lieferungen`, also schon direkt ab Anlage im ERP — nicht erst, wenn eine
Auftragsbestätigung eingegangen ist.

Kennzahlen und Tabellenspalten auf der Seite `/lieferungen` (Systemhandbuch, ergänzend,
soweit nicht im Widerspruch zum Lastenheft): Gesamt / Überfällig / Diese Woche fällig /
Aktive Sendungen; Spalten Bestellnr., Lieferant, Soll-Termin, Bestätigter Termin,
Terminstatus, Auffälligkeiten.

## 6. Versandtermin, Transportlogik & Versanddokumente (Lastenheft 4.3 + 4.4)

**4.3 Versandtermin & Transportlogik**: Der Versandtermin (Abholzeitpunkt) wird
systemseitig berechnet aus dem **bestätigten Liefertermin** und **vordefinierten
Transitzeiten je Transportmittel** (LKW, Luft, See, Bahn). Überwachung: Vergleich
zwischen berechnetem Anliefertermin und bestätigtem Anliefertermin aus der AB — bei
Abweichung automatische Eskalation an den Einkäufer.

**Geklärt (Sebastian, 15.07.)**: Wenn kein Vessel-Tracking vorliegt, wird der Termin
schlicht berechnet als **Abholzeitpunkt + vorgegebene Transitdauer** (siehe Transitzeit-
Tabelle in Abschnitt 4). Das ist die Antwort auf die zuvor offene Frage, wie die Ankunft
ohne Live-Tracking ermittelt wird.

**4.4 Packliste & Versanddokumente**: Packlisten werden automatisiert ins System geladen
und der Lieferung/Bestellung zugeordnet — die **Packliste ist gleichwertig relevant** wie
andere Versanddokumente (keine Sonderbehandlung). Automatisch erkannte Versanddokumente:
Bill of Lading (B/L), Packliste, AWB, CMR, Handelsrechnung — B/L und Packliste sind
gleichwertig priorisiert. **Alle Versanddokumente werden automatisch an den Zolldeklaranten
weitergeleitet: `schaufler@transauriga.de`.**

Mehr passiert an dieser Stelle laut Lastenheft nicht — kein weiterer Verarbeitungsschritt
außer der Weiterleitung.

**Geklärt (Sebastian, 15.07.)**: `schaufler@transauriga.de` aus dem Lastenheft ist die
korrekte Adresse — die `.com`-Variante aus einer anderen Quelle ist hinfällig.

## 7. Vessel Tracking & Verzollung (Lastenheft 4.5 + 4.6)

**4.5 Vessel Tracking (Seefracht) — geklärt (Sebastian, 15.07.): Lastenheft geht vor.**
ETA = Estimated Time of Arrival, die voraussichtliche Ankunftszeit einer Sendung. Ablauf:

1. Der Schiffsname wird KI-gestützt aus den Versanddokumenten extrahiert.
2. Automatische Übergabe an einen externen Vessel-Tracking-Service (z. B. vesselfinder.com).
3. Tägliche Statusabfrage bei diesem Dienst — Position und ETA.
4. Der abgefragte Status wird 1:1 im System gespeichert.
5. **Keine automatische ETA-Neuberechnung erforderlich** — das System übernimmt die ETA
   direkt vom externen Tracking-Dienst, ohne eigene Formel, ohne zusätzlichen Tage-Puffer.

Eine andere Quelle (Konzept-Präsentation) hatte hier eine tägliche interne Neuberechnung
mit 10 Tagen Zuschlag beschrieben — das gilt nach der Lastenheft-Vorrang-Regel für dieses
Thema **nicht mehr**.

**4.6 T1-Dokumente & Verzollung**: Sollte ein T1-Dokument erforderlich sein, erfolgt
automatische Erkennung und automatische Weiterleitung an den Zolldeklaranten
(`schaufler@transauriga.de`). **Ziel ist die Verzollung am örtlichen Zollamt (Ulm) — nicht
an der EU-Außengrenze.**

**Geklärt**: Das beantwortet die zuvor offene Frage nach dem Verzollungsort — laut
Lastenheft ist die örtliche Verzollung (Ulm) das Ziel, nicht die Verzollung an der Grenze
(z. B. Polen). Damit ist auch die Frage "Agent oder Mensch entscheidet" hinfällig, da gar
keine Ortsentscheidung zwischen zwei Optionen vorgesehen ist, sondern ein fester Zielort.

**Was T1 als Dokument rechtlich genau ist, bleibt unklar** — das Lastenheft beschreibt nur
die Verarbeitung (erkennen, weiterleiten), nicht die rechtliche Bedeutung. **E1 kommt im
Lastenheft gar nicht vor** — laut Sebastian für diesen Report aber nicht mehr relevant.

**Tracking-Website**: erst am 14.07. fixiert (vesselfinder.com) — kein Beleg für einen
abgeschlossenen Integrationstest vor Go-Live.

## 8. Messberichte

**Anforderung** (Lastenheft 4.2): Eingang an `Order@schaufler.de`, automatische
Weiterleitung an `Quality@schaufler.de`, Zuordnung zu Bestellung + Stücklistenposition,
Vollständigkeitsprüfung.

**Umsetzung** (Systemhandbuch Kap. 6, Seite `/messberichte`): Kennzahlen Gesamt /
Vollständig (alle wichtigen Angaben erkannt) / Unvollständig (fehlende/unklare Angaben).
Tabellenspalten: Eingegangen (Zeitpunkt), Absender, Betreff, Bestellnr. (oder "nicht
erkannt"), Position, Vollständigkeit (Grün/Gelb), Weitergeleitet an.

Wichtiger Verhaltenshinweis: eine Messbericht-Mail kann mehrere Positionsnummern
enthalten — das System verarbeitet dann jede erkannte Position einzeln, sowohl im
Aktivitätslog als auch in der Messberichtsicht. Unvollständige Messberichte werden
markiert und können Folgeaktionen (System-Task, manuelle Nachverfolgung) auslösen. Der
Agent schreibt nicht ins Feld `messbericht_eingegangen` — das pflegt der Messraum, der
Agent liest es nur, eine Woche vor Liefertermin.

**Flaschenhals** (nicht die Prüflogik, sondern der Dokumenteneingang): sechs
unterschiedliche Eingangswege — OneDrive, WeTransfer, SharePoint (mit Verifizierung),
Schneider-Form-Portal (Anmeldung + Passwort), SwissTransfer, Mail-Anhang (PDF oder
gezippt) — sowie ein bestätigtes technisches Problem: ProLeiS kann Daten aus einer
ZIP-Datei nicht speichern. Wichtige Einigung im Meeting mit Michael Maier (15.06.): der
Agent soll nicht inhaltlich prüfen, ob eine Messung "in Ordnung" ist (zu fehleranfällig),
sondern nur erkennen, ablegen und eine Infomail an Quality schicken.

**Status (aktualisiert 15.07.)**: Gelöst wird das über eine **Shared Mailbox** (nicht wie
zuvor angenommen über einen SharePoint-Watchfolder), Umsetzung laut Sebastian nächste
Woche zusammen mit Lieferverfolgung und Vessel Tracking. Bis dahin bleibt der
uneinheitliche Dateieingang der Engpass.

## 9. Lieferanten

**Anforderung**: weder Lastenheft noch Workshop-Agenda fordern explizit eine
Lieferantenbewertung — Erweiterung, die erst im Systemhandbuch auftaucht.

**Umsetzung** (Systemhandbuch Kap. 5, Seite `/lieferanten`): Kennzahlen Lieferanten
gesamt / Ø Performance Score / Score ≥ 80 (Gut) / Score < 60 (Kritisch).

**Score-Formel**: Gesamt-Score = Termintreue × 50 % + Dokumentenqualität × 30 % +
Reaktionszeit × 20 %.

- Termintreue = (Anzahl ABs ohne Abweichungen / Anzahl ABs gesamt) × 100
- Dokumentenqualität = (Vollständige Messberichte / Messberichte gesamt) × 100 (100 % wenn
  keine Messberichte vorliegen)
- Reaktionszeit, gestaffelt nach Ø Reaktionszeit auf Eskalationen:

| Ø Reaktionszeit | Punkte |
|---|---|
| ≤ 2 Tage | 100 |
| ≤ 5 Tage | 80 |
| ≤ 10 Tage | 60 |
| ≤ 14 Tage | 40 |
| > 14 Tage | 20 |

Score-Bewertung: ≥ 80 Gut (Grün), 60–79 Akzeptabel (Gelb), < 60 Kritisch (Rot).

Tabellenspalten: Lieferant, Score, Status, Termintreue, Doku-Qualität, Reaktionszeit, ABs,
Eskl. offen, Letzte AB, Letzte Abfrage. Detaildialog pro Lieferant: Score-Balken, offene/
gesamte Eskalationen, Messberichte, Ø Reaktionszeit, verknüpfte Bestellungen, offene
fehlende ABs.

**Bezug zur Top-10-Liste**: `Top 10 Lieferanten.xlsx` liegt im Kundenordner vor. Die
14.07.-Mail nennt konkrete Lieferantengruppen mit Bestellformularen: Stahl-Hersteller,
Wärmebehandler, Normhersteller, Dienstleister, Spedition, plus ein chinesischer Lieferant
mit eigener Kontaktperson (`sarah.peng@schaufler.com.cn`).

## 10. Bestellpositionen (Modullieferungen)

Der Begriff "Modullieferungen" kommt in keinem Dokument vor. Das System trackt
durchgängig auf **Bestellpositionsebene**, nicht auf Bestellebene — jede Position hat
eigene Termin-, Wareneingangs- und Messbericht-Felder, auch wenn mehrere Positionen in
einer Bestellung oder einem Messbericht zusammen auftreten. Falls Schaufler eine explizite
Baugruppen-Sicht über mehrere Bestellungen hinweg braucht ("sind alle Teile für Baugruppe
X da?"), ist das aktuell nicht als eigene Fachseite vorgesehen.

## Weitere Dashboard-Seiten

**Unklarheiten** (`/unklarheiten`): zeigt E-Mails, die das System nicht sauber zuordnen
konnte. Typische Ursachen: keine erkennbare Bestellnummer, Absender keinem Lieferanten
zugeordnet, gemischte/ungewöhnliche Inhalte, kein belastbares Auslese-/Zuordnungsergebnis.
Unterstützt Suche, Filterung, Excel-Export. Nachrichten bleiben bewusst sichtbar, bis sie
fachlich geprüft und ggf. manuell nachverarbeitet wurden.

**Reporting** (`/reporting`): Frühwarnquote = Frühzeitige Warnungen / (Frühzeitige +
Späte Warnungen) × 100 %. Abweichungsgründe (Verteilung): Terminabweichung,
Preisabweichung, Mengenabweichung, Fehlende AB, Überfällige Lieferung, Fehlende
Dokumente, Messbericht unvollständig. Verfügbare Excel-Exporte:

| Export | Inhalt |
|---|---|
| Gesamtbericht | Zusammenfassung, ABs, Eskalationen, Lieferanten-Scores, Messberichte, Aktivitäten, Unklarheiten |
| Lieferanten-Bericht | Performance-Scores und Kennzahlen je Lieferant |
| Eskalations-Bericht | Offene/geschlossene Eskalationen, Gründe, fehlende ABs |
| Messberichte-Bericht | Messbericht-Vorgänge mit Vollständigkeitsstatus |
| Aktivitäten-Bericht | Agent-Protokoll inklusive Unklarheiten |

**Aktivität** (`/aktivitaet`): chronologisches Protokoll aller fachlichen und
betrieblichen Aktionen. Aktionstypen: AB-Verarbeitung, Weiterleitung, Eskalation,
Erinnerung, Liefertermin-Anfrage, Versanddokument-Anfrage, Transit-Warnung, Vessel
Tracking, ERP-Task, Unklarheit, Verarbeitungsfehler/Alarm. Volltextsuche, Zeitraumfilter,
Aktionstyp-Filter, Excel-Export.

**Steuerung** (`/steuerung`, nur Admin): Aktionen — Starten, Stoppen, Manueller Zyklus
(sofortiger vollständiger Verarbeitungszyklus), Neustart. Weitere Inhalte: Statusleiste mit
Systemstatus + letztem Lauf, letztes Zyklusergebnis (neue E-Mails, verarbeitete ABs,
Eskalationen, Fehler), Konfiguration der aktiven Anbindungen und Toleranzen,
Sprachumschaltung Deutsch/Englisch, Logs. Es gibt keine separate "Pause"-Schaltfläche —
fachlich übernimmt "Stoppen" diese Funktion.

**Anmeldung, Rollen und Zugriffe** (Kap. 15): zwei Anmeldewege — klassisch
(Benutzername/Passwort) oder Microsoft-Anmeldung über das Firmenkonto. Neue
Microsoft-Benutzer erhalten standardmäßig zunächst die Rolle Einkauf.

| Rolle | Standardseiten | Typischer Fokus |
|---|---|---|
| Admin | Steuerung, Benutzerverwaltung + alle weiteren Seiten | Systemaufsicht, Rechtevergabe, Betrieb |
| Einkauf | Auftragsbestätigungen, Lieferanten, Lieferungen, Unklarheiten, Reporting, Aktivität | AB-Prüfung, Eskalationen, Lieferantenkommunikation |
| Qualität | Messberichte, Auftragsbestätigungen, Reporting, Aktivität | Messberichte, fachliche Prüfung |
| Logistik | Lieferungen, Reporting, Aktivität | Liefertermine, Transporte, Sendungsverfolgung |

Standard-Startseiten: Admin → Steuerung, Einkauf → Auftragsbestätigungen, Qualität →
Messberichte, Logistik → Lieferungen. Zugriffsarten: rollenbasiert (Standardseiten der
Rolle) oder benutzerdefiniert (Admin schaltet einzelne Seiten gezielt frei).

## Glossar (Auswahl)

| Begriff | Erklärung |
|---|---|
| AB | Auftragsbestätigung |
| Ampel | Farbsystem (Grün/Gelb/Rot) für den Prüfstatus einer AB |
| ERP | Bestellsystem/Datenquelle, aus der die Bestellungen kommen |
| DMS | Dokumentenmanagementsystem (ELO) |
| ETA | Estimated Time of Arrival — voraussichtliche Ankunftszeit einer Sendung, laut Lastenheft 1:1 vom externen Tracking-Dienst übernommen, keine eigene Neuberechnung |
| Konfidenz | Wie sicher die KI bei der Erkennung von Daten war |
| Vessel Tracking | Sendungsverfolgung für Seetransporte |
| T1-Dokument | Zolldokument für bestimmte Transporte, separat weitergeleitet |
| Failure Queue | Interne Liste nicht sauber verarbeiteter Vorgänge zur Prüfung |
| Adapter | Technische Anbindung an externe Systeme (E-Mail, Bestelldaten, DMS, Tracking) |
