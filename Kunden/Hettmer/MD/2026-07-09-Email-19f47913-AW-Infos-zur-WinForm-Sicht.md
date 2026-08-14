---
type: email-korrespondenz
kunde: Hettmer
von: "Hettmer, Jochen" <jochen@hettmer-edv.de>
betreff: AW: Infos zur WinForm-Sicht
datum: 2026-07-09
datum_email: Thu, 9 Jul 2026 15:48:39 +0000
---

# AW: Infos zur WinForm-Sicht

**Von:** "Hettmer, Jochen" <jochen@hettmer-edv.de>
**Datum:** Thu, 9 Jul 2026 15:48:39 +0000

## Zusammenfassung
Hallo Sebastian, ja, da wurde bei der neuen Instanz euer Login nicht angelegt … jetzt müsste es klappen … Weiterhin habe ich dir auf die komplette Tabelle „Bestelldatei“ noch Lesezugriff gegeben … falls du das benötigst, bitte kurz Bescheid geben, welche Informationen du da gebrauchen kannst ! Viele Grüße Jochen Von: Sebastian Spuhler Gesendet: Donnerstag, 9. Juli 2026 16:54 An: Hettmer, Jochen ; Jonas Rösch Cc: Benjamin Schmohl Betreff: Re: Infos zur WinForm-Sicht Hallo Jochen, Hallo Jonas, wir haben den Zugang jetzt gegen beide Instanzen getestet: SQL2022EX01: Login "Prozessia" funktioniert,…

## Volltext
Hallo Sebastian, ja, da wurde bei der neuen Instanz euer Login nicht angelegt … jetzt müsste es klappen … Weiterhin habe ich dir auf die komplette Tabelle „Bestelldatei“ noch Lesezugriff gegeben … falls du das benötigst, bitte kurz Bescheid geben, welche Informationen du da gebrauchen kannst ! Viele Grüße Jochen Von: Sebastian Spuhler Gesendet: Donnerstag, 9. Juli 2026 16:54 An: Hettmer, Jochen ; Jonas Rösch Cc: Benjamin Schmohl Betreff: Re: Infos zur WinForm-Sicht Hallo Jochen, Hallo Jonas, wir haben den Zugang jetzt gegen beide Instanzen getestet: SQL2022EX01: Login "Prozessia" funktioniert, aber die Datenbank Winform2000_TEST.72SQL existiert dort nicht (Fehler 4060). SQL2022EX02: Die Datenbank Winform2000_TEST.72SQL liegt dort (laut Screenshot bestätigt), aber der Login "Prozessia" wird abgelehnt (Fehler 18456 – Login failed). Der Login scheint also nur auf EX01 angelegt zu sein, die Test-Datenbank aber auf EX02 zu liegen. Könntet ihr den Login Prozessia (gerne mit demselben Passwort) zusätzlich auf SQL2022EX02 anlegen bzw. dort Zugriff auf Winform2000_TEST.72SQL / VIEW_fuer_Prozessia freischalten? Sobald das steht, testen wir sofort weiter. Danke euch! Viele Grüße Sebastian Spuhler Prozessia Am Do., 9. Juli 2026 um 16:02 Uhr schrieb Hettmer, Jochen >: Hallo Sebastian, Jonas hat dir ja in der Zwischenzeit den VPN-Zugang bereitgestellt … Die Test-Datenbank wurde von Jonas hier bereitgestellt: [cid:image001.png@01DD0FCB.2B593FF0] Login-Name: Prozessia Passwort: Prozessia#66123#-A11! Sichtname: Bestelldatei (VIEW_fuer_Prozessia) Feldname Beschreibung BestellNr enthält die fortlaufende „Bestell-Positionsnr.“ Liefertermin Liefertermin (Vorgabe an Lieferanten) Liefertermin_bestätigt Liefertermin bestätigt Liefertermin_erwartet Liefertermin erwartet Terminüberwachung_Bemerkung Freitext – manueller erfasster Kommentar in Bezug auf die Terminüberwachung Idee: beim letzten Feld „Terminüberwachung_Bemerkung“ handelt es sich um ein Textfeld nvarchar(300); dieses könnte doch bei jeder Terminaktualisierung von euch mit einer kurzer Info ergänzt werden … Wenn’s Fragen gibt sehr gerne melden … Viele Grüße Jochen ================================= Kompetenz in Sachen EDV durch mehr als 25 Jahre Berufserfahrung Sie als Anwender stehen bei uns im Vordergrund! ================================= J. Hettmer EDV-Beratung Beratung, Schulung, Software-Entwicklung, Vertrieb Jochen Hettmer Dipl.-Betriebswirt (BA) Fachr. Wirtschaftsinformatik Heinrich-Lang-Str. 25 89150 Laichingen Tel. 07333 / 9222-99 www.hettmer-edv.de