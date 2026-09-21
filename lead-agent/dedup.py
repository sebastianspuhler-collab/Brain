"""Dublettenerkennung für neue Prospects (Vault UND Close, Firmenname UND
Domain) - gemeinsamer Baustein für save_prospect/check_companies
(prospects.py).

Zwei Trefferstufen, bewusst getrennt behandelt:
  exakt    - normalisierter Firmenname identisch ODER gleiche Domain
             (Website bzw. geschäftliche E-Mail-Domain). Das IST dieselbe
             Firma: save_prospect legt nichts Neues an, sondern
             aktualisiert den bestehenden Eintrag.
  aehnlich - ein Name enthält den anderen bzw. gleiches erstes Namenswort
             (z.B. "Kaiser GmbH" vs. "Kaiser Elektrotechnik"). Könnte eine
             andere Firma sein: save_prospect legt dann NICHTS an und
             verlangt eine bewusste Entscheidung (bestaetigt_neu bzw.
             update_lead).

Close wird für die Prüfung LIVE abgefragt (nie über den Platten-Snapshot,
siehe close_client.SNAPSHOT_PATH) - ein veralteter Cache würde genau die
Dubletten durchlassen, die diese Prüfung verhindern soll."""
import re
from urllib.parse import urlparse

import close_client
import name_matching
import vault_kunden
import vault_leads

# Diese Domains sagen nichts über die Firma aus - eine gemeinsame gmail.com
# macht zwei Leads nicht zu einer Firma.
FREE_MAIL_DOMAINS = {
    "gmail.com", "googlemail.com", "gmx.de", "gmx.net", "gmx.at", "web.de",
    "t-online.de", "outlook.com", "outlook.de", "hotmail.com", "hotmail.de",
    "yahoo.com", "yahoo.de", "icloud.com", "me.com", "freenet.de", "posteo.de",
    "arcor.de", "aol.com", "live.de", "live.com", "mail.de", "protonmail.com",
    "proton.me", "1und1.de", "online.de", "mailbox.org",
}

_MIN_CONTAINMENT_LEN = 5
_MIN_FIRST_TOKEN_LEN = 6


def domain_of(value: str) -> str:
    """Host einer URL oder E-Mail-Adresse ohne 'www.' ('' wenn keiner
    erkennbar ist oder es eine Freemail-Domain ist)."""
    v = (value or "").strip().lower()
    if not v:
        return ""
    if "@" in v and "//" not in v:
        v = v.rsplit("@", 1)[-1]
    if "//" not in v:
        v = "//" + v
    try:
        host = urlparse(v).hostname or ""
    except ValueError:
        return ""
    host = host.removeprefix("www.").strip(".")
    if "." not in host or host in FREE_MAIL_DOMAINS:
        return ""
    return host


def domains_match(a: str, b: str) -> bool:
    if not a or not b:
        return False
    return a == b or a.endswith("." + b) or b.endswith("." + a)


def significant_tokens(name: str) -> list[str]:
    """Namens-Tokens ohne Rechtsformen/Datumspräfix (gleiche Regeln wie
    name_matching.normalize, inkl. Umlaut-Faltung)."""
    return name_matching.tokens(name)


def _umlaut_variants(text: str) -> list[str]:
    """Close findet 'Karre' zu 'Karré', aber NICHT 'Guenther' zu 'Günther' -
    deshalb beide Schreibweisen als Suchbegriff."""
    out = []
    ascii_ = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    ascii_ = ascii_.replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue")
    if ascii_ != text:
        out.append(ascii_)
    umlaut = re.sub(r"ae", "ä", re.sub(r"oe", "ö", re.sub(r"ue", "ü", text)))
    if umlaut != text:
        out.append(umlaut)
    return out


def search_terms(firma: str) -> list[str]:
    """Live-Suchbegriffe für Close (Close-Suche ist unscharf, die eigentliche
    Entscheidung trifft erst find_matches per Namens-/Domainvergleich):
    Originalschreibweise, Kernname ohne Rechtsform, Umlaut-Varianten und das
    erste Namenswort."""
    original = re.sub(r"\s+", " ", firma or "").strip()
    toks = significant_tokens(firma)
    terms = [original]
    if toks:
        terms.append(" ".join(toks))
        if len(toks[0]) >= 3:
            terms.append(toks[0])
    terms += _umlaut_variants(original)
    return list(dict.fromkeys(t for t in terms if t))


def _lead_domains(close_lead: dict) -> set[str]:
    domains = {domain_of(close_lead.get("url") or "")}
    for c in close_lead.get("contacts") or []:
        for e in c.get("emails") or []:
            domains.add(domain_of(e.get("email") or ""))
    domains.discard("")
    return domains


def _vault_domains(fields: dict) -> set[str]:
    domains = {domain_of(fields.get("website") or "")}
    domains.discard("")
    return domains


def _entities(close_candidates: list[dict]) -> list[dict]:
    """Alle bekannten Firmen als einheitliche Einträge, Vault-Leads und
    Close-Leads über close_lead_id zu EINER Entität verschmolzen."""
    by_key: dict[str, dict] = {}

    for lead in vault_leads.list_leads():
        firma = name_matching.strip_date_prefix(lead["filename"].removesuffix(".md"))
        close_id = (lead["fields"].get("close_lead_id") or "").strip()
        key = close_id or f"vault:{lead['filename']}"
        by_key[key] = {
            "firma": firma, "vault_path": lead["filename"], "typ": "lead",
            "close_lead_id": close_id, "close_status": "",
            "domains": _vault_domains(lead["fields"]),
        }

    for k in vault_kunden.list_kunden():
        close_id = (k.get("close_lead_id") or "").strip()
        key = close_id or f"kunde:{k['path']}"
        ent = by_key.get(key)
        if ent is None:
            by_key[key] = {
                "firma": k["firma"], "vault_path": k["path"], "typ": "kunde",
                "close_lead_id": close_id, "close_status": "", "domains": set(),
            }
        else:
            ent["typ"] = "kunde"
            ent["kunde_pfad"] = k["path"]

    for c in close_candidates:
        cid = c.get("id") or ""
        name = c.get("display_name") or c.get("name") or ""
        ent = by_key.get(cid)
        if ent is None:
            by_key[cid or f"close:{name}"] = {
                "firma": name, "vault_path": "", "typ": "close",
                "close_lead_id": cid, "close_status": c.get("status_label") or "",
                "domains": _lead_domains(c),
            }
        else:
            ent["close_status"] = c.get("status_label") or ""
            ent["domains"] |= _lead_domains(c)
            ent["close_name"] = name

    return list(by_key.values())


def _grade(firma_norm: str, first_token: str, input_domains: set[str], ent: dict) -> tuple[str, str] | None:
    names = {name_matching.normalize(ent["firma"])}
    if ent.get("close_name"):
        names.add(name_matching.normalize(ent["close_name"]))
    names.discard("")

    for n in names:
        if firma_norm and n == firma_norm:
            return "exakt", f"gleicher Firmenname ('{ent.get('close_name') or ent['firma']}')"
    for d in input_domains:
        for ed in ent["domains"]:
            if domains_match(d, ed):
                return "exakt", f"gleiche Domain ({ed})"

    for n in names:
        shorter, longer = sorted((firma_norm, n), key=len)
        if len(shorter) >= _MIN_CONTAINMENT_LEN and shorter in longer:
            return "aehnlich", f"Name enthält '{shorter}'"
    for name in [ent["firma"], ent.get("close_name") or ""]:
        toks = significant_tokens(name)
        if toks and first_token and toks[0] == first_token and len(first_token) >= _MIN_FIRST_TOKEN_LEN:
            return "aehnlich", f"gleiches erstes Namenswort '{first_token}'"
    return None


def find_matches(firma: str, website: str = "", email: str = "", close_candidates: list[dict] | None = None) -> dict:
    """Prüft `firma` gegen Vault (Leads + Kunden) und Close.
    close_candidates=None -> LIVE-Suche in Close (Namen + Domain; wirft
    CloseAPIError, wenn Close nicht erreichbar ist - "keine Treffer" wäre
    dann eine gefährliche Fehlinformation). Für Massenprüfungen kann der
    Aufrufer eine schon geladene Close-Liste übergeben.
    Rückgabe: {"exakt": [...], "aehnlich": [...]} mit je
    {firma, typ, vault_path, close_lead_id, close_status, grund}."""
    input_domains = {d for d in (domain_of(website), domain_of(email)) if d}

    if close_candidates is None:
        queries = search_terms(firma) + sorted(input_domains)
        close_candidates = close_client.find_lead_candidates(queries)

    firma_norm = name_matching.normalize(firma)
    toks = significant_tokens(firma)
    first_token = toks[0] if toks else ""

    result: dict[str, list[dict]] = {"exakt": [], "aehnlich": []}
    for ent in _entities(close_candidates):
        graded = _grade(firma_norm, first_token, input_domains, ent)
        if not graded:
            continue
        grad, grund = graded
        result[grad].append({
            "firma": ent.get("close_name") or ent["firma"], "typ": ent["typ"],
            "vault_path": ent["vault_path"], "close_lead_id": ent["close_lead_id"],
            "close_status": ent["close_status"], "grund": grund,
        })
    return result
