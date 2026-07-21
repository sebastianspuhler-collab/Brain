#!/usr/bin/env python3
"""Pro Monat eine eigene Excel-Datei mit allen Transaktionen INKL. Netto-Betrag pro
Zeile (aus dem verknuepften Beleg, falls vorhanden - sonst leer, NICHT geschaetzt)."""
import json, os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

BASE = "/Users/sesp01-user/vault/Prozessia-Brain/Finanzen/Belegauswertung_2025/out"
OUTDIR = f"{BASE}/monatsdateien"
os.makedirs(OUTDIR, exist_ok=True)

merged = json.load(open(f"{BASE}/04_merged.json", encoding='utf-8'))
tx_all = merged['transaktionen']
belege_by_id = {b['id']: b for b in merged['belege']}

RICHTUNG_LABEL = {"AUSGANG": "UMSATZ (Geld rein)", "EINGANG": "AUSGABE (Geld raus)"}
MONATSNAMEN = ["", "01_Januar", "02_Februar", "03_Maerz", "04_April", "05_Mai", "06_Juni",
               "07_Juli", "08_August", "09_September", "10_Oktober", "11_November", "12_Dezember"]

HEADER_FILL = PatternFill(start_color="1F2937", end_color="1F2937", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)

def style_and_fit(ws, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal='center')
    ws.freeze_panes = "A2"
    for c in range(1, ncols + 1):
        col = get_column_letter(c)
        maxlen = 10
        for cell in ws[col]:
            if cell.value is not None:
                maxlen = max(maxlen, min(60, len(str(cell.value)) + 2))
        ws.column_dimensions[col].width = maxlen

headers = ["Zahlungsdatum", "Richtung", "Betrag brutto", "Betrag netto (aus Beleg)",
           "USt-Betrag (aus Beleg)", "Netto-Quelle", "Gegenpartei", "Verwendungszweck",
           "Kategorie", "Beleg-Datei", "Status", "Pruefgrund"]

for m in range(1, 13):
    wb = Workbook()
    ws = wb.active
    ws.title = MONATSNAMEN[m][3:]
    ws.append(headers)

    month_tx = [t for t in tx_all if t['monat'] == m]
    sum_brutto_umsatz = sum_netto_umsatz = 0.0
    sum_brutto_ausgabe = sum_netto_ausgabe = 0.0
    sum_ust_umsatz = sum_ust_ausgabe = 0.0
    n_ohne_netto = 0

    for t in sorted(month_tx, key=lambda x: x['zahlungsdatum']):
        beleg = belege_by_id.get(t['beleg_ids'][0]) if t.get('beleg_ids') else None
        netto = beleg.get('betrag_netto') if beleg else None
        ust = beleg.get('ust_betrag') if beleg else None
        if netto is not None:
            quelle = beleg['quellref'].split('/')[-1]
        elif t.get('beleg_ids'):
            quelle = "Beleg gefunden, aber ohne Netto-/USt-Angabe"
        else:
            quelle = "KEIN BELEG GEFUNDEN"
        if netto is None and t['kategorie'] == 'GESCHAEFTLICH':
            n_ohne_netto += 1

        ws.append([t['zahlungsdatum'], RICHTUNG_LABEL[t['richtung']], t['betrag_brutto'],
                   netto, ust, quelle, t['gegenpartei'], t['verwendungszweck'],
                   t['kategorie'], beleg['quellref'].split('/')[-1] if beleg else None,
                   t['status'], t.get('pruefgrund')])

        if t['kategorie'] == 'GESCHAEFTLICH':
            if t['richtung'] == 'AUSGANG':
                sum_brutto_umsatz += t['betrag_brutto']
                if netto is not None:
                    sum_netto_umsatz += netto
                    sum_ust_umsatz += (ust or 0)
            else:
                sum_brutto_ausgabe += t['betrag_brutto']
                if netto is not None:
                    sum_netto_ausgabe += netto
                    sum_ust_ausgabe += (ust or 0)

    r = ws.max_row + 2
    rows_summary = [
        ("SUMME Umsatz brutto (geschaeftlich):", round(sum_brutto_umsatz, 2)),
        ("SUMME Umsatz netto (nur wo Beleg mit Netto vorhanden):", round(sum_netto_umsatz, 2)),
        ("SUMME USt auf Umsatz (aus Beleg):", round(sum_ust_umsatz, 2)),
        ("SUMME Ausgaben brutto (geschaeftlich):", round(sum_brutto_ausgabe, 2)),
        ("SUMME Ausgaben netto (nur wo Beleg mit Netto vorhanden):", round(sum_netto_ausgabe, 2)),
        ("SUMME Vorsteuer aus Belegen:", round(sum_ust_ausgabe, 2)),
        ("Anzahl geschaeftliche Zahlungen OHNE Netto-Angabe (kein/unvollstaendiger Beleg):", n_ohne_netto),
    ]
    for label, val in rows_summary:
        ws.cell(row=r, column=1, value=label).font = Font(bold=True)
        ws.cell(row=r, column=3, value=val).font = Font(bold=True)
        r += 1

    style_and_fit(ws, len(headers))
    fname = f"{OUTDIR}/{MONATSNAMEN[m]}_2025.xlsx"
    wb.save(fname)
    print(f"{MONATSNAMEN[m]}: {len(month_tx)} Transaktionen, {n_ohne_netto} ohne Netto -> {fname}")

print()
print("Alle 12 Monatsdateien gespeichert in:", OUTDIR)
