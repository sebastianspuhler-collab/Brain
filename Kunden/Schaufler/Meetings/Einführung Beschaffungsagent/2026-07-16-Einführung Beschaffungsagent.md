---
tags:
  - Beschaffungsagent
  - Auftragsbestätigung
  - Eskalation
  - ERP
  - Schaufler
quelle: Einführung Beschaffungsagent.docx
datum: 2026-07-16
kategorie: Produkt
---

# Einführung Beschaffungsagent

## Zusammenfassung
Besprechungstranskript zur Einführung/Weiterentwicklung des Beschaffungsagenten mit Benjamin Schmohl, Amin Douioui und Sebastian Spuhler. Themen: fehlende Zuordnung von Auftragsbestätigungen zu Bestellungen, die drei Eskalationsfälle (fehlende AB, Mengenabweichung, AB ohne Bestellung) sowie Umrechnungsprobleme zwischen Einheiten (z.B. Fass vs. Liter).

## Vollständiger Inhalt
Einführung Beschaffungsagent-20260716_083828-Besprechungstranskript 16. Juli 2026, 06:38AM 29 Min. 36 Sek. 
Sebastian Spuhler Transkription gestartet 
Benjamin Schmohl   0:03
Kein klares, eine klare Identifikation haben. 
Amin Douioui   0:05
Yeah.
Also, das kann schon öfters vorkommen. 
Benjamin Schmohl   0:12
Das kommt durchaus mal vor, weil wir auch in dem Postfach kommen, ja wirklich alle Auftragsbestätigungen an und auch also. 
Amin Douioui   0:14
Ja. 
Benjamin Schmohl   0:24
Ja, wenn wir auch mal keine Ahnung mal telefonisch mal was bestellt haben, da gibt es ja noch keine Bestellbelegnummer. 
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
OK, die hat OK. Die sollten wir dann aber auch ausschließen aus der Auftragsbestätigungsseite. 
Benjamin Schmohl   0:52
Yep. 
Amin Douioui   0:54
die sollten jetzt hier nicht angezeigt werden, in dem Sinne. Also, so hatten wir das jetzt implementiert gehabt und die werden hier unter Lieferung, Bestellung werden die halt aufgezählt, aber nur mit einem Hinweis, Bestellung wurde nicht im E. R. P. gefunden. So hatte ich das jetzt gemacht, aber es würde jetzt auch nicht 
Benjamin Schmohl   0:56
OK, good. 
Amin Douioui   1:12
Lieferantenstore oder den Report mit aufgenommen.
O.K., dann noch eine zweite Sache, die mir noch aufgefallen ist. 
Sebastian Spuhler   1:18
gerade, weil ich das Ganze das Ganze mal zusammenfassen kann, wenn ich kurz unterbreche. Ja, und zwar ist es ja so genau, wie gesagt, dass es Fälle gibt, wo Auftragsbestätigungen da sind, die aber keiner Bestellung direkt zugeordnet werden können. Ja, dass die dann quasi aus der Wertung rausgenommen werden, also komplett. 
Benjamin Schmohl   1:32
Yeah. 
Sebastian Spuhler   1:33
Ja, der umgekehrte Fall ist ja, es gibt ja 3 Fälle, sag ich jetzt mal. Ja, es ist ne, es ist ne Bestellung da, aber keine A. B., dann eskaliert das wegen fehlender A. B. Wenn ne Bestellung ohne A. B. da ist, dann vergleicht er die und eskaliert per Abweichung. Und in diesem Fall, wenn A. B. da ist. 
Amin Douioui   1:33
Ja. 
Benjamin Schmohl   1:34
Yeah. 
Sebastian Spuhler   1:50
Aber keine Bestellung dazu. Dann passiert gar nichts. Dann wird das nicht in die Wertung rausgenommen, sondern nur als Hinweis markiert. 
Benjamin Schmohl   1:57
Mhm. 
Amin Douioui   1:57
Yeah. 
Sebastian Spuhler   1:59
OK. 
Amin Douioui   1:59
Genau, und dann gab es noch einmal den Fall, dass da genau da war auf der A. B. stand da drauf ein Fass 200 Liter, aber dann im E. A. P. als ein Stück. Gibt es erst das von solchen Umrechnungen, die wir wissen sollten. 
Benjamin Schmohl   2:10
Yeah. 
Sebastian Spuhler   2:11
Be. 
Benjamin Schmohl   2:12
Yeah. 
Amin Douioui   2:15
Weil das hatte dann bei uns eskaliert gehabt, weil es ja keine klare Umrechnung zwischen ein Fass und Liter g
