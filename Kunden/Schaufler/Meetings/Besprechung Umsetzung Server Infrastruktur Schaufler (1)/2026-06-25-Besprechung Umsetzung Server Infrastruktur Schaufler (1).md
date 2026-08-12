---
tags:
  - Server-Infrastruktur
  - Hetzner
  - WireGuard
  - Deployment
  - Schaufler
quelle: Besprechung Umsetzung Server Infrastruktur Schaufler (1).docx
datum: 2026-06-25
kategorie: Kunde
---

# Besprechung Umsetzung Server Infrastruktur Schaufler (1)

## Zusammenfassung
Besprechungstranskript vom 25. Juni 2026 zur Umsetzung der Server-Infrastruktur für den Kunden Schaufler. Besprochen wurden der geplante Hetzner Cloud-Server, die Vergabe von Zugriffsrechten an das Prozessia-Team, das Deployment und die Einrichtung eines WireGuard-Tunnels für den Zugriff auf WinForm. Offene Punkte: Klärung des Zeitplans für die Bereitstellung des Servers sowie Status der Testview bei Jochen.

## Vollständiger Inhalt
Besprechung Umsetzung Server Infrastruktur Schaufler-20260625_093747-Besprechungstranskript 25. Juni 2026, 07:37AM 27 Min. 0 Sek. 
Sebastian Spuhler Transkription gestartet 
Sebastian Spuhler   0:03
Ähm.
Die Woche noch, ja, uns versucht an den Jochen zu wenden. Also, ich weiß nicht, wie weit er ist oder wie lange das dauert, aber um da mal so eine kleine Einschätzung zu bekommen, wann der ja der Testview fertig ist, damit wir auch endlich mit WinForm mit der Anbindung loslegen können. 
Benjamin Schmohl   0:13
Mhm. 
Sebastian Spuhler   0:26
Bestellung ist ja schon abgeschlossen und ja, deswegen freuen wir uns, wenn es da losgeht. 
Benjamin Schmohl   0:33
Muss eh noch dem Jochen gleich noch auf eine E-Mail zurückschreiben. Von daher kann ich gleich dann mal fragen, weil der da vielleicht. 
Sebastian Spuhler   0:46
OK, super.
Weil ansonsten, das sind eigentlich so die einzigen Punkte, die noch grad ja offen waren jetzt außerhalb des Hauptthemas dieses Meetings. Das war einmal, ja wie gesagt, das mit Messberichten und einmal das mit der mit der Testview. Aber das haben wir ja alles im Blick.
Hm.
Guten Morgen. 
Jonas Rösch   1:21
So, hallo, Verzeihung, mein Update, mein Laptop hatte gerade noch ein Update des Todes. 
Florian Knoblauch   1:27
Wie gesagt, ich find es lustig, wenn die IT Probleme am Rechner hat. 
Jonas Rösch   1:33
Problem ist es nicht, sondern eher das Ärgernis, das mittlerweile jeden betrifft. Da ist die IT nicht geschützt davor. 
Sebastian Spuhler   1:42
Ja, guten Morgen von unserer Seite aus. Also, ich weiß nicht, ob Sie so raushören, aber ich bin etwas krank und angeschlagen. Noch deswegen wird hier tendenziell eher mein Teampartner heute reden und ich mich da ein bisschen raushalten. Aber ja, wir wollen jetzt erstmal vorstellen, was jetzt wirklich die konkreten Handlungen
Schritte sind, da wir jetzt ja auch ja die Bestellungen für den Server und alles haben. Wollten wir einfach nur mal klären, okay, welchen Server, wie läuft das Ganze im Detail ab und wie kriegen wir das jetzt so schnell wie möglich deployed. Das ist so ein bisschen das Ziel hinter diesem Meeting heute.
So, ja, dann Armin, willst du mal starten? 
Amin Douioui   2:28
Also genau, also wir haben uns ja, wir haben ja uns darauf vereinbart, dass wir uns ja so ein Cloud, dass ihr euch halt einen Cloud-Server holt, jetzt bei Hetzner, uns dann die Zugriffsrechte gibt, dass wir das dann danach verwalten und genau betreuen und dass wir das Deployment dann auf diesem Cloud-Server machen.
Genau, außerdem müssten wir das mit dem noch so 'n Wireguard Tunnel erstellen, mit damit wir auch Zugriff auf Winform haben. Genau, aber Ersteres ist natürlich, dass wir erstmal, dass wir den Cloud-Server holen, dann wieder 'n
Darauf deployen können, was wir dann verwalten können. Jetzt meine Frage: Wann ist das jetzt geplant? Wie machen wir das? Wann? Wie ist so gerade der Stand der Dinge? 
Florian Knoblauch   3:14
An wen war die Frage gestellt? 
Amin Douioui   3:17
Allgemein trat in die Run
