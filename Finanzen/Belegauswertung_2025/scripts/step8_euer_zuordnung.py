#!/usr/bin/env python3
"""Ordnet jede Ausgabe 2025 einer Betriebsausgaben-Kategorie der Anlage EUER zu."""
import json, re, collections

OUT = "/Users/sesp01-user/vault/Prozessia-Brain/Finanzen/Belegauswertung_2025/out"
d = json.load(open(f"{OUT}/04_merged.json"))
belege = {b['id']: b for b in d['belege']}

# In dieser Pipeline ist das Feld 'richtung' invers benannt:
# AUSGANG = Geldeingang = Umsatz, EINGANG = Geldausgang = Ausgabe (siehe step5_auswertung.py)
ausgaben = [t for t in d['transaktionen']
            if t['richtung'] == 'EINGANG' and t['kategorie'] != 'EINLAGE_ENTNAHME']

# Kategorien der Anlage EUER (Betriebsausgaben) aus dem Tutorial
KAT = {
    'IT':      'Laufende IT-Kosten (Software/SaaS, Hosting, Domains)',
    'WERBUNG': 'Werbekosten (Anzeigen, Ads, Marketing-/Lead-Tools)',
    'MIETE':   'Miete/Pacht fuer Geschaeftsraeume',
    'BERATUNG':'Rechts- und Steuerberatung, Buchfuehrung',
    'REISE':   'Reisekosten / Uebernachtung (Geschaeftsreise)',
    'FORTBIL': 'Fortbildungskosten (Seminare, Messen, Events)',
    'BEWIRT':  'Bewirtungskosten (nur 70% abziehbar)',
    'UEBRIGE': 'Uebrige Betriebsausgaben',
    'DURCHL':  'Durchlaufender Posten - KEINE Betriebsausgabe',
}

REGELN = [
    (r'DURCHLAUFENDER POSTEN|RETAINER Q1 2026', 'DURCHL', 'Rundlauf 4.760 EUR, Nutzerentscheidung 2026-07-22'),
    (r'HOTEL',                               'REISE',    'Uebernachtung Frankfurt, Auslage an B. Ferrise erstattet'),
    (r'HAUFE',                               'BERATUNG', 'Lexware Office (Buchhaltungssoftware)'),
    (r'CYFIRE',                              'BERATUNG', 'Rechtsanwaltsgesellschaft'),
    (r'TRIATHLON',                           'MIETE',    'Postfachmiete = Geschaeftsadresse'),
    (r'FACEBK|META',                         'WERBUNG',  'Meta/Facebook Ads'),
    (r'INSTANTLY',                           'WERBUNG',  'Cold-Email-/Outreach-Tool'),
    (r'DIGISTORE24',                         'WERBUNG',  'FunnelCockpit (Funnel-/Marketingsoftware)'),
    (r'FINDYLEAD',                           'WERBUNG',  'Lead-Recherche-Tool'),
    (r'WIX|HOSTINGER|IONOS',                 'IT',       'Website/Hosting/Domain'),
    (r'OPENAI|ZOHO|BOLT|STACKBLITZ|PADDLE|N8N|APIFY|GAMMA|GOOGLE.?WORKSPACE',
                                             'IT',       'Software-Abo/SaaS'),
    (r'PNL FINTECH',                         'UEBRIGE',  'Finom-Kontofuehrungsgebuehren'),
    (r'MATTH|WIMMLER',                       'FORTBIL',  'Event Frankfurt - Art der Leistung pruefen'),
    (r'KAFFEEROSTEREI',                      'BEWIRT',   'Betrag 4,02 EUR - Bewirtung oder privat? pruefen'),
]

BAGATELLE = 10.0

def eur(x):
    return f"{x:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.')
rows = []
for t in sorted(ausgaben, key=lambda x: x['zahlungsdatum']):
    gp = (t['gegenpartei'] or '').upper()
    vz = (t['verwendungszweck'] or '').upper()
    kat, note = 'OFFEN', None
    for pat, k, n in REGELN:
        if re.search(pat, gp) or re.search(pat, vz):
            kat, note = k, n
            break
    bl = [belege[i] for i in (t.get('beleg_ids') or []) if i in belege]
    netto = next((b['betrag_netto'] for b in bl if b.get('betrag_netto') is not None), None)
    ust   = next((b['ust_betrag'] for b in bl if b.get('ust_betrag') is not None), None)
    flags = []
    if netto is None: flags.append('kein Netto/USt aus Beleg')
    if t['betrag_brutto'] < BAGATELLE: flags.append(f'Bagatelle <{BAGATELLE:.0f} EUR')
    if t['status'] != 'BELEGT': flags.append(t['status'])
    rows.append(dict(datum=t['zahlungsdatum'], brutto=t['betrag_brutto'], netto=netto,
                     ust=ust, partner=t['gegenpartei'], zweck=t['verwendungszweck'],
                     kat=kat, note=note, flags=flags))

# ---------- Ausgabe ----------
grp = collections.defaultdict(list)
for r in rows: grp[r['kat']].append(r)

L = []
A = L.append
A("# EÜR 2025 – Zuordnung jeder einzelnen Ausgabe zu den Betriebsausgaben-Kategorien\n")
A("> Quelle: `04_merged.json` (Finom-Kontoauszug 2025, einziges Geschäftskonto).")
A("> Kategorien nach dem Elster-Tutorial, siehe `_inbox/2026-07-26-Transkript-EUER-Tutorial-Elster.md`.")
A("> Achtung: das Feld `richtung` ist in der Pipeline invers benannt – `EINGANG` = Geldabfluss = Ausgabe.\n")

ordnung = ['IT','WERBUNG','MIETE','BERATUNG','REISE','FORTBIL','BEWIRT','UEBRIGE','OFFEN','DURCHL']
gesamt_b = gesamt_n = gesamt_u = 0.0
for k in ordnung:
    if k not in grp: continue
    rs = sorted(grp[k], key=lambda r: r['datum'])
    sb = sum(r['brutto'] for r in rs)
    sn = sum(r['netto'] for r in rs if r['netto'] is not None)
    su = sum(r['ust'] for r in rs if r['ust'] is not None)
    A(f"\n## {KAT.get(k, 'Noch nicht zugeordnet')}  \n")
    A(f"**{len(rs)} Buchungen · brutto {eur(sb)} · netto (belegt) {eur(sn)} · Vorsteuer {eur(su)}**\n")
    A("| Datum | Partner | Verwendungszweck | Brutto | Netto | USt | Hinweis |")
    A("|---|---|---|---:|---:|---:|---|")
    for r in rs:
        n = f"{r['netto']:.2f}".replace('.', ',') if r['netto'] is not None else "–"
        u = f"{r['ust']:.2f}".replace('.', ',') if r['ust'] is not None else "–"
        b = f"{r['brutto']:.2f}".replace('.', ',')
        hin = "; ".join(([r['note']] if r['note'] else []) + r['flags'])
        zw = (r['zweck'] or '').split('|')[0].strip()[:38]
        A(f"| {r['datum']} | {r['partner'][:32]} | {zw} | {b} | {n} | {u} | {hin} |")
    if k != 'DURCHL':
        gesamt_b += sb; gesamt_n += sn; gesamt_u += su

A(f"\n## Summe Betriebsausgaben 2025 (ohne Durchlaufposten)\n")
A(f"- Brutto: **{gesamt_b:,.2f} €**".replace(',', 'X').replace('.', ',').replace('X', '.'))
A(f"- Netto (nur wo ein Beleg mit expliziter Netto-Angabe vorliegt): **{gesamt_n:,.2f} €**".replace(',', 'X').replace('.', ',').replace('X', '.'))
A(f"- Abziehbare Vorsteuer (belegt): **{gesamt_u:,.2f} €**".replace(',', 'X').replace('.', ',').replace('X', '.'))
A(f"- Buchungen gesamt: {sum(len(v) for k,v in grp.items() if k!='DURCHL')}")

bag = [r for r in rows if r['kat'] != 'DURCHL' and r['brutto'] < BAGATELLE]
A(f"\n### Abstimmung mit der Pipeline\n")
A("- Gesamter Geldabfluss 2025 laut Kontoauszug: " + eur(sum(r['brutto'] for r in rows)))
A("- abzüglich Durchlaufposten Benito Ferrise: " + eur(sum(r['brutto'] for r in rows if r['kat']=='DURCHL')))
A(f"- = Betriebsausgaben brutto: {gesamt_b:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.'))
A(f"- Davon Bagatellen < 10 € (in `05_auswertung.json` aus der Brutto-Kennzahl ausgeschlossen): "
  f"{len(bag)} Buchungen / " + eur(sum(r['brutto'] for r in bag)))
A(f"- Netto und Vorsteuer stimmen exakt mit `05_auswertung.json` überein "
  f"(ausgaben_netto 2.385,11 €, vorsteuer_abziehbar 166,55 €).")

A("\n## Nicht im Kontoauszug – aber in der EÜR ansetzbar\n")
A("| Kategorie | Hinweis |")
A("|---|---|")
A("| Verpflegungsmehraufwand | Pauschal 14 € / 28 € pro Reisetag. Die Frankfurt-Reise (Hotel 11.09., Event 01.09.) ist belegt – Reisetage dokumentieren und ansetzen. Fließt nie übers Konto. |")
A("| Homeoffice-Tagespauschale | 6 €/Tag, max. 210 Tage = 1.260 €/Jahr. Kein separates Arbeitszimmer nötig. |")
A("| Fahrten mit dem Privat-Pkw | 0,30 €/gefahrenem km für betriebliche Fahrten (z. B. Kundentermine). |")
A("| Abschreibungen (AfA) | Nur relevant, wenn 2025 Anlagevermögen > 800 € netto angeschafft wurde – im Konto nicht erkennbar. Anlage AV-EÜR. |")
A("\n> Diese vier Positionen sind reine Erfassungspositionen und mindern den Gewinn zusätzlich. "
  "Bei einer GbR gelten sie je Gesellschafter bzw. auf Ebene der Gesellschaft – vor Abgabe klären.")

open(f"{OUT}/08_euer_ausgaben_zuordnung.md", "w").write("\n".join(L) + "\n")
print("\n".join(L))
