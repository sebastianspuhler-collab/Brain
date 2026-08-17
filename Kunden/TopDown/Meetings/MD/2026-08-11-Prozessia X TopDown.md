---
tags:
  - Lead
  - Erstgespräch
  - Rechnungsverarbeitung
  - EU-KI-Act
  - Schatten-KI
quelle: Prozessia X TopDown.docx (Notta-Transkript)
datum: 2026-08-11
kategorie: Lead
---

# Prozessia X TopDown

## Zusammenfassung
Erstgespräch zwischen Sebastian Spuhler und Dominik Nussbaumer (TopDown, ~20
Mitarbeitende, Automotive-Zulieferer, Standorte Verwaltung/Salzgitter/Eisenstadt,
TSAX-zertifiziert). Anwendungsfall: KI-gestützte Automatisierung der
Eingangsrechnungsverarbeitung, aktuell vollständig papierbasiert/manuell. Gespräch
deckte Anwendungsfall, Infrastrukturempfehlung (Hetzner + Azure OpenAI),
Datenschutz/EU-KI-Act-Compliance, Referenzen und weiteres Vorgehen ab. Sehr
positiver Gesprächsverlauf, Dominik bat aktiv um ein Angebot zur internen
Präsentation bei der Geschäftsführung.

## Teilnehmer
- Sebastian Spuhler (Prozessia)
- Dominik Nussbaumer (TopDown, dominik.nussbaumer@topdown-cf.com — laut Gespräch
  IT-Hintergrund/IT-Projektmanager)

## Kernpunkte

**Ist-Zustand bei TopDown (Eingangsrechnungen):**
- Rechnungen kommen klassisch per E-Mail-Postfach an
- Manuelle, händische Erfassung im ERP-System
- Zettel werden ausgedruckt, mit Belegnummern beschriftet, physisch durch die
  Freigaberunde gereicht und zurückgeführt
- Nach Freigabe: Zahlung, Ablage für Buchhaltung/Steuerberater
- Am Monatsende: Belege + Kontoauszüge gehen an den Steuerberater, der die
  Grundbuchungen erstellt
- TopDown nutzt selbst kein Buchhaltungsprogramm, Datenexport erfolgt über DATEV
- ERP-System: im Gespräch unterschiedlich benannt ("Globe Manager" bzw. später
  "Jobmanager" — Transkriptionsunschärfe, **Name mit Dominik verifizieren**)
- Zwei Rechnungsarten: mit und ohne erforderlichen Wareneingangsabgleich; bei
  Wareneingangspflicht müssen laut Dominik mehrere Parameter im ERP übereinstimmen,
  damit die Zuordnung automatisch erfolgen kann ("das sollte schon der Fall sein")

**Vorgeschlagener KI-Agent-Prozess:**
1. Agent überwacht das Rechnungs-Postfach (z.B. invoice@topdown-cf.com)
2. Klassifiziert eingehende Mail: ist das eine Rechnung?
3. Formale Prüfung: Betrag korrekt? Entspricht der Bestellung? Wareneingangs-Abgleich
   über ERP-Parameter, falls erforderlich
4. Automatische Übertragung ins ERP-System ohne manuellen Zwischenschritt
5. Weiterleitung an den Projektleiter zur inhaltlichen/sachlichen Freigabe
   (menschliche Prüfung bleibt bewusst im Prozess)
6. KI-Vorprüfung soll mit der Zeit die "Trefferquote" korrekter Rechnungen erhöhen,
   sodass bei der manuellen Freigabe weniger Klärungsbedarf entsteht
7. Danach ggf. weitere Automatisierung Richtung DATEV-Export möglich

**Infrastrukturempfehlung (Sebastian):**
- Cloud-Server mieten statt eigene Hardware kaufen — empfohlen: Hetzner
  (deutsch, EU-Server, güngstig, skalierbar per Abo-Anpassung)
- Sprachmodelle: OpenAI über Microsoft Azure, EU Data Boundary, AVV-Vertrag,
  Server in Frankfurt, verschlüsselt, keine Nutzung als Trainingsdaten
- Eigene/lokale KI-Hardware aktuell für den Anwendungsfall/diese Unternehmensgröße
  wirtschaftlich nicht sinnvoll (Modelle zu groß, Hardware zu teuer im Vergleich)
- Einmal aufgebaute Infrastruktur ist skalierbar für künftige KI-Anwendungsfälle
  (Einkauf, Vertrieb, Konstruktion) — Mehraufwand für Folgeprojekte sinkt deutlich

**Datenschutz & Compliance:**
- EU-KI-Verordnung seit 2. August 2026 in Kraft: verlangt lückenlose
  Dokumentation aller KI-gestützten Verarbeitungsschritte (jedes analysierte
  Dokument, jede gelesene/geschriebene/weitergeleitete E-Mail)
- Keine sensiblen Firmen-/personenbezogenen/Lieferantendaten in
  nicht-EU-konforme Tools (z.B. Consumer-ChatGPT)
- Prozessias Agenten sind von vornherein mit Dokumentations-/Audit-Trail gebaut
- Konzept "Schatten-KI": entsteht, wenn keine offizielle KI-Infrastruktur da ist —
  Mitarbeiter nutzen dann eigenständig Tools wie ChatGPT, mit entsprechendem
  rechtlichem Risiko
- Empfehlung: unternehmensinternen KI-Beauftragten benennen
- TopDown-Status: Mitarbeiter bereits für KI-Nutzung sensibilisiert; wegen
  Automotive-Branche und TSAX-Zertifizierung bisher eher Vermeidungsstrategie
  ("Vermeidung als Problemlöser")

**TopDown-Unternehmensdaten (aus dem Gespräch):**
- ca. 20 Mitarbeitende gesamt, 3 Standorte: Verwaltungsbüro (kein Publikumsverkehr),
  Vertrieb in Salzgitter, Infrastruktur/Projektmanagement in Eisenstadt (15–17 MA)
- Serverinfrastruktur: ein Hauptserver mit virtuellen Unterservern, Backup-Server
  mit NAS-System, Firewall — überschaubar, nichts Großes
- Automotive-Zulieferer, TSAX-zertifiziert, entsprechende Geheimhaltungspflichten

**Prozessia-Referenzen (von Sebastian genannt):**
- Kunden vor allem aus Baden-Württemberg/Schwäbische Alb: Automobilzulieferer,
  Werkzeugbauer, Maschinenbauer
- Ein größeres Lebensmittelunternehmen im Saarland
- Kundengröße meist 20–150 Mitarbeitende
- Schwerpunkte: Einkauf/Rechnungsverwaltung/Buchhaltung, Konstruktion/CAD-Daten,
  kaufmännische Bestellprozesse (ein- und ausgehend)
- Auch ein Projekt mit ZF (Formenbau) erwähnt — explizit NICHT die Zielgruppe
  (Konzernstrukturen zu träge/ineffizient); Zielgruppe sind kleine/mittelständische
  Unternehmen
- Prozessia-Team: 4 Personen (Sebastian, 1 Vertrieb, 1 Mitgesellschafter,
  1 Entwicklung); nutzt selbst ein "Company Brain" (internen KI-Chatbot mit
  Zugriff auf Mail/Kalender)
- Standort: Uni-Campus Saarbrücken (Innovationscampus) — **kein** Uni-Projekt,
  keine Investoren, eigenständiges Unternehmen aus ehemaligen Kommilitonen heraus

## Zusagen
- Sebastian: erstellt eine kurze Präsentation/Angebotsübersicht mit Leistungen
  und Stundensatz, Versand noch am 11.08. bzw. spätestens am 12.08.
- Dominik: bespricht die Übersicht intern mit dem Management, gibt erstes Feedback

## Nächste Schritte
- **Einzige offene Abhängigkeit:** Schnittstelle zum ERP-System muss geklärt/
  bestätigt werden — bei Vorhandensein ist der beschriebene Prozess direkt umsetzbar
- Geschätzte Projektlaufzeit: 8–10 Wochen ab Start (kann bei organisatorischen
  Komplikationen länger dauern)
- Fester Projektansprechpartner bei Prozessia, regelmäßige (wöchentliche)
  Abstimmung zu fachlichen Details
- Prozessia übernimmt: Server-Setup, Spracheinrichtung, datenschutzrechtliches
  Drumherum — in Abstimmung mit TopDowns IT/Verantwortlichen
- **Folgetermin: Freitag, 14.08.2026, 10:00–10:30 Uhr** (statt kommender Woche,
  da Dominik dann im Urlaub ist)

## Entscheidungen
- (keine formale Entscheidung — Dominik muss zunächst intern mit der
  Geschäftsführung abstimmen)

## Offene Punkte / zu prüfen
- Exakter Name des ERP-Systems ("Globe Manager" vs. "Jobmanager" laut Transkript
  uneindeutig)
- Ob die ERP-Schnittstelle (API bzw. Alternative) tatsächlich existiert

---

## Vollständiges Transkript

Prozessia X TopDown-20260811_093246-Besprechungstranskript
11. August 2026, 07:32AM
38 Min. 0 Sek.

Sebastian Spuhler Transkription gestartet

Sebastian Spuhler   0:03
Ne Notizen machen nebenbei und kann mich voll und ganz aufs Gespräch fokussieren.

Dominik Nussbaumer   0:09
OK.

Sebastian Spuhler   0:10
O.K., ja und zwar, du kannst erstmal erzählen, was überhaupt, ja, wenn wir jetzt mal davon ausgehen, dass wir 'nen K.I. Programm in der Buchhaltung machen, was du davon erwartest von so einem System, wo es aufhört, wo es endet, was es kann
Und äh, was du von mir erwartest hier heute, was ich dir dazu mehr erzählen kann.

Dominik Nussbaumer   0:33
Ja, also grundsätzlich unser Arbeitsweise momentan ist relativ. Ja, Steinzeit sagt der. Der Geschäftsführer immer, ähm, wir Thema Eingangsrechnungen beziehungsweise

Sebastian Spuhler   0:43
Mhm.

Dominik Nussbaumer   0:48
Buchhaltung. Wir erfassen die ganzen Belege heute manuell händisch. Das heißt, wir bekommen die klassisch ins E-Mail-Postfach geschickt und daraufhin wird das die Rechnung dann erfasst in unserem E. A. P. System.

Sebastian Spuhler   0:53
Mhm.
Mhm.

Dominik Nussbaumer   1:05
Das geschieht alles per Hand und.
Ja, die Zettel werden dann auch ausgedruckt. Beschriftet halt mit den Belegnummern und so weiter und gehen dann halt in die Freigaberunde, auch wieder physisch natürlich, und dann wieder retour.

Sebastian Spuhler   1:20
Mhm.

Dominik Nussbaumer   1:23
Wenn Freigabe erteilt, dann erfolgt die Zahlung und das wird dann abgelegt für die Buchhaltung und Steuerberater.
Am Monatsende bekommt ihr dann der Steuerberater die ganzen Belege mit den Kontoauszügen.

Sebastian Spuhler   1:32
Bye.

Dominik Nussbaumer   1:38
Da ist ein relativ großer Papieraufwand dahinter und ja, der erstellt dann die Grundierung in Buchungen. Prüf die dann halt nochmals und schick die unsere Tour.

Sebastian Spuhler   1:43
Mhm.

Dominik Nussbaumer   1:53
So mal der grobe Ablauf von den von unserer Eingangsrechnung.

Sebastian Spuhler   1:58
OK.

Dominik Nussbaumer   1:58
beziehungsweise die Haltung. Und der Plan ist halt schon, dass man das ja auch deutlich digitalisieren und vereinfachen, damit wir weniger Papieraufwand haben beziehungsweise die ganzen Abläufe sind sicher auch ja.

Sebastian Spuhler   2:08
Mhm.

Dominik Nussbaumer   2:15
Im System bei uns abbildbar, wahrscheinlich.

Sebastian Spuhler   2:18
OK, was für ein ERP-System nutzt du hier?

Dominik Nussbaumer   2:21
Benutzen den Globe Manager.

Sebastian Spuhler   2:24
Jobmanager, OK. Ja, nee, das ist immer wichtig zu wissen, was man E.E.P. Systeme hat, weil davon hängt es dann natürlich dann am Ende ab, ob das Ganze, ob so ein Projekt Erfolg hat oder nicht, ne? Weil ich kann mal gerade sagen, also ist ja, ja, um ehrlich gesagt, natürlich ein Anwendungsfall, den wir kennen. Es ist eigentlich immer das Gleiche mit.

Dominik Nussbaumer   2:32
Mhm.
Yeah.

Sebastian Spuhler   2:40
Im kaufmännischen Bereich, im bürokratischen Bereich mit KI-Automatisierung oder KI-Agenten, die da arbeiten. Ich kann das zum Beispiel nur am Beispiel sagen von unseren Einkaufsagenten, was die machen. Das machen sie übrigens auch mit Rechnungen. Rechnungen gehört jetzt eher in die Buchhaltung, aber wenn man was einkauft, dann bekommt man ja auch eine Rechnung davon und das geht alles ineinander über, meistens, ne?

Dominik Nussbaumer   2:52
Mhm.
Ja.

Sebastian Spuhler   2:59
Ich kann dir mal den Prozess da grob ja erzählen, wie das bei uns in der Regel läuft. Also es ist möglich, dass ein K.I. Agent das E-Mail-Postfach überwacht. Ja, das heißt, er schaut nur da drauf und wenn das dann irgendein

Dominik Nussbaumer   3:11
Okay.

Sebastian Spuhler   3:14
Ja, Buchhaltungs Postfach ist invoice@topdown.com oder sowas in der Art. Ja, genau sowas zum Beispiel. Ja, wird's wahrscheinlich sein. Dann kann man dem Agenten sagen: 'Okay, über wartet dieses Buchhaltungspostfach und schaut, ob deine Rechnung ist, ja.'

Dominik Nussbaumer   3:21
Genau, genau, ja.

Sebastian Spuhler   3:30
Das müsste man eigentlich relativ gut klassifizieren können, dass das eine Rechnung ist, oder kannst das selber überprüfen. Wenn es eine Rechnung ist, dann kann er die erstmal prüfen. Ja, oft haben Firmen einfach so.

Dominik Nussbaumer   3:35
Mhm.

Sebastian Spuhler   3:41
Ja, gewisse gewisse Dinge, die ne Rechnung erfüllen muss. Ja, da geht's dann um, ist der Betrag überhaupt richtig? Ist das das, was wir bestellt haben? Weicht das nicht von dem ab, was überhaupt im Wareneingang angekommen ist und so? Ne, da gibt's dann mehrere Prüfungsmöglichkeiten.

Dominik Nussbaumer   3:55
Genau.

Sebastian Spuhler   3:57
Also, so formalen, auf die man die Rechnung prüft, das kann der Agent übernehmen. Und dann, wenn man dann die Schnittstelle zum ERP-System baut, kann man auch einfach durch den Agenten, also ohne händische Arbeit, ohne dass irgendjemand dazwischen funkt, ins ERP-System die Daten übertragen und die Rechnung dort hochladen, ja.

Dominik Nussbaumer   4:13
OK.

Sebastian Spuhler   4:14
Wenn ihr das so macht, ja, das können wir von dort. Also, man kann quasi den Schritt vom E-Mail-Postfach.

Dominik Nussbaumer   4:15
Ja.

Sebastian Spuhler   4:20
Bis ins ERB-System können wir automatisieren und danach hast du gemeint, geht es mit einer Freigabe für die Buchhaltung weiter. Kannst du mal kurz erklären, was da genau an welchem Punkt bei euch passiert?

Dominik Nussbaumer   4:29
Mhm.
Vielleicht mal kurz ein Schritt zurück bei der bei der Erfassung. Da gibt's bei uns theoretisch 2 Optionen. Das heißt, wir haben bekommen Rechnungen, wo jetzt da vielleicht ein Wareneingang erforderlich ist und dort Rechnungen, wo keine erforderlich ist.

Sebastian Spuhler   4:36
Mhm.
Mhm.

Dominik Nussbaumer   4:50
Die Frage ist, ob obs da schon mal zu Einschränkungen kommt, weil ich mach mir halt schon so, dass wir den Wareneingangsbeleg dann in der Rechnung übernehme klassisch.

Sebastian Spuhler   4:58
Mhm.

Dominik Nussbaumer   4:59
Also, die Verknüpfung, die muss halt in dem Ablauf schon gegeben sein, dass man das, wenn es passt, dann automatisch erfolgt.

Sebastian Spuhler   5:07
Mhm.

Dominik Nussbaumer   5:07
Dass der Wareneingang übernommen wird und ihren Rechnungsbeleg.

Sebastian Spuhler   5:11
OK, ist der Wareneingang? Habt ihr das auch im ERP-System drin? Welche Bestellungen waren eingegangen?

Dominik Nussbaumer   5:16
Natürlich, ja. Also, gibt es verschiedene Parameter, die dann halt übereinstimmen müssen, damit das dann zugeordnet werden kann. Das sollte schon der Fall sein, wenn man sagt, wir ja, wir gehen den Weg.

Sebastian Spuhler   5:17
OK, ja.
Ja.
Mhm.
Genau, ja, ja, nee, nee, nee, das kann man auf jeden Fall machen. Solang das irgendwo im ERP-System dokumentiert ist, kann man das machen. Also grundsätzlich, um ein bisschen weiter aufzuholen, KI ist immer nur hört sich ein bisschen plump an, weil du das bestimmt auch schon mal oft gehört hast, aber es wirklich so ist eine Datenfrage, ne?

Dominik Nussbaumer   5:36
Ja, sicher.
Mhm.
Yeah.

Sebastian Spuhler   5:46
Und Datenfrage ist halt nicht immer nur Trainingsdaten, sondern halt einfach OK. Ist das Wissen, das die KI haben muss, irgendwo dokumentiert, ja?

Dominik Nussbaumer   5:54
Ja, natürlich.

Sebastian Spuhler   5:54
Also, steht das in irgendeinem Dokument, in irgendeinem System drin? Ja, ist das Wissen irgendwo drin? Also, nicht nur im Kopf von Menschen, ne? Und gibt es die Möglichkeit, da ranzukommen, irgendwie ja, für uns, wenn wir KI Agenten bauen. Und wenn das ERP-System 'ne Schnittstelle hat, was man prüfen muss, was ja bei den meisten ERP-Systems kein Problem ist, also dass die offene Programmierschnittstellen haben, ja.

Dominik Nussbaumer   6:02
Mhm.
Ja.
Mhm.

Sebastian Spuhler   6:14
Und wenn nicht, bekomme die auch meistens relativ leicht in 99 Prozent der Fällen. Dann geht das auch. Ja, dann kann man da Abfragen machen, Wareneingang ja, nein zum Beispiel, ne? Und davon kann man dann abhängig machen, was mit der Rechnung passiert und was eben nicht mit der Rechnung passiert. Dann kann man die auch einkategorisieren.
Ja, das Ganze kann man dann auch schön im Dashboard aufmalen, wo man dann ja die Rechnung sortiert nach 2 Kategorien zum Beispiel ne.

Dominik Nussbaumer   6:31
Mhm, OK.

Sebastian Spuhler   6:40
Und dort kann man das Ganze dann einsehen. Das ist eigentlich wirklich, wirklich mit K.I. sind wir da sehr, sehr flexibel dran, solange die Gegebenheiten da sind, ja, solange alle Daten verfügbar sind und wenn die rankommen, ne, dann kann K.I. auch ehrlich gesagt alles machen, was ein Mensch auch kann, ja, vor allem im

Dominik Nussbaumer   6:51
Ja.
Gut, das sollte jetzt kein Problem haben. Darstellen, ja.

Sebastian Spuhler   6:58
Genau, vor allem im kaufmännischen Bereich, nur halt deutlich effizienter, schneller und mehr Sachen gleichzeitig. Ne, das ist immer der Hauptvorteil daran. Genau, das heißt, das kann.

Dominik Nussbaumer   7:03
A.
OK.

Sebastian Spuhler   7:10
Das können wir auch machen und dann würden die Rechnungen einkategorisiert werden, würden kontrolliert werden, ins ERP-System übertragen und dann könnte man es theoretisch noch irgendwie, wenn man dann den Prozess weitergeht an den Steuerberater oder ins Buchhaltungsprogramm, könnte man auch noch automatisieren diesen Schritt.
Ja, je nachdem, was ihr da genau benutzt.

Dominik Nussbaumer   7:29
Genauso, wir benutzen jetzt selbst kein Buchhaltungsprogramm. Der Plan ist momentan, dass wir die ganzen Daten dann über Datev exportieren.

Sebastian Spuhler   7:33
Mhm.
Mhm.

Dominik Nussbaumer   7:41
Und ja, die ist damit und die ganzen Papierkram ab.
Bisschen ab, ne, ersetzt im Prinzip.

Sebastian Spuhler   7:51
Mhm, ja, das könnten wir machen. Ja, ja, klar. Ja, ja, klar. Hat auch eine Schnittstelle. Haben wir auch schon mit programmiert. Ja, genau.

Dominik Nussbaumer   7:52
Dartes ist dir bekannt? Schnittstelle Dartes? Ja, natürlich. Ja, genau, ja.
Genau, ja, auf jeden Fall zum Ablauf. Das ist die Rechnung ist erfasst und danach folgte die Freigabe. Was ich vorhin gemeint habe, die ist dann halt nach der Inhalts und sachlichen Prüfung. Das heißt, die geht dann an den.

Sebastian Spuhler   8:05
Mhm.

Dominik Nussbaumer   8:16
Projektleiter im Normalfall, dass der dann eine Info bekommt. Die Rechnung ist jetzt erfasst. Bitte um Freigabe und um Prüfung, jetzt einfach gesagt.

Sebastian Spuhler   8:18
Mhm.
Mhm.

Dominik Nussbaumer   8:27
Ja, der prüft die Rechnung, gibt vielleicht Anmerkungen, Ja, Nein-Bestätigung und die geht dann wieder retour. Wenn es Klärungsbedarf gibt, dann muss man schauen, wie man das dann dementsprechend handhabt.

Sebastian Spuhler   8:41
Mhm.
Genau, ja, ne, also ich würde dir dann

Dominik Nussbaumer   8:44
Ja, also ist ganz simpel im Prinzip. Also, wir haben jetzt da keinen Mörderprozess dahinter stehen.

Sebastian Spuhler   8:46
Ja, ja, ja, ja.
Ja, genau, also diese menschliche Prüfung, die würde ich ja immer noch drin lassen bei solchen Rechnungen, ne, die ist auf jeden Fall sehr wichtig, ne. Man kann zum Beispiel einhauen, dass der Agent, also ein K.I. Agent, dann so eine Vorprüfung macht auf gewissen Kriterien, ne, und dann, ja, und dann im Optimalfall erhöht man dann.

Dominik Nussbaumer   8:54
Yep.
Genau.

Sebastian Spuhler   9:05
die ja die Quote der Rechnungen, die Stimmen oder die die Pasten, erhöht man dann soweit, dass die bei der manuellen Prüfung, ne, dann das da gar keine bei der Freigabe Freigabe es gar keine Probleme mehr gibt, ne, dass man sich da auch Zeit sparen kann, ja. Das kann man alles mit der Zeit noch optimieren, ne. Man kann mit der Zeit kann man in der Regel immer mehr an KI Agenten abgeben,

Dominik Nussbaumer   9:18
Mhm, no.

Sebastian Spuhler   9:25
wenn man den mal eintrainiert hat, ne, aber es schadet auch nichts, klein anzufangen und dann das Ganze einfach mal auszuprobieren, ja, weil theoretisch der Automatisierungsgrad in der Theorie ist schon sehr, sehr hoch, was man alles machen kann, ne, nur ja, man darf nicht zu viel machen, man muss erst mal gucken, dass man 'ne K.I., kleine K.I. Infrastruktur aufbaut, also dass man so
So technisch und datenschutzrechtlich alles geregelt hat, ja außenrum, dass man dann mal reinkommt, einen Anwendungsfall findet, den auch richtig umsetzt und dann kann man danach immer weiter gehen. Und deswegen finde ich es auch so sinnvoll, wenn man dann gerade so einen konkreten Anwendungsfall hat wie du jetzt, ne, dass man da auch direkt loslegen kann, ne, weil ich meine, es ist jetzt.

Dominik Nussbaumer   9:47
Mhm.
Ja.

Sebastian Spuhler   10:04
Ja, und das, was ihr jetzt davor habt oder was ihr braucht, ist jetzt nichts, was keine neue Erfindung, die sich erst beweisen muss, ne? Das ist, das ist jetzt alles, sind alles relativ simple Anwendungsfälle, ne, die wir alle schon, die die wir schon relativ schnell gemacht haben, ne?

Dominik Nussbaumer   10:11
Definitiv nicht, na.
Is common knowledge quasi.

Sebastian Spuhler   10:20
Und dann lohnt es sich eigentlich auch gerade damit anzufangen und dabei auch noch so eine, ja, auch die Basis zu schaffen für weitere K.I. Anwendungen, ne. Weil ich meine, es ist ja so Dokumente und sowas, Dokumente analysieren, E-Mails empfangen, große Texte analysieren, Schnittstellen zwischen Systemen, Daten übertragen und sowas, ne. Das sind ja alles

Dominik Nussbaumer   10:20
Mhm.
Yep.

Sebastian Spuhler   10:40
machen, das kannst du ja nicht nur in in der Rechnungsverwaltung, sondern auch im im Einkauf, in Vertrieb, in der Konstruktion, überall gibt es das ja, ne. Das da gibt ja tausende Möglichkeiten, wie man das Ganze machen kann und das da ist noch relativ, ja eigentlich ein guter Einstiegsfall, muss man sagen, ne.

Dominik Nussbaumer   10:47
Yeah, definitely.

Sebastian Spuhler   10:56
Ähm, weils halt noch relativ simpel gehalten ist.
Habt ihr bisher schon euch Gedanken gemacht über ja KI Infrastruktur oder habt ihr da eine gewisse Compliance Regeln überhaupt? Habt ihr zum Beispiel verboten, euren Mitarbeitern KI zu benutzen, Stand jetzt oder wie heißt das geregelt?

Dominik Nussbaumer   11:14
Ja, grundsätzlich haben wir die Mitarbeiter schon darauf sensibilisiert, die wie die KI zu nutzen ist. Nachdem wir auch in der Automobilbranche tätig sind, haben wir diverse Geheimhaltungen, auch die wir erfüllen müssen, beziehungsweise auch eine T-Sax-Zertifizierung.

Sebastian Spuhler   11:26
Yeah.

Dominik Nussbaumer   11:31
Und da haben wir schon bisher versucht, das Thema weitestgehend einfach abzuwenden, dass wir sagen, wir müssen uns darüber Gedanken machen, wie man das am besten abwickeln lohnt.
Das heißt, das war eigentlich bis jetzt dann. Die ja Vermeidung von K.I. des der Problemlöser. Bisher und jetzt ist ja.

Sebastian Spuhler   11:52
Mhm, ja, ja, ja, ja. Vermeidung von Ja.

Dominik Nussbaumer   11:57
Bitte, bitte.

Sebastian Spuhler   11:58
Ja, sorry, wenn ich unterbrochen hab, aber Vermeidung von K.I. ist auch tatsächlich ein Problemlöser in dem Sinne, weil man dann einfach Strafen aus dem aus dem Weg geht, ne. Also es ist ja auch jetzt seit 2. August hier der E.U.A.I. Act in Kraft, ne. Und.

Dominik Nussbaumer   12:07
Ja, richtig.

Sebastian Spuhler   12:13
Der sagt quasi, also den mal kurz zusammengefasst: Der hat sehr, sehr viele Artikel. Nennt die, weiß ich selber nicht alle auswendig. Aber der Grundsatz von diesem Artikel ist: Man muss alles, was man mit KI macht, dokumentieren. Ja, jedes Dokument muss dokumentiert werden, was man analysiert, jeden Schritt, jede E-Mail, die geschrieben wird, die gelesen wird.

Dominik Nussbaumer   12:29
Okay.

Sebastian Spuhler   12:30
Jede Weiterleitung, alles muss dokumentiert werden, ja, auch aus datenschutzrechtlichen Gründen. Sie dürfen zum Beispiel keine sensiblen Firmendaten, personenbezogenen Daten in keine Lieferantendaten, zum Beispiel in JGBT oder Cloud, angeben, weil das US-amerikanische Unternehmen sind, ja.

Dominik Nussbaumer   12:43
Ja, Bluetooth.

Sebastian Spuhler   12:46
Da gibt es tausende Gründe, warum man das nicht machen darf. Trainingsdaten, die sind außerhalb von der E.U., das ist ganz schlecht. Und das darf man alles nicht und da muss man erstmal eine sichere Infrastruktur haben. Also sowohl aus dem rechtlichen Aspekt und die Unternehmen wollen logischerweise auch nicht, dass ihre Daten ihr Wissen abfließt, ne?

Dominik Nussbaumer   12:47
Yep.

Sebastian Spuhler   13:03
Also, generell auch an Wettbewerber und so, oder potenziell an Wettbewerber. Die Regierung, was weiß der Geier was, ne, die wollen berechtigterweise nicht, dass das Ganze, dass diese Daten abfließen. Und deswegen ist die Infrastruktur drumherum so wichtig, dass man da.

Dominik Nussbaumer   13:03
Gut drin, ja.

Sebastian Spuhler   13:18
Was flexibles, datenschutzkonformes findet, was man macht. Bei unseren Agenten ist es immer schon drin, die wir bauen, dass wir sagen: "OK, die haben sowieso eine Dokumentations-."

Dominik Nussbaumer   13:20
Mhm.

Sebastian Spuhler   13:29
Prozess dann, wo alles dokumentiert wird und wo man alles nachlesen kann. Ja, wir machen, wenn wir so 'n Projekt machen, machen wir auch die Infrastruktur so, dass man egal welche Daten man hat, dass man die ohne Probleme in die K.I. eingeben kann. Ja, weil das finde ich, sollte das Ziel sein von so einer K.I. Infrastruktur, dass kein Mitarbeiter sich mehr Gedanken machen muss.

Dominik Nussbaumer   13:41
Ja.

Sebastian Spuhler   13:47
Welche Daten er wo eingibt nachher oder dass man dann nicht mehr unterscheiden muss, OK, darf ich das jetzt mit KI machen und das vielleicht nicht und so? ne, Darum soll es am Ende einfach nicht mehr gehen. Darum darfst du auch nicht mehr gehen, ne? Das Problem ist halt oft bei Unternehmen, die Mitarbeiter, die sind ja nicht blöd. Die wissen ja, was so Chatbots können, ne?

Dominik Nussbaumer   13:50
Wichtige.
Mhm.
Yep.

Sebastian Spuhler   14:04
Und wissen dann auch, wenn sie eine Aufgabe haben oder eine E-Mail formulieren müssen oder irgendwas haben, ja, dass es auch schneller geht. Wenn sie das jetzt einfach mal in den Cloud oder Chat mit dir reinkopieren, ne, das wissen die, die sind nicht blöd, dass sie sich dadurch den Arbeitsalltag erleichtern können.

Dominik Nussbaumer   14:14
Ja, natürlich, natürlich.

Sebastian Spuhler   14:18
Und das ganze Thema nennt man Schatten K.I., ne? Schatten K.I. entsteht, wenn man keine richtige K.I. Infrastruktur Infrastruktur hat, ne? Und deswegen nutzen die Mitarbeiter schon so K.I., ja. Und das sind dann natürlich doppelt gefährlich wegen diesen ganzen potenziellen rechtlichen Konsequenzen und allem.

Dominik Nussbaumer   14:20
A.
Ja.

Sebastian Spuhler   14:35
Ja, und deswegen ist es unfassbar wichtig, dass man die KI-Infrastruktur so aufbaut, dass da alles drumrum passt. Das ist eigentlich gar nicht auch kein so großes Ding. Ja, man braucht gewisse Compliance-Vorschriften, was den EUAI Act angeht. Ne, das übernehmen wir eigentlich grundsätzlich alles.

Dominik Nussbaumer   14:47
Mhm.
OK.

Sebastian Spuhler   14:50
Mit unseren K.I. Agenten und es schadet halt nicht, wenn man im Unternehmen einen K.I. Beauftragten hat, der sich da allgemein mal ein bisschen mit dem Thema auseinandersetzt. Ja, also das schadet eigentlich nie.

Dominik Nussbaumer   14:59
Okay, okay.
Ja.
Okay.
Gut.

Sebastian Spuhler   15:11
Also, irgendwelche Fragen zum Thema Compliance?

Dominik Nussbaumer   15:17
Ich sag jetzt einmal nein, ich mein, wie gesagt, so so lange Datenschutz und die Sax damit abgedeckt ist halt, das ist das Wichtigste für uns eigentlich, dass man da jetzt dann nicht in die Quere kommen mit unseren Zertifizierungen.

Sebastian Spuhler   15:26
A.

Dominik Nussbaumer   15:31
Ja, das müssen wir doch immer beachten, wenn wir das dann umsetzen.

Sebastian Spuhler   15:34
Ja, ja, ja, genau. Also, ich kann grundsätzlich immer mal sagen, wie wir das machen. Ich weiß nicht, ob ihr habt ihr, wie groß ist eure Serverinfrastruktur bei euch? Also, was habt ihr da alles?

Dominik Nussbaumer   15:48
Die ist relativ überschaubar. Also, wir sind ein Unternehmen von circa 20 Mitarbeitern gesamt.

Sebastian Spuhler   15:53
Mhm.

Dominik Nussbaumer   15:53
Und ja, wir haben im Prinzip einen Hauptserver. Dort sind halt die ganzen virtuellen Unterserver, da aufgelistet am Backup-Server mit einem kleinen Backup-System mit so NAS-Systemen, die dann gespielt werden. Ja, und natürlich Firewall.

Sebastian Spuhler   16:07
Mhm.

Dominik Nussbaumer   16:10
Klassisch, also es ist jetzt da. Wir haben jetzt so eine große Infrastruktur, eigentlich bei uns.

Sebastian Spuhler   16:11
Mhm.
Ihr seid nur 20 Mitarbeiter auf 3 Standorten.

Dominik Nussbaumer   16:17
Yep.
Ja.

Sebastian Spuhler   16:20
Auf alle verteilt nur 20 Mitarbeiter, okay.

Dominik Nussbaumer   16:22
Ja, ja, in ist eigentlich nur Verwaltungsbüro.

Sebastian Spuhler   16:24
Hätt ich nicht gedacht, ja.

Dominik Nussbaumer   16:28
So, jetzt ja, kein Personenverkehr in dem Sinne, äh, in Salzgitter ist unser Vertrieb.

Sebastian Spuhler   16:32
Mhm.
Mhm.

Dominik Nussbaumer   16:36
Und in Eisenstadt ist eigentlich die ganze Infrastruktur und das Projektmanagement vorhanden.
So, da sind dann 15, 16, 17 weiter, je nachdem.

Sebastian Spuhler   16:42
Mhm.
O. K., ja gut, hätte ich, also ich hätte auf den ersten Blick hätte ich gesagt, wär 3 Standorten größer, ist aber, ja O. K., es ist ja auch bisschen was. Und zwar, ja nee, ich frag nur bei dieser Serverinfrastruktur, also ich kann einfach mal sagen, was so der normale Use-Kit ist, wie wir das machen, ne.

Dominik Nussbaumer   16:54
Yeah.
Ja, unbedingt bitte, ja.

Sebastian Spuhler   17:02
Wir empfehlen eigentlich immer 'nen Server erstmal zu mieten, ja, so 'n Cloud-Server zu mieten von dem seriösen deutschen Unternehmen zum Beispiel wie Hetzner, ja. Aber das hat den Grund, ja, es ist deutlich weniger Aufwand, ja, man kann das einfach mieten, die Rechenressourcen.

Dominik Nussbaumer   17:10
OK, mhm.

Sebastian Spuhler   17:20
Auf Anfrage kaufen, wie man gerade Lust hat. Ja, das heißt, man wird es halt für ein KI-Agehen, würde man am Anfang dann nicht allzu viel bezahlen, ja, weil das nicht allzu viel Rechenleistung braucht. Die sind sicher, die sind in der EU. Ja, da muss man sich überhaupt keine Gedanken machen und man kann die Sachen.

Dominik Nussbaumer   17:22
Okay.
OK.

Sebastian Spuhler   17:35
Die Dinge einfach skalieren. Ja, man kann, wenn ihr jetzt keine Ahnung, noch 34 weitere KI-Projekte irgendwann habt, dann müsst ihr nicht physisch irgendwie ja neuen Serverraum kaufen oder so, sondern dann müsst ihr einfach per Klick kann man einmal das Abo vergrößern, ne? Und dann habt ihr da mehr Rechenleistung.
Ja, das ist ehrlich gesagt das Beste, was ich machen kann. Empfehlen wir auch immer. Also, wie gesagt, ich, wir sagen auch grundsätzlich OK, wenn das Unternehmen eine eigene riesige Server-Infrastruktur und die bestehen da drauf, dass wir darauf die Anwendungen drauf installieren, dann machen wir das. Aber meine Empfehlung ist immer ne.

Dominik Nussbaumer   17:52
OK.

Sebastian Spuhler   18:06
Am pragmatischsten ist dieser hetzender Server, ja.

Dominik Nussbaumer   18:11
Frage dann, was wäre das Ponton dazu in Hardware, wenn man sich das selbst beschaffen würde?

Sebastian Spuhler   18:20
Wenn man sich das selbst beschaffen würde, dann müsste man sich überlegen, was man für für 'n Gerät holt. Dann könnte man sich zum Beispiel 'nen Server oder so 'n kleinen Spa könnte man sich kaufen. Das Ding kostet 'n paar 1000€, Da kommt es dann natürlich drauf an, was man machen will. Also es gibt gewisse Server, die sind für K.I. Modelle spezialisiert, K.I. Sprachmodelle

Dominik Nussbaumer   18:33
Mhm.

Sebastian Spuhler   18:39
Modelle, ja, sind die spezialisiert, aber die Kosten meistens insgesamt ist das finanziell noch nicht so lohnenswert wie ein hetzender Server zum Beispiel, ja, einfach weil, weil vor allem das Sprachmodell, da kommen wir auch gleich dazu,

Dominik Nussbaumer   18:40
Okay.
OK.

Sebastian Spuhler   18:56
Weil das Sprachmodell dann nutzen wir zum Beispiel die Sprachmodelle von Open AI, die in Deutschland betrieben werden. Ja, also ihr nutzt ja bestimmt auch Microsoft, ne?

Dominik Nussbaumer   19:03
OK.
Ja.

Sebastian Spuhler   19:07
Microsoft hat ja die EU Data Boundary mit Microsoft hat ja jedes Unternehmen, das das nutzt auch nen AVV Vertrag ja, das heißt, man kann die Sprachmodelle von Open AI kann man nutzen.

Dominik Nussbaumer   19:18
OK.

Sebastian Spuhler   19:20
Auf Microsoft Basis, ja, und die sind dann auf Servern in Frankfurt. Ja, die Daten sind dann verschlüsselt. Die werden nicht für Trainingsdaten verwendet. Das ist alles safe, das ist alles sicher. Ja, das ist halt das Pragmatischste, was man machen kann, weil da kann man auch einfach so viel Sprachmodelle, wie man nutzt, also so viel Tokens, wie man nutzt. Du weißt, was Tokens sind, ja.

Dominik Nussbaumer   19:38
Mhm, ja.

Sebastian Spuhler   19:39
genau, hast du auch, glaub ich, 'nen kleinen IT-Hintergrund, also wenn ich es richtig in Erinnerung hab, oder bist IT-Projektmanager, genau, ja, also deswegen Tokens, das ist sind ja einfach die, ja, diese

Dominik Nussbaumer   19:46
Mhm, ja, oberflächlich, ja.

Sebastian Spuhler   19:55
Die diese Teile an Zeichen, die man eben die über die das eben abgerechnet wird, wenn man eine ein KI Modell nutzt.

Dominik Nussbaumer   20:02
Genau.
Yep.

Sebastian Spuhler   20:15
Infrastruktur hat man vorinstalliert und die muss man dann quasi nur monatlich bezahlen. Ja, das ist so ein bisschen der, der der Punkt dahinter. Man kann sich auch überlegen, OK, was für ein Rechner, was für ein Server, was für ein Spark oder was für eine Speicherkarte man sich holt, ne, wenn man das Ganze lokal machen will.

Dominik Nussbaumer   20:30
Mhm.

Sebastian Spuhler   20:32
Da werden wir auch hinkommen, irgendwann, aber für kleine mittelständische Unternehmen ist es aktuell einfach finanziell lohnt es sich mehr, wenn man das Ganze outsourced.
Weil also, wenn ich es jetzt ganz lokal machen wollen würdet, ja, die Sprachmodelle, die ihr zum Beispiel braucht, damit die wirklich diesen Rechnungseingang, den wir grad besprochen haben, richtig absolvieren können, damit die das wirklich verlässlich, die Dokumente analysieren können, ja.

Dominik Nussbaumer   20:54
Mhm.

Sebastian Spuhler   20:59
Die sind zu groß, als dass ich das also die sind so groß, dass die Hardware dafür zu teuer wäre im Vergleich zu der anderen Alternative, ja.

Dominik Nussbaumer   21:09
OK.

Sebastian Spuhler   21:10
Ja, das kann sich noch ändern. Ne, muss man sich auch alles immer im Detail anschauen. Aber aktuell sind wir noch an dem Punkt, wo das halt einfach die beste Alternative ist, vor allem wenn man einfach mal einsteigen will, ja.

Dominik Nussbaumer   21:14
Mhm.
Natürlich.
OK.

Sebastian Spuhler   21:22
Kann ich, kann ich das nur empfehlen. Und wenn ihr sagt "OK, ich habe jetzt keine so große Serverinfrastruktur", dann würde ich auch nicht da irgendwie rumprobieren, da irgendwie ein KI-Modell noch auf ein bestehendes System zu quetschen, sondern einfach mal.
Ja, den Headsner Server holen die die Kosten insgesamt, die sind sehr, sehr überschaubar und da einfach mal loslegen und dann gucken, wie es anläuft. Ja, das wäre jetzt so meine Empfehlung.

Dominik Nussbaumer   21:44
OK, ja, also auf einem bestehenden Server oder Geräte zu installieren, glaube ich, ist eh keine Option. Die SAM wird ja sicher nicht ausgelegt von der von den Ressourcen her, das.

Sebastian Spuhler   21:51
Mhm.
Mhm.
Und wie gesagt, das ist so 'n bisschen Aufwand, das dann insgesamt einzurichten mit allem. Also, wenn man dann mal das Sprachmodell mit Microsoft Azure installiert hat und da sein seine Sprachmodelle aufgebaut hat, sein Headster Server eingerichtet hat, ne.

Dominik Nussbaumer   21:58
Ja.

Sebastian Spuhler   22:12
Dann hat man ja auch ein skalierfähiges System, ja, dass man dann für jeden weiteren K.I.R. gehen oder für jede Erweiterung einfach nicht mehr groß erweitern muss. Das heißt, der Aufwand nach dem ersten Projekt wird in Zukunft deutlich weniger sein, dann für euch.

Dominik Nussbaumer   22:19
Mhm.
OK.

Sebastian Spuhler   22:29
Wenn man das einmal aufgebaut hat, ne? Und da ist halt so ein kleines, überschaubares, also so ein Prozess, der jetzt relativ überschaubar ist, wie der von den Rechnungen zum Beispiel.
Der ist ja ein relativ dankbarer Anwendungsfall, weil da muss man sich ja, da kümmert sich in einem einmal um die Infrastruktur. Wir wissen, wie das funktioniert, wie man so was baut.
Das Einzige, was wir dann noch schauen müssen, ist, dass wir es mit dem EMP-System verbunden bekommen und das einrichten. Ne, aber wenn das steht, dann ist ein Grundstein quasi gelegt für alles Weitere.

Dominik Nussbaumer   22:54
Mhm, genau, genau.
OK.
Ja.
Ich sag jetzt nochmal, soweit alles klar. Die Frage ist, wie werden jetzt so die Vorgehensweise dann? Wie werden die nächsten Schritte an sich?

Sebastian Spuhler   23:16
Mhm.
Also.
Also, die nächsten Schritte, ja.

Dominik Nussbaumer   23:20
Beziehungsweise, wie wie wird das dann bewertet? Jetzt, welche Ressourcen das jetzt da nötig sein, um das umzusetzen?

Sebastian Spuhler   23:28
Ja, also was wir immer brauchen, ist die einzige, ja gut, die einzige große Lücke ist tatsächlich die Schnittstelle zum ERP-System. Die müssten wir dann klären, ob die existiert. Wenn die existiert, ist perfekt, dann kann man es genauso umsetzen, wie ich es gerade gesagt hab.

Dominik Nussbaumer   23:37
Mhm.

Sebastian Spuhler   23:43
Ja, und wenn das warum auch immer nicht gehen sollte, wovon ich nicht ausgehe, ne, da muss man schauen, ob man da eine Zwischenlösung findet oder so, ne. Aber das ist eigentlich das Einzige, was wir brauchen. Also, muss das jetzt auch nicht hier komplizierter machen, alles ist ne, wenn.

Dominik Nussbaumer   23:43
Ja.

Sebastian Spuhler   23:59
wir das mit dem K.I. Agenten machen, das wir übernehmen können, ist halt das ganze datenschutzrechtliche Drumherum, den Server, das Sprachmodell, das können wir alles einrichten oder mit eurer I.T., mit den Verantwortlichen einrichten, ne, wer auch immer dafür zuständig ist.

Dominik Nussbaumer   24:12
Yep.
Mhm.

Sebastian Spuhler   24:14
Das wird auch eigentlich kein Problem sein. Und ja, nee, allgemein in so einem Prozess ist es immer so, dass man halt miteinander miteinander sprechen muss, die Leute von der Buchhaltung mit reinnimmt, die Leute von der IT mit reinnimmt. Das wird nicht zu verhindern sein, ne, dass man da ein bisschen Zeit aufwendet, ne, das ist immer so.

Dominik Nussbaumer   24:29
Natürlich.
Ja.

Sebastian Spuhler   24:32
Es ist noch immer gerade bei solchen Prozessen, die ein bisschen die ein paar Schritte umfassen, ist auch immer so, dass es Kleinigkeiten gibt, an die man am Anfang gar nicht gedacht hat, die man irgendwie lösen muss, ne. Aber ja, das sind so die aus meiner Erfahrung aus die Sachen, wo man einfach durch muss.

Dominik Nussbaumer   24:42
Mhm.

Sebastian Spuhler   24:50
wo auch immer zu lösen sind, normalerweise, ne, wo auch immer optimiert werden kann. Und deswegen ist halt wichtig, dass wir jetzt einen Scope haben, ja, wo wir sagen, okay, das wär das Anwendungsprojekt, da fängt's an, da hört's auf, ne, das soll der Agent können, ja, und dafür braucht man die Infrastruktur.

Dominik Nussbaumer   24:58
Mhm, yeah.
You know.

Sebastian Spuhler   25:07
Wenn du auch sagst: 'OK, wir holen einen neuen Server, wir mieten den bei Hetzner, was ich empfehle, dann ist gut. Wir machen Sprachmodell bei Azure Open A.I. Dann sind infrastrukturtechnisch eigentlich alle Ressourcen geklärt. Ja, also da musst du jetzt kein riesengroßes Ding draus machen und ein größeres Ding altes ist.
Da würde ich dann tatsächlich schauen, dass man da in die, ja einfach in die Umsetzung kommt und am wichtigsten ist halt, dass du da ein Ansprechpartner fürs E.R.P. System findest, um die Schnittstellen dort zu bauen, weil eine Schnittstelle zum E.R.P. System ist mit das Wichtigste für ein K.I. Agent in der Industrie allgemein, ne.

Dominik Nussbaumer   25:40
No.

Sebastian Spuhler   25:41
Also nicht nur Rechnungen verwalten, sondern allgemein der ganze kaufmännische Abwechslungsprozess mit Lieferanten, mit Kunden, mit allem. Wenn da die Schnittstellen stehen, dann ist das Potenzial quasi unendlich. Ja, wie man sich das Leben einfacher machen kann, das wirklich.
wirklich Wahnsinn und deswegen wären das so die wichtigsten Sachen, die man erklären müsste und ansonsten ja, steht eigentlich alles soweit. Von meiner Seite aus.

Dominik Nussbaumer   26:12
OK.
Welche Kunden hast du als Referenzen? Vielleicht in der gleichen Branche? Gibst du Kunden?
Oder ist es draußen Datenschutz?

Sebastian Spuhler   26:22
Ja, wir, also genau, wir haben, wir sind tatsächlich, also wenn ihr nur 20 Mitarbeiter habt, seid ihr tendenziell noch eher kleiner als die meisten unserer.
Kunden, wir haben viel aus Baden-Württemberg, aus der Schwäbischen Alb, Automobilzulieferer, Werkzeugbauer, Maschinenbauer. Wir haben hier im Saarland haben wir einen relativ großen Lebensmittel.

Dominik Nussbaumer   26:33
Mhm.
OK.

Sebastian Spuhler   26:44
Relativ große Lebensmittelunternehmen als Kunde. Ja, die sind zwar jetzt nicht in der Industrie, also in der Automobilindustrie tätig, aber die Vorgänge sind die gleichen. Also, es macht keinen Unterschied, ne, ob man jetzt ja irgendwie Getreide einkauft oder irgendwelche Werkzeugteile.

Dominik Nussbaumer   26:47
Mhm.
Ja.

Sebastian Spuhler   26:59
Und ja, und das sind so die, die wir grundsätzlich haben in der Größe, teilweise von ja, von 20 bis zu 150 Mitarbeitern im Allgemeinen. Das sind so ein bisschen unsere Referenzen und die, also was wir meistens.

Dominik Nussbaumer   27:09
OK.

Sebastian Spuhler   27:16
machen, ist die Bereiche, in denen wir unterwegs sind, sind Einkauf, vor allem Rechnungsverwaltung, also Buchhaltung, Konstruktion, C.A.D. Daten, sowas in der Art kaufmännischer Abwechslungsprozess, wenn man selber Bestellungen aufgibt, ja.

Dominik Nussbaumer   27:28
OK.

Sebastian Spuhler   27:32
Oder wenn man, wenn eingehende Bestellung bei einem selber reinkommt, ne sowas in der Art einfach ne, das sind so die die die klassischen Fälle, die wir betreuen.

Dominik Nussbaumer   27:36
Ja, OK.

Sebastian Spuhler   27:42
Quasi und ja, wir haben ja auch mit der mit der ZF ein Projekt, sage ich jetzt mal, da geht es um Formenbau. ne, Die sind ja auch hier aus dem Saarland relativ nah, ne, aber mit so einem Unternehmen der Form ist es insgesamt sehr, sehr unangenehm zu arbeiten, weil da sind halt einfach also.
bis da mal eine Entscheidung getroffen ist, das dauert gefühlt Jahre. Und das ist und bis man da mal den richtigen Ansprechpartner für irgendwas gefunden hat, das ist alles sehr, sehr ineffizient und ist halt nicht unsere Zielgruppe, ne. Das unsere Zielgruppe sind halt eher kleine und mittelständische Unternehmen.

Dominik Nussbaumer   28:02
Mhm.
Ja, verstehe. OK.

Sebastian Spuhler   28:16
weil die auch am meisten, also weil die auch ja großen Bedarf haben, auch teilweise weit hinterherhängen, wie ihr sagen würde, teilweise in der Steinzeit hängen, ne? Und weil da man mit denen auch einfach besser zusammenarbeiten kann, weil da die Wege und so kürzer ist und das ist für.

Dominik Nussbaumer   28:25
Nächste, ja.

Sebastian Spuhler   28:31
Ja, und deutlich angenehmer. Genau, ja.

Dominik Nussbaumer   28:37
Okay.
Das hat, wie wie groß ist dann dein Team oder wie groß hat sie das Unternehmen oder wie wie sagt sie es dann aufgestellt? Wie sagt sie dann?
Uni am Campus, wenn du das vergessen oder wie?

Sebastian Spuhler   28:50
Wir sind ja, wir sind am Uni-Campus, also wir gehören nicht zur Uni, ne, wir sind nicht nur, also wir, wir haben rechtlich nichts mit Uni zu tun. Hier am Uni-Campus ist halt wie in den, um Gottes willen, das will ich, wenn wir die nichts damit zu tun haben. Ich hab zwar hier studiert und so, ne, und da ist die Verbindung leicht da, ne.

Dominik Nussbaumer   28:55
OKOK.
Ist kein Uni Projekt.
Okay.
Yep.

Sebastian Spuhler   29:08
Also, das Ganze ist auch aus dem aus der Uni raus, also ja, aus ehemaligen Kommilitonen raus entstanden, ne? Aber generell am Uni-Campus sind ja sehr, sehr viele Unternehmen, die hier angesiedelt sind, ne? Wir haben ja damals angefangen und das Ganze einfach sinnvoll wegen dem Netzwerk, das man hier hat.
wegen den, ja, die ganzen, die ganzen Infrastruktur, Büroräume, die wir ja hier haben und so und alles und die ganzen Leute, die hier rumlaufen, dieser Innovationscampus hier an der Uni Saarbrücken, ne, das ist halt einfach was, das will man nicht nicht abgeben, ja, ist halt einfach schon gut und deswegen ist unser

Dominik Nussbaumer   29:38
Mhm.

Sebastian Spuhler   29:40
Hauptplatz am Campus, quasi unsere, ja, unser Büro. Aber wir haben nichts mit der Uni zu tun. Also, wir sind, wir haben keinen Investor oder sonst irgendwas, wir sind ein eigenständiges Unternehmen, das hier einfach den ihren Standort hat, ne.

Dominik Nussbaumer   29:48
Yep.

Sebastian Spuhler   29:56
Das ist quasi, das ist quasi alles, um das es geht. Genau, ja, und wir sind insgesamt, sind wir.

Dominik Nussbaumer   29:56
OK, now, let's go, let's go.

Sebastian Spuhler   30:04
Teammitglied, Team umfassend 4 Leute, ja. Außer mir noch einen Vertriebler, einen Mitgesellschafter und einen in der Entwicklung quasi, ne. Wir brauchen auch ehrlich gesagt nicht viel mehr Leute, weil ja.

Dominik Nussbaumer   30:08
OK.
OK.

Sebastian Spuhler   30:19
Wir predigen ja quasi, dass man viel Kosten sich einsparen kann und Aufgaben automatisieren kann mit KI. Ja, das muss man dann natürlich auch vorleben. Ja, also wir, bevor man.

Dominik Nussbaumer   30:27
Ja, verstehe.
Ja, müsste schon alles automatisiert werden.

Sebastian Spuhler   30:34
ja, ja, ja, ja, genau. Nee, also wir haben noch, also wie ich, ich hab zum Beispiel, wir haben zum Beispiel so ein Company Brain, sag ich jetzt mal, das ist wie so ein Chatbot. Ja, der hat quasi Zugriff auf alle meine. Meine Mails, Kalender, sonst irgendwas, ja, also quasi, ich bräuchte zum Beispiel keine Sekretärin oder sowas, ne?

Dominik Nussbaumer   30:35
******.
Mhm, OK, ja.
Mhm, OK.

Sebastian Spuhler   30:53
das Geld kann ich mehr sparen. Ja, so, so kann man es ungefähr, so kann man es ungefähr ausdrücken. Generell solche Aufgaben haben die halt alles automatisiert und wenn man weiß, wie man K.I. richtig einsetzt, dann ja, kommt man auch so klar. Also wir kommen auch so sehr, sehr gut klar von den Kapazitäten aktuell her.

Dominik Nussbaumer   31:10
Mhm, OK.

Sebastian Spuhler   31:12
Und ja, das kann insgesamt so weitergehen.

Dominik Nussbaumer   31:17
Wie lange werden Sie umsetzen, dann für so ein Projekt circa?

Sebastian Spuhler   31:22
Ich schätze mal, 8 bis 10 Wochen. Wäre so mein Tipp. Ja, also bei so einem Projekt ist es jetzt nicht allzu groß, aber natürlich trotzdem einiges an ja, Testaufwand, Programmieraufwand, Kommunikationsaufwand, vor allem, ne, wenn es um den Preis geht und so.

Dominik Nussbaumer   31:25
Mhm.
Danke.
Mhm.

Sebastian Spuhler   31:38
Da muss man immer ein bisschen Puffer einplanen. Deswegen sage ich, ab Start, wenn alles geklärt ist, wären es acht bis zehn Wochen. Ne, da muss man dann also, wir haben dann meistens so, machen wir das so, dass wir dann einen Projektansprechpartner haben. Das wäre es dann du oder jemand anderes, ne, und der kümmert sich dann um alles und.

Dominik Nussbaumer   31:51
Mhm, yeah.
So.

Sebastian Spuhler   31:54
Wenn es denn irgendwelche ja betriebswirtschaftlichen Details gibt oder fachspezifischen Details gibt bei euch, die wir nicht wissen können, wo wir wissen müssen, ne, dass man da 'n Meeting macht und das klärt, am besten jede Woche und dann ist so der Regelzeitraum 8 bis 10 Wochen, kann auch länger dauern, je nachdem welche Organisation.

Dominik Nussbaumer   32:00
Yep.
But du wieder.

Sebastian Spuhler   32:10
Welche organisatorischen Komplikationen da reinkommen, damit muss man immer damit rechnen, dass es so etwas gibt oder man es besser mal einplant. Aber ich hätte gesagt, acht bis zehn Wochen ist eine gute Range.

Dominik Nussbaumer   32:14
Mhm.
OK.
OK.
Ja, ich will sagen so weit.
Soweit so, alles klar. Ich muss jetzt da trotzdem die dich bitten, dass du vielleicht ein Angebot in dem Sinne stellst, damit du was präsentieren kann bei uns jetzt auch intern.

Sebastian Spuhler   32:43
Mhm, ja klar, ja.

Dominik Nussbaumer   32:44
Oder eine Übersicht jetzt da mit den Leistungen, die jetzt da umfasst sind, oder mit dem Stundensatz, wie auch immer, damit du was. Ich muss auf jeden Fall was präsentieren können, ne? Weil das ist doch eine Entscheidung. Das ist doch nicht so einfach zu treffen, auch auch wenn wir ein kleines Unternehmen sind, aber.

Sebastian Spuhler   32:54
Ja, ja, ja, klar, ja.

Dominik Nussbaumer   33:01
Ja.
Natürlich muss ich das auch der Geschäftsführung präsentieren, wenn man sowas auch angeht. Und ja, ich würde dich bitten, da kurze Übersicht vielleicht zu schicken.

Sebastian Spuhler   33:05
Mhm.
Mach ich sowieso. Das mach ich sowieso. Wie gesagt, wir haben jetzt ja in dem Mitglied sind wir sehr, sehr weit gekommen. Ne, wir haben jetzt einen guten Scope, was das Ganze angeht, was der KI-Agent können soll. Ne, wenn ich das Ganze zusammengefasst habe, dann.

Dominik Nussbaumer   33:15
Ja, ja.
Mhm.
Yep.

Sebastian Spuhler   33:27
ja, kann ich auch relativ gut abschätzen, was für Aufwendungen da für uns drauf kommt, wenn wir das bauen. Ja, das kann man eigentlich relativ schnell einschätzen. Und ja, da würde ich dir da, was das angeht, hinsichtlich dessen eine Rückmeldung geben, in welcher Form auch immer. Und ja, das bekommen wir auf jeden Fall hin, weil wie gesagt, man muss es nicht weiter in die Länge oder komplizierter machen als es ist. Wir

Dominik Nussbaumer   33:30
Mhm, yo.

Sebastian Spuhler   33:47
bin jetzt schon relativ weit gekommen in dem Meeting hier, ne. Da kann ich auch dann ja in den nächsten Tagen und Wochen direkt zum Punkt kommen und sagen, was ich euch konkret anbieten kann, was wir machen, ne. Und dann ja, kannst du das ja mal intern präsentieren und dann

Dominik Nussbaumer   33:49
Mhm.
Yep.
Definitiv.

Sebastian Spuhler   34:03
Hätte ich einfach mal gesagt, würde ich uns nächste Woche noch mal oder heute in einer Woche ungefähr noch mal einen Termin reinlegen, wo wir dann schauen oder wo du dann sagst "OK, da ist Update." Ich habe das Ganze mir angeguckt, habe es vielleicht schon angesprochen oder so. Ne, so ist das Ganze intern angekommen.

Dominik Nussbaumer   34:14
Mhm.

Sebastian Spuhler   34:18
Wo wir uns noch mal austauschen und einfach schauen, wie es weitergeht. Ja, weil wie gesagt, ich also kein Zeitdruck von meiner Seite aus. Ne, ich sag nur, wir sind sehr weit gekommen heute insgesamt, ne und.

Dominik Nussbaumer   34:25
OK.
Ja.

Sebastian Spuhler   34:30
Jo, also von von meiner Seite aus kann ich da relativ schnell bei diesem Anwendungsfall sagen, was da auf euch zukommt und ich würde dann einfach sagen, dass wir uns nochmal hören. Nächste Woche war ich schon mal grad in den Kalender. Wie sieht's bei dir nächste Woche aus von
Den Zeiten her.

Dominik Nussbaumer   34:49
So.

Sebastian Spuhler   34:51
Also, ich könnte zum Beispiel nächste Woche um halb zehn Grad wiedersehen, um diese Uhrzeit.

Dominik Nussbaumer   34:59
It's musical could chat on.
Ja, des mit.
Oder vor.
Ich würd dir noch die Info geben für nächste Woche. Ich bin nämlich, ich bin nämlich im Urlaub nächste Woche.

Sebastian Spuhler   35:26
Alex, du bist im Urlaub. Gut, der Mama, dann können wir auch 2 Wochen machen.

Dominik Nussbaumer   35:29
Die Die Frage ist, ob wir es die Woche vielleicht noch schaffen am Freitag.
Wenn du sagst, du kannst es vorab schicken, vielleicht, oder bis dahin schicken die Übersicht und würde versuchen, dass ich das noch mit dem Management bespreche für erstes Feedback.

Sebastian Spuhler   35:34
Am Freitag.
Mhm, ja, ja, genau. Also, Präsentation oder sowas bekomme ich auf auf jeden Fall bis diese Woche noch hin, ne? Das kriegen wir hin und dann können wir auch schon eigentlich am Freitag machen, Freitagmorgen oder so, ne? Also, wenn das bei euch so schnell geht, dann da schick ich dir, versuch ich noch dir heute Abend oder so oder.

Dominik Nussbaumer   35:50
Ja.
Yeah.
Ja, das wäre vielleicht besser.

Sebastian Spuhler   36:02
Irgendwann im Laufe des Tages. Ich habe jetzt noch ein paar Meetings, aber im Laufe des Tages versuche ich dir.

Dominik Nussbaumer   36:05
Ja, es reicht auch morgen oder so. Es ist da kein Stress, nur ich würde das dann mal kurz besprechen und dann erst das Feedback geben, wie du ja, wie man da zu stehen.

Sebastian Spuhler   36:08
Ja, ja, genau.
Ja.
und dann versuch ich dir da eine kleine Präsentation zu erstellen und ja, dann können wir eigentlich schon direkt am Freitag machen. Ich schau noch mal grad, wie es bei mir da terminlich aussieht. Also irgendwas ist frei, das weiß ich auf jeden Fall. Ich schau nur noch grad was und zwar, ich hab am Freitag eigentlich die ganze Zeit

Dominik Nussbaumer   36:23
Mhm.

Sebastian Spuhler   36:32
Zeit wollen wir grad ähm ja 10:00 Uhr machen.

Dominik Nussbaumer   36:34
Mhm.
Ja, gerne, gerne.

Sebastian Spuhler   36:39
Gut, dann mach ich das uns gerade hier und ähm.
Planen uns das hier ein, dass wir freitags 10:00 Uhr machen und dann ja freue mich, dass das so schnell klappt, dass du da so gut dahinter bist.

Dominik Nussbaumer   36:53
Ja, sonst vergeht nicht mehr so viel Zeit und den Rest des Arbeits, wenn wir schon dran sind, dass wir das vielleicht einmal gleich vertiefen oder versuchen zu vertiefen und dann Dann können wir noch entscheiden, wie wir weitermachen.

Sebastian Spuhler   36:53
Mhm.
Mhm.
Ja, ja, ja, ja, wie gesagt, also ich habe auch Projekte, da muss einiges, da sind die Anforderungen von allen Seiten deutlich komplizierter als hier, ne, oder die sind deutlich spezifischer. Das hier ist 'n Anwendungsfall, da spricht nichts dagegen, das Ganze, ja,

Dominik Nussbaumer   37:11
Ja.

Sebastian Spuhler   37:18
Nicht überhastet, ne, aber ja, zügig und fokussiert das Ganze durchzuziehen, ne. Also, 14.8. ist am Freitag, 10 bis 10:30 Uhr schick ich grad 'ne 'ne Einladung und dann ja, lass ich dir auf jeden Fall ein paar Infos zukommen, wenn ich das Ganze hier gesammelt hab.

Dominik Nussbaumer   37:19
Mhm, ja, natürlich, natürlich.
Ja.
Mhm.

Sebastian Spuhler   37:36
Im Laufe des heutigen Tages, ich bedanke mich für das Gespräch. und Hast du sonst noch irgendwelche irgendwelche Fragen, Anmerkungen noch, was noch offen geblieben ist? Nee.

Dominik Nussbaumer   37:40
Ja, danke dir für deine Zeit.
No.
Soweit so gut, wir ja.
Besprechen wir dann am Freitag, würd ich sagen. Alles klar, gut, schönen Tag noch und Tschüss. Ja.

Sebastian Spuhler   37:52
OK, gut. Ja, dann danke schön. Dir noch einen schönen Tag.
Bis dann, ciao.

Sebastian Spuhler Transkription beendet
