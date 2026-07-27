#!/usr/bin/env python3
"""Schritt 8: ordnet jede gewertete Ausgabe 2025 einem Feld der Anlage EUER zu.

Grundlage sind exakt die Buchungen, die auch in ergebnis_2025_monatlich_netto.xlsx
zur Wertung zaehlen (step5_auswertung.zaehlt_zur_wertung), mit derselben Netto-Logik
wie step7: Beleg vorhanden -> Netto vom Beleg, sonst geschaetzt als brutto / 1,19.
Die Gesamtsumme muss mit dem Blatt 13_Jahresgesamt uebereinstimmen.
"""
import json, re, collections, sys

BASE = "/Users/sesp01-user/vault/Prozessia-Brain/Finanzen/Belegauswertung_2025"
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

# Tatsaechliche Finanzamt-Cashflows 2025 (aus Finom-Kontoauszug-Analyse 2026-07-26, siehe
# project-euer-2025-finanzamt-zahlungen-Memory). Werden separat gefuehrt, weil Finanzamt-Buchungen
# in zaehlt_zur_wertung() bewusst ausgeschlossen sind (kein normaler Umsatz/keine normale Ausgabe),
# aber auf der Anlage EUER als eigene Zeilen (17/18 Einnahmen, 58 Ausgaben) noetig sind.
FA_ERSTATTET_2025 = 25.59 + 93.27 + 155.10   # Zeile 18: vom Finanzamt erstattete Umsatzsteuer
FA_GEZAHLT_2025 = 0.0                          # Zeile 58: an das Finanzamt gezahlte Umsatzsteuer

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
A("# EÜR 2025 – Betriebsausgaben nach Feldern der Anlage EÜR\n")
A("> Erzeugt von `scripts/step8_euer_zuordnung.py`. Stand nach der Belegprüfung vom 2026-07-26.")
A("> Grundlage: dieselben Buchungen wie `ergebnis_2025_monatlich_netto.xlsx` (Blatt `13_Jahresgesamt`).")
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
A(f"| An das Finanzamt gezahlte Umsatzsteuer | {eur(FA_GEZAHLT_2025)} |")
A(f"\n{G['n']} gewertete Buchungen.\n")

# --- Betriebseinnahmen (Umsatzseite) -------------------------------------------
A("\n## Betriebseinnahmen\n")
A("| Datum | Partner | Netto | Vereinnahmte USt | Beleg |")
A("|---|---|---:|---:|---|")
E = {'nt': 0.0, 'ust': 0.0}
for t in sorted(gewertet_ein, key=lambda x: x['zahlungsdatum']):
    b = bel.get(t['beleg_ids'][0]) if t.get('beleg_ids') else None
    n = (b.get('betrag_netto') if b else None) or round(t['betrag_brutto'] / (1 + USTSATZ), 2)
    v = (b.get('ust_betrag') if b else None) or 0.0
    E['nt'] += n; E['ust'] += v
    hinweis = b['quellref'].split('/')[-1] if b else f"**fehlt** – Netto geschätzt aus {eur(t['betrag_brutto'])}"
    A(f"| {t['zahlungsdatum']} | {t['gegenpartei'][:34]} | {eur(n)} | {eur(v)} | {hinweis} |")
A(f"| | **Summe** | **{eur(E['nt'])}** | **{eur(E['ust'])}** | {len(gewertet_ein)} Buchungen |")

# --- Gesamtrechnung: Netto-Gewinn plus NUR die tatsaechlichen Finanzamt-Transaktionen 2025 --
A("\n## Gesamtrechnung EÜR 2025\n")
A("> Nutzerentscheidung 2026-07-27: Vereinnahmte USt und Vorsteuer werden NICHT separat aufaddiert")
A("> (das waere Doppelzaehlung). Zum Netto-Gewinn zaehlt nur dazu, was tatsaechlich 2025 mit dem")
A("> Finanzamt transaktioniert wurde (§ 11 EStG Zufluss-/Abflussprinzip).\n")
netto_gewinn = E['nt'] - G['nt']
A(f"| | Betrag |")
A("|---|---:|")
A(f"| Umsatz netto | {eur(E['nt'])} |")
A(f"| Ausgaben netto | {eur(G['nt'])} |")
A(f"| Netto-Gewinn (Umsatz − Ausgaben) | {eur(netto_gewinn)} |")
A(f"| + Vom Finanzamt erstattete Umsatzsteuer 2025 | {eur(FA_ERSTATTET_2025)} |")
A(f"| − An das Finanzamt gezahlte Umsatzsteuer 2025 | {eur(FA_GEZAHLT_2025)} |")
finaler_gewinn = netto_gewinn + FA_ERSTATTET_2025 - FA_GEZAHLT_2025
A(f"| **Gewinn 2025** | **{eur(finaler_gewinn)}** |")

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
    ws = openpyxl.load_workbook(f"{BASE}/out/ergebnis_2025_monatlich_netto.xlsx",
                                data_only=True)['13_Jahresgesamt']
    excel = next(r[1] for r in ws.iter_rows(values_only=True)
                 if r[0] and str(r[0]).startswith('GESAMTAUSGABEN'))
    print(f"Summe step8: {G['nt']:.2f} | Excel 13_Jahresgesamt: {excel:.2f} | "
          f"Abweichung: {round(G['nt'] - excel, 2):.2f}")
except Exception as e:
    print("Gegenprobe uebersprungen:", e)
print("Geschrieben:", out)
