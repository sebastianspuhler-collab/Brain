---
tags:
  - Prototyp
  - Dashboard
  - Auftragsbestätigung
  - Zwischenstand
  - Schaufler
quelle: Zwischenstand Prototyp.pdf
datum: 2026-06-09
kategorie: Kunde
---

# Zwischenstand Prototyp

Transkript eines Meeting-Calls (23 Min.) vom 03.11. zwischen Prozessia (Sebastian Spuhler, Amin) und Kunde Schaufler (Benjamin). Präsentation des aktuellen Prototyp-Stands eines KI-Dashboards mit Ampel-Logik für Auftragsbestätigungen und Messeberichte gemäß Lastenheft (4.1 und 4.2). Weitere Funktionen wie Lieferungsverfolgung sind architektonisch geplant, aber noch nicht implementiert.

## Vollständiger Inhalt
Zwischenstand Prototyp
Wed, 03/11 11:02AM · 23mins
Transcript
Sebastian Spuhler 00:00
Der redet auch nichts. Der ist nur damit wir nachher sicher sein können, dass man nichts vergessen haben oder wie ihr das
ganze noch mal Revue passieren können und uns sicher sein können, dass man alle Anforderungen die heute noch mal dazu
kommen, wenn wir euch das Dashboard zeigen und alles mögliche das da alle Stimmen und das war nichts verbessern
vergessen so okay, also ich hätte gesagt, ich kann ja aber mal kurz erklären, was Du bisher gemacht haben und dann würde
ich meinen Kollege auch noch gleich das bisherige Dashboard den Entwurf zeigen, den wir bisher haben. Ja und dann
erklären wir euch die Grundstruktur, was Du bisher gemacht haben und was für in den nächsten Wochen noch vorhaben,
okay?
Sebastian Spuhler 00:45
Also, wir werden ja gesagt wird ein Prototyp ist der Scope Auftragsbestätigung, also alles rund um die Auftragsbestätigung.
Diese Funktion haben wir auch implementiert tatsächlich. Also das ist im Lastenheft, das ist 4.1. Und 4.2. Diese beiden
Aspekte das waren Auftragsbestätigung und Messeberichte dazu haben wir die Funktion zu Analyse zur Vollständigkeit und
so haben wir im Dashboard schon implementiert und haben für Auftragsbestätigung und Messbereiche halt auch schon die
Statistiken eingerichtet Armin, vielleicht kannst du kurz Bildschirm übertragen machen, dann kannst du den Benjamin kurz
zeigen, wie das ganze aussieht und für die weiteren Prozesse haben wir schon.
Sebastian Spuhler 01:30
In der Architektur so ein Platz, also Lieferungen verfolgen und so weiter, wo das ganze stehen soll. Ja, aber haben dazu noch
nichts implementiert und getestet genau hier sind okay gut ja, davor bei euch dazu überfallen. Können wir euch ja nach und
nach erklären, wie das Ganze aufgebaut ist.
Amin 01:54
Also, wir haben hier oben haben wir Auftragsbestätigungen und links da unten drunter sind Messbericht das war vielleicht
erklärst du noch ganz kurz ja, wie diese wie dieses Dashboard aufgebaut ist mit der Ampel Logik und was wir uns sogar
gedacht haben und dann kann der Benjamin noch sagen, was er davon hält. Okay? Also, wir haben erstmal jetzt hier sehen
wir jetzt schon die verschiedenen Spalten, also Seiten auf das bisschen Messe, Berichte Lieferanten Lieferung Unklarheiten
Aktivität und Steuerung, wir hatten das jetzt hier schon ergänzt, aber noch nicht alles hundertprozentig funktioniert, aber
das Auftragsbestätigung funktioniert erstmal eine Gesamtübersicht der eingegangen und auf natürlich Bestätigung, wenn
eine also eine war in Ordnung drei sind installiert und einmal ein Hinweis, aber halt wie die Ampel oder halt, wenn das
innerhalb des Toleranzbereich ist ist dann wird es zu gelb, dann ist auch hier so bereits implementiert.
Amin 02:54
Milliarden wir haben uns Auftragsbestätigung generieren lassen, also selber erstellt Investor so Mock Daten hatten wir
einfach verwendet, um das zu testen genau und dann sieht man jetzt hier erstmal so ein Ampel Vert
