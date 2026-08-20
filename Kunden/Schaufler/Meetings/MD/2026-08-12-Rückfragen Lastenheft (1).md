---
tags:
  - Lastenheft
  - Stücklistenagent
  - Meeting
  - Schaufler
  - Rückfragen
quelle: Rückfragen Lastenheft (1).docx
datum: 2026-08-12
kategorie: Kunde
firma: Schaufler
teilnehmer: "Sebastian Spuhler, Marvin Wiegner, Amin Douioui"
---

# [Schaufler] Rückfragen Lastenheft (1)

## Zusammenfassung
Besprechungstranskript vom 12.08.2026 zwischen Prozessia (Sebastian Spuhler, Amin Douioui) und Schaufler (Marvin Wiegner) mit Rückfragen zum Lastenheft für den Stücklistenagenten. Themen u.a. Anzahl der parallel arbeitenden Konstrukteure (12-15 bei Schaufler Laichingen) und Menge der monatlich zu verarbeitenden Stücklisten für die Belastbarkeitsauslegung.

## Teilnehmer
- Sebastian Spuhler
- Marvin Wiegner
- Amin Douioui

## Kernpunkte
- Klärung der zu erwartenden Systemlast: Anzahl Stücklisten und gleichzeitig arbeitender Konstrukteure
- Marvin nennt grobe Zahlen: ca. 90 große Stücklisten und ca. 420 kleine Ersatzteil-Stücklisten pro Jahr, maximal ca. 5 Konstrukteure gleichzeitig
- Diskussion über Bereitstellungsmodell: On-Premise vs. DSGVO-konforme Cloud-Lösung für das KI-Sprachmodell
- Wirtschaftliche Abwägung zwischen Hardware-Investition für lokales Modell und Nutzung eines externen Cloud-Modells (z.B. Azure)
- Bedeutung einer Vektordatenbank zur Reduktion von Fehlinterpretationen/Halluzinationen bei firmenspezifischem Wissen
- Fehlen konkreter quantifizierbarer KPIs; Erfolg soll über Zeiterfassung und Konstrukteurs-Feedback abgeschätzt werden

## Zusagen
- Marvin sagt zu, eine genauere Auswertung der Stücklisten-Zahlen aus der Datenbank zu erstellen
- Sebastian sagt zu, das Transkript an Marvin zu schicken
- Prozessia sagt zu, basierend auf den Infos einen Vorschlag zum weiteren Projektvorgehen zu machen

## Nächste Schritte
- Genaue Erhebung der Stücklisten-Zahlen pro Monat/Jahr durch Marvin
- Klärung der Hardware-/IT-Voraussetzungen mit der internen IT von Schaufler
- Dokumentation der wirtschaftlichen Aufwendungen für On-Premise- vs. Cloud-Variante des KI-Modells
- Prüfung durch Amin, ob eine Vektordatenbank für den Use Case tatsächlich notwendig ist
- Nächstes Meeting mit Jürgen und weiteren Beteiligten geplant

## Entscheidungen
- Grundsätzliche Offenheit für eine externe, DSGVO-konforme Cloud-Lösung (z.B. Azure) statt zwingend On-Premise-Sprachmodell

## Vollständiger Inhalt
Rückfragen Lastenheft-20260812_170126-Besprechungstranskript 12. August 2026, 03:01PM 30 Min. 36 Sek. 
Sebastian Spuhler Transkription gestartet 
Sebastian Spuhler   0:04
Und ja, wir warten dann noch auf Armin. Der wird auch teilnehmen. Der hat vielleicht unabhängig von mir noch mal ein paar Rückfragen gleich, aber ich schau mal grad, ob der irgendwas von Verspätung geschrieben hat. Nee, gut, der soll kommen. 
Marvin Wiegner   0:04
Ja, kannst du gerne machen, ja. 
Sebastian Spuhler   0:19
Ja, aber ist eigentlich egal. Ich fang einfach mal an mit den, ja, mit den wichtigsten Sachen voraus, und zwar Azizaja, perfekt.
Sind ja schon pünktlich.
Hallo. 
Marvin Wiegner   0:32
Hallo Armin. 
Amin Douioui   0:35
Hallo, hört man mich? Hallo. 
Sebastian Spuhler   0:36
Ja, perfekt. 
Amin Douioui   0:39
Alles klar. 
Sebastian Spuhler   0:40
Gut, also ich fang ja mal an. Also grundsätzlich erstmal danke schön für das Lastenheft noch mal. Das ist, merkt man wirklich, dass das Ganze sehr durchdacht ist und man sich da auch ja nicht über das, nur über das war es das grundsätzlich, sondern auch teilweise schon über das, wie Gedanken gemacht hat, wie das nachher benutzt werden soll, ne, die Benutzeroberfläche und alles.
Und der ganze Prozessablauf ist sehr, sehr angenehm beschrieben. Man kann auch schon die technischen Voraussetzungen dafür sehr, sehr gut ableiten. An den meisten Stellen, aber an den Stellen, wo es noch unklar ist, ja genau, würden wir heute dann noch.
Ein 2 Sachen besprechen und zwar die erste wichtige Sache ist, habt ihr mittlerweile mal gemessen, wie viele ja Stücklisten pro Monat oder pro Tag verarbeitet werden und wie viele Konstrukteure sollen das Ding nachher bedienen, weil das ist unfassbar wichtig für die Belastbarkeit, dass wir wissen können,
Wie viele Konstrukteure gleichzeitig oder wie viele Stücklisten gleichzeitig oder allgemein im Monat oder in einem bestimmten Zeitintervall damit verarbeitet werden. 
Marvin Wiegner   1:41
Konstrukteure, die parallel daran arbeiten, also jetzt nur bei uns Schaufler Laichingen, sind wir so im Bereich 12 bis 14-15 Konstrukteure. 
Sebastian Spuhler   1:52
Mhm. 
Marvin Wiegner   1:56
So, die Anzahl der Stücklisten heruntergebrochen auf den Monat, die Zahl ist, haben wir immer noch nicht erhoben. Ich könnte da vielleicht mal 'ne grobe Auswertung starten über die Aufträge, die wir hatten. Also, ich hab mir da schon mal
N paar.
Infos aus unserer Datenbank rausziehen lassen. Ich kann mal schauen, ob ich die Datei finde, dann kann ich euch da ungefähr was sagen. 
Sebastian Spuhler   2:17
Mhm. 
Marvin Wiegner   2:28
Wir unterscheiden natürlich da auch sehr stark in dem Auftragstypen nach Umfang auch, aber so generell würde ich das eigentlich dann dieses Tool schon bei jedem Projekt sehen.
My jedes Projekt ist ja irgendwie mit gewissen Absprachen verbunden und.
Ein gewisses Maß an Zusammenarbeit, Kollaboration brauche ich da eben.
Umm.
Ja, also wie ihr wahrscheinlich gemerkt habt aus dem Lastenheft, das ist dann so die die Hoffnung, die sich dann so bei mir eingestellt hat, was wir mit dem K.I. Agenten lösen wollen oder lösen können, einfach die bessere Zusammenarbeit, dass eben alle Infos.
Besser zusammengetragen werden können.
Yeah.
Mhm. 
Sebastian Spuhler   3:26
Mhm. 
Amin Douioui   3:28
OK. 
Sebastian Spuhler   3:28
OK, good. 
Amin Douioui   3:30
Also, jetzt auch keine Einschätzung kannst du jetzt auch nicht geben. So eine ungefähre Zahl ist jetzt auch nicht, kannst du jetzt auch nicht. 
Sebastian Spuhler   3:30
Ja, dann. 
Amin Douioui   3:37
Nen. 
Marvin Wiegner   3:40
Ich öffne, ich schaue gerade.
Also, Aufträge hatten wir in Summe 608. Da wird wahrscheinlich dann auch in jedem oder fast an jedem eine Stückliste dranhängen. 
Sebastian Spuhler   4:33
Mhm. 
Marvin Wiegner   4:35
Jetzt müsste ich da noch mal über die Typen filtern. Wir haben auch Ersatzteilaufträge, das sind sehr kleine Aufträge, meist nur ein oder 2 Positionen, kann aber auch größere Positionsumfänge sein, also dass die Stückliste dann 20 
Amin Douioui   4:45
weg 
Marvin Wiegner   4:54
30 Positionen hat. Das kann auch sein, also das ist sehr variabel, aber der Großteil dieser Ersatzteil Auftragstyp ist eben dann nur so ein, 2 Stücklisten Positionen. Aber davon haben wir sehr viel, davon hatten wir im Jahr 2023 400.
22 Aufträge,
Auftragstyp vom Typ Änderung, da steht häufig nicht so oft 'ne Stückliste dahinter. Wenn dann Änderungen an Stücklisten, weil es eben ja Auftragstyp Änderung ist, dann wahrscheinlich die.
Aufträge zusammengenommen, wo wir dann wirklich 'ne Stückliste neu erstellen oder wirklich Stücklistenaufwand verbunden ist, ist dann
Bei uns die Aufträge Reparatur, Neubestückung oder beziehungsweise auch unser Hauptgeschäft, Erstformen, Neukonstruktionen und dann dementsprechend auch Folgeformen, also wo wir wirklich komplett eine komplette Baugruppe herstellen müssen.
das sind dann auch größere Stücklisten, also mehrere 100 Positionen bis an die 1000 rein. Also von den Folgeformen und Erstformen haben wir nicht so viele, das waren jetzt da nur 16 Aufträge.
Aber dann diese Reparaturen, Neubestückungen.
da gibt es dann schon wieder mehr, da hatten wir insgesamt 75 in dem Jahr und wenn man das dann mal zusammenrechnet, also dann die 75 plus die 1615, dann ja so 90
Stücklisten würde ich mal auf den aufs Jahr sehen und dann halt noch diese 420 kleinere Stücklisten. 
Sebastian Spuhler   6:46
Mhm. 
Marvin Wiegner   6:47
Um.
Ja. 
Sebastian Spuhler   6:52
O. K., ja, ja, nee, O. K., auf jeden Fall, danke für die Info. Das reicht ja auch erst mal, weil also wir brauchen ja erst mal Dimension von dem Ganzen, ne, damit wir wissen, wie viel also welche Dimension das Ganze in Zahlen ungefähr annimmt, damit man die Belastbarkeit abschätzen kann. Wie ist es denn mit den Konstrukteuren, die dann nachher damit arbeiten sollen? Ihr habt euch ja schon sehr, sehr Gedanken gemacht, wie die damit arbeiten.
Ja, wie viele denkst du denn, werden gleichzeitig an diese, wenn die Desktop-App umgesetzt ist, werden maximal gleichzeitig daran arbeiten? Ja, weil also ich meine, wenn es 90 große Stücklisten pro Jahr sind, ne, dann wird ja, wenn das auf Monat und Tag runterrechnet, es nicht immer.
Jemand da sitzen, also nicht jeder immer da sitzt oder an den Stücklisten arbeiten. Ne, also ich weiß, das ist vielleicht schwer zu quantifizieren, aber wie viele? 
Marvin Wiegner   7:29
Mhm, ja. 
Sebastian Spuhler   7:37
Maximale Nutzer zur gleichen Zeit wird das, wird die App denn, wenn so ganz ausgerollt ist und das Ganze wie gehabt, wie man sich sehr oft läuft, ne? Wie viel werden denn dann da gleichzeitig arbeiten? Maximal. 
Marvin Wiegner   7:51
Ja, gleichzeitige Arbeit haben wir natürlich dann nur bei den größeren Projekten, also gerade bei Folgeformen, Neuformen. Gut, bei Reparatur und Neubestückung kommt es halt dann auf die Komplexität von dem Projekt an, aber da kann es dann auch schon sein, dass dann 23 oder sogar 4 Leute daran arbeiten. In der Regel bei so Folgeformen, 
Sebastian Spuhler   8:07
Mhm. 
Marvin Wiegner   8:10
Neuformen machen schon 23 Leute immer arbeiten parallel an dem Projekt. 
Sebastian Spuhler   8:18
Mhm. 
Marvin Wiegner   8:21
Genau, das kann auch sein, dass da mal auch teilweise 4 oder 5 Leute dran arbeiten, wenn wir eine Hochzeit haben, wo wir viel Konstruktions und Detailarbeit haben. Also, ich denk mal so, jetzt aus das, was ich die letzten Jahre über beobachtet hab, würde ich sagen.
Ja, so 5 Leute ungefähr könnte schon 'ne gute Maximalzahl sein. Ja, plus minus, je nach Schwankungen, je nach Auftragsart. Wir haben auch teilweise dann arbeiten wir auch noch mit externen Konstruktionsdiensten,
Dienstleistern zusammen und aber die machen dann keine Stückliste, die tragen dann vielleicht 'ne Stückliste bei uns in die Vorlage ein und sagen dann, ja das und das haben wir gemacht, das das sind jetzt neue Bauteile, die in die Stückliste kommen und.
Wir prüfen das aber alles noch mal, bevor wir das bei uns in das Stücklistensystem aufnehmen.
Also ja, es ist jetzt schwierig zu sagen, ob man da externe Konstrukteure mitberücksichtigt, jetzt für euer System wahrscheinlich sowieso nicht, aber deswegen ging es mir auch darum zu sagen, dass man eben dieser ganzen Informationen, die man in dem Projekt erhält, 
Sebastian Spuhler   9:26
Mhm. 
Marvin Wiegner   9:30
Dass man die irgendwo zentral sammeln kann und beziehungsweise dann durch den KI-Agent unterstützt, die Informationen zusammentragen kann. 
Sebastian Spuhler   9:32
Ja, ja, genau, ja.
Ja, ja, nee, nee, das war ja auch relativ gut beschrieben, wie das Ganze gemacht werden soll. Das ist ja relativ, ja klar beschrieben, wo welche Änderungen was dokumentiert werden soll. Das ist ja relativ klar. Das war jetzt nichts, wo man sagt, das ist technisch nicht umsetzbar, ne?
Da geht es halt um die reine ja Belastbarkeit nachher des Systems. So, wenn man sich dann drum kümmert, ja um Infrastruktur, Technik, Dinge kümmert wie Hardware und so nachher, ne, ist das natürlich von Relevanz. Deswegen müssen wir diese, ja diese Zahlen müssen wir auf jeden Fall wissen. 
Marvin Wiegner   10:09
Ja, also wenn wir oder ich bin jetzt auch davon ausgegangen und ich glaub da seid ihr wahrscheinlich auch der gleichen Meinung, dass wir das Ganze dann on premise bei uns aufsetzen werden. Da muss man dann schauen, wo man das Ganze aufsetzt, ob man es dann auf einem bestehenden Server aufsetzen kann oder ob man dafür was Neues anschaffen müsste.
Aber das muss dann unsere IT sagen. 
Sebastian Spuhler   10:29
Mhm, ja, ja, nee, genau, das müssen wir mit der I.D. bestimmen, ja. 
Amin Douioui   10:31
Das K.I. Sprachmodell, das K.I. Sprachmodell muss auch on premise sein. Oder ist es OK, wenn das jetzt auf Deutsch Clouds K.I.?
Weil da stand jetzt Bereitstellungsmodell. Da war jetzt die Frage, ob alles on-promise sein muss oder ob das KI-Modell auch einfach extern in der Cloud-Anwendung sein kann, wenn es auf deutschen Servern ist, also DSTVO-konform KI. 
Marvin Wiegner   10:42
am 
Sebastian Spuhler   10:49
Bing. 
Marvin Wiegner   10:52
Ja.
Ja, also ich denk mal schon, das muss auf jeden Fall D.S.G.V.O. konform sein, weil wir also nicht nur, nicht nur datenschutzmäßig oder personenbezogene Daten, sondern auch unsere firmeninternen Daten sensible 
Amin Douioui   11:00
Ja, klar. 
Marvin Wiegner   11:09
Daten, unser Know-how, das wir dann ja auch bestmöglich schützen wollen, darum geht es uns primär. Also war ja mit Stücklisten, ja personenbezogene Daten ist nicht unbedingt, aber 
Amin Douioui   11:15
Yeah. 
Sebastian Spuhler   11:15
Mhm. 
Marvin Wiegner   11:24
ja, firmenbezogene Daten, also dann nicht um private oder persönliche oder reale Personen, sondern juristische Personen in dem Fall. Aber solche Daten müssen wir natürlich auch sichern und ja, sehr verantwortungsvoll damit umgehen. 
Amin Douioui   11:25
No. 
Sebastian Spuhler   11:26
Yeah. 
Marvin Wiegner   11:42
und wir oder ihr werdet dann wahrscheinlich auch mit einer Vektordatenbank arbeiten. Das heißt, man kann dann wahrscheinlich über diese Vektordatenbank auch 'n gewissen Kontext der K. I. mitgeben. Also man muss der K. I. nicht den kompletten Kontext überlassen zum Interpretieren.
Oder wie würde das technisch bei euch aussehen? 
Sebastian Spuhler   12:03
Yeah. 
Amin Douioui   12:03
Ja, das ist so. Erzählst du. 
Sebastian Spuhler   12:05
Ja, Armin, ja, du zuerst, dann kann ich was sagen. 
Amin Douioui   12:07
Ach so, ja genau. Also, es kommt halt immer drauf an. Also, mit der Vektordatenbank ist ja nur so, wenn man halt wirklich größere Mengen an Listen speichern möchte und Vektordatenbank nutzt, nutzt man ja so, dass man genau das Wissen, was in der Datenbank liegt, nutzen möchte und jetzt nicht anderes Wissen dafür sind in der Vektordatenbank da.
Bei dem Use Case müsste ich mir das genauer anschauen, ob es auch anders schon einfach funktioniert und ausreicht. Also, ich glaube jetzt nicht. Also, wenn du deine Meinung ist, ja wirklich, dass man da wirklich eine sehr, sehr große Menge an Wissen speichert. Und ich glaube, wenn man einfach jetzt. 
Marvin Wiegner   12:40
Mhm. 
Amin Douioui   12:42
Bei diesem Projekt müsste ich mir das anschauen, ob man eigentlich, ob da auch wirklich ein Vector davon benötigt wird oder ob das auch einfach einfacher umzusetzen ist. Das kann ich jetzt noch nicht genau sagen, aber grundsätzlich ja. 
Marvin Wiegner   12:53
Also das Interpretieren, das dafür nicht im speziellen Wissen gefordert wird, so das musst du dir oder das ist jetzt wahrscheinlich dann der Kern deiner Fragestellung, dass du dir anschauen möchtest, möchtest, brauche ich um die richtigen Schlussfolgerungen für die Stückliste zu ziehen, brauche ich dafür spezielles Wissen oder reicht dafür das Wissen 
Amin Douioui   13:02
Ja.
Genau. 
Marvin Wiegner   13:12
Oder das Vortraining, was die KI-Modelle bereits haben. 
Amin Douioui   13:15
Genau, das ist jetzt das, das ist 'ne Frage, die wir auch noch klären wollten. Genau, bräuchten wir irgendwelches interne Wissen, was jetzt einfach nur intern irgendwie festgehalten ist, irgendwo, dass man das in den Vektor da dran lädt, damit man die Sitzen nutzt, um halt Entscheidungen zu treffen bei der Stückliste. Das ist halt das, was wir klären müssen.
Falls das Wissen jetzt, falls das jetzt nichts neuartiges Wissen ist und man das so schon anhand der Stücke schon so raus interpretieren kann, dann bräuchte es man halt grundsätzlich nicht. Genau, das ist der Punkt, ja. 
Marvin Wiegner   13:41
Mhm.
Ja, also prinzipiell haben wir natürlich schon sehr, also ich hab es auch versucht zu beschreiben, sehr kontextabhängiges Wissen auch. Also das eine Projekt kann so laufen, das nächste kann wieder anders laufen, aber
ja, diese Informationen müssen wir dann einfach zusammentragen und müssen dann das in dem Projekt in Verbindung setzen, dass das zu dem Projekt gehört. Dann kann das dann könnte das die K. I. schon aus dem Projekt heraus schon selber identifizieren und interpretieren. 
Amin Douioui   14:08
Ja. 
Marvin Wiegner   14:18
Was wir aber auch haben, ist schon auch 'n gewisses Maß an Kontextwissen, an technischen Wissen. Wenn ich jetzt da dann hier 'nen Bauteilbeschreibung in der Stückliste hab, irgendwie 'nen 'nen Ohrring oder was auch immer.
Da ist irgendeine Nummer hinterlegt und ich sage dann: "Ja, bitte nimm dieses Bauteil in die Stückliste auf." Da muss das Bauteil natürlich auch so beschrieben sein, dass ich es auch bestellen kann. Irgendeine Nummer von irgendeinem Katalog sagt einem da vielleicht wenig, vielleicht ist es auch eine.
ganz alte Nummer, eine ganz alte Katalognummer von irgendeinen großen Hersteller, großen Zulieferer oder irgendeinen Hersteller, den es heute nicht mehr gibt. Da muss ich natürlich auch herausfinden, ja was ist das denn überhaupt für ein Bauteil, was beschreibt diese Nummer, dieses Bauteil genau?
und da jetzt die K. I. loszuschicken und sagen, ja finde mal raus, was das für 'n Bauteil ist, das finde ich sehr gefährlich. Also weil es da sehr viel Interpretationsspielraum gibt. 
Amin Douioui   15:18
Yeah, genau.
I know. 
Marvin Wiegner   15:23
Das habe ich dann aber auch versucht mit aufzunehmen. Also, das meine ich mit dem Stichwort Ontologie, also dass man hier diese. 
Sebastian Spuhler   15:23
Ja. 
Marvin Wiegner   15:32
Dieses Wissen beschreibt, das sehe ich aber jetzt nachgelagert oder zukünftig, dass wir uns hier so eine Art Wissensdatenbank aufbauen. 
Amin Douioui   15:40
Genau, ja. 
Marvin Wiegner   15:42
Ich hoffe, das passt auch für euch so, dass ihr das da genauso seht. 
Amin Douioui   15:47
Yeah, you know, it's passing. 
Sebastian Spuhler   15:47
Ja, nee, genau, für so was braucht man ja eigentlich Vektordatenbank, ne, wenn man irgendein kontextuelles Wissen haben muss, was nicht fehlinterpretiert werden darf, ja. Das heißt, die die K. I. ruft dann wirklich nur das ab, was auch in der Vektordatenbank steht, damit man die ja Fehlinterpretationswahrscheinlichkeiten, Halluzinationswahrscheinlichkeiten nachher auf 0 bringt, ne, da ist das. 
Marvin Wiegner   15:51
Ja. 
Sebastian Spuhler   16:06
Gut, und auf diese Vektordatenbank kann man dann auch natürlich später dann weiteres Wissen, das dazu kommt, dort indexieren und dann alles darauf aufbauen. Das wird dann kein Problem sein. Das können wir dann einbauen, ja.
War ja auch, glaube ich, in den späteren Stufen des Projekts war ja auch, glaube ich, gewollt, dass es eine Chatoberfläche gibt, ne, meine ich, ja. 
Marvin Wiegner   16:26
Genau, ja. Also, da, ja, also.
So, diese Chat-Oberfläche, beziehungsweise was ich mir bei der UI gedacht habe, jetzt wo du es jetzt halt angesprochen hast, ist halt einfach, dass ich glaube, dass wir nicht.
Das einfach unsere Situation, unsere Anforderung ist sehr komplex. Wir haben irgendwas als Input und wollen dann irgendwas als Output haben beziehungsweise unser Output ist schon 'n bisschen definierter, aber wir haben immer irgendwas als als Input und dieses Irgendwas dann 
Sebastian Spuhler   16:55
Mhm. 
Marvin Wiegner   17:01
in so 'ner Logik greifbar zu machen, das würde so 'ne komplexe Logikstruktur ja mit sich bringen oder wahrscheinlich anfordern, dass es wahrscheinlich dann für uns auch wenig
Sinn macht, auch weil wir das natürlich, dieses Programm muss für jeden Konstrukteur zugänglich sein. Also man muss sich jetzt da nicht unbedingt irgendwelche Methoden aneignen, irgendwelches ja Spezialwissen über irgendwelche I. T. Algorithmen oder irgendwelche Logikableitungen.
So, das war eigentlich mein Gedanke. Aber mein Gedanke ist auch dabei, dass wir natürlich auch das transparent darstellen müssen: Wie fällt die KI ihre Entscheidung?
Also, was führt dazu, dass aus diesem Input dieses Ergebnis wird und das war halt so meine Idee dabei, dass man da mit so einem Logikgatter das am besten darstellen kann. Ob das jetzt halt so ist, könnt ihr wahrscheinlich wesentlich besser beurteilen. 
Amin Douioui   17:45
Mhm. 
Sebastian Spuhler   18:02
Mhm. 
Marvin Wiegner   18:03
Also darum ging es mir, dass ich halt die Entscheidungen transparent darstellen kann. Und wenn ich dann die Entscheidungen in so einer Logik darstelle, dann hab ich natürlich hier wieder irgendwas, was vielleicht nicht so ganz zugänglich ist, ganz einfach zu.
Editieren ist, dass man dann sagt: "OK, bitte KI, bau mir das so und so um, dass die Information so und so verarbeitet wird." Aber ich kann das dann immer noch nachvollziehen, wie die Entscheidung getroffen wird. 
Sebastian Spuhler   18:32
Ja, ja, genau. Also, ich hatte mir das auch angeschaut und es wird am Ende auch sowieso darauf hinauslaufen, dass wir diese ja ganzen Funktionen Schritt für Schritt dann nachbauen oder Schritt für Schritt implementieren, dass man zum Beispiel, wie die Situation ist mit dem Logikgatter zum Beispiel und dieser ja Chat-Oberfläche, dass das mit der Zeit immer mehr interaktiver wird, ne.
Dass man diese Funktionen, wie der Konstrukteur darauf zugreifen kann und wie er mit diesem, ja, mit diesem Modell, diesem, ja, diesem Raster, wie die K.I. gehandelt hat, soll sie ja nachher dokumentieren und so, ne? Und diese Regeln, die dann auch entstehen, mit denen, die der Konstrukteur nachher auch verändern können soll, wenn ich es richtig verstanden hab, ne? 
Marvin Wiegner   18:52
Yeah.
Genau, ja. 
Sebastian Spuhler   19:10
teilweise auch per Chat, ne? Das ist alles, das hört man dann ja stückweise nach und nach, wird man das System immer interaktiver machen, ne? Wenn die Basis steht, dann ist es ganz normal, dass von der U.I., dass man dann außen rum nachher die ganzen Funktionen hinzufügt. Das ist ganz normal und da sehe ich auch.
Ja, an sich kein Problem. Jetzt immer noch mal zum Punkt. So kommen wir jetzt ein bisschen abgeschliffen, das heißt.
Das Sprachmodell on Premise ist Stand jetzt geplant. Es ist aber kein K.O.-Kriterium, oder? 
Marvin Wiegner   19:44
Ich würde sagen, nein. Also, wenn der Anbieter das garantieren kann, dass da die Daten nicht irgendwie weiterverarbeitet werden, nicht irgendwie für K. I. Modelltraining verwendet werden und so weiter und nicht weitergespeichert werden, ich glaub 'n gewisses. 
Sebastian Spuhler   19:46
Mhm. 
Marvin Wiegner   20:00
Ne gewisse Zeit werden die Daten glaub ich gespeichert. Ich glaub so 30 Tage ist glaub ich da so n so n Zeitraum, aber da geht es ja dann eher so um. 
Sebastian Spuhler   20:14
Ja, ja. 
Marvin Wiegner   20:19
Ja, aber ich glaub halt auch, dass diese Externen dann auch wesentlich leistungsfähiger sind. Also, wenn wir das alles intern bei uns aufbauen, dann müssen wir halt auch die dementsprechende Hardware bereitstellen. Und ich glaub, dass genau, ja, ich glaub, dass das lohnt, würde sich dann für uns gar nicht lohnen. 
Amin Douioui   20:25
Genau, ja. 
Sebastian Spuhler   20:30
Mhm, darüber will ich hinaus, ja. 
Marvin Wiegner   20:36
Also, wir sind da bestimmt auch auf externe Ressourcen angewiesen. 
Sebastian Spuhler   20:36
Mhm.
Ja genau, darauf will ich hinaus, auf jeden Fall, weil ja, wenn man das ganz on premise macht, also ich weiß ja ungefähr, wie die Hardware-Situation ja bei euch ist, welche Server da zur Verfügung stehen und weiß, dass man, wenn man das Ding wirklich laufen lassen will, dass da auch. 
Amin Douioui   20:42
Yeah. 
Sebastian Spuhler   20:58
Aber wahrscheinlich nicht in ja gewisse Investitionen in Hardware, wenn man drum rum kommt, ne wenn man das wirklich kommt, dann auch hosten will ne und dann muss man sich irgendwann muss man sich dann halt auch fragen OK gut, in welchem Verhältnis steht das jetzt finanziell zueinander? Ne, das muss man in einer größeren Runde besprechen ne. 
Marvin Wiegner   21:02
No. 
Sebastian Spuhler   21:13
Aber wenn wirklich das Sprachmodell auch noch on premise machen muss, ne, dann sind das auch ja Dinge, die dann nebenbei noch passieren müssen, was Hardware angeht und ja, was gewisse Rechenleistung angeht, die ihr euch noch besorgen müsstet. Und da ist dann der Weg, dass man dann auch 'ne Diskussionslage hat und dann einfach schaut und klar dokumentieren kann, O. K.
Das ist jetzt wirtschaftlich gesehen, ist es jetzt, wenn man einen externen Cloud-Dienstleister holt, ne, ist das jetzt so und so. Und wenn man es intern macht, ne, dann mit der bestehenden Hardware, ne, müsste man so und so 'ne Zusatzinvestition machen, ne, das ist halt einfach so. 
Marvin Wiegner   21:39
Ja. 
Sebastian Spuhler   21:47
Und will ich nur wissen, dass wir da einen gewissen Spielraum haben, weil da stand ja auch ja, keine externen Cloud-Abhängigkeiten, ne? Stand ja auch so Wort für Wort im Lastenheft drin, ne? Und ja, da wìrd ich halt einfach. 
Marvin Wiegner   21:47
Ja.
Genau, ja. 
Sebastian Spuhler   22:02
Es ist halt einfach gut zu wissen, dass man da 'ne gewisse Offenheit hat. Ja, nicht man will sich auf eine Sache festlegen, aber man ist bereit, die Sachen gegeneinander abzuwägen. Was das denn, wenn wir euch dann mal das genau dokumentieren, was das denn von beiden Seiten für, also was dann jeweils bei beiden Varianten für Aufwendungen.
Auf euch zukommen würden und was das, wie sich das unterscheiden würde. 
Marvin Wiegner   22:23
Ja, also wir setzen ja auch heute schon.
ja K. I. bei uns ein, natürlich dann halt die Modelle, die dann auch ja für Firmen gedacht sind, die ganzen Enterprise Versionen davon. Ja, also da, da sind wir auch schon relativ offen im Umgang damit. 
Sebastian Spuhler   22:37
Mhm. 
Marvin Wiegner   22:44
Aber ja, es ist halt dabei immer die Gefahr, dass man da dann was nach draußen gibt und das wollen wir auf das Minimalste reduzieren. Das war uns da schon immer wichtig. Aber eine eine Sache, die ich mir auch die letzten. 
Sebastian Spuhler   22:51
Mhm. 
Amin Douioui   22:54
Ja. 
Sebastian Spuhler   22:57
Ja, gerade diese Modelle sind ja. 
Marvin Wiegner   23:02
Wochen so überlegt habe, wenn wir dann eine Vektordatenbank haben, dann ist es ja eigentlich schon klar, nach welchen Regeln die Schlussfolgerung läuft. Dann bräuchte man ja gar nicht so ein leistungsfähiges Modell. Dann könnte ja ein lokales Modell auch an die gleiche Leistungsfähigkeit herankommen. 
Amin Douioui   23:16
Ne, bräuchte man nicht, ne.
Ja, ja, aber das Problem ist halt auch bei bei lokalen Modellen, wenn mehrere Leute gleichzeitig zugreifen, dass dass die Geschwindigkeit extrem langsam ist und halt einfach man merkt, man merkt einfach, dass es ein lokales Modell ist, vor allem bei den kleineren. 
Marvin Wiegner   23:31
Mhm. 
Amin Douioui   23:38
Man könnte sich also, man könnte, wenn man jetzt so anschaut, was sind so die besten lokalen Modelle aktuell, die jetzt auch einfach an jetzt so gute Frontier Modelle rankommen, da bräuchte man auch Hardware-Investitionen, die auch gigantisch hoch sind. 
Marvin Wiegner   23:53
Also im sechsstelligen Bereich, dann ne. 
Amin Douioui   23:54
Dann.
Ja, fünf bis sechsstelligen Bereich. Klar, gibt es auch lokale Modelle, die kleiner sind, die man die auch ausreichen würden, hätte man dann 'ne Vektordatenbank, aber da ist halt auch, da braucht man trotzdem Hardware und vor allem wegen der Performance und da muss halt auch wirklich die Vektordatenbank noch sehr gut sein. Man sagt ja immer so, lokale Modelle sind 'n paar Monate hinterher, denn der auf den offiziellen Modellen, das sind
inzwischen ja nicht mehr so, aber wenn man, ich würde jetzt sagen, das beste lokale Modell, was man jetzt für diesen Usecast nutzen könnte, wäre dieses Tween 3.6. Also müsste man halt auch Hardware in Hardware investieren, ja, muss man halt am Ende einfach abwägen. Aber die natürlich, genau, wenn man jetzt alle Regeln, alle das ganze Wissen in einer Vektordatenbank
speichert, dann könnte man auch einfach bei den Cloud Modellen, die D. S. T. V. O. konform sind, Azure gehostet, könnte man da halt auch gegebenenfalls einfach einfachere Modelle nutzen und da sind ja die Kosten auch deutsch, deutlich, deutlich, deutlich niedriger, da muss man halt auch einfach am Ende abwägen. Aber klar, wenn man schon eine sehr gute Wissensdatenbank hat, Wissensbasis hat, 
Marvin Wiegner   24:44
Mhm. 
Amin Douioui   24:54
Dann ist die Qualität, ist es ja genau die Qualität von dem Sprachmodell nicht mehr so wichtig, weil genau er nur auf das Wissen zugreift. Und wenn das dann schon gut ausgereift ist, dann bräuchte man jetzt nicht in Frontier Modell, sondern reicht auch, wenn man so einfach die.
GPT 5.4 Mini oder so verwendet. Das reicht auch schon aus, ja.
oder halt ja, 44 vierer Modelle, das würde auch alles ausreichen. 
Marvin Wiegner   25:18
Yeah.
Ja, also nach unserer momentanen Einschätzung, nach unserer momentanen Situation, spricht da ja auch nichts dagegen, da ein externes Cloud-Modell zu nehmen. 
Sebastian Spuhler   25:22
Nein. 
Amin Douioui   25:30
Ja, das haben wir auch bei dem Einkaufsprojekt gemacht. Da haben wir. 
Marvin Wiegner   25:34
Genau, ja. 
Sebastian Spuhler   25:35
Ja, und das ist ja nun mal, und das ist nun mal, also mit den Servern, die in Frankfurt stehen, von Azure, das ist auf jeden Fall immer ein gutes Stück sicherer als die Enterprise-Varianten von so manchen großen Anbietern, weil die sind ein Zeitthema, das ist eine Grauzone, sag ich mal so. 
Marvin Wiegner   25:46
Ja. 
Sebastian Spuhler   25:50
Was da alles, ja, wie man denen trauen kann, welche Daten da wohin abfließen und was mit denen nachher passiert und wie das rechtlich anzusiedeln ist. Seit dem jetzt, seit dem 2. August, ist ja eh nochmal alles ein bisschen strenger geworden, seit der AI Act da vollständig in Kraft tritt. 
Amin Douioui   25:57
Ja. 
Sebastian Spuhler   26:05
Und ja, da sind solche Sachen immer bisschen bisschen komplizierter, aber ja, man muss immer noch trotzdem die wirtschaftliche Perspektive im Auge behalten. Also ich bin ja also grundsätzlich das ich bin was heißt mit zuversichtlich, aber grundsätzlich ist es ja so, dass dass die Leistung auch von lokalen Modellen jetzt in.
in der letzten Zeit nicht schlechter geworden ist und die wird auch immer besser. Das Ganze wird auch immer kostengünstiger. Na ja, wenn man das Projekt startet, dann muss man einfach mit dem den Status quo erheben. Wie ist es Stand jetzt? Wie sind hier die Bedingungen, die wirtschaftliche Lage, wenn wir das machen und Und dann muss man sich halt dementsprechend entscheiden.
Ein letzter Punkt, wenn ihr nichts mehr zu dem Thema zu sagen habt. 
Marvin Wiegner   26:43
Von mir aus kann es weitergehen, ja. 
Amin Douioui   26:43
Ja. 
Sebastian Spuhler   26:45
wäre, hast du oder habt ihr für das Projekt schon bestimmte, ja, K. P. I. s erhoben, an denen der Erfolg gemessen werden soll, also quasi Zahlen oder ja, also unmittelbar messbare Zahlen.
ne, die in dieser Desktop-App, dieser Stücklistenagent, nachher produziert an ja an Ergebnissen, an Leistung, mit der man nachher den das Projekt als erfolgreich messen kann, an denen man sich orientieren kann, ja lang oder mittelfristig. 
Marvin Wiegner   27:18
Ich glaube, da gibt es keine quantifizierbaren.
ja, Messungen, die wir machen können, weil bei uns die Projekte immer unterschiedlich sind. Also kein Projekt ist 1 zu 1 vergleichbar mit einem anderen. Deswegen ist sowas schwierig. Deswegen ich glaube, unsere beste Chance ist da wirklich 'ne Tendenz festzustellen in unserem 
Sebastian Spuhler   27:30
Mhm. 
Marvin Wiegner   27:43
allgemeinen in unserer allgemeinen Aufwendung, wie viel unserer Zeit wir investieren, um Stücklisten zu erstellen und vielleicht auch durch die Befragung der 
Sebastian Spuhler   27:49
Mhm. 
Marvin Wiegner   27:59
Einzelnen Konstrukteure: Was bringt das?
Das Tool und.
Ja, es ist schwierig, solche Zahlen festzulegen. 
Amin Douioui   28:13
OK, also einfach der größte, also das, was halt das System nutzen soll, einfach eine große Zeiteinsparung und halt einfach effizientere Arbeit, damit sich schon Konstrukteure auf ihre eigentliche Arbeit konzentrieren können und nicht nur Stücklisten abtippen. 
Marvin Wiegner   28:28
Genau, ja. Ich glaube, da werden wir auch in unserer Zeiterfassung schon einiges sehen. 
Amin Douioui   28:28
Yeah. 
Sebastian Spuhler   28:33
Mhm. 
Marvin Wiegner   28:35
Ja. 
Amin Douioui   28:37
Ja.
OK. 
Sebastian Spuhler   28:40
OK, good, ja.
Ja, O. K., also von meiner Seite war es das jetzt erstmal mit den Fragen oder den Unklarheiten, die es noch gab. Wie gesagt, das mit diesen, das Wichtigste war halt das wirklich mit den mit den Zahlen, wie viel Leute da halt gleichzeitig arbeiten oder wie man das ungefähr aufs Jahr oder auf 'n Monat quantifizieren kann und was damit halt direkt zusammenhängt, ist halt das.
Die Modellwahl oder beziehungsweise ob man Cloud verwendet oder nicht beziehungsweise wie offen ihr dafür seid. Ne, ich denke, wenn wir diese ganzen Infos haben, können wir euch da auch einen näheren ja Vorschlag machen, wie wir da weiter vorgehen, wie wir das Projekt strukturieren würden, ne. 
Marvin Wiegner   29:16
Yeah. 
Sebastian Spuhler   29:17
Dazu wird in den nächsten Wochen was kommen. Ich glaube, bei euch ist ja bestimmt auch noch jetzt bisschen, ja, klein bisschen Sommerpause. Sind ja auch einige im Urlaub, wie ich mitbekommen habe, und. 
Marvin Wiegner   29:24
Ja, ja, jetzt im August ist noch einige. Ja, ist noch Urlaubszeit, ja. 
Sebastian Spuhler   29:28
Ja genau, aber ich denke, ihr werdet in den nächsten Wochen noch von uns was hören. Wie gesagt, es war mir nur wichtig, dass jetzt paar Rückfragen zum Lastenheft noch lernen, damit wir da nichts fehlinterpretieren oder keine Fehlschlüsse draus ziehen im Großen und Ganzen. Und ja,
Das ist einfach noch mal wichtig. Beim nächsten Meeting holen wir dann mindestens noch mal den Jürgen und ja, alle anderen Personen, die irgendwie beteiligt sind, mit rein und dann ja, freu ich mich drauf, wie es weitergeht. Danke für dein Input auf jeden Fall. Ich schick dir noch das Transkript und. 
Marvin Wiegner   29:55
Ja. 
Sebastian Spuhler   30:02
Armin, hast du noch irgendwas zu sagen oder zu fragen gerade? 
Amin Douioui   30:05
Ja, das passt alles. 
Sebastian Spuhler   30:06
Bevor ich hier schnell abbreche und Feierabend mache.
Ne, good. OK.
Mhm. 
Amin Douioui   30:24
OK, super. 
Marvin Wiegner   30:24
Ja. 
Sebastian Spuhler   30:25
Ja, perfekt. Haben wir keinen Zeitdruck, was es angeht, und dir noch viel Spaß auf deinem Lehrgang. 
Marvin Wiegner   30:28
Ja.
Alles klar, vielen Dank. 
Amin Douioui   30:31
Danke. Tschüss. 
Sebastian Spuhler   30:31
Yep. Bis dann. Ciao. 
Marvin Wiegner   30:33
Dann ja, ciao. 
Sebastian Spuhler Transkription beendet
