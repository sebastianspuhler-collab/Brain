#!/usr/bin/env python3
"""Schritt 2: Felder aus lokalen Belegen (Rechnungen + Angebote) extrahieren.
Konservativ: nur bei klarem Label:Wert-Muster wird ein Feld gefuellt, sonst null + PRUEFFALL.
"""
import json, re, os, uuid

RAW = "/Users/sesp01-user/vault/Prozessia-Brain/Finanzen/Belegauswertung_2025/out/_local_text_raw.json"
OCR = "/Users/sesp01-user/vault/Prozessia-Brain/Finanzen/Belegauswertung_2025/out/_ocr_results.json"
OUT = "/Users/sesp01-user/vault/Prozessia-Brain/Finanzen/Belegauswertung_2025/out/02_belege_ordner.json"

EIGENE_FIRMA_MARKER = ["prozessia", "webwokr"]
SELF_ISSUED_PHRASE = "unsere lieferungen/leistungen stellen wir ihnen"

MONTHS = {
    "januar":1,"februar":2,"märz":3,"maerz":3,"april":4,"mai":5,"juni":6,"juli":7,
    "august":8,"september":9,"oktober":10,"november":11,"dezember":12,
}

def find_first(patterns, text, flags=re.IGNORECASE):
    for pat in patterns:
        m = re.search(pat, text, flags)
        if m:
            return m.group(1).strip()
    return None

def parse_de_amount(s):
    if s is None:
        return None
    s = s.strip().replace('EUR', '').replace('€', '').strip()
    s = s.replace('.', '').replace(',', '.')
    try:
        return round(float(s), 2)
    except ValueError:
        return None

# --- Robuste Betrags-Extraktion (Fallback fuer heterogene Vendor-Layouts) ---
AMOUNT_LINE_RE = re.compile(
    r'^[+\-]?\s*(?:€|\$)?\s*(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*(€|\$|EUR|USD)?\s*$'
)

def parse_amount_token(num_str):
    if re.search(r',\d{2}$', num_str):
        return round(float(num_str.replace('.', '').replace(',', '.')), 2)
    if re.search(r'\.\d{2}$', num_str):
        return round(float(num_str.replace(',', '')), 2)
    return None

def amount_currency(cur):
    if cur in ('$', 'USD'):
        return 'USD'
    return 'EUR'

GROSS_LABELS = [
    r'Zu zahlender Betrag',
    r'Bezahlter Betrag',
    r'F[aä]lliger Betrag',
    r'Gesamtbetrag',
    r'Gesamtsumme',
    r'Invoice Amount',
    r'(?<!Zwischen)(?<!zwischen)\bInsgesamt\b',
    r'(?<!Zwischen)(?<!zwischen)\bSumme\b',
    r'\bGesamt\b(?!\s*\(?netto)',
    r'Total\s*\(?incl',
    r'\bTotal\b(?!\s*excl)',
    r'Amount [Dd]ue(?!\s*\(EUR\)\s*\n?\s*[€$]?0)',
]
NET_LABEL_WORDS = re.compile(r'zwischensumme|subtotal|nettopreis|\bnetto\b|excl\.?\s*vat|excluding tax|before tax', re.IGNORECASE)

def amounts_forward_window(text, start, max_lines=6):
    rest = text[start:start + 400]
    lines = rest.split('\n')
    amounts = []
    for line in lines[:max_lines]:
        line_s = line.strip()
        if not line_s:
            continue
        m = AMOUNT_LINE_RE.match(line_s)
        if m:
            val = parse_amount_token(m.group(1))
            if val is not None:
                amounts.append((val, amount_currency(m.group(2))))
        else:
            break
    return amounts

def extract_betrag_brutto_robust(text):
    """Sucht nach bekannten Brutto-Labels, nimmt bei mehrspaltigen Zeilen (Netto/Steuer/Brutto)
    den letzten Betrag im Fenster. Liefert (betrag, waehrung) oder (None, None)."""
    for label_pat in GROSS_LABELS:
        for m in re.finditer(label_pat, text, re.IGNORECASE):
            amounts = amounts_forward_window(text, m.end())
            if amounts:
                return amounts[-1]
    return None, None

def extract_amount_label_value_block(text):
    """Fallback fuer Layouts, bei denen erst alle Labels, dann alle Werte kommen
    (z.B. LinkedIn: 'Zwischensumme :\\nUSt. : 19%\\nInsgesamt :\\n...' gefolgt von
    'X EUR\\nY EUR\\nZ EUR\\n...')."""
    lines = [l.strip() for l in text.splitlines()]
    label_words = ['zwischensumme', 'ust.', 'insgesamt', 'zahlung', 'ausstehender betrag', 'summe', 'gesamt']
    for i in range(len(lines)):
        block = []
        j = i
        while j < len(lines) and lines[j] and (lines[j].endswith(':') and any(w in lines[j].lower() for w in label_words)):
            block.append(lines[j])
            j += 1
        if len(block) >= 3:
            amounts = []
            k = j
            while k < len(lines) and len(amounts) < len(block):
                if lines[k].strip():
                    m = AMOUNT_LINE_RE.match(lines[k].strip())
                    if not m:
                        break
                    amounts.append(parse_amount_token(m.group(1)))
                k += 1
            if len(amounts) == len(block):
                for idx, lbl in enumerate(block):
                    if 'insgesamt' in lbl.lower() or 'gesamt' in lbl.lower():
                        return amounts[idx], 'EUR'
    return None, None

def parse_de_date(s):
    if not s:
        return None
    s = s.strip()
    m = re.match(r'^(\d{1,2})\.(\d{1,2})\.(\d{4})$', s)
    if m:
        d, mo, y = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    m = re.match(r'^(\d{1,2})\.\s*([A-Za-zäöüÄÖÜ]+)\s*(\d{4})$', s)
    if m:
        d, monat_name, y = m.groups()
        mo = MONTHS.get(monat_name.lower().replace('ä','ae').replace('ü','ue').replace('ö','oe'))
        if mo:
            return f"{y}-{mo:02d}-{int(d):02d}"
    return None

def extract_rechnungsnummer(text):
    val = find_first([
        r'Rechnungsnr\.?:?\s*\n?\s*([A-Za-z0-9\-_./]+)',
        r'Rechnungsnummer:?\s*\n?\s*([A-Za-z0-9\-_./]+)',
        r'Rechnung Nr\.?\s*([A-Za-z0-9\-_./]+)',
        r'Invoice\s*(?:No\.?|Number)?[:#]?\s*([A-Za-z0-9\-_./]+)',
        r'Bestellnr\.?:?\s*\n?\s*([A-Za-z0-9\-_./]+)',
    ], text)
    return val

def extract_rechnungsdatum(text):
    raw = find_first([
        r'Rechnungsdatum:?\s*\n?\s*(\d{1,2}\.\d{1,2}\.\d{4})',
        r'Rechnungsdatum:?\s*\n?\s*(\d{1,2}\.\s*[A-Za-zäöüÄÖÜ]+\s*\d{4})',
        r'Datum:?\s*\n?\s*(\d{1,2}\.\d{1,2}\.\d{4})',
        r'invoice date[:\s]*\n?\s*(\d{1,2}\.\d{1,2}\.\d{4})',
    ], text)
    return parse_de_date(raw)

def extract_betrag_brutto(text):
    val, cur = extract_betrag_brutto_robust(text)
    if val is not None:
        return val, cur
    val, cur = extract_amount_label_value_block(text)
    if val is not None:
        return val, cur
    return None, None

def extract_betrag_netto(text):
    for label_pat in [r'Zwischensumme\s*\(?netto\)?', r'Nettopreis', r'Total excl(?:uding|\.)\s*(?:tax|VAT)',
                       r'Services before tax', r'Gesamt\s*\(?netto\)?', r'(?<!zwischen)Netto(?:betrag|summe)?']:
        for m in re.finditer(label_pat, text, re.IGNORECASE):
            amounts = amounts_forward_window(text, m.end(), max_lines=2)
            if amounts:
                return amounts[0][0]
    return None

def extract_ust(text):
    """Liefert (ust_satz, ust_betrag) NUR wenn explizit auf dem Beleg -> nie zurueckrechnen."""
    m = re.search(r'(?:Umsatzsteuer|MwSt\.?|Mehrwertsteuer|VAT)\s*\(?\s*(\d{1,2})(?:[.,]\d)?\s*%[^\n]*\)?\s*\n?\s*(?:\(?[€$]?\s*(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})\)?)?', text, re.IGNORECASE)
    if m and m.group(2):
        satz = int(m.group(1))
        betrag = parse_amount_token(m.group(2))
        return satz, betrag
    if m:
        satz = int(m.group(1))
        amounts = amounts_forward_window(text, m.end(), max_lines=2)
        if amounts:
            return satz, amounts[0][0]
        return satz, None
    m = re.search(r'0\s*%\s*\n?\s*-', text)
    if m:
        return 0, 0.0
    return None, None

def detect_richtung(text):
    low = text.lower()
    if SELF_ISSUED_PHRASE in low:
        return "AUSGANG"
    self_issuer = any(marker in low.split('rechnung')[0][:400] for marker in EIGENE_FIRMA_MARKER) if 'rechnung' in low else False
    # Heuristik: eigene Firma als Kunden-/Empfaengeradresse erwaehnt -> wir haben empfangen
    if any(marker in low for marker in EIGENE_FIRMA_MARKER):
        return "EINGANG"
    return None

def extract_partner(text, richtung):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for l in lines[:15]:
        low = l.lower()
        if any(m in low for m in EIGENE_FIRMA_MARKER):
            continue
        if len(l) > 3 and not re.match(r'^\d', l):
            return l
    return None

def detect_waehrung(text):
    if re.search(r'\bUSD\b|\$\s*\d', text):
        if '€' not in text and 'EUR' not in text:
            return 'USD'
    return 'EUR'

def main():
    raw = json.load(open(RAW, encoding='utf-8'))
    ocr = json.load(open(OCR, encoding='utf-8'))

    out = []
    for r in raw:
        path = r['path']
        text = r['text']
        if (not text or len(text.strip()) < 20) and path in ocr:
            text = ocr.get(path) or ''
        if text is None:
            text = ''

        beleg_id = str(uuid.uuid5(uuid.NAMESPACE_URL, path))
        rechnungsnummer = extract_rechnungsnummer(text)
        rechnungsdatum = extract_rechnungsdatum(text)
        betrag_brutto, brutto_waehrung = extract_betrag_brutto(text)
        betrag_netto = extract_betrag_netto(text)
        ust_satz, ust_betrag = extract_ust(text)
        richtung = detect_richtung(text)
        partner = extract_partner(text, richtung)
        waehrung = brutto_waehrung or detect_waehrung(text)

        pruefgruende = []
        if not text.strip():
            pruefgruende.append("Kein extrahierbarer Text (auch nach OCR-Versuch leer) - vermutlich kein lesbarer Beleg")
        if richtung is None:
            pruefgruende.append("Richtung (AUSGANG/EINGANG) nicht eindeutig bestimmbar - EIGENE_FIRMA weder als Aussteller noch als Empfaenger klar erkennbar")
        if betrag_brutto is None and text.strip():
            pruefgruende.append("Bruttobetrag nicht eindeutig extrahierbar")
        if rechnungsdatum is None and text.strip():
            pruefgruende.append("Rechnungsdatum nicht eindeutig extrahierbar")
        if waehrung != 'EUR':
            pruefgruende.append(f"Fremdwaehrung vermutet: {waehrung}")

        status = "PRUEFFALL" if pruefgruende else "OHNE_ZAHLUNG"

        rec = {
            "id": beleg_id,
            "quelle": ["ordner"],
            "quellref": path,
            "richtung": richtung,
            "rechnungsdatum": rechnungsdatum,
            "rechnungsnummer": rechnungsnummer,
            "partner": partner,
            "beschreibung": None,
            "betrag_netto": betrag_netto,
            "ust_satz": ust_satz,
            "ust_satz_unterstellt": False,
            "ust_betrag": ust_betrag,
            "betrag_brutto": betrag_brutto,
            "waehrung": waehrung,
            "ist_abo": False,
            "abo_intervall": None,
            "tx_id": None,
            "zahlungsdatum": None,
            "zahlungsweg": "UNBEKANNT",
            "status": status,
            "pruefgrund": "; ".join(pruefgruende) if pruefgruende else None,
            "_text_len": len(text),
            "_text_preview": text[:300],
        }
        out.append(rec)

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    n = len(out)
    n_pruef = sum(1 for r in out if r['status'] == 'PRUEFFALL')
    n_richtung_null = sum(1 for r in out if r['richtung'] is None)
    n_betrag_null = sum(1 for r in out if r['betrag_brutto'] is None)
    n_datum_null = sum(1 for r in out if r['rechnungsdatum'] is None)
    print(f"Lokale Belege gesamt: {n}")
    print(f"  status=PRUEFFALL: {n_pruef}")
    print(f"  richtung=null: {n_richtung_null}")
    print(f"  betrag_brutto=null: {n_betrag_null}")
    print(f"  rechnungsdatum=null: {n_datum_null}")

if __name__ == '__main__':
    main()
