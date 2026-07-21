#!/usr/bin/env python3
"""Schritt 4: Belege <-> Transaktionen matchen (siehe Aufgabenspezifikation Schritt 4)."""
import json, re
from datetime import date, timedelta

TX_PATH = "/Users/sesp01-user/vault/Prozessia-Brain/Finanzen/Belegauswertung_2025/out/01_transaktionen.json"
BELEGE_PATH = "/Users/sesp01-user/vault/Prozessia-Brain/Finanzen/Belegauswertung_2025/out/02_belege_ordner.json"
OUT = "/Users/sesp01-user/vault/Prozessia-Brain/Finanzen/Belegauswertung_2025/out/04_merged.json"

BAGATELLE = 15.0

LEGAL_FORMS = re.compile(r'\b(gmbh|ag|ltd|inc|gbr|ug|egbr|se|bv|b\.v\.|llc|kg|co)\b', re.IGNORECASE)
HAFTUNGSBESCHR = re.compile(r'\(haftungsbeschr[aä]nkt\)', re.IGNORECASE)

def normalize_partner(name):
    if not name:
        return ""
    n = name.lower()
    n = HAFTUNGSBESCHR.sub('', n)
    n = LEGAL_FORMS.sub('', n)
    n = re.sub(r'[^a-z0-9äöüß]+', ' ', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n

def partner_match(a, b):
    na, nb = normalize_partner(a), normalize_partner(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    # Teilstring-Match in beide Richtungen (z.B. "IONOS" in "IONOS SE Elgendorfer...")
    a_tokens = set(na.split())
    b_tokens = set(nb.split())
    if not a_tokens or not b_tokens:
        return False
    overlap = a_tokens & b_tokens
    # signifikanter Wortueberlapp
    return len(overlap) >= 1 and (len(overlap) / min(len(a_tokens), len(b_tokens))) >= 0.5

# Bekannte Marken/Anbieter, um falsche "betragsgleich"-Zufallstreffer zwischen
# eindeutig UNTERSCHIEDLICHEN Anbietern zu verhindern (z.B. Google Workspace 8,99 EUR
# faelschlich auf einen Facebook-Ads-Beleg von 9,00 EUR gemappt, nur weil |Delta|<=0.02).
KNOWN_BRAND_TOKENS = {
    "google": "google", "facebk": "meta", "facebook": "meta", "meta": "meta",
    "instantly": "instantly", "apify": "apify", "anthropic": "anthropic",
    "openai": "openai", "mistral": "mistral", "microsoft": "microsoft",
    "hostinger": "hostinger", "ionos": "ionos", "hetzner": "hetzner",
    "sipgate": "sipgate", "digistore24": "digistore24", "wix": "wix",
    "linkedin": "linkedin", "gamma": "gamma", "paddle": "paddle", "n8n": "n8n",
    "zoho": "zoho", "bolt": "bolt", "findylead": "findylead", "haufe": "haufe",
    "lexware": "haufe", "triathlon": "triathlon", "pnl": "finom", "finom": "finom",
    "cyfire": "cyfire",
}

def known_brand(name):
    low = (name or "").lower()
    for token, brand in KNOWN_BRAND_TOKENS.items():
        if token in low:
            return brand
    return None

def is_known_brand_conflict(a, b):
    """True nur wenn BEIDE Seiten einer bekannten (unterschiedlichen) Marke zugeordnet
    werden koennen - dann ist ein reiner Betragszufallstreffer ausgeschlossen."""
    ba, bb = known_brand(a), known_brand(b)
    return ba is not None and bb is not None and ba != bb

def parse_iso(d):
    if not d:
        return None
    y, m, dd = d.split('-')
    return date(int(y), int(m), int(dd))

def within_window(zahlungsdatum, rechnungsdatum, days_before=5, days_after=60):
    zd = parse_iso(zahlungsdatum)
    rd = parse_iso(rechnungsdatum)
    if not zd or not rd:
        return None  # unbekannt
    return (rd - timedelta(days=days_before)) <= zd <= (rd + timedelta(days=days_after))

def main():
    transaktionen = json.load(open(TX_PATH, encoding='utf-8'))
    belege = json.load(open(BELEGE_PATH, encoding='utf-8'))

    # Nur Belege mit prinzipiell brauchbaren Daten fuer Matching-Versuch
    for b in belege:
        b['_matched_tx'] = None

    for tx in transaktionen:
        tx['beleg_ids'] = []
        if tx['kategorie'] != 'GESCHAEFTLICH':
            continue  # Einlagen/Entnahmen/Umbuchungen/Unklar brauchen keinen Belegabgleich
        if tx['status'] == 'PRUEFFALL' and tx.get('pruefgrund'):
            continue  # bereits in Schritt 1 als Pruefall geflaggt (z.B. Duplikat-Verdacht) - nicht ueberschreiben

        tx_richtung_beleg = "AUSGANG" if tx['richtung'] == 'AUSGANG' else "EINGANG"
        candidates = []
        for b in belege:
            if b.get('betrag_brutto') is None:
                continue
            if abs(b['betrag_brutto'] - tx['betrag_brutto']) > 0.02:
                continue
            candidates.append(b)

        if not candidates:
            continue

        # a) exakt: Betrag + Richtung + Partner + Zeitfenster
        exact = []
        for b in candidates:
            if b.get('richtung') and b['richtung'] != tx_richtung_beleg:
                continue
            pm = partner_match(tx['gegenpartei'], b.get('partner'))
            win = within_window(tx['zahlungsdatum'], b.get('rechnungsdatum'))
            if pm and win is True:
                exact.append(b)
        # c) Rechnungsnummer im Verwendungszweck -> starker Match (auch ohne Partner/Datum-Match)
        by_nummer = []
        vzw = (tx.get('verwendungszweck') or '')
        for b in candidates:
            nr = b.get('rechnungsnummer')
            if nr and len(str(nr)) >= 4 and str(nr) in vzw:
                by_nummer.append(b)

        # Rechnungsnummer im Verwendungszweck ist das staerkste Signal - wenn es EINDEUTIG
        # auf einen Kandidaten zeigt, entscheidet das, auch wenn 'exact' zusaetzlich einen
        # zufaellig betragsgleichen, aber anderen Beleg enthaelt (z.B. zwei Rechnungen mit
        # identischem Rundbetrag an denselben Kunden).
        if len(by_nummer) == 1:
            strong_matches = by_nummer
        else:
            strong_matches = list({b['id']: b for b in (exact + by_nummer)}.values())

        if len(strong_matches) == 1:
            b = strong_matches[0]
            tx['beleg_ids'] = [b['id']]
            b['_matched_tx'] = tx['tx_id']
            b['tx_id'] = tx['tx_id']
            b['zahlungsdatum'] = tx['zahlungsdatum']
            b['zahlungsweg'] = 'BANK'
            b['status'] = 'VOLLSTAENDIG' if b.get('status') != 'PRUEFFALL' else b['status']
            tx['status'] = 'BELEGT'
            tx['pruefgrund'] = None
            continue

        if len(strong_matches) > 1:
            names = '; '.join(f"{b['quellref'].split('/')[-1]} (Beleg {b['id'][:8]})" for b in strong_matches)
            tx['status'] = 'PRUEFFALL'
            tx['pruefgrund'] = f"Mehrere Beleg-Kandidaten mit passender Rechnungsnummer/Partner+Zeitfenster: {names}"
            continue

        # b) betragsgleich + Zeitfenster passend, Partner unklar -> Match, aber PRUEFFALL
        window_only = []
        for b in candidates:
            if b.get('richtung') and b['richtung'] != tx_richtung_beleg:
                continue
            if is_known_brand_conflict(tx['gegenpartei'], b.get('partner')):
                continue  # z.B. Google-Transaktion nicht auf Facebook-Beleg mappen, nur weil Betrag zufaellig fast gleich ist
            win = within_window(tx['zahlungsdatum'], b.get('rechnungsdatum'))
            if win is True:
                window_only.append(b)

        if len(window_only) == 1:
            b = window_only[0]
            tx['beleg_ids'] = [b['id']]
            b['_matched_tx'] = tx['tx_id']
            b['tx_id'] = tx['tx_id']
            b['zahlungsdatum'] = tx['zahlungsdatum']
            b['zahlungsweg'] = 'BANK'
            tx['status'] = 'PRUEFFALL'
            tx['pruefgrund'] = f"Zuordnung nur ueber Betrag+Zeitfenster, Partner nicht eindeutig: Transaktion '{tx['gegenpartei']}' vs. Beleg-Partner '{b.get('partner')}' ({b['quellref'].split('/')[-1]})"
            b['status'] = 'PRUEFFALL'
            b['pruefgrund'] = "Zuordnung nur ueber Betrag, Partner nicht eindeutig bestaetigt"
            continue
        elif len(window_only) > 1:
            names = '; '.join(f"{b['quellref'].split('/')[-1]}" for b in window_only)
            tx['status'] = 'PRUEFFALL'
            tx['pruefgrund'] = f"Mehrere betragsgleiche Beleg-Kandidaten im Zeitfenster, kein automatischer Match: {names}"
            continue

        # Betragsgleiche Kandidaten ohne Datumsfenster-Bestaetigung (z.B. Beleg ohne rechnungsdatum)
        no_date_candidates = [b for b in candidates if (not b.get('richtung') or b['richtung'] == tx_richtung_beleg) and not b.get('rechnungsdatum')]
        if len(no_date_candidates) == 1:
            b = no_date_candidates[0]
            pm = partner_match(tx['gegenpartei'], b.get('partner'))
            if pm:
                tx['beleg_ids'] = [b['id']]
                b['_matched_tx'] = tx['tx_id']
                b['tx_id'] = tx['tx_id']
                b['zahlungsdatum'] = tx['zahlungsdatum']
                b['zahlungsweg'] = 'BANK'
                tx['status'] = 'PRUEFFALL'
                tx['pruefgrund'] = f"Beleg ohne Rechnungsdatum, Partner passt, Betrag passt - bitte Datum pruefen ({b['quellref'].split('/')[-1]})"
                b['status'] = 'PRUEFFALL'
                b['pruefgrund'] = "Kein Rechnungsdatum extrahierbar, Zuordnung ueber Betrag+Partner"
                continue

        # kein Match gefunden -> unten per Bagatellgrenze behandelt

    # Fremdwaehrungs-Pass: unmatchte Transaktionen gegen USD/Fremdwaehrungs-Belege
    # desselben Partners in zeitlicher Naehe pruefen (Betrag weicht wegen FX-Umrechnung
    # ab - NIEMALS selbst umrechnen, nur als Pruefall mit Fremdwaehrungs-Hinweis melden).
    for tx in transaktionen:
        if tx['kategorie'] != 'GESCHAEFTLICH' or tx['beleg_ids']:
            continue
        if tx['status'] == 'PRUEFFALL' and tx.get('pruefgrund'):
            continue
        tx_richtung_beleg = "AUSGANG" if tx['richtung'] == 'AUSGANG' else "EINGANG"
        fx_candidates = []
        for b in belege:
            if b.get('waehrung') == 'EUR' or b.get('waehrung') is None:
                continue
            if b.get('richtung') and b['richtung'] != tx_richtung_beleg:
                continue
            if not partner_match(tx['gegenpartei'], b.get('partner')):
                continue
            win = within_window(tx['zahlungsdatum'], b.get('rechnungsdatum'), days_before=10, days_after=10)
            if win is True:
                fx_candidates.append(b)
        if len(fx_candidates) == 1:
            b = fx_candidates[0]
            tx['beleg_ids'] = [b['id']]
            b['_matched_tx'] = tx['tx_id']
            b['tx_id'] = tx['tx_id']
            b['zahlungsdatum'] = tx['zahlungsdatum']
            b['zahlungsweg'] = 'BANK'
            tx['status'] = 'PRUEFFALL'
            tx['pruefgrund'] = (f"Fremdwaehrungs-Beleg gefunden ({b.get('betrag_brutto')} {b.get('waehrung')}), "
                                 f"Bankbuchung in EUR ({tx['betrag_brutto']}) nach Kartenumrechnung - Betrag NICHT automatisch "
                                 f"umgerechnet, bitte Wechselkurs/Zuordnung manuell pruefen ({b['quellref'].split('/')[-1]})")
            b['status'] = 'PRUEFFALL'
            b['pruefgrund'] = "Fremdwaehrungsbeleg, Bankbetrag weicht wegen Kartenumrechnung ab - manuell pruefen"

    # Bagatellgrenze auf Transaktionsseite anwenden
    for tx in transaktionen:
        if tx['kategorie'] != 'GESCHAEFTLICH':
            continue
        if tx['beleg_ids']:
            continue  # bereits behandelt oben
        if tx['status'] == 'PRUEFFALL' and tx.get('pruefgrund'):
            continue  # bereits mit konkretem Pruefgrund belegt (z.B. mehrdeutige Kandidaten, Duplikat-Verdacht) - nicht ueberschreiben
        if tx['betrag_brutto'] <= BAGATELLE:
            tx['status'] = 'AKZEPTIERT_BAGATELLE'
            tx['pruefgrund'] = None
        else:
            tx['status'] = 'BELEG_FEHLT'
            tx['pruefgrund'] = None

    # Belege ohne Transaktion (nicht gematcht) einordnen
    ausserhalb_zeitraum = []
    for b in belege:
        if b['_matched_tx']:
            continue
        if b['status'] == 'PRUEFFALL':
            continue  # bereits mit eigenem Pruefgrund aus Schritt 2 (fehlende Felder etc.)
        rd = b.get('rechnungsdatum')
        if rd and not rd.startswith('2025'):
            ausserhalb_zeitraum.append(b)
            continue
        brutto = b.get('betrag_brutto')
        if brutto is not None and brutto <= BAGATELLE and b.get('richtung') is not None and b.get('waehrung') == 'EUR':
            b['status'] = 'AKZEPTIERT_BAGATELLE'
            b['pruefgrund'] = None
        elif brutto is not None:
            b['status'] = 'OHNE_ZAHLUNG'
            vzw_hint = (b.get('beschreibung') or '') + ' ' + (b.get('partner') or '')
            if re.search(r'kreditkarte|paypal|visa|kredit|lastschrift', vzw_hint, re.IGNORECASE) or (b.get('waehrung') != 'EUR'):
                b['zahlungsweg'] = 'ANDERER_WEG_VERMUTET'
            else:
                b['zahlungsweg'] = 'UNBEKANNT'

    for b in ausserhalb_zeitraum:
        belege.remove(b)

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({"transaktionen": transaktionen, "belege": belege}, f, ensure_ascii=False, indent=2)

    with open("/Users/sesp01-user/vault/Prozessia-Brain/Finanzen/Belegauswertung_2025/out/ausserhalb_zeitraum.json", 'w', encoding='utf-8') as f:
        json.dump(ausserhalb_zeitraum, f, ensure_ascii=False, indent=2)

    # Konsolenausgabe
    from collections import Counter
    tx_status = Counter(t['status'] for t in transaktionen)
    beleg_status = Counter(b['status'] for b in belege)
    print("Transaktionsstatus:", dict(tx_status))
    print("Belegstatus:", dict(beleg_status))
    print("Ausserhalb Zeitraum verschoben:", len(ausserhalb_zeitraum))

if __name__ == '__main__':
    main()
