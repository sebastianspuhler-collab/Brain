#!/usr/bin/env python3
"""Schritt 4b: wendet die manuell geprueften Korrekturen aus korrekturen_2025.json
auf out/04_merged.json an. Idempotent - mehrfaches Ausfuehren aendert nichts.

Laufen muss: step4 -> step4b -> step5 -> step6 -> step7 -> step8
"""
import json

BASE = "/Users/sesp01-user/vault/Prozessia-Brain/Finanzen/Belegauswertung_2025"
MERGED = f"{BASE}/out/04_merged.json"
KORR = f"{BASE}/korrekturen_2025.json"

merged = json.load(open(MERGED, encoding='utf-8'))
korr = json.load(open(KORR, encoding='utf-8'))
belege = merged['belege']
tx_list = merged['transaktionen']
by_datei = {b['quellref'].split('/')[-1]: b for b in belege}
by_tx = {t['tx_id']: t for t in tx_list}

n_beleg = n_tx = n_link = 0

# --- 1. Belegwerte korrigieren -------------------------------------------------
for k in korr['beleg_korrekturen']:
    b = by_datei.get(k['datei'])
    if b is None:
        print(f"  ! Beleg nicht gefunden: {k['datei']}")
        continue
    geaendert = [f"{f}: {b.get(f)} -> {v}" for f, v in k['setze'].items() if b.get(f) != v]
    b.update(k['setze'])
    b['korrektur_grund'] = k['grund']
    if geaendert:
        n_beleg += 1
        print(f"  Beleg {k['datei']}")
        for g in geaendert:
            print(f"      {g}")
    # Beleg einer bestehenden Kontobuchung zuordnen
    if k.get('verknuepfe_tx'):
        t = by_tx.get(k['verknuepfe_tx'])
        if t is not None and b['id'] not in (t.get('beleg_ids') or []):
            t.setdefault('beleg_ids', []).append(b['id'])
            t['status'] = 'BELEGT'
            t['pruefgrund'] = None
            b['tx_id'] = t['tx_id']
            b['zahlungsdatum'] = t['zahlungsdatum']
            b['status'] = 'VOLLSTAENDIG'
            b['_matched_tx'] = t['tx_id']
            n_link += 1
            print(f"      verknuepft mit Kontobuchung {t['tx_id']} vom {t['zahlungsdatum']}")

# --- 1b. Transaktionsfelder direkt korrigieren (z.B. Kategorie aendern) --------
for k in korr.get('tx_korrekturen', []):
    t = by_tx.get(k['tx_id'])
    if t is None:
        print(f"  ! Transaktion nicht gefunden: {k['tx_id']}")
        continue
    geaendert = [f"{f}: {t.get(f)} -> {v}" for f, v in k['setze'].items() if t.get(f) != v]
    t.update(k['setze'])
    t['korrektur_grund'] = k['grund']
    if geaendert:
        n_tx += 1
        print(f"  Transaktion {k['tx_id']}")
        for g in geaendert:
            print(f"      {g}")

# --- 2. Privat bezahlte Ausgaben als Pseudo-Buchung ergaenzen ------------------
for p in korr['privat_bezahlte_ausgaben']:
    if p['tx_id'] in by_tx:
        continue
    b = by_datei.get(p['beleg_datei'])
    if b is None:
        print(f"  ! Beleg nicht gefunden: {p['beleg_datei']}")
        continue
    t = {
        'tx_id': p['tx_id'],
        'zahlungsdatum': p['zahlungsdatum'],
        'monat': int(p['zahlungsdatum'][5:7]),
        # Konvention der Pipeline: EINGANG = Geldabfluss = Ausgabe
        'richtung': 'EINGANG',
        'betrag_brutto': p['betrag_brutto'],
        'gegenpartei': p['gegenpartei'],
        'verwendungszweck': f"PRIVAT BEZAHLT (kein Geschaeftskonto) - Einlage | {p['beleg_datei']}",
        'kategorie': 'GESCHAEFTLICH',
        'fremdwaehrung': False,
        'fx_hinweis': None,
        'beleg_ids': [b['id']],
        'status': 'BELEGT',
        'pruefgrund': None,
        'quelle': 'privatzahlung',
        'quellref': b['quellref'],
        'privat_bezahlt': True,
        'korrektur_grund': p['grund'],
    }
    tx_list.append(t)
    by_tx[t['tx_id']] = t
    b['tx_id'] = t['tx_id']
    b['zahlungsdatum'] = t['zahlungsdatum']
    b['zahlungsweg'] = 'PRIVAT'
    b['status'] = 'VOLLSTAENDIG'
    b['_matched_tx'] = t['tx_id']
    n_tx += 1
    print(f"  Privatzahlung ergaenzt: {p['zahlungsdatum']} {p['gegenpartei']} {p['betrag_brutto']:.2f} EUR")

tx_list.sort(key=lambda t: (t['zahlungsdatum'], t['tx_id']))
json.dump(merged, open(MERGED, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f"\nKorrekturen angewendet: {n_beleg} Belegwerte, {n_link} Beleg-Zahlung-Verknuepfung(en), "
      f"{n_tx} Privatzahlung(en). Gesamt {len(tx_list)} Buchungen, {len(belege)} Belege.")
