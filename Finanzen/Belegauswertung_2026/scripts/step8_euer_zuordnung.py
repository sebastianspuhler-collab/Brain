#!/usr/bin/env python3
"""Schritt 8: ordnet jede gewertete Ausgabe 2026 einem Feld der Anlage EUER zu.

Grundlage sind exakt die Buchungen, die auch in ergebnis_2026_monatlich_netto.xlsx
zur Wertung zaehlen (step5_auswertung.zaehlt_zur_wertung), mit derselben Netto-Logik
wie step7: Beleg vorhanden -> Netto vom Beleg, sonst geschaetzt als brutto / 1,19.
Die Gesamtsumme muss mit dem Blatt 13_Jahresgesamt uebereinstimmen.

WICHTIGE LEHRE AUS 2025 (siehe NOTIZEN.md): Bei jeder Rechnung mit MwSt/USt-Ausweis
vor dem Zaehlen als Vorsteuer pruefen, ob die USt-IdNr. des Ausstellers deutsch (DE...)
ist. Auslaendische USt (z.B. NL, CZ) ist keine abzugsfaehige deutsche Vorsteuer - dann
gehoert der volle Bruttobetrag als Netto-Ausgabe in korrekturen_2026.json, nicht die
automatisch aus dem Beleg gelesene "ust_betrag"-Zahl.
"""
import json, re, collections, sys

BASE = "/Users/sesp01-user/vault/Prozessia-Brain/Finanzen/Belegauswertung_2026"
sys.path.insert(0, f"{BASE}/scripts")
from step5_auswertung import zaehlt_zur_wertung

USTSATZ = 0.19

# Feldbezeichnungen der Anlage EUER (Betriebsausgaben). Reihenfolge = Prioritaet.
REGELN = [
    (r'FACEBK|META|INSTANTLY|DIGISTORE24|FINDYLEAD|LINKEDIN', 'Werbekosten'),
    (r'HAUFE|CYFIRE|PNL FINTECH',                              'Rechts- und Steuerberatung, Buchführung'),
    (r'TRIATHLON',                                             'Miete/Pacht für Geschäftsräume'),
    (r'WIX|HOSTINGER|IONOS|OPENAI|ZOHO|BOLT|STACKBLITZ|PADDLE|N8N|APIFY|GAMMA|GOOGLE.?WORKSPACE',
                                                               'Laufende IT-Kosten'),
    (r'MATTH|WIMMLER',                                         'Fortbildungskosten'),
    (r'FERRISE|HOTEL|MELIA',                                   'Übernachtungs- und Reisekosten'),
]

def eur(x):
    return f"{x:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.')

# Tatsaechliche Finanzamt-Cashflows 2026 (aus Finom-Kontoauszug, analog zur 2025er-Analyse,
# siehe project-euer-2025-finanzamt-zahlungen-Memory). Werden separat gefuehrt, weil Finanzamt-
# Buchungen in zaehlt_zur_wertung() bewusst ausgeschlossen sind (kein normaler Umsatz/keine
# normale Ausgabe), aber auf der Anlage EUER als eigene Zeilen (17/18 Einnahmen, 58 Ausgaben)
# noetig sind. TODO: vor dem ersten echten Lauf aus den 2026er-Finanzamt-Buchungen befuellen
# (Suche nach "FINANZAMT" in out/_finom_alle_jahre.json, gefiltert auf 2026) - siehe NOTIZEN.md.
FA_ERSTATTET_2026 = 0.0   # Zeile 18: vom Finanzamt erstattete Umsatzsteuer - NOCH AUSZUFUELLEN
FA_GEZAHLT_2026 = 0.0     # Zeile 58: an das Finanzamt gezahlte Umsatzsteuer - NOCH AUSZUFUELLEN

merged = json.load(open(f"{BASE}/out/04_merged.json", encoding='utf-8'))
bel = {b['id']: b for b in merged['belege']}
alle = [t for t in merged['transaktionen'] if t['richtung'] == 'EINGANG']   # EINGANG = Geldabfluss
gewertet = [t for t in alle if zaehlt_zur_wertung(t, bel)]

alle_ein = [t for t in merged['transaktionen'] if t['richtung'] == 'AUSGANG']   # AUSGANG = Geldeingang
gewertet_ein = [t for t in alle_ein if zaehlt_zur_wertung(t, bel)]

def netto_von(t):
    """(netto, vorsteuer, beleg_vorhanden) - identisch zur Logik in step7."""
    b = bel.get(t['beleg_ids'][0]) if t.get('beleg_ids') else None
    if b:
        return (b.get('betrag_netto') or 0.0, b.get('ust_betrag'), True)
    return (round(t['betrag_brutto'] / (1 + USTSATZ), 2), None, False)

def feld_von(t):
    s = ((t['gegenpartei'] or '') + ' ' + (t['verwendungszweck'] or '')).upper()
    return next((f for p, f in REGELN if re.search(p, s)), 'NICHT ZUGEORDNET')

gruppen = collections.defaultdict(list)
for t in gewertet:
    gruppen[feld_von(t)].append(t)

def summe(feld):
    return sum(netto_von(t)[0] for t in gruppen[feld])

L = []
A = L.append
A("# EÜR 2026 – Betriebsausgaben nach Feldern der Anlage EÜR\n")
A("> Erzeugt von `scripts/step8_euer_zuordnung.py`. Stand: Scaffold angelegt 2026-07-28, noch nicht final durchlaufen.")
A("> Grundlage: dieselben Buchungen wie `ergebnis_2026_monatlich_netto.xlsx` (Blatt `13_Jahresgesamt`).")
A("> Netto: Beleg vorhanden → Netto vom Beleg, sonst geschätzt als brutto / 1,19.")
A("> In der Anlage EÜR werden **Nettobeträge** eingetragen, die Vorsteuer separat.\n")

G = {'nt': 0.0, 'vst': 0.0, 'n': 0}
for feld in sorted(gruppen, key=lambda f: -summe(f)):
    rows = sorted(gruppen[feld], key=lambda t: t['zahlungsdatum'])
    sn = sv = 0.0
    A(f"\n## {feld}\n")
    A("| Datum | Partner | Netto | Vorsteuer | Beleg |")
    A("|---|---|---:|---:|---|")
    for t in rows:
        n, v, hat = netto_von(t)
        sn += n; sv += v or 0.0
        if hat:
            hinweis = bel[t['beleg_ids'][0]]['quellref'].split('/')[-1]
            if t.get('privat_bezahlt'):
                hinweis += " · **privat bezahlt (Einlage)**"
        else:
            hinweis = f"**fehlt** – Netto geschätzt aus {eur(t['betrag_brutto'])}"
        A(f"| {t['zahlungsdatum']} | {t['gegenpartei'][:34]} | {eur(n)} | "
          f"{eur(v) if v is not None else '–'} | {hinweis} |")
    A(f"| | **Summe** | **{eur(sn)}** | **{eur(sv)}** | {len(rows)} Buchungen |")
    G['nt'] += sn; G['vst'] += sv; G['n'] += len(rows)

A("\n## Übertrag in die Anlage EÜR\n")
A("| Feld | Betrag |")
A("|---|---:|")
for feld in sorted(gruppen, key=lambda f: -summe(f)):
    A(f"| {feld} | {eur(summe(feld))} |")
A(f"| **Summe Betriebsausgaben** | **{eur(G['nt'])}** |")
A(f"| Gezahlte Vorsteuerbeträge | {eur(G['vst'])} |")
A(f"| An das Finanzamt gezahlte Umsatzsteuer | {eur(FA_GEZAHLT_2026)} |")
A(f"\n{G['n']} gewertete Buchungen.\n")

# --- Betriebseinnahmen (Umsatzseite) -------------------------------------------
A("\n## Betriebseinnahmen\n")
A("| Datum | Partner | Netto | Beleg |")
A("|---|---|---:|---|")
E = {'nt': 0.0}
for t in sorted(gewertet_ein, key=lambda x: x['zahlungsdatum']):
    b = bel.get(t['beleg_ids'][0]) if t.get('beleg_ids') else None
    n = (b.get('betrag_netto') if b else None) or round(t['betrag_brutto'] / (1 + USTSATZ), 2)
    E['nt'] += n
    hinweis = b['quellref'].split('/')[-1] if b else f"**fehlt** – Netto geschätzt aus {eur(t['betrag_brutto'])}"
    A(f"| {t['zahlungsdatum']} | {t['gegenpartei'][:34]} | {eur(n)} | {hinweis} |")
# TODO 2026: hier die echten Finanzamt-Erstattungszeilen 2026 eintragen, sobald bekannt
# (siehe FA_ERSTATTET_2026 oben und NOTIZEN.md). Solange FA_ERSTATTET_2026 == 0.0 bleibt
# diese Zeile aus, um keine falsche Zahl vorzutaeuschen.
if FA_ERSTATTET_2026:
    A(f"| ? | Finanzamt-Erstattung(en) 2026 (TODO: Einzeldaten eintragen) | {eur(FA_ERSTATTET_2026)} | Finom-Kontoauszug |")
umsatz_gesamt = E['nt'] + FA_ERSTATTET_2026
A(f"| | **Summe (inkl. Finanzamt-Erstattung)** | **{eur(umsatz_gesamt)}** | {len(gewertet_ein)} Buchungen (+ FA-Erstattungen sobald eingetragen) |")

# --- Gesamtrechnung: Betriebseinnahmen (inkl. FA-Erstattung) minus Betriebsausgaben ---------
A("\n## Gesamtrechnung EÜR 2026\n")
A("> Regel wie 2025 (Nutzerentscheidung 2026-07-27): Vereinnahmte USt und Vorsteuer werden NICHT")
A("> separat aufaddiert (das waere Doppelzaehlung). Die tatsaechlich vom Finanzamt erhaltene")
A("> Erstattung zaehlt direkt zu den Betriebseinnahmen (§ 11 EStG Zufluss-/Abflussprinzip).\n")
A(f"| | Betrag |")
A("|---|---:|")
A(f"| Umsatz netto (Kunden) | {eur(E['nt'])} |")
A(f"| Vom Finanzamt erstattete Umsatzsteuer 2026 | {eur(FA_ERSTATTET_2026)} |")
A(f"| **Betriebseinnahmen gesamt** | **{eur(umsatz_gesamt)}** |")
A(f"| Ausgaben netto | {eur(G['nt'])} |")
A(f"| An das Finanzamt gezahlte Umsatzsteuer 2026 | {eur(FA_GEZAHLT_2026)} |")
ausgaben_gesamt = G['nt'] + FA_GEZAHLT_2026
A(f"| **Betriebsausgaben gesamt** | **{eur(ausgaben_gesamt)}** |")
finaler_gewinn = umsatz_gesamt - ausgaben_gesamt
A(f"| **Gewinn 2026** | **{eur(finaler_gewinn)}** |")

priv = [t for t in gewertet if t.get('privat_bezahlt')]
if priv:
    A("## Privat bezahlt – zugleich Einlage\n")
    A("| Datum | Partner | Netto | Vorsteuer | Brutto = Einlage |")
    A("|---|---|---:|---:|---:|")
    for t in sorted(priv, key=lambda x: x['zahlungsdatum']):
        n, v, _ = netto_von(t)
        A(f"| {t['zahlungsdatum']} | {t['gegenpartei'][:34]} | {eur(n)} | {eur(v or 0)} | {eur(t['betrag_brutto'])} |")
    A(f"| | **Summe** | **{eur(sum(netto_von(t)[0] for t in priv))}** | "
      f"**{eur(sum(netto_von(t)[1] or 0 for t in priv))}** | **{eur(sum(t['betrag_brutto'] for t in priv))}** |")
    A("\n> Diese Rechnungen liefen nicht über das Geschäftskonto. Sie sind Betriebsausgabe **und** Einlage.")
    A("> Alle drei sind auf Sebastian Spuhler privat bzw. auf „WebWokr“ ausgestellt, nicht auf die GbR –")
    A("> für den Vorsteuerabzug der Gesellschaft mit dem Steuerberater klären.\n")

A("## Nicht in der Wertung\n")
A("| Grund | Betrag brutto | Buchungen |")
A("|---|---:|---|")
raus = collections.defaultdict(lambda: [0.0, 0])
DURCHL = {"FINOM-ab4c797b9d8a034a", "FINOM-15f016a7977dc19d"}
for t in alle:
    if zaehlt_zur_wertung(t, bel):
        continue
    g = ('Durchlaufposten Benito Ferrise' if t['tx_id'] in DURCHL
         else 'Nicht als geschäftlich eingestuft' if t['kategorie'] != 'GESCHAEFTLICH'
         else 'Finanzamt (steuerneutral, gehört auf die Einnahmenseite)'
              if 'finanzamt' in (t['gegenpartei'] or '').lower()
         else 'Bagatelle < 10 € ohne Beleg')
    raus[g][0] += t['betrag_brutto']; raus[g][1] += 1
for g, (v, c) in sorted(raus.items(), key=lambda x: -x[1][0]):
    A(f"| {g} | {eur(v)} | {c} |")

out = f"{BASE}/out/08_euer_ausgaben_zuordnung.md"
open(out, 'w', encoding='utf-8').write("\n".join(L) + "\n")

try:
    import openpyxl
    ws = openpyxl.load_workbook(f"{BASE}/out/ergebnis_2026_monatlich_netto.xlsx",
                                data_only=True)['13_Jahresgesamt']
    excel = next(r[1] for r in ws.iter_rows(values_only=True)
                 if r[0] and str(r[0]).startswith('GESAMTAUSGABEN'))
    print(f"Summe step8: {G['nt']:.2f} | Excel 13_Jahresgesamt: {excel:.2f} | "
          f"Abweichung: {round(G['nt'] - excel, 2):.2f}")
except Exception as e:
    print("Gegenprobe uebersprungen:", e)
print("Geschrieben:", out)
