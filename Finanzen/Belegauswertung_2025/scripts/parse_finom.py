#!/usr/bin/env python3
"""Parst den Finom-Kontoauszug (PDF Text) in strukturierte Transaktionen (alle Jahre)."""
import re
import json
import hashlib
import sys

RAW_PATH = "/Users/sesp01-user/vault/Prozessia-Brain/Finanzen/Belegauswertung_2025/out/_finom_raw.txt"
OUT_ALL = "/Users/sesp01-user/vault/Prozessia-Brain/Finanzen/Belegauswertung_2025/out/_finom_alle_jahre.json"

DATE_RE = re.compile(r'^\d{2}\.\d{2}\.\d{4}$')
FX_RATE_RE = re.compile(r'^1 EUR = [\d.,]+ \w+$')
MONEY_RE = re.compile(r'^-?\s*[\d.,]+\s*[€$£]$')
NOISE_LINES = {
    "Vervollständigt", "Beschreibung", "Einnahmen /", "Ausgaben", "Guthaben",
    "Mit Finom.co erstellt",
}
HEADER_BLOCK_MARKERS = {
    "KONTOAUSZUG", "Ausstellungsdatum:", "Von:", "Bis:",
    "Eröffnungssaldo:", "Abschlusssaldo:",
}

def parse_money(s):
    s = s.strip().rstrip('€$£').strip()
    neg = s.startswith('-')
    s = s.lstrip('-').strip()
    s = s.replace('.', '').replace(',', '.')
    val = float(s)
    return -val if neg else val

def parse_date(s):
    d, m, y = s.split('.')
    return f"{y}-{m}-{d}"

def main():
    with open(RAW_PATH, encoding='utf-8') as f:
        lines = [l.rstrip('\n') for l in f]

    # Zeilen bereinigen: Page-Marker, Footer-Seitenzahl, Header/Footer-Rauschen, Erststeiten-Metablock
    cleaned = []
    skip_meta_block = False
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('--- PAGE'):
            i += 1
            continue
        if line == '':
            i += 1
            continue
        if line in NOISE_LINES:
            i += 1
            continue
        # Erste Seite: Metadaten-Block bis "BIC: FNOMDEB2" ueberspringen
        if line.startswith('Sebastian Spuhler, Mohamed Douioui Gbr'):
            skip_meta_block = True
            i += 1
            continue
        if skip_meta_block:
            if line.startswith('BIC:'):
                skip_meta_block = False
            i += 1
            continue
        # Footer-Seitenzahl (nackte Zahl direkt vor "Mit Finom.co erstellt")
        if re.match(r'^\d+$', line) and i + 1 < len(lines) and lines[i+1].strip() == 'Mit Finom.co erstellt':
            i += 1
            continue
        cleaned.append(line)
        i += 1

    # In Transaktionsbloecke gruppieren (Start = Datumszeile)
    blocks = []
    current = None
    for line in cleaned:
        if DATE_RE.match(line):
            if current is not None:
                blocks.append(current)
            current = {'date': line, 'lines': []}
        else:
            if current is not None:
                current['lines'].append(line)
    if current is not None:
        blocks.append(current)

    transactions = []
    for b in blocks:
        desc_lines = []
        money_lines = []
        fx_rate = None
        for l in b['lines']:
            if FX_RATE_RE.match(l):
                fx_rate = l
            elif MONEY_RE.match(l):
                money_lines.append(l)
            else:
                desc_lines.append(l)

        if len(money_lines) < 2:
            # Unerwartetes Format -> als Parse-Fehler markieren, nichts erfinden
            transactions.append({
                'zahlungsdatum': parse_date(b['date']),
                'parse_error': True,
                'pruefgrund': f"Unerwartetes Zeilenformat, {len(money_lines)} Geldzeilen gefunden, Rohzeilen: {b['lines']}",
                'raw_lines': b['lines'],
            })
            continue

        balance_line = money_lines[-1]
        amount_lines = money_lines[:-1]
        eur_amount_line = next((m for m in amount_lines if m.strip().endswith('€')), amount_lines[0])
        other_amount_lines = [m for m in amount_lines if m != eur_amount_line]

        eur_amount = parse_money(eur_amount_line)
        gegenpartei = desc_lines[0] if desc_lines else None
        verwendungszweck = ' | '.join(desc_lines[1:]) if len(desc_lines) > 1 else (desc_lines[0] if desc_lines else '')

        richtung = "AUSGANG" if eur_amount > 0 else "EINGANG"  # Geldeingang -> AUSGANG (Umsatz), lt. Vorgabe

        raw_id_src = f"{b['date']}|{gegenpartei}|{verwendungszweck}|{eur_amount_line}|{balance_line}"
        tx_id = "FINOM-" + hashlib.sha1(raw_id_src.encode('utf-8')).hexdigest()[:16]

        tx = {
            'tx_id': tx_id,
            'zahlungsdatum': parse_date(b['date']),
            'betrag_brutto': round(abs(eur_amount), 2),
            'richtung': richtung,
            'gegenpartei': gegenpartei,
            'verwendungszweck': verwendungszweck,
            'guthaben_nach_buchung': parse_money(balance_line),
            'fremdwaehrung': None,
            'fx_hinweis': None,
        }
        if other_amount_lines or fx_rate:
            tx['fremdwaehrung'] = True
            tx['fx_hinweis'] = {
                'fx_rate_line': fx_rate,
                'fx_amount_lines': other_amount_lines,
            }
        transactions.append(tx)

    with open(OUT_ALL, 'w', encoding='utf-8') as f:
        json.dump(transactions, f, ensure_ascii=False, indent=2)

    n_err = sum(1 for t in transactions if t.get('parse_error'))
    n_ok = len(transactions) - n_err
    print(f"Transaktionen gesamt geparst: {len(transactions)} (ok={n_ok}, parse_error={n_err})")
    dates = sorted(t['zahlungsdatum'] for t in transactions if not t.get('parse_error'))
    if dates:
        print(f"Zeitraum: {dates[0]} bis {dates[-1]}")

if __name__ == '__main__':
    main()
