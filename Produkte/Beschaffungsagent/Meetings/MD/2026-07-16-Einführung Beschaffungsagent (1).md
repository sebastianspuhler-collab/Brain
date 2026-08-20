---
tags:
  - Beschaffungsagent
  - Meeting
  - Produktentwicklung
  - ERP
  - Auftragsbestätigung
quelle: Einführung Beschaffungsagent (1).pdf
datum: 2026-07-16
kategorie: Produkt
teilnehmer: "Benjamin Schmohl, Amin Douioui, Sebastian Spuhler, Jonas Rösch"
---

# Einführung Beschaffungsagent (1)

## Zusammenfassung
Internes Meeting-Transkript des Prozessia-Teams (Sebastian Spuhler, Benjamin Schmohl, Amin Douioui) zur Weiterentwicklung des Beschaffungsagenten. Besprochen werden Fälle fehlender Zuordnung von Auftragsbestätigungen zu Bestellungen, Eskalationslogik bei fehlenden AB/Bestellungen sowie Umrechnungsprobleme (z.B. Fass vs. Liter) im ERP-Abgleich.

## Teilnehmer
- Benjamin Schmohl
- Amin Douioui
- Sebastian Spuhler
- Jonas Rösch

## Kernpunkte
- Auftragsbestätigungen ohne zuordenbare Bestellung sollen nicht in die Wertung einfließen, nur als Hinweis markiert werden
- Mengeneinheiten-Abweichungen (z.B. Fass vs. Stück) führten zu unnötigen Eskalationen und müssen geklärt werden
- Lieferungs-Tracking: Vessel Tracker wird nur für Lieferungen aus China benötigt, sonst gilt der AB-Termin direkt
- Bei rabattierten Preisen soll der rabattierte Nettopreis für den Preisvergleich herangezogen werden
- Messberichte werden vorerst manuell in ProLeiS abgelegt, da noch keine API-Schnittstelle existiert
- Shared Mailboxes für Messberichte haben Speicherplatzbegrenzung (50GB) und benötigen künftig ein Löschkonzept

## Zusagen
- Benjamin Schmohl erstellt eine Excel-Tabelle mit Lieferantenstamm inkl. Besonderheiten (z.B. Portugal/Deutschland-Regeln) in den Bemerkungen
- Jonas Rösch schreibt eine Mail zur Dokumentation des aktuellen Vorgehens bei Messberichten
- Amin Douioui kontaktiert Jochen wegen Zugangsdaten zum Produktivsystem (Winform)
- Prozessia schreibt eine Mail, sobald der AB-Workflow live ist

## Nächste Schritte
- Zugangsdaten zur Produktivdatenbank (Winform) von Jochen einholen
- Detaillierte Übersicht/Lastenheft zu Lieferanten-Ländern und Transitzeiten-Berechnung erstellen
- AB-Workflow morgen bzw. am Montag live schalten
- Messbericht-Funktionalität am Dienstag nächste Woche einführen
- Klärung der Zip-Datei- und WeTransfer-Problematik bei Messberichten bleibt bei Schaufler (Benjamin)
- Nächste Woche Meeting für Zwischenfazit vereinbaren

## Entscheidungen
- Auftragsbestätigungen ohne zuordenbare Bestellung werden nicht in die Wertung aufgenommen, sondern nur als Hinweis markiert
- Bei Preisabweichungen wird der rabattierte Preis als Vergleichswert verwendet
- Vessel Tracking wird ausschließlich für Lieferungen aus China implementiert
- Für andere Lieferungen wird der AB-Termin direkt übernommen bzw. bei Bedarf lieferantenspezifisch mit Pufferzeiten (z.B. Portugal) berechnet
- Messberichte werden vorerst weiterhin manuell in ProLeiS abgelegt, bis eine API-Schnittstelle existiert
- AB-Workflow startet als erstes (morgen/Montag), Messberichte folgen danach, Lieferungen erst nach Klärung der Detailregeln

## Vollständiger Inhalt
Einführung Beschaffungsagent-20260716_083828-
Besprechungstranskript
16. Juli 2026, 06:38AM
29 Min. 36 Sek.
Sebastian Spuhler Transkription gestartet
Benjamin Schmohl   0:03
Kein klares, eine klare Identifikation haben.
Amin Douioui   0:05
Yeah.
Also, das kann schon öfters vorkommen.
Benjamin Schmohl   0:12
Das kommt durchaus mal vor, weil wir auch in dem Postfach kommen, ja 
wirklich alle Auftragsbestätigungen an und auch also.
Amin Douioui   0:14
Ja.
Benjamin Schmohl   0:24
Ja, wenn wir auch mal keine Ahnung mal telefonisch mal was bestellt haben, da 
gibt es ja noch keine Bestellbelegnummer.
Amin Douioui   0:31
OK, out.
Benjamin Schmohl   0:31
Oder wenn wir über einen Online-Shop oder so erstmal etwas bestellt haben.
Amin Douioui   0:36
OK.
Benjamin Schmohl   0:38
Das ist aber halt hauptsächlich bei den nicht.
Äh, projektbezogenen Artikeln.
Amin Douioui   0:46
OK, die hat OK. Die sollten wir dann aber auch ausschließen aus der 
Auftragsbestätigungsseite.
Benjamin Schmohl   0:52
Yep.
 Amin Douioui   0:54
die sollten jetzt hier nicht angezeigt werden, in dem Sinne. Also, so hatten wir 
das jetzt implementiert gehabt und die werden hier unter Lieferung, Bestellung  
werden die halt aufgezählt, aber nur mit einem Hinweis, Bestellung wurde nicht  
im E. R. P. gefunden. So hatte ich das jetzt gemacht, aber es würde jetzt auch 
nicht
Benjamin Schmohl   0:56
OK, good.
Amin Douioui   1:12
Lieferantenstore oder den Report mit aufgenommen.
O.K., dann noch eine zweite Sache, die mir noch aufgefallen ist.
Sebastian Spuhler   1:18
gerade, weil ich das Ganze das Ganze mal zusammenfassen kann, wenn ich 
kurz unterbreche. Ja, und zwar ist es ja so genau, wie gesagt, dass es Fälle gibt, 
wo Auftragsbestätigungen da sind, die aber keiner Bestellung direkt 
zugeordnet werden können. Ja, dass die dann quasi aus der Wertung 
rausgenommen werden, also komplett.
Benjamin Schmohl   1:32
Yeah.
Sebastian Spuhler   1:33
Ja, der umgekehrte Fall ist ja, es gibt ja 3 Fälle, sag ich jetzt mal. Ja, es ist ne, es 
ist ne Bestellung da, aber keine A. B., dann eskaliert das wegen fehlender A. B. 
Wenn ne Bestellung ohne A. B. da ist, dann vergleicht er die und eskaliert per 
Abweichung. Und in diesem Fall, wenn A. B. da ist.
Amin Douioui   1:33
Ja.
Benjamin Schmohl   1:34
Yeah.
Sebastian Spuhler   1:50
Aber keine Bestellung dazu. Dann passiert gar nichts. Dann wird das nicht in die  
Wertung rausgenommen, sondern nur als Hinweis markiert.
Benjamin Schmohl   1:57
Mhm.
Amin Douioui   1:57
Yeah.
 Sebastian Spuhler   1:59
OK.
Amin Douioui   1:59
Genau, und dann gab es noch einmal den Fall, dass da genau da war auf der A. 
B. stand da drauf ein Fass 200 Liter, aber dann im E. A. P. als ein Stück. Gibt es 
erst das von solchen Umrechnungen, die wir wissen sollten.
Benjamin Schmohl   2:10
Yeah.
Sebastian Spuhler   2:11
Be.
Benjamin Schmohl   2:12
Yeah.
Amin Douioui   2:15
Weil das hatte dann bei uns eskaliert gehabt, weil es ja keine klare Umrechnung  
zwischen ein Fass und Liter gibt, die standardisiert ist. Oder gibt da bei euch so 
eine standardisierte Rede? Das müsste man halt auch noch wissen, ob es da 
noch Regeln gibt, weil sonst hätte man sehr viele Eskalationen durch diese zwei 
Fälle, die ich aufgezählt habe.
Die eigentlich nicht eskalieren sollten.
Benjamin Schmohl   2:33
Mhm.
Amin Douioui   2:38
Genau, habt ihr da so eine? Gibt es da so irgendwelche Regeln, die ihr da so 
intern habt, die wir wissen sollten oder genau?
Benjamin Schmohl   2:49
Ich überleg grad, hast du das Fass? Ja, das ist, ich überleg, ich bin halt mehr in 
diesen projektbezogenen Materialien drin. Da haben wir eigentlich mehr so.
Ein Kilogramm, was noch alles, aber dann bestellen wir auch Kilogramm. Also, 
wir bestellen tatsächlich.
Amin Douioui   3:06
So.
Benjamin Schmohl   3:10
schon mit der Mengeneinheit, die wir auch tatsächlich bekommen. Also jetzt 
nicht, dass wir ein Fass bestellen, aber ein Stück in der Bestellung nur 
 schreiben, sondern wenn wir Stahl bestellen und 300 Kilogramm Stahl 
bestellen, dann bestellen wir auch 300 Kilogramm.
Sebastian Spuhler   3:23
Okay.
Amin Douioui   3:27
OK, das mit dem Kilo und das funktioniert alles bei uns ganz gut. Also, das ist 
kein Problem.
Benjamin Schmohl   3:31
Ja, aber es ist hauptsächlich eskaliert eben diese, wenn wenn wir halt eben in 
der Auftragsbüsche ein Fass steht, da wir in im System nur ein Stück drin stehen  
haben. Also dass hier eben die Mengeneinheiten voneinander abweichen.
Amin Douioui   3:42
Ja.
Ja, genau, das war das Problem. Genau, das waren so die 2 Fälle, weil keiner 
keine klare Bestellpositionsnummer und diese eine Umrechnung hier mit der 
rast so 200 Liter und ein Stück im EHP. Das wäre das die 2 Probleme, die wir 
jetzt
Benjamin Schmohl   3:47
OK.
Mhm.
Amin Douioui   4:01
Die mir aufgefallen sind. Und dann haben wir noch da waren noch paar andere 
ABS, mit denen wir es getestet hatten. Da wurden halt auch alle keine 
Bestellungen, keine Bestellungen im ERP gefunden. Das war meistens so 
Lohnauftragsbestätigung.
Da sollten wir es dann genauso machen, wenn die Bestellung nicht im RP 
gefunden wurde, anhand der Bestellpositionsnummer, dass wir das dann halt 
einfach auch nicht in die Wertung mitnehmen.
Sebastian Spuhler   4:17
OK.
Benjamin Schmohl   4:21
Richtig, genau.
Amin Douioui   4:22
O.K., gut, dann machen wir das so. Dann die Fälle, die nicht, ja, dann machen 
wir das nur als Hinweis, nimm das nicht in die Wertung auf, sondern jetzt nur 
von den Lieferanten, die uns da genannt wurden. Das funktioniert dann schon. 
Alles klar.
 Benjamin Schmohl   4:32
Cut.
Good.
Amin Douioui   4:36
OK, also ich, also ich würde schon sagen, dass der Auftragsbestätigung 
Workflow, der ist schon eigentlich ready, könnte man mit dem, können wir 
theoretisch auch schon morgen starten. Messberichte müssten wir jetzt noch 
klären, genau das würde ich dann schrittweise machen, dann einfach jede jede 
Funktionalität von diesen 4 Kernfundet Funktionalitäten
Schrittweise nacheinander einführen.
Benjamin Schmohl   4:59
Ja, super, genau.
Amin Douioui   5:01
Mhm.
Benjamin Schmohl   5:02
Ja, aber die haben ja den Auftragsbestellung. Ja, das kann man da auch direkt 
anfangen.
Amin Douioui   5:08
No.
Sebastian Spuhler   5:09
Mhm.
Benjamin Schmohl   5:09
Die Frage ist nur.
Amin Douioui   5:13
Yeah.
Benjamin Schmohl   5:13
Um.
Könnt ihr die Termine dann direkt schon in Winform schreiben? Habt ihr das 
schon getestet?
Amin Douioui   5:22
Genau, also wir haben, der hat, er hat, das funktioniert schon. Also auf der 
Testdatenbank, die uns bereitgestellt wurde, das ist 'ne Kopie von eurem E.R.P. 
System, 'ne kleine Kopie. Genau, da hatten wir auch 'n Feld gehabt, Liefertermin  
bestätigt und das Reinschreiben hat auch schon funktioniert.
Und zusätzlich gab es so 'ne Kommentarspalte, wo reingeschrieben wurde von 
 einem Agenten, was er gemacht hat. A. B. bestätigt Eskalation und keine 
Eskalation. So 'n kleines Dokumentarfeld war noch dazu zur Dokumentation, 
was der Agent gemacht hat. Aber in die reinschreiben in die Datenbank hat 
schon funktioniert.
Benjamin Schmohl   5:50
Mhm.
Amin Douioui   5:54
Also, das ist ehrlich.
Sebastian Spuhler   5:54
Ja, ja, wir schreiben hier erstmal in die Agentenschreibe quasi nur rein, wenn 
der Termin früher ist, weil anders gibt es ja dann in den meisten Fällen einen 
Eskalationsmechanismus oder Ähnliches, wenn es später ist.
Benjamin Schmohl   5:54
OK.
Amin Douioui   6:06
Nee, er schreibt immer den Liefertermin ein, der auf der AB drin stand. Er 
bestätigt den Liefertermin, den schreibt er.
Sebastian Spuhler   6:11
Auch also, also, also, wir bestätigen. OK, ja, genau. Ja, das stimmt. Ja, genau. OK.
Amin Douioui   6:15
Genau.
Das ist ja also Preisminderung Termin. Da schreibt er dann nichts rein, da wird 
so abgeglichen außergewöhnlicher Termin, da wird das reingeschrieben.
Sebastian Spuhler   6:19
Ein.
Mhm, OK, gut. So, ich sehe, Jonas auch schon dazu gestoßen.
Jonas Rösch   6:30
One journal.
Sebastian Spuhler   6:31
Minister, also bevor wir zum TMS-Bericht übergehen, würde ich gerade noch 
das Thema Lieferungen, also diese Seite würde ich noch gerade abhaken.
Wenn du mal grad da drauf gehst.
Damit genau, damit wir das kurz erklären können, wie das losgeht. Und zwar, ja  
genau, da ist es ja so, dass eine Lieferung, also die kommt.
 Amin Douioui   6:44
Warum? Ja.
Sebastian Spuhler   6:56
Grundsätzlich ist die Lieferung direkt drin, sobald die A. B. da ist, gilt etwas als 
Lieferung. Der Sinn dieser Seite ist ja, dass hier die Termine, also die Termine 
der Ankunft, dass die quasi getrackt beziehungsweise prognostiziert werden. Ja,  
da gibt es ja jetzt 2 Fälle.
Benjamin Schmohl   7:08
Mhm.
Sebastian Spuhler   7:12
Mit Besseltracker, das sind nämlich, wie wir es verstanden haben, die wenigsten  
Fälle und in den meisten Fällen soll der Termin einfach nur berechnet werden 
ab dem Abholzeitpunkt, wo es ja auf den Versand oder Versand losgeht, bis zur 
klassischen.
Benjamin Schmohl   7:21
Session scary.
It know.
Sebastian Spuhler   7:27
Ja.
Benjamin Schmohl   7:27
Ja, ja.
Sebastian Spuhler   7:29
Ach so, ich dachte gerade, ich bin, aber das gehört ne ganz genau bis zum bis 
zu dem Zeitpunkt, dass man ja je nach Ort, Fracht, Transport erwarten kann. Ja, 
diese also diese Zeit noch draufgerechnet quasi, da ist jetzt Stand jetzt nur.
Benjamin Schmohl   7:37
So ist es.
Sebastian Spuhler   7:45
Die Frage, auf welche Versanddokumente muss der Agent da schauen, dass er 
erstens weiß, wann ist der genaue Abholzeitpunkt und wie lange ist genau die 
Zeit? Also, wo finde ich heraus, wo ist die Ware und wie, wie finde ich heraus, 
mit welchem Transportmittel ist das? Wir haben da so 'ne Tabelle ja bekommen.
Benjamin Schmohl   7:46
Was?
 Sebastian Spuhler   8:04
Die quasi aufzeigt: "OK, gut, aus Deutschland mit dem Schiff oder aus China mit  
dem Schiff dauert es so und so lange, ja, nur dann, dann müssen wir noch, ja."
Benjamin Schmohl   8:13
Ja genau, ich die die Dokumente. Das muss ich noch mit der Kollegin aus China 
noch besprechen.
Die schickt mir, sobald sobald sie die Bill of Lading und sowas alles hat, krieg ich  
die Information mit eben auch in diesem Tracking.
E-Mail-Adresse oder diese mit dieser URL.
Und da ist dann auch gleich noch ein C.M.R. dabei, wenn es also aus diesen 
Dokumenten, dann kann ich dann das erkennen. OK, mit was für einem 
Transportmittel?
Amin Douioui   8:47
Hill.
Mhm.
Benjamin Schmohl   8:56
Kommt es aus China her, also Schiff, Zug?
Sebastian Spuhler   8:56
Mhm.
Benjamin Schmohl   9:01
Truck.
Sebastian Spuhler   9:03
Mhm, alles sehr gut. Das ist der Fall Schiene, aber Ziel war es ja auch zu 
erkennen, allgemein aus welchem, also für alle Lieferungen, den Termin zu 
prognostizieren, auch ohne Vesseltracker. Ja, das war ja, glaub ich, mein, das 
war 4.3.
Amin Douioui   9:11
Ich.
Sebastian Spuhler   9:18
Im R. P. S. im im Internet genau Punkt.
Amin Douioui   9:18
Ja.
Benjamin Schmohl   9:19
Ja, ja, genau, also.
Also in der Regel.
 Amin Douioui   9:25
Also, oft 'n paar Auftragsbestätigungen hab ich, hab ich gelesen, dass da drin 
stand mit einem Schiff oder mit einem LKW. Manchmal steht es auf der AB 
drauf, aber manchmal halt auch nicht. Und da ist jetzt auch die Frage, wie wir es  
dann lösen, ob wir das dann standardisiert lassen, wenn es nicht auf der AB 
drauf steht, dass dann
Mit diesen Tagen vom LKW liefern, weil es dann wahrscheinlich aus 
Deutschland ist oder genau.
Alles gut, alles gut.
Ja.
Benjamin Schmohl   10:05
Kommt ganz normal mit dem LKW zu uns.
Amin Douioui   10:08
OK.
Benjamin Schmohl   10:08
Aus Europa.
Sebastian Spuhler   10:09
Mhm.
Benjamin Schmohl   10:11
Und da krieg ich ja den Termin aus der Auftragsbestätigung. Die 
Auftragsbestätigung des Lieferanten bestätigt mir den Termin, wann es bei mir 
im Haus eintrifft. Also brauch ich hier keine Berechnung anstellen, die 
hauptsächlich Berechnung.
Amin Douioui   10:16
Ja.
Ja.
Benjamin Schmohl   10:27
Warum wir das eigentlich haben wollten, war eigentlich nur die Ware aus China 
von Schaufel China zu uns, weil wir hier ein extrem große dunkelgrau Bereich 
haben, wo wir nicht wissen, wann geht das Ding überhaupt mal auf den L.K.W. 
Wann geht das Ding überhaupt mal auf den Schiff aufs Schiff?
Sebastian Spuhler   10:30
In a cam.
Amin Douioui   10:44
Okay.
 Benjamin Schmohl   10:44
Wie lange ist das Schiff unterwegs? Wann kommt es in Hamburg an? Wie lange 
braucht es dann, um das Schiff zu löschen? Geht es dann in den 
Verwahrschuppen? Wie lange braucht dann noch der Zoll? Wie lange dauert 
dann das von einem weiteren Spediteur, die Ware aus dem Verwahrschuppen 
aufzunehmen?
Um es dann zu uns herzubekommen, diese ganze Apparatur, das ist ein 
absoluter Graubereich, wir wissen, oder eher eine Blackbox. Da stecken wir 
nicht wirklich drin, aber da geht es wirklich hauptsächlich nur aus.
Amin Douioui   11:11
Ja.
Sebastian Spuhler   11:14
Mhm.
Amin Douioui   11:14
Mhm.
Benjamin Schmohl   11:20
Für die Ware schau für China zu alle anderen Bereiche, wo wir noch sowas 
hätten, sind alle Lieferanten aus Portugal, weil dann eben einfach von der 
iberischen Halbinsel bis zu uns.
Amin Douioui   11:23
O.K., dann könnte man, ach so, ja.
Benjamin Schmohl   11:39
das ungefähr 'ne Woche dauert. Aber auch da hab ich 'ne Auftragsbestätigung, 
wann die Ware bei uns eintrifft. Klar, könnten wir dann sagen, von dieser von 
diesem Termin rechnen wir mal 'ne Woche zurück. Dort sollte die Ware auf den 
L.K.W. kommen, weil ungefähr eine Woche dauert.
Dauert es mit dem LKW von Portugal bis nach Deutschland?
Amin Douioui   12:01
Yeah.
Benjamin Schmohl   12:02
Dass man dann hier vielleicht ein Event auftun und sagen, eine Woche vor 
diesem Termin, frage ich mal, ist die Ware schon auf dem LKW?
Sebastian Spuhler   12:13
Mhm.
Amin Douioui   12:13
 O.K., also sollten wir das dann auch nach den Lieferanten filtern?
oder ist das nicht so 'ne, gibt es nicht 'ne, habt ihr 'ne klare Liste an Lieferanten, 
wo wir sagen können, OK, wenn es dieser Lieferant, der ist aus Portugal und bei  
dem könnten wir dann diese Funktionalität dann ein anschalten, in dem Sinne, 
OK, dann würde ich das auch so machen.
Benjamin Schmohl   12:19
Ja.
Sebastian Spuhler   12:26
Ich.
Benjamin Schmohl   12:31
Immer können wir ja.
Also wie gesagt, hauptsächlich die ganze Tracking-Gedöns von Vessel Tracker 
und so was, nur Schaufler China.
Amin Douioui   12:39
Yeah.
Schau vielleicht China, OK.
OK, das ist gut zu wissen, weil wir hatten dann jetzt überall hatten wir halt diese  
Kalkulation gemacht, falls es sich halt irgendwo geht. Also dann ist halt 
Vestitracker wirklich nur für Schaufler Schiene.
Benjamin Schmohl   12:50
Yeah.
Ja.
Amin Douioui   12:55
OK, das gibt es. Das passt dann.
Sebastian Spuhler   12:55
Yeah.
Ja genau, also wäre der Großteil der Bestellungen hätte dann wahrscheinlich 
gar keine, gar keinen prognostizierten Ankunftstermin, ja.
Benjamin Schmohl   13:05
Nein, sondern da ist wirklich der Termin, was auf der Auftragsbestätigung ist, 
ich bin an diesem Tag, haben Sie bestätigt, die Ware ist bei uns auf dem Haus. 
Ab und zu, das muss man halt prüfen. Ab und zu steht in Auftragsbestätigung,
Sebastian Spuhler   13:12
In.
Benjamin Schmohl   13:20
 Das ist der abgehende Termin. Also, ich bestätige, an diesem Termin wird 
versendet.
Sebastian Spuhler   13:26
Mhm.
Benjamin Schmohl   13:27
Da kann man dann eine Prognostizierung machen und sagen: "OK, das ist ein 
deutscher Lieferant." Da machen wir einfach.
Den Tag geht es raus, dann ist es 23 Tage später bei uns im Haus.
Amin Douioui   13:40
OK.
Sebastian Spuhler   13:41
Mhm.
Amin Douioui   13:42
Jetzt gut zu essen.
Sebastian Spuhler   13:43
O.K., gut, ja, ja, weil weil da brauchen wir wirklich eine klare Definition. O.K., mit 
mit mit welchen Bestellungen macht man das? Bekomme ich bei jeder 
Lieferung einen Abholzeitpunkt raus? Wie berechne ich genau die Transitzeit 
und so? Ne, da haben wir ja eine Tabelle und so, nur kann man halt nicht immer  
ja alles ausdehnen.
Benjamin Schmohl   13:47
Ja.
Sebastian Spuhler   14:01
Versanddokumenten klar nachlesen, aber das würden wir dann ja genauso 
handhaben, dass wir dann sagen: 'Okay, je nachdem welcher Lieferant das ist, 
wenn Abholzeitpunkt dabei ist. Ja, also wenn da drauf steht, wann das Ding 
versendet wird, ja dann rechnen wir bei einem deutschen Lieferanten 3 Tage 
drauf, zum Beispiel, ja.'
Benjamin Schmohl   14:21
Genau.
Sebastian Spuhler   14:22
OK also wär gut, wenn du downs vielleicht oder wenn wenn wenn du downs 
vielleicht sogar ne ja so ne allgemeine Übersicht noch mal ja hinstellen könntest  
nur so OK welche Lieferanten von welchen Ländern wie prognostiziert und 
getrackt werden sollen, weil ja.
 Benjamin Schmohl   14:24
Summer.
Timer.
Sebastian Spuhler   14:38
Da hatten wir ja in dem Lastenheft 'ne relativ allgemeine Beschreibung bei 4.3, 
was die nicht Wessel Tracker Lieferung angeht, aber grundsätzlich wär es ja 
immer gut, wenn man das dann wirklich im Detail weiß, wie man auch jeden 
Sonderfall behandelt. Ja, damit das das ganze Modul hier auch Sinn macht und.
Weil es transparent und nachvollziehbar ist, wo die Berechnungen herkommen.
Benjamin Schmohl   14:59
Ja.
Amin Douioui   15:00
Ich hätte noch einen Punkt bei A. B. S., was mir noch eingefallen ist, manchmal 
habt ihr den Fall, dass da der ein Rabatt draufsteht und aufgrund der 
Preisabweichung sollen wir den rabattierten Preis beachten betrachten oder 
der Standardpreis. Ich habe es jetzt mal mit dem Standardpreis gemacht.
Benjamin Schmohl   15:19
Nee, rabattierter Preis, weil ja, weil sonst habe ich eine Abweichung. Wenn wir 
eine Bestellung abgeben, nehmen wir auch da den Nettopreis. Also der 
rabattierte Preis steht in unserer Bestellung und dann kriege ich ab und zu 
vielleicht eine Auftragsbestellung, Bruttopreis minus Rabatt.
Amin Douioui   15:21
Rabattierter Preis. OK.
Ja.
Sebastian Spuhler   15:28
Gib mich.
Benjamin Schmohl   15:37
Gleich noch etwas.
Amin Douioui   15:40
O. K., O. K.
Ja, manchmal stand da ja 3% Rabatt und dann war es halt über Jobs halt ne 
genaue Situation, die man aufgegeben ist.
Benjamin Schmohl   15:49
Ja, ich würde es jetzt aber auch da halt gar nicht so, mir das, ich hätte jetzt mal 
gesagt, wir testen jetzt einfach mal, wir gucken einfach mal, was passiert und 
 dann und dann stellen wir die, die die Schrauben einfach ein bisschen enger, 
wenn man das.
Amin Douioui   15:56
Ja.
Ja, will ich auch sagen.
Ja, auf jeden Fall, ja.
Benjamin Schmohl   16:04
Aber jetzt lass mal lieber ein bisschen mehr eskalieren.
Amin Douioui   16:09
Yeah.
Benjamin Schmohl   16:09
Dann sehen wir mal, wie arbeitet der K.I. Agent und wenn man dann merken, 
ah, OK, das können wir noch mit dieser Regel abdecken, dann schaut man 
danach mit einer Regel.
Amin Douioui   16:13
Ja.
Ja, genau. Das werden auch nur Entwürfe erstellt. Also, es kann jetzt auch nichts  
passieren, so eine Testphase, genau.
Benjamin Schmohl   16:26
Yep.
Amin Douioui   16:30
Mhm.
Okay, ja, dann passt das.
Also, was wir dann noch machen müssten, damit wir mit 'n A. B. starten können,  
wäre eigentlich noch nur, dass der, dass uns die richtige Datenbank 
bereitgestellt wird. Der kann uns noch mal 'ne noch noch mal Zugangsdaten 
geben und dann sollten wir eigentlich schon damit starten können.
Genau und dann ist wir können ja auch hier nach Einkäufer filtern, aber jetzt in 
der Testdatenbank wurden jetzt nur diese 5 aufgezählt, wer kann bei Passt das 
auch oder habt ihr noch viel mehr andere? Es kann halt auch gut sein, dass es 
halt nur daran liegt, dass 'ne Testdatenbank nicht alles drin ist.
Benjamin Schmohl   16:59
Mhm.
Sag mal, wen, wen hast du denn jetzt austrinkert?
Amin Douioui   17:09
Mhm.
 Björte Bergmann bei CNK, Rainer Payer, Philipp Süß, die werden halt aus der 
Datenbank geladen.
Benjamin Schmohl   17:16
Und ah.
Yeah, you know, needs past.
Amin Douioui   17:20
Ja.
OK.
Gut, dann haben wir das mal mit den Lieferungen geklärt. Bestellung A. B. ist ja 
auch geklärt. Jetzt Messbericht müssten wir jetzt auch noch machen, wie wir 
das jetzt machen.
Sebastian Spuhler   17:34
Ja, der Jonas ist hier im Meeting. Ich weiß nicht, ob er uns hört.
Jonas Rösch   17:40
Anwesend, anwesend, anwesend.
Sebastian Spuhler   17:42
Ach, sehr gut. O. K., gut. Ja, du hast mir gestern schon 'nen Vorschlag gemacht, 
tatsächlich. Das sah auch ja relativ gut aus, hat sich relativ machbar angehört. 
Dann ja, hätte ich gesagt, gehen wir da mal noch mal rein und besprechen das 
jetzt.
Jonas Rösch   17:57
Also dann würde ich kurz loslegen. Also ich habe dem Beschaffungsagent 
bereits Vollzugriff inklusive Senderechte auf diese 3 Postfächer, HNO, 
Werkzeugnisse und Quality, unterstrich Staufler at schaufler.de gegeben. Das 
heißt, er kann die schon pullen.
Jetzt gibt es aber noch ein paar Problematiken, die ich in der Zukunft sehe. Das 
wird jetzt natürlich erstmal funktionieren.
Benjamin Schmohl   18:17
Bei dir eigentlich die.
Just in the push.
Jonas Rösch   18:21
Aber die Shared Mailboxes laufen ja irgendwann voll. Das heißt, die Dinger 
haben 50 Gigabyte.
Benjamin Schmohl   18:27
Dicke Seite.
Jonas Rösch   18:27
 Das heißt, es müsste sich noch überlegt werden, was passiert, also wie lang die 
Daten da drin sein müssen beziehungsweise was wir tun können, damit die 
Daten halt nicht irgendwann überlaufen in den Postferien.
Sebastian Spuhler   18:41
Mhm.
Jonas Rösch   18:42
Ob wir zum Beispiel sagen können, es ist nur ein spontaner Gedanke, dass mit 
dem Beschaffungsagent sagen können, alles älter im Jahr, weil er da raus, keine  
Ahnung.
Sebastian Spuhler   18:54
Mhm, die Dokumente sollen doch eh irgendwann abgelegt werden in.
Jonas Rösch   19:02
Allies.
Amin Douioui   19:03
Prola ist ja.
Sebastian Spuhler   19:04
Oder ist genau ja.
Benjamin Schmohl   19:05
Ola.
Jonas Rösch   19:05
Also, also, erstmal redet mir keinen Stress. Ich will es halt nur vermeiden, dass 
wir dann halt heute in einem Jahr da sitzen und sagen, da es geht irgendwie 
nicht mehr und dann gucke ich rein und dann sehe ich halt 50 Gigabyte 
Postplan. Das ist halt doof.
Benjamin Schmohl   19:14
Inspect.
Sebastian Spuhler   19:16
Mhm, ja, nee, also das können wir. Diese Mailbox ist dann quasi am besten, 
würde ich sagen, nur so eine Übergangsphase und dann kann man sie 
irgendwann in Poleiste ablegen. Da wird jemand gerufen, glaube ich, aber.
Benjamin Schmohl   19:20
So.
I have for i wish.
Amin Douioui   19:29
 Ja, und dann, wenn man das dann noch mal rauslöscht aus dem Postfach, wird 
das ja auch noch mal reduzieren den Speicherplatz.
Oder wie ist denn das? Fünf? Ja.
Jonas Rösch   19:40
Ja, es ist nur, es ist, es ist halt nur so, dass die Postfächer relativ schwierig zu 
händeln sind, wenn die irgendwann mal so groß sind. Weil dann brauchst du 
irgendeinen Automatismus oder Grad einen Agent, der das halt durch 
durchforstet. Weil wenn du es halt manuell mit der Maus machst, dann lädt der 
immer nur so.
20 E-Mails rein oder 50 und ja, keine Ahnung. Ihr wisst bestimmt, wenn du, 
wenn ich in Outlook über 100 Mails markiere, dann geht alles in die Hose.
Amin Douioui   20:05
Ja, ja.
Sebastian Spuhler   20:08
Mhm, ja, da müssen wir die dann, wenn die ein gewisses Alter erreicht haben, 
müssen wir sie dann erstens rausholen und dann irgendwie gucken, dass man 
sie dann irgendwo anders ablegt, damit sie eben nicht verloren gehen.
Jonas Rösch   20:20
Benjamin, wie ist denn das jetzt gerade aktuell? Das heißt, ist das noch 
Zukunftsmusik, dass die Dinger ins Proleis reinkommen, oder würde das dann 
auch schon automatisch stattfinden?
Sebastian Spuhler   20:25
OK.
Benjamin Schmohl   20:25
Ich weiß auch nicht.
Also, Messberichte müssen heute schon in Prohlas abgelegt werden.
Also eigentlich die komplette Dokumentenablage ist schon scharf geschalten, 
dass alle Dokumente in Prolet abgelegt werden müssen.
An sich dürfen ist eigentlich vom vom Joachim Schuster ein absolutes Verbot M 
1 Doku zu nutzen.
Jonas Rösch   20:58
OK, und wie muss ich mir das in der Praxis vorstellen? Macht der KI-Agent das 
dann automatisch ins ProLeiS oder wie kommt das Zeug ins ProLeiS?
Benjamin Schmohl   21:05
Das weiß ich, das muss Sebastian jetzt sagen. Wie weit seid ihr mit VOLA schon 
mit der API-Schnittstelle?
Sebastian Spuhler   21:12
 Nicht weit, also Stillstand, ja. Deswegen hätte ich also grundsätzlich nochmal für  
die Messberichte, da war ja ursprünglich die Anforderung, dass der Agent die 
holt und auch weiterleitet an Quality at Schauffler. So, wenn jetzt haben wir 
aber gesagt, OK, gut wegen diesen ganzen.
Benjamin Schmohl   21:14
Nicht weit.
Sebastian Spuhler   21:30
vielen verschiedenen Möglichkeiten, wie man Messberichte rankommt, werden 
die erst manuell rausgeholt und irgendwo in Watch Folder abgelegt. So, das ist 
jetzt ja schon quasi diese Quality at Schaufler Postfach, wo wo jetzt da im Raum 
steht. So, das heißt, was er gerne machen kann, ist er kann.
Benjamin Schmohl   21:40
Yeah.
Sebastian Spuhler   21:48
Diese Mailboxen absuchen, ja, man kann dann seinen Vollständigkeitscheck 
machen und danach müsste man dann irgendwie schauen. Okay, dass die also 
übergangsweise, dass die Mitarbeiter sehen. Okay, gut, dieser Messbericht ist 
geprüft worden, ja. Den kann ich jetzt in Proleis reinlegen, weil Stand jetzt 
haben wir keine Schnittstelle zu Proleis. Das kann ich natürlich noch ändern.
Ja, aber die ist dann jetzt nicht da und deswegen müssen dieser Schritt auch 
noch das Ablegen in Polar ist dann auch noch manuell funktionieren, bis wir die  
Schnittstelle haben.
Jonas Rösch   22:21
O.K., das heißt quasi, wenn also, wenn ich es jetzt richtig verstehe, das heißt, es 
ändert sich erstmal gar nichts vom Doing her, Benjamin. Korrigier mich, falls ich  
falsch liege. Und dann irgendein der K.I. Agent schafft es aber immerhin, die 
Infos schon mal zu bekommen, dass das Zeug da drin ist. Und dann an einem 
Tag X schafft er es dann auch, das Zeug von den Postfächern.
Benjamin Schmohl   22:26
Yeah, yeah.
Sebastian Spuhler   22:39
Hey.
Jonas Rösch   22:39
in Brola reinzubeamen.
Benjamin Schmohl   22:41
Richtig.
 Jonas Rösch   22:42
O.K., dann können wir das alles erstmal so laufen lassen oder so, so initiieren, 
wie wir es jetzt schon gemacht haben. Dann hab ich erstmal keinen Stress 
mehr. Das ist schon mal schön. Ich schreib jetzt auch noch eine Mail, dass wir 
das so gemacht sind an euch alle und lass mir halt uns noch für die Zukunft 
überlegen müssen, wie wir es hinkriegen, dass es Post bei.
Postfach nicht voll läuft. Und dann gibt es halt noch so kleine Sachen, die man 
beachten muss. Wo wir gestern im Gespräch festgestellt haben, ist, wenn du 
jetzt eine Zip-Datei in diesem Postfach bekommst, musst du wieder ja manuell 
eingreifen, weil du ja sagst, Sporoleis kann keine Zip verarbeiten. Das heißt, 
dann musst die E-Mail theoretisch ja.
Sebastian Spuhler   23:16
Mhm.
Jonas Rösch   23:17
Rausnehmen, die Datei entzippen und sie da wieder hinschicken, ne?
Sebastian Spuhler   23:19
B.
Benjamin Schmohl   23:22
Richtig.
Jonas Rösch   23:23
Ja, OK, aber das weißt du ja dann. Das vergesse ich jetzt somit. Das ist quasi 
dein Problem.
Benjamin Schmohl   23:29
Genau, das Gleiche habe ich ja auch mit diesem ganzen WeTransfer und 
anderen Gedöns, dass ich, dass ich das ja mir erstmal da runterziehen muss 
und dann die Einzeldokumente dann an an die E-Mail-Adresse hinschicken 
muss und ab dann dann.
Jonas Rösch   23:30
OK.
Genau, genau, das kannst du hier nicht hin.
Benjamin Schmohl   23:45
der K.I. Agent dann überprüfen. Hey, für dieses Produkt hab ich eine Bestellung  
vorliegen. Messbericht ist da, wunderbar abgehakt. A. für dieses Produkt hab 
ich noch keinen Messbericht. E-Mail schreiben, wo ist mein Messbericht?
Jonas Rösch   24:00
OK.
 Gut, ich denke, dann ist von meiner Seite aus die Arbeit erstmal getan.
Und sonst wüsste ich jetzt gerade nicht, dass man sonst noch irgendwas offen 
hätte oder machen müsste.
Sebastian Spuhler   24:13
Ja, genau, dann ja.
Amin Douioui   24:15
Das sind technisch, ist alles geklärt.
Sebastian Spuhler   24:18
Ja, ja, dann nur noch mal um festzuhalten. Also morgen gehen morgen oder am  
Montag vor allem der A. B. Workflow geht dann raus. Das mit den Bestellungen 
lassen wir dann einfach mal, also mit den mit den Lieferungen lassen wir 
einfach mal so laufen, bis wir dann nähere Informationen haben, wie welcher 
Transit berechnet wird.
Ja, und genau, Messberichte implementieren wir dann auch. Ich nehm an, so 
Montag, Dienstag werden dann würde die Funktion mit den Messberichten 
dazu gehen. Und ja, wir lassen es einfach mal laufen. Grad was die A. B. S 
angeht, ist ja schon alles vollständig. Da kann der Benjamin dann regelmäßig 
die Entwürfe prüfen, falls er was eskaliert oder allgemein, was das Ding.
Benjamin Schmohl   24:46
Yeah.
Sebastian Spuhler   24:54
sonst noch für Statistiken rausgibt und dann ja, testen wir einfach mal aus und 
dann kommt das Ganze nach und nach, wie gesagt, mit Vessel Tracking und 
den ganzen Transitberechnungen. Das werden wir dann, denke ich, auch 
innerhalb der nächsten Woche die Daten bekommen, dass wir das dann rein 
machen können.
Jonas Rösch   25:11
O. K., ich bin morgen nicht da, falls es nur irgendwas zum Einstellen gibt. Meine 
Kollegen sind da, die haben auch Zugriff auf 365, die wissen halt nicht, um was 
es geht. Die müssten wir dann halt genau loten, falls noch irgendeine 
Berechtigung oder irgendwas fehlt. Ja,
Benjamin Schmohl   25:12
Sehr good.
Amin Douioui   25:27
Alles gut. Ich glaube, da sollte schon alles geklärt sein.
Sebastian Spuhler   25:28
OK, yeah.
 Ja, wenn nicht, wir haben heute den ganzen Tag, dann schreibe ich dich noch 
über Teams an, falls es noch irgendeine Kleinigkeit geben sollte. Und sonst, ja, 
passt das.
Amin Douioui   25:33
If it.
Jonas Rösch   25:39
Ja.
Gut, dann bin ich raus und dann danke für die Zusammenarbeit. Und ja, keine 
Ahnung, was sagt man bei der Einführung von K.I. Agent? Viel Glück.
Amin Douioui   25:50
Ja.
Sebastian Spuhler   25:50
Ja, Dankeschön.
Amin Douioui   25:52
Ich will.
Benjamin Schmohl   25:53
Lass sie.
Jonas Rösch   25:54
Ciao.
Sebastian Spuhler   25:55
Gut, schönen Tag noch. Ciao.
Benjamin Schmohl   25:55
Danke dir.
Amin Douioui   25:55
Okay, ciao.
Benjamin Schmohl   25:57
Ja.
Amin Douioui   25:59
You.
Benjamin Schmohl   26:02
Gut, nee, dann würde ich mal sagen, starten wir mal so. Wir gucken mal.
 Sebastian Spuhler   26:02
So.
Amin Douioui   26:02
Also, ja, ja.
OK.
Benjamin Schmohl   26:10
Ich sehs wies anläuft.
Amin Douioui   26:13
OK, also ich würde glaube ich so feste Tage jetzt einfach mal so fest machen, 
wann wir starten. Wenn wir jetzt morgen mit den AB starten, also wir könnten 
von mir auch schon morgen starten. Wenn uns Jochen heute noch die 
Zugangsdaten zu der richtigen Datenbank gibt, also zu Winform, dem 
Produktivsystem, dann könnten wir eigentlich schon morgen starten.
dann mit dem Gas, dass wir mit Messbericht dann auch schon nächste Woche 
starten können, dass das dann auch eingeführt wird und sobald das zu den 
Lieferungen jetzt angegeben ist, können wir eigentlich auch da schon starten. 
Auch
Benjamin Schmohl   26:43
Mhm.
Amin Douioui   26:44
sind doch alles einfach die Messberichte und das Weitere, denke ich, laufen 
nächster Woche. Genau,
Sebastian Spuhler   26:53
Ja, also Messbereiche denkst du schaffen wir am Dienstag.
Amin Douioui   26:56
Ja, also wenn ich es richtig verstanden habe, dann sollte der Dienstag schon 
gehen, ja.
Sebastian Spuhler   26:58
Ja, OK.
Yeah.
Amin Douioui   27:05
Soll nur Vollständigkeit in den vollständigen Pool.
You know.
Sebastian Spuhler   27:11
Ja, ist ja gut. Ja, haben wir dann alles, was auf der Agenda stand, für heute 
 technisch gesehen alles abgeklärt oder hast du noch irgendeinen offenen 
Punkt?
Benjamin Schmohl   27:19
Schon.
Ich hab kein.
Amin Douioui   27:30
Oder wen?
Sebastian Spuhler   27:31
O. K., gut. Ja, also bei bei dir, Benjamin, wär halt jetzt nur noch das, ja das mit 
den Lieferungen, dass man da, wenn wir das nächste Woche machen sollen, 
dass man da klare Infos haben, wer bekommt genau 'n Vesseltracker und wer ja  
halt eben nicht. Und bei welchen Lieferanten sollen wir genau wo drauf achten, 
also ob es jetzt Portugal oder Deutschland ist,
Benjamin Schmohl   27:44
Ja.
Sebastian Spuhler   27:51
Ne, wie also, dass wir dann eine klare, detaillierte Analyse haben, bei welchem 
Fall wird was berechnet und bei welchem Fall wird gar nichts berechnet. Ne, das  
ist halt so, dann auch das, was wir da brauchen. Gut.
Benjamin Schmohl   27:51
Yep.
Amin Douioui   27:59
Yeah.
Noch eine Frage, ja.
Benjamin Schmohl   28:03
Ich würd, ich würd dir, würde das, glaub ich, in diesen Lieferantenstamm, was 
wir vorher gesprochen haben, dass ich dir deine Excel-Tabelle mit dem 
gesamten Lieferantenstamm und bei den Lieferanten, wo 'ne Besonderheit ist, 
schreib ich einfach hinten in Bemerkung diese Besonderheit rein.
Sebastian Spuhler   28:04
Ja.
Mhm.
Amin Douioui   28:19
OK, ja, das ist super. Das passt.
Sebastian Spuhler   28:20
 Genau, ja, damit wir dann auch auf die Lieferanten anpassen können, wie der 
Agent zum Beispiel eine Ankunfts-, eine Sendezeit oder sonst was berechnet.
Amin Douioui   28:27
Mhm.
Benjamin Schmohl   28:29
Mhm.
Amin Douioui   28:31
Also, Eskalation auch bei Preis und Mengenabweichung jetzt immer noch 0%, 
also beziehungsweise 0 oder OK, das können wir schnell ändern. 
Terminabweichung größer als 5 Kalendertage, war ja ursprünglich auch 
gespannt. OK,
Benjamin Schmohl   28:31
Genau.
Ja.
Yeah.
Yeah.
Amin Douioui   28:46
Alles klar.
Gut, dann sind wir durch und ich würde mich dann wir können uns noch mal 
morgen melden, wenn wir damit starten.
Sebastian Spuhler   28:48
Gut.
Ja, wir schreiben einfach kurz für morgen eine Mail, wenn es live ist, dann.
Amin Douioui   28:58
No.
Sebastian Spuhler   28:59
Hätt ich gesagt, ja. Und dann, wie gesagt, es können ja, es sind ja bisher eh nur 
Entwürfe, die dann ins Postfach generiert werden. Da könnt ihr euch in den 
nächsten Tagen einfach mal anschauen, wie das Ganze anläuft. Und dann, ja, 
finden wir nächste Woche, denk ich, noch mal 'n Termin für 'n Meeting, um kurz  
Zwischenfazit zu ziehen und die anderen Sachen nach und nach hochzuziehen.
Benjamin Schmohl   28:59
Perfekt.
Amin Douioui   29:00
Genau.
 Benjamin Schmohl   29:16
Genau.
Amin Douioui   29:18
OK, passt. Also, ich werde dann werden wir gleich noch mal dem Jochen 
schreiben, dass du uns das bereitstellen kann und dann machen wir alles ready.
Benjamin Schmohl   29:23
Yep.
Super.
Sebastian Spuhler   29:25
OK, gut.
Amin Douioui   29:26
Alles klar, dann.
Bis morgen oder bis nächste Woche.
Sebastian Spuhler   29:30
Ja, bis dann. Ciao. Dankeschön. Tschüss.
Benjamin Schmohl   29:30
Genau, alles klar. Mach's gut. Ciao, ciao, ciao, ciao.
Amin Douioui   29:31
Ist dann klar.
Sebastian Spuhler Transkription beendet

