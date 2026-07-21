#!/usr/bin/env python3
"""Schritt 5: Monats-/Jahresauswertung auf Basis Zahlungsdatum."""
import json
from collections import defaultdict

MERGED = "/Users/sesp01-user/vault/Prozessia-Brain/Finanzen/Belegauswertung_2025/out/04_merged.json"
OUT = "/Users/sesp01-user/vault/Prozessia-Brain/Finanzen/Belegauswertung_2025/out/05_auswertung.json"

def main():
    data = json.load(open(MERGED, encoding='utf-8'))
    tx_all = data['transaktionen']
    belege_by_id = {b['id']: b for b in data['belege']}

    guv_tx = [t for t in tx_all if t['kategorie'] == 'GESCHAEFTLICH']

    monate = {m: {
        'umsatz_brutto': 0.0, 'umsatz_netto': 0.0, 'ust_vereinnahmt': 0.0,
        'ausgaben_brutto': 0.0, 'ausgaben_netto': 0.0, 'vorsteuer_abziehbar': 0.0,
        'vorsteuer_gefaehrdet': 0.0, 'brutto_ohne_aufteilung': 0.0,
        'anzahl_pruefaelle': 0,
    } for m in range(1, 13)}

    BAGATELLE = 15.0

    for t in guv_tx:
        m = t['monat']
        row = monate[m]
        beleg = belege_by_id.get(t['beleg_ids'][0]) if t.get('beleg_ids') else None
        has_split = beleg and beleg.get('betrag_netto') is not None and beleg.get('ust_betrag') is not None

        if t['status'] == 'PRUEFFALL':
            row['anzahl_pruefaelle'] += 1

        if t['richtung'] == 'AUSGANG':  # Geldeingang = Umsatz
            row['umsatz_brutto'] += t['betrag_brutto']
            if has_split:
                row['umsatz_netto'] += beleg['betrag_netto']
                row['ust_vereinnahmt'] += beleg['ust_betrag']
            else:
                row['brutto_ohne_aufteilung'] += t['betrag_brutto']
        else:  # EINGANG = Geldausgang = Ausgabe
            row['ausgaben_brutto'] += t['betrag_brutto']
            if has_split:
                row['ausgaben_netto'] += beleg['betrag_netto']
                row['vorsteuer_abziehbar'] += beleg['ust_betrag']
            else:
                row['brutto_ohne_aufteilung'] += t['betrag_brutto']
                if t['status'] == 'BELEG_FEHLT' and t['betrag_brutto'] > BAGATELLE:
                    geschaetzte_ust = round(t['betrag_brutto'] - t['betrag_brutto'] / 1.19, 2)
                    row['vorsteuer_gefaehrdet'] += geschaetzte_ust

    for m in monate:
        row = monate[m]
        # HAUPTKENNZAHL (angefordert): reine Brutto-Differenz, unabhaengig von der
        # (noch unvollstaendigen) Netto-/USt-Aufschluesselung je Beleg.
        row['ergebnis_brutto'] = round(row['umsatz_brutto'] - row['ausgaben_brutto'], 2)
        # Netto-basierter Gewinn NUR als Nebeninfo, solange Beleglage unvollstaendig ist.
        row['gewinn_netto_unvollstaendig'] = round(row['umsatz_netto'] - row['ausgaben_netto'], 2)
        row['ust_zahllast'] = round(row['ust_vereinnahmt'] - row['vorsteuer_abziehbar'], 2)
        for k in row:
            if isinstance(row[k], float):
                row[k] = round(row[k], 2)

    jahr = {
        k: round(sum(monate[m][k] for m in monate), 2)
        for k in ['umsatz_brutto', 'umsatz_netto', 'ust_vereinnahmt', 'ausgaben_brutto',
                  'ausgaben_netto', 'vorsteuer_abziehbar', 'vorsteuer_gefaehrdet',
                  'brutto_ohne_aufteilung', 'anzahl_pruefaelle']
    }
    jahr['ergebnis_brutto'] = round(jahr['umsatz_brutto'] - jahr['ausgaben_brutto'], 2)
    jahr['gewinn_netto_unvollstaendig'] = round(jahr['umsatz_netto'] - jahr['ausgaben_netto'], 2)
    jahr['ust_zahllast'] = round(jahr['ust_vereinnahmt'] - jahr['vorsteuer_abziehbar'], 2)
    jahr['gewinnanteil_je_gesellschafter_brutto'] = round(jahr['ergebnis_brutto'] / 2, 2)
    jahr['hinweis'] = ("HAUPTKENNZAHL ist 'ergebnis_brutto' (Umsatz brutto - Ausgaben brutto), da die "
                        "Netto-/USt-Aufschluesselung je Beleg noch unvollstaendig ist (viele Zahlungen ohne "
                        "verknuepften Beleg mit Netto-Angabe). 'gewinn_netto_unvollstaendig' NICHT als "
                        "verlaesslichen Gewinn verwenden, bis mehr Belege geklaert sind. Kein echter "
                        "steuerlicher Gewinn (keine Abschreibungen/Abgrenzungen/Hinzurechnungen) -> "
                        "Steuerberater konsultieren.")

    einlagen_entnahmen = [t for t in tx_all if t['kategorie'] == 'EINLAGE_ENTNAHME']
    umbuchungen = [t for t in tx_all if t['kategorie'] == 'UMBUCHUNG']

    out = {
        'monate': monate, 'jahr': jahr,
        'einlagen_entnahmen_summe': round(sum(t['betrag_brutto'] for t in einlagen_entnahmen), 2),
        'einlagen_entnahmen_anzahl': len(einlagen_entnahmen),
        'umbuchungen_anzahl': len(umbuchungen),
    }
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("Jahreskennzahlen:")
    for k, v in jahr.items():
        print(f"  {k}: {v}")
    print("Einlagen/Entnahmen Summe:", out['einlagen_entnahmen_summe'], "Anzahl:", out['einlagen_entnahmen_anzahl'])

if __name__ == '__main__':
    main()
