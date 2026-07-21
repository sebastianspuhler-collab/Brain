#!/usr/bin/env python3
"""
Schritt 1 - Transaktionen 2025 aus dem Finom-Kontoauszug (Ersatz fuer die nicht
existierende Lexoffice-Banktransaktions-API, s. Rueckfrage an Nutzer).
Kategorisiert jede Transaktion konservativ; bei Unklarheit -> UNKLAR + PRUEFFALL.
"""
import json
import re

ALL_TX = "/Users/sesp01-user/vault/Prozessia-Brain/Finanzen/Belegauswertung_2025/out/_finom_alle_jahre.json"
OUT = "/Users/sesp01-user/vault/Prozessia-Brain/Finanzen/Belegauswertung_2025/out/01_transaktionen.json"

PARTNER_IBANS = {
    "DE67590501010610680357": "Sebastian Spuhler",
    "DE86590400000535956702": "Mohamed Amin Douioui",
}
GENERIC_TRANSFER_WORDS = {
    "sparplan", "umschichtung", "offener betrag", "test", "anlage", "einlage",
    "entnahme", "",
}
INVOICE_REF_RE = re.compile(r'\b(RE\d{4,}|RG[_\d]+|AG\d{3,}|AU\d{3,}|RE\d{2}-\d+)\b', re.IGNORECASE)

# Bekannte Geschaeftspartner (SaaS/Vendoren/Kunden/Dienstleister) -> GESCHAEFTLICH
KNOWN_BUSINESS_SUBSTRINGS = [
    "openai", "mistral.ai", "anthropic", "instantly", "google*workspace", "google workspace",
    "zoho", "bolt (by stackblitz)", "apify", "paddle.net", "n8n", "gamma.app", "hostinger",
    "wix.com", "ionos", "haufe service center", "facebk", "digistore24", "notta", "sipgate",
    "microsoft", "triathlon transfer", "pnl fintech", "martin veser", "cyfire",
    "mattha", "matthä", "wimmler", "findylead", "hetzner", "benito ferrise",
]

def normalize_partner_iban(verwendungszweck):
    m = re.search(r'IBAN:\s*([A-Z]{2}[0-9A-Z]+)', verwendungszweck or "")
    return m.group(1).replace(" ", "") if m else None

def classify(tx):
    gegenpartei = (tx.get('gegenpartei') or "").strip()
    vzw = (tx.get('verwendungszweck') or "")
    vzw_lower = vzw.lower()
    ge_lower = gegenpartei.lower()
    iban = normalize_partner_iban(vzw)

    has_invoice_ref = bool(INVOICE_REF_RE.search(vzw))

    # 1) Gesellschafter-Privatkonto (per Name + bekannte private IBAN)
    if iban in PARTNER_IBANS and not has_invoice_ref:
        rest = vzw
        rest = re.sub(r'IBAN:\s*[A-Z0-9 ]+', '', rest, flags=re.IGNORECASE)
        rest = re.sub(r'BIC:\s*[A-Z0-9]+', '', rest, flags=re.IGNORECASE)
        rest_words = {w.strip().lower() for w in rest.split('|') if w.strip()}
        if rest_words <= GENERIC_TRANSFER_WORDS or not rest_words:
            return "EINLAGE_ENTNAHME", None
        # unbekannter Zusatztext bei Partner-IBAN -> lieber UNKLAR als raten
        return "UNKLAR", f"Transfer von/zu Gesellschafter-Privatkonto ({PARTNER_IBANS[iban]}) mit unbekanntem Verwendungszweck: {vzw!r}"

    # 2) Finanzamt (USt-Erstattung/-Zahlung) -> geschaeftlich, aber kein Waren-/Dienstleistungsumsatz
    if "finanzamt" in ge_lower:
        return "GESCHAEFTLICH", None

    # 3) Bekannte Geschaeftspartner/Vendoren/Kunden
    if any(s in ge_lower or s in vzw_lower for s in KNOWN_BUSINESS_SUBSTRINGS):
        return "GESCHAEFTLICH", None

    # 4) Rechnungsnummer im Verwendungszweck -> klarer Geschaeftsbezug
    if has_invoice_ref:
        return "GESCHAEFTLICH", None

    # 5) Alles andere: nicht entscheidbar
    return "UNKLAR", f"Gegenpartei/Verwendungszweck nicht eindeutig zuordenbar: {gegenpartei!r} / {vzw!r}"

def main():
    all_tx = json.load(open(ALL_TX, encoding='utf-8'))
    tx2025 = [t for t in all_tx if not t.get('parse_error') and t['zahlungsdatum'].startswith('2025')]

    out = []
    for t in tx2025:
        kategorie, pruefgrund_kat = classify(t)
        monat = int(t['zahlungsdatum'].split('-')[1])
        if kategorie == "UNKLAR":
            status = "PRUEFFALL"
        elif kategorie in ("EINLAGE_ENTNAHME", "UMBUCHUNG"):
            status = "BELEGT"  # kein Rechnungsbeleg noetig, Bankbeleg genuegt
        else:
            status = "BELEG_FEHLT"  # vorlaeufig, wird in Schritt 4 verfeinert
        rec = {
            "tx_id": t['tx_id'],
            "zahlungsdatum": t['zahlungsdatum'],
            "monat": monat,
            "richtung": t['richtung'],
            "betrag_brutto": t['betrag_brutto'],
            "gegenpartei": t['gegenpartei'],
            "verwendungszweck": t['verwendungszweck'],
            "kategorie": kategorie,
            "fremdwaehrung": bool(t.get('fremdwaehrung')),
            "fx_hinweis": t.get('fx_hinweis'),
            "beleg_ids": [],
            "status": status,
            "pruefgrund": pruefgrund_kat,
            "quelle": "finom_kontoauszug",
            "quellref": "Finom_statement_21072026.pdf",
        }
        out.append(rec)

    # Duplikat-/Rundlauf-Verdacht: gleicher Betrag + gleiches Datum (unabhaengig von
    # Kategorie/Richtung) -> IMMER echter Pruefall, unabhaengig von Bagatellgrenze.
    from collections import defaultdict
    groups = defaultdict(list)
    for r in out:
        groups[(r['zahlungsdatum'], r['betrag_brutto'])].append(r)
    for key, members in groups.items():
        if len(members) > 1:
            names = ', '.join(f"{m['gegenpartei']} ({m['richtung']})" for m in members)
            for m in members:
                m['status'] = 'PRUEFFALL'
                zusatz = f"Duplikat-/Rundlauf-Verdacht: gleicher Betrag {key[1]} am {key[0]} bei mehreren Buchungen: {names}"
                m['pruefgrund'] = (m['pruefgrund'] + ' | ' + zusatz) if m['pruefgrund'] else zusatz

    out.sort(key=lambda r: r['zahlungsdatum'])
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    n = len(out)
    ausgang = [r for r in out if r['richtung'] == 'AUSGANG']
    eingang = [r for r in out if r['richtung'] == 'EINGANG']
    print(f"Transaktionen 2025: {n}")
    print(f"  AUSGANG (Geldeingang/Umsatz-Kandidaten): {len(ausgang)}, Summe {sum(r['betrag_brutto'] for r in ausgang):.2f} EUR")
    print(f"  EINGANG (Geldausgang/Ausgaben-Kandidaten): {len(eingang)}, Summe {sum(r['betrag_brutto'] for r in eingang):.2f} EUR")
    from collections import Counter
    kat_counter = Counter(r['kategorie'] for r in out)
    print("  Kategorien:", dict(kat_counter))
    unklar = [r for r in out if r['kategorie'] == 'UNKLAR']
    print(f"  UNKLAR (-> PRUEFFALL): {len(unklar)}")
    for r in unklar:
        print("   -", r['zahlungsdatum'], r['betrag_brutto'], r['gegenpartei'], '|', r['pruefgrund'])

if __name__ == '__main__':
    main()
