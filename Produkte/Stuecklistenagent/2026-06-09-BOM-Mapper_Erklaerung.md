---
tags:
  - BOM-Mapper
  - Stücklisten
  - Werkzeugbau
  - KI-Automatisierung
  - Produktdokumentation
quelle: BOM-Mapper_Erklaerung.pdf
datum: 2026-06-09
kategorie: Produkt
---

# BOM-Mapper_Erklaerung

Technische Erklärungsdokumentation zum BOM-Mapper, einem KI-gestützten System für automatisches Stücklisten-Mapping im Werkzeugbau. Das Dokument beschreibt den Prozess, die Pain Points bei der manuellen Übertragung von Kundenstücklisten sowie die Funktionsweise des Systems inkl. Ampel-System zur Zuverlässigkeitsbewertung. Es richtet sich an Personen ohne Branchenkenntnisse und deckt Onboarding, Einsatzgrenzen und Voraussetzungen ab.

## Vollständiger Inhalt
BOM-Mapper — Stücklisten-Mapping für den Werkzeugbau
Seite 1
BOM-Mapper
KI-gestütztes Stücklisten-Mapping für den Werkzeugbau
Von Null erklärt: Der Konstruktionsprozess, seine Probleme, wie das System hilft,
wie man es benutzt, wann es sinnvoll ist und was man für einen neuen Kunden
braucht.
Dieses Dokument richtet sich an Personen ohne Vorwissen über Werkzeugbau oder Druckguss — z. B. Entwickler,
Projektleiter oder neue Teammitglieder. Es setzt keine Branchenkenntnis voraus und erklärt jeden Fachbegriff.
 BOM-Mapper — Stücklisten-Mapping für den Werkzeugbau
Seite 2
Inhalt
1. Worum geht es? (Die Kurzfassung)
2. Was macht ein Werkzeugbauer? — Die Branche von Null
3. Was ist eine Stückliste (BOM)?
4. Der heutige Prozess: Wie ein Konstrukteur arbeitet
5. Die Probleme und Pain Points
6. Was sind Stammdaten? (Der Wahrheitsanker)
7. Wie unser System das löst — die 5 Schichten
8. Das Ampel-System: Grün / Gelb / Rot
9. Wie man das System benutzt — Schritt für Schritt
10. Wann ist das System sinnvoll — und wo sind die Grenzen?
11. Voraussetzungen für den Einsatz
12. Neuer Kunde: Was man alles braucht (Onboarding)
13. Zusammenfassung
 BOM-Mapper — Stücklisten-Mapping für den Werkzeugbau
Seite 3
1. Worum geht es? (Die Kurzfassung)
Ein Werkzeugbauer bekommt von seinen Kunden Stücklisten — also Bauteil-Listen — in den
unterschiedlichsten Formaten, Sprachen und Strukturen. Jeder Kunde macht es anders. Damit der
Werkzeugbauer arbeiten kann, muss er jede dieser Listen in seine eigene, einheitliche Vorlage
übertragen. Das passiert heute von Hand und dauert im Schnitt rund 5 Stunden pro Stückliste —
kurze Listen 1–2 Stunden, komplexe Werkzeuge auch 2–3 Tage.
Unser System automatisiert diese Übertragung mit Künstlicher Intelligenz. Das Entscheidende dabei
ist nicht „die KI macht alles”, sondern: Das System sagt für jeden Wert ehrlich, wie sicher es ist
— über ein Ampel-System (Grün/Gelb/Rot). So weiß der Mitarbeiter genau, worauf er sich verlassen
kann und was er prüfen muss. Genau daran sind bisherige Anbieter gescheitert: Sie lieferten
hübsche, aber unzuverlässige Ergebnisse.
Der Kerngedanke in einem Satz
Nicht den Menschen zu 100 % ersetzen, sondern seine stumpfe Arbeit drastisch reduzieren
— und dabei absolut ehrlich sein, welchen Ergebnissen man trauen kann.
2. Was macht ein Werkzeugbauer? — Die Branche von
Null
Stell dir einen Autohersteller vor, der ein Aluminium-Getriebegehäuse in Millionenstückzahl
produzieren will. Dafür braucht er eine Gießform — ein riesiges, tonnenschweres Stahlwerkzeug, in
das flüssiges Aluminium unter hohem Druck gepresst wird (das nennt man Druckguss).
Der Werkzeugbauer baut genau diese Form — nicht das fertige Aluminiumteil, sondern das
Werkzeug, mit dem der Kunde das Teil später selbst produziert. Eine solche Form ist kein einzelnes
Stück, sondern eine Baugruppe aus hunderten Einzelteilen.
Ein paar Bauteil-Begriffe (nur zum Einordnen)

Formplatte: große Stahlplatte, Grundgerüst der Form.

Schieber: bewegliches Teil, das seitlich
