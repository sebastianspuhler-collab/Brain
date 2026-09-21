"""Geschäftslogik für Prospects: anlegen ohne Dubletten (save_prospect),
bestehende Leads gezielt ergänzen/ändern (update_lead) und Firmenlisten
gegen Vault + Close abgleichen (check_companies). mcp_server.py enthält nur
die dünnen Tool-Wrapper, damit diese Logik ohne MCP-Prozess testbar bleibt.

Leitregeln (Auftrag Sebastian 2026-09-21: "keine Dubletten, aber Leads
müssen updatebar sein, und der Agent muss im Detail korrekt arbeiten"):

1. Keine Dubletten: exakter Treffer (Name/Domain) -> Upsert statt Neuanlage;
   nur ähnlicher Treffer -> nichts schreiben, Rückfrage-Ergebnis (siehe
   dedup.py). Kann Close nicht abgefragt werden, wird NICHTS angelegt.
2. Nichts still überschreiben: Upsert/Update füllt nur leere Felder;
   abweichende Bestandswerte werden gemeldet (nicht_ueberschrieben) und nur
   bei ueberschreiben=True ersetzt. Jede Änderung steht im Ergebnis.
3. Alles vor dem ersten Schreibzugriff validieren (URLs, Status-Labels,
   Quellenpflicht) - kein halb geschriebener Lead wegen eines Tippfehlers.
4. Recherchierte Fakten brauchen eine Quell-URL (Quelle 'Recherche...');
   manuell von Sebastian genannte Angaben nicht.
5. Verdächtige Kontaktdaten (E-Mail passt nicht zum Namen bzw. zur
   Firmendomain) werden nicht blockiert, aber als Warnung zurückgegeben UND
   im Close-Notiztext vermerkt."""
import re
from datetime import datetime
from pathlib import Path

import close_client
import dedup
import name_matching
import vault_kunden
import vault_leads
from close_client import CloseAPIError
from config import get_settings

FACT_FIELDS = ("branche", "mitarbeiter", "umsatz", "ort")
VAULT_STATUSES = ("neu", "kontaktiert", "qualifiziert", "heiss", "verloren", "gewonnen")

# Vault-Feld -> Close-Custom-Field-Name (existiert in diesem Account,
# Stand 2026-09-21). Fehlt ein Feld in Close, wird es übersprungen und
# gemeldet, nie stillschweigend neu angelegt.
_CLOSE_CUSTOM_BY_FIELD = {"branche": "branche", "mitarbeiter": "mitarbeiteranzahl", "umsatz": "umsatz"}

_GENERIC_MAILBOXES = (
    "info", "kontakt", "contact", "office", "mail", "post", "vertrieb", "sales",
    "einkauf", "sekretariat", "zentrale", "buero", "büro", "empfang", "service",
    "verwaltung", "hello", "team", "anfrage", "bestellung", "order", "support",
    "marketing", "personal", "hr", "bewerbung", "buchhaltung", "rechnung",
)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_URL_RE = re.compile(r"^https?://[^\s/]+\.[^\s/]+\S*$", re.IGNORECASE)


# ── Eingabe-Validierung / -Bereinigung ───────────────────────────────────

def normalize_url(value: str) -> str:
    """'' wenn leer; ValueError bei unbrauchbarer URL."""
    v = (value or "").strip()
    if not v:
        return ""
    if not re.match(r"^https?://", v, re.IGNORECASE):
        v = "https://" + v
    if not _URL_RE.match(v):
        raise ValueError(f"'{value}' ist keine gültige URL")
    return v.rstrip("/")


def parse_sources(quellen: str) -> list[str]:
    urls = []
    for part in re.split(r"[\s,;|]+", quellen or ""):
        if not part:
            continue
        urls.append(normalize_url(part))
    return list(dict.fromkeys(urls))


def _needs_sources(quelle: str) -> bool:
    return (quelle or "").strip().lower().startswith("recherche")


def split_name_role(name: str, role: str = "") -> tuple[str, str]:
    """'Hans Muster (Geschäftsführer)' -> ('Hans Muster', 'Geschäftsführer').
    Die Rolle gehört in das Close-Titelfeld, nicht in den Namen."""
    name = (name or "").strip()
    m = re.match(r"^(.*?)\s*\(([^()]+)\)\s*$", name)
    if m and m.group(1):
        name = m.group(1).strip()
        role = role or m.group(2).strip()
    return name, (role or "").strip()


def parse_employee_count(value: str) -> int | None:
    """Nur eindeutige Einzelzahlen ('140', 'ca. 140', '~1.200 Mitarbeiter');
    Spannen ('50-100') liefern None und landen nur im Notiztext."""
    m = re.match(
        r"^\s*(?:ca\.?|circa|rund|~)?\s*(\d{1,3}(?:\.\d{3})+|\d+)\s*(?:mitarbeiter\w*|ma|employees)?\s*$",
        value or "", re.IGNORECASE,
    )
    return int(m.group(1).replace(".", "")) if m else None


def contact_warnings(name: str, email: str, website: str = "") -> list[str]:
    warnings: list[str] = []
    email = (email or "").strip()
    if not email:
        return warnings
    if not _EMAIL_RE.match(email):
        return [f"E-Mail '{email}' hat kein gültiges Format"]
    local = email.split("@")[0].lower()
    generic = any(local == g or local.startswith(g + ".") or local.startswith(g + "-") for g in _GENERIC_MAILBOXES)
    name_tokens = [t for t in re.findall(r"[a-zäöüß]+", (name or "").lower()) if len(t) >= 3]
    if name_tokens and not generic and not any(t in local for t in name_tokens):
        warnings.append(
            f"E-Mail '{email}' passt nicht zum Kontaktnamen '{name}' - evtl. Sekretariat/andere Person, "
            "Zuordnung ungeprüft"
        )
    site, mail = dedup.domain_of(website), dedup.domain_of(email)
    if site and mail and not dedup.domains_match(site, mail):
        warnings.append(f"E-Mail-Domain ({mail}) weicht von der Firmenwebsite ({site}) ab")
    return warnings


class InputError(ValueError):
    pass


def _validate_common(
    quelle: str, quellen: str, facts: dict, website: str,
) -> tuple[str, list[str]]:
    """Prüft URL-Formate + Quellenpflicht; gibt (website_normalisiert, quellen_urls)."""
    try:
        site = normalize_url(website)
        urls = parse_sources(quellen)
    except ValueError as e:
        raise InputError(str(e))
    if facts and _needs_sources(quelle) and not urls:
        raise InputError(
            "Recherchierte Fakten (" + ", ".join(sorted(facts)) + ") brauchen mindestens eine Quell-URL im "
            "Parameter 'quellen' - ohne Beleg nicht speichern. Stammt die Angabe direkt von Sebastian, "
            "quelle auf z.B. 'Sebastian (manuell)' setzen."
        )
    return site, urls


# ── Close-Hilfen ─────────────────────────────────────────────────────────

def _close_custom_payload(facts: dict) -> tuple[dict, list[str], dict]:
    """({vault_key: (custom.<id>, wert)}, Hinweise, nicht_in_close_gespeichert).
    Felder, die es in Close nicht gibt bzw. keine eindeutige Zahl sind,
    landen in dritten Rückgabewert (kommen dann in die Close-Notiz)."""
    payload: dict = {}
    hints: list[str] = []
    skipped: dict = {}
    wanted = {f: facts[f] for f in _CLOSE_CUSTOM_BY_FIELD if facts.get(f)}
    if not wanted:
        return payload, hints, skipped
    fields = close_client.custom_field_ids()
    for vault_key, value in wanted.items():
        meta = fields.get(_CLOSE_CUSTOM_BY_FIELD[vault_key])
        if not meta:
            hints.append(f"Close-Feld '{_CLOSE_CUSTOM_BY_FIELD[vault_key]}' existiert nicht - {vault_key} nur im Vault/Notiz gespeichert")
            skipped[vault_key] = value
            continue
        if meta["type"] == "number":
            number = parse_employee_count(value)
            if number is None:
                hints.append(f"{vault_key} '{value}' ist keine eindeutige Zahl - nur in der Close-Notiz")
                skipped[vault_key] = value
                continue
            payload[vault_key] = (f"custom.{meta['id']}", number)
        else:
            payload[vault_key] = (f"custom.{meta['id']}", value)
    return payload, hints, skipped


def _same_value(key: str, a: str, b: str) -> bool:
    """Gleicher Wert? Websites zählen als gleich, wenn Host (ohne www.) und
    Pfad übereinstimmen - 'https://www.x.de' und 'https://x.de/' sind kein Konflikt."""
    if key == "website":
        return dedup.domain_of(a) == dedup.domain_of(b) and bool(dedup.domain_of(a))
    return (a or "").strip().lower() == (b or "").strip().lower()


def _close_current(close_lead: dict, key: str) -> str:
    if key == "website":
        return (close_lead.get("url") or "").strip()
    if key == "ort":
        for a in close_lead.get("addresses") or []:
            if a.get("city"):
                return a["city"]
        return ""
    custom = close_lead.get("custom") or {}
    name = _CLOSE_CUSTOM_BY_FIELD.get(key)
    if name:
        for k, v in custom.items():
            if k.strip().lower() == name and v not in (None, ""):
                return str(v)
    return ""


def _close_note_text(quelle: str, notiz: str, aehnlich_zu: str, urls: list[str], warnings: list[str], extra_facts: dict) -> str:
    lines = [f"Lead-Agent ({datetime.now().strftime('%Y-%m-%d')}, Quelle: {quelle}):"]
    if notiz:
        lines.append(notiz.strip())
    if aehnlich_zu:
        lines.append(f"Ähnlich zu: {aehnlich_zu}")
    for k, v in extra_facts.items():
        lines.append(f"{k}: {v}")
    if urls:
        lines.append("Quellen: " + ", ".join(urls))
    for w in warnings:
        lines.append(f"⚠ {w}")
    return "\n".join(lines)


def _upsert_contact(close_lead: dict, name: str, role: str, email: str, phone: str, overwrite: bool) -> dict:
    """Legt den Kontakt an bzw. ergänzt einen bestehenden (Match per E-Mail,
    sonst per Name). Gibt {"aktion": ..., "warnungen": [...]} zurück."""
    lead_id = close_lead["id"]
    contacts = close_lead.get("contacts") or []
    email_l = (email or "").strip().lower()
    match = None
    if email_l:
        match = next((c for c in contacts if email_l in [(e.get("email") or "").lower() for e in c.get("emails") or []]), None)
    if not match and name:
        nn = name_matching.normalize(name)
        match = next((c for c in contacts if nn and name_matching.normalize(c.get("name") or "") == nn), None)

    if not match:
        close_client.create_contact(lead_id, name, role, [email] if email else None, [phone] if phone else None)
        return {"aktion": "angelegt", "warnungen": []}

    payload: dict = {}
    warnings: list[str] = []
    if name and (match.get("name") or "").strip() != name:
        if not (match.get("name") or "").strip() or overwrite:
            payload["name"] = name
        else:
            warnings.append(f"Kontakt heißt in Close '{match.get('name')}', nicht '{name}' - Name nicht überschrieben")
    if role and (match.get("title") or "").strip() != role:
        if not (match.get("title") or "").strip() or overwrite:
            payload["title"] = role
        else:
            warnings.append(f"Kontakt-Rolle in Close '{match.get('title')}', nicht '{role}' - nicht überschrieben")
    have_emails = [(e.get("email") or "") for e in match.get("emails") or []]
    if email and email_l not in [e.lower() for e in have_emails]:
        payload["emails"] = [{"email": e, "type": "office"} for e in have_emails] + [{"email": email, "type": "office"}]
    have_phones = [(p.get("phone") or "") for p in match.get("phones") or []]
    if phone and phone not in have_phones:
        payload["phones"] = [{"phone": p, "type": "office"} for p in have_phones] + [{"phone": phone, "type": "office"}]
    if payload:
        close_client.update_contact(match["id"], payload)
        return {"aktion": "aktualisiert", "warnungen": warnings}
    return {"aktion": "unverändert", "warnungen": warnings}


# ── Kernroutine: Änderungen auf bestehenden Lead anwenden ────────────────

def _apply_updates(
    vault_lead: dict | None, close_lead: dict | None, updates: dict, *, urls: list[str],
    overwrite: bool, contact: dict, notiz_text: str, close_status: str, vault_status: str, score: str,
    close_note: str,
) -> dict:
    """Wendet Änderungen auf Vault-Datei und/oder Close-Lead an.
    updates: website/ort/branche/mitarbeiter/umsatz/aehnlich_zu (nur nicht
    leere). Füllt leere Felder, ersetzt Vorhandenes nur bei overwrite=True."""
    geaendert: list[str] = []
    nicht_ueberschrieben: list[str] = []
    hinweise: list[str] = []
    result: dict = {"geaendert": geaendert, "nicht_ueberschrieben": nicht_ueberschrieben}

    # Vault
    if vault_lead:
        path = Path(vault_lead["path"])
        current = vault_lead["fields"]
        vault_updates: dict = {}
        for key, value in updates.items():
            cur = (current.get(key) or "").strip()
            if cur == value or (cur and _same_value(key, cur, value)):
                continue
            if not cur or overwrite:
                vault_updates[key] = value
                geaendert.append(f"vault.{key}: '{cur}' -> '{value}'" if cur else f"vault.{key}: '{value}' gesetzt")
            else:
                nicht_ueberschrieben.append(f"vault.{key}: behalten '{cur}' (vorgeschlagen: '{value}')")
        if urls:
            existing = [u for u in re.split(r"[\s,;|]+", current.get("quellen") or "") if u]
            merged = list(dict.fromkeys(existing + urls))
            if merged != existing:
                vault_updates["quellen"] = " ".join(merged)
                geaendert.append("vault.quellen ergänzt")
        if vault_status:
            vault_updates["status"] = vault_status
            geaendert.append(f"vault.status: '{current.get('status', '')}' -> '{vault_status}'")
        if score:
            vault_updates["score"] = score
            geaendert.append(f"vault.score: '{current.get('score', '')}' -> '{score}'")
        if vault_updates:
            vault_leads.update_fields(path, vault_updates)
        if notiz_text:
            vault_leads.append_note(path, notiz_text)
            geaendert.append("vault: Notiz angehängt")
        if any(contact.get(k) for k in ("name", "email", "phone")):
            parts = [contact.get("name", ""), contact.get("role", "")]
            line = ", ".join(x for x in parts if x)
            extra = " ".join(x for x in (f"<{contact['email']}>" if contact.get("email") else "", contact.get("phone", "")) if x)
            vault_leads.append_note(path, f"Kontakt: {(line + ' ' + extra).strip()}", heading="Kontakte")
            geaendert.append("vault: Kontakt vermerkt")

    # Close
    if close_lead:
        lead_id = close_lead["id"]
        payload: dict = {}
        custom_payload, custom_hints, _ = _close_custom_payload({k: v for k, v in updates.items() if k in _CLOSE_CUSTOM_BY_FIELD})
        hinweise += custom_hints

        if updates.get("website"):
            cur = _close_current(close_lead, "website")
            if not cur or overwrite:
                if cur != updates["website"]:
                    payload["url"] = updates["website"]
                    geaendert.append(f"close.website: '{cur}' -> '{updates['website']}'" if cur else f"close.website: '{updates['website']}' gesetzt")
            elif not _same_value("website", cur, updates["website"]):
                nicht_ueberschrieben.append(f"close.website: behalten '{cur}' (vorgeschlagen: '{updates['website']}')")

        if updates.get("ort"):
            cur = _close_current(close_lead, "ort")
            if not cur or overwrite:
                if cur != updates["ort"]:
                    addresses = [dict(a) for a in (close_lead.get("addresses") or [])]
                    if addresses:
                        addresses[0]["city"] = updates["ort"]
                    else:
                        addresses = [{"label": "business", "city": updates["ort"]}]
                    payload["addresses"] = addresses
                    geaendert.append(f"close.ort: '{cur}' -> '{updates['ort']}'" if cur else f"close.ort: '{updates['ort']}' gesetzt")
            elif cur != updates["ort"]:
                nicht_ueberschrieben.append(f"close.ort: behalten '{cur}' (vorgeschlagen: '{updates['ort']}')")

        for vault_key, (cf_key, value) in custom_payload.items():
            cur = _close_current(close_lead, vault_key)
            if not cur or overwrite:
                if str(cur) != str(value):
                    payload[cf_key] = value
                    geaendert.append(f"close.{vault_key}: '{cur}' -> '{value}'" if cur else f"close.{vault_key}: '{value}' gesetzt")
            elif str(cur) != str(value):
                nicht_ueberschrieben.append(f"close.{vault_key}: behalten '{cur}' (vorgeschlagen: '{value}')")

        if close_status:
            payload["status_id"] = close_status
            geaendert.append(f"close.status: '{close_lead.get('status_label', '')}' -> neu gesetzt")

        if payload:
            close_client.update_lead(lead_id, payload)

        if contact.get("name") or contact.get("email") or contact.get("phone"):
            c = _upsert_contact(close_lead, contact.get("name", ""), contact.get("role", ""), contact.get("email", ""), contact.get("phone", ""), overwrite)
            geaendert.append(f"close.kontakt: {c['aktion']}")
            hinweise += c["warnungen"]

        if close_note:
            close_client.create_note(lead_id, close_note)
            geaendert.append("close: Notiz angelegt")

    if hinweise:
        result["hinweise"] = hinweise
    return result


# ── Auflösen eines bestehenden Leads (streng, keine Zufallstreffer) ──────

def _entity_summary(vault: dict | None, close: dict | None, kunde: dict | None = None) -> dict:
    firma = (
        (close or {}).get("display_name") or (close or {}).get("name")
        or (name_matching.strip_date_prefix(vault["filename"].removesuffix(".md")) if vault else "")
        or (kunde or {}).get("firma", "")
    )
    return {
        "firma": firma,
        "vault_path": vault["filename"] if vault else ((kunde or {}).get("path", "")),
        "close_lead_id": (close or {}).get("id") or ((vault or {}).get("fields", {}).get("close_lead_id") or "") or (kunde or {}).get("close_lead_id", ""),
        "close_status": (close or {}).get("status_label", ""),
    }


def resolve_strict(identifier: str) -> dict:
    """Löst GENAU EINEN Lead auf. Anders als vault_leads.find_lead (erste
    Teilstring-Übereinstimmung) wird bei mehreren Kandidaten nicht geraten,
    sondern {"ok": False, "mehrdeutig": [...]} geliefert - beim Schreiben ist
    ein falscher Treffer schlimmer als eine Rückfrage."""
    ident = (identifier or "").strip()
    if not ident:
        return {"ok": False, "error": "Kein Lead angegeben."}

    if ident.startswith("lead_"):
        close = close_client.get_lead(ident)
        return {"ok": True, "vault": vault_leads.find_lead_by_close_id(ident), "close": close, "kunde": None}

    settings = get_settings()
    direct = settings.vault_path / ident
    if direct.is_file() and direct.suffix == ".md" and settings.leads_dir in direct.resolve().parents:
        vault = vault_leads.read_lead(direct)
        close_id = (vault["fields"].get("close_lead_id") or "").strip()
        return {"ok": True, "vault": vault, "close": close_client.get_lead(close_id) if close_id else None, "kunde": None}

    norm = name_matching.normalize(ident)
    if not norm:
        return {"ok": False, "error": f"'{identifier}' ist kein brauchbarer Firmenname."}

    def name_grade(name: str) -> int:
        n = name_matching.normalize(name)
        if not n:
            return 0
        if n == norm:
            return 2
        shorter, longer = sorted((n, norm), key=len)
        return 1 if len(shorter) >= 4 and shorter in longer else 0

    vault_hits = [(name_grade(name_matching.strip_date_prefix(l["filename"].removesuffix(".md"))), l) for l in vault_leads.list_leads()]
    close_hits = [(name_grade(c.get("display_name") or c.get("name") or ""), c) for c in close_client.find_lead_candidates(dedup.search_terms(ident) + [ident])]
    kunden_hits = [(name_grade(k["firma"]), k) for k in vault_kunden.list_kunden()]

    best = max([g for g, _ in vault_hits + close_hits + kunden_hits] or [0])
    if best == 0:
        return {"ok": False, "error": f"Kein Lead gefunden für '{identifier}' (weder Vault noch Close)."}

    vaults = [l for g, l in vault_hits if g == best]
    closes = [c for g, c in close_hits if g == best]
    kunden = [k for g, k in kunden_hits if g == best]

    entities: dict[str, dict] = {}
    close_by_id = {c["id"]: c for c in closes}
    for v in vaults:
        cid = (v["fields"].get("close_lead_id") or "").strip()
        key = cid or f"vault:{v['filename']}"
        entities[key] = {"vault": v, "close": close_by_id.pop(cid, None) if cid else None, "kunde": None, "cid": cid}
    for cid, c in close_by_id.items():
        entities.setdefault(cid, {"vault": None, "close": c, "kunde": None, "cid": cid})
    for k in kunden:
        cid = (k.get("close_lead_id") or "").strip()
        ent = entities.get(cid) if cid else None
        if ent is not None:
            ent["kunde"] = k
        else:
            entities[cid or f"kunde:{k['path']}"] = {"vault": None, "close": None, "kunde": k, "cid": cid}

    if len(entities) > 1:
        return {
            "ok": False,
            "mehrdeutig": [_entity_summary(e["vault"], e["close"], e["kunde"]) for e in entities.values()],
            "hinweis": "Mehrere passende Leads - mit close_lead_id (lead_...) oder dem vollen Firmennamen erneut aufrufen.",
        }

    ent = next(iter(entities.values()))
    close = ent["close"]
    if not close and ent["cid"]:
        try:
            close = close_client.get_lead(ent["cid"])
        except CloseAPIError:
            close = None
    return {"ok": True, "vault": ent["vault"], "close": close, "kunde": ent["kunde"]}


# ── Öffentliche Operationen ──────────────────────────────────────────────

def _clean_facts(**kw) -> dict:
    return {k: re.sub(r"\s+", " ", (v or "")).strip() for k, v in kw.items() if (v or "").strip()}


def _create_close_lead(
    firma: str, site: str, name: str, role: str, email: str, phone: str, facts: dict,
    quelle: str, notiz: str, aehnlich_zu: str, urls: list[str], warnings: list[str],
) -> dict:
    """Legt den Close-Lead samt Kontakt, nativen Feldern, Custom Fields und
    Startnotiz an. Gibt {"close_lead_id", "close_link", "hinweise"?,
    "close_note_error"?} zurück; wirft CloseAPIError, wenn der Lead selbst
    nicht angelegt werden konnte."""
    custom, hints, skipped = _close_custom_payload(facts)
    contact: dict = {}
    if name:
        contact["name"] = name
    if role:
        contact["title"] = role
    if email:
        contact["emails"] = [{"email": email, "type": "office"}]
    if phone:
        contact["phones"] = [{"phone": phone, "type": "office"}]
    extra: dict = {}
    if site:
        extra["url"] = site
    if facts.get("ort"):
        extra["addresses"] = [{"label": "business", "city": facts["ort"]}]
    lead = close_client.create_lead(
        firma, contacts=[contact] if contact else None,
        custom_fields={cf: val for cf, val in custom.values()} or None, extra=extra or None,
    )
    close_client.tag_lead_source(lead["id"])
    out: dict = {"close_lead_id": lead["id"], "close_link": f"https://app.close.com/lead/{lead['id']}/"}
    try:
        close_client.create_note(lead["id"], _close_note_text(quelle, notiz, aehnlich_zu, urls, warnings, skipped))
    except CloseAPIError as e:
        out["close_note_error"] = str(e)
    if hints:
        out["hinweise"] = hints
    return out


def save_prospect(
    firma: str, kontakt_name: str = "", kontakt_email: str = "", notiz: str = "",
    quelle: str = "Recherche", website: str = "", ort: str = "", branche: str = "",
    mitarbeiter: str = "", umsatz: str = "", kontakt_rolle: str = "", kontakt_telefon: str = "",
    aehnlich_zu: str = "", quellen: str = "", bestaetigt_neu: bool = False,
) -> dict:
    firma = re.sub(r"\s+", " ", firma or "").strip()
    if not firma:
        return {"ok": False, "error": "firma fehlt."}

    facts = _clean_facts(ort=ort, branche=branche, mitarbeiter=mitarbeiter, umsatz=umsatz)
    try:
        site, urls = _validate_common(quelle, quellen, facts, website)
    except InputError as e:
        return {"ok": False, "error": str(e)}

    name, role = split_name_role(kontakt_name, kontakt_rolle)
    email = (kontakt_email or "").strip()
    phone = (kontakt_telefon or "").strip()
    warnings = contact_warnings(name, email, site)

    try:
        matches = dedup.find_matches(firma, site, email)
    except CloseAPIError as e:
        return {
            "ok": False,
            "error": f"Dublettenprüfung nicht möglich, Close nicht erreichbar ({e}). Es wurde NICHTS angelegt.",
        }

    if matches["exakt"]:
        return _upsert_existing(
            matches["exakt"], firma=firma, site=site, facts=facts, urls=urls, name=name, role=role,
            email=email, phone=phone, notiz=notiz, aehnlich_zu=aehnlich_zu, quelle=quelle, warnings=warnings,
        )

    if matches["aehnlich"] and not bestaetigt_neu:
        return {
            "ok": False,
            "duplikat_verdacht": True,
            "aehnliche": matches["aehnlich"],
            "hinweis": (
                "Ähnlich benannte Firmen existieren bereits - es wurde NICHTS angelegt. Ist es dieselbe Firma: "
                "update_lead mit deren close_lead_id nutzen. Ist es eindeutig eine andere Firma (z.B. andere Website/"
                "Ort geprüft): save_prospect mit bestaetigt_neu=True wiederholen."
            ),
        }

    fields = {
        "website": site, "ort": facts.get("ort", ""), "branche": facts.get("branche", ""),
        "mitarbeiter": facts.get("mitarbeiter", ""), "umsatz": facts.get("umsatz", ""),
        "aehnlich_zu": aehnlich_zu.strip(), "quellen": " ".join(urls),
    }
    path = vault_leads.write_prospect(firma, name, email, notiz, quelle, fields=fields, kontakt_rolle=role)
    result: dict = {"ok": True, "aktion": "neu angelegt", "vault_path": str(path.relative_to(get_settings().vault_path))}
    if warnings:
        result["warnungen"] = warnings
    try:
        created = _create_close_lead(firma, site, name, role, email, phone, facts, quelle, notiz, aehnlich_zu, urls, warnings)
        vault_leads.update_fields(path, {"close_lead_id": created["close_lead_id"]})
        result.update(created)
    except CloseAPIError as e:
        result["close_error"] = str(e)
        result["hinweis_close"] = (
            "Vault-Lead ist angelegt, Close nicht. Erneut save_prospect mit derselben Firma aufrufen legt "
            "den Close-Lead nach (kein zweiter Vault-Lead)."
        )
    return result


def _upsert_existing(
    exact: list[dict], *, firma: str, site: str, facts: dict, urls: list[str], name: str, role: str,
    email: str, phone: str, notiz: str, aehnlich_zu: str, quelle: str, warnings: list[str],
) -> dict:
    """save_prospect fand exakt dieselbe Firma -> bestehenden Eintrag
    ergänzen statt eine Dublette anzulegen."""
    target = exact[0]
    vault = vault_leads.find_lead_by_filename(target["vault_path"]) if target["typ"] == "lead" else None
    if not vault and target["close_lead_id"]:
        vault = vault_leads.find_lead_by_close_id(target["close_lead_id"])
    try:
        close = close_client.get_lead(target["close_lead_id"]) if target["close_lead_id"] else None
    except CloseAPIError as e:
        return {"ok": False, "error": f"Bestehender Lead in Close nicht lesbar ({e}) - nichts geändert."}
    if not vault and not close:
        return {
            "ok": False, "treffer": exact,
            "error": "Firma existiert als Kundenordner ohne Vault-Lead und ohne Close-Eintrag - zuerst sync_lead_to_close.",
        }

    updates = {**facts}
    if site:
        updates["website"] = site
    if aehnlich_zu.strip():
        updates["aehnlich_zu"] = aehnlich_zu.strip()
    note_text = _close_note_text(quelle, notiz, aehnlich_zu.strip(), urls, warnings, {}) if (notiz or urls or aehnlich_zu.strip() or warnings) else ""

    out: dict = {}
    try:
        if not close and vault:
            # Vault-Lead ohne Close-Verknüpfung (früherer Close-Fehler) und in
            # Close gibt es keinen Treffer -> Close-Lead jetzt nachziehen.
            merged_facts = {**{k: vault["fields"].get(k, "") for k in ("ort", "branche", "mitarbeiter", "umsatz")}, **facts}
            created = _create_close_lead(
                firma, site or vault["fields"].get("website", ""), name, role, email, phone,
                {k: v for k, v in merged_facts.items() if v}, quelle, notiz, aehnlich_zu, urls, warnings,
            )
            vault_leads.update_fields(Path(vault["path"]), {"close_lead_id": created["close_lead_id"]})
            out.update(created)
            close = None
        applied = _apply_updates(
            vault, close, updates, urls=urls, overwrite=False,
            contact={"name": name, "role": role, "email": email, "phone": phone},
            notiz_text=notiz.strip(), close_status="", vault_status="", score="", close_note=note_text,
        )
    except CloseAPIError as e:
        return {"ok": False, "error": f"Close-Fehler beim Aktualisieren: {e}", "hinweis": "Ein Teil der Änderungen kann bereits geschrieben sein - Lead prüfen."}

    summary = _entity_summary(vault, close)
    if out.get("close_lead_id"):
        summary["close_lead_id"] = out["close_lead_id"]
    result = {
        "ok": True, "aktion": "bereits vorhanden - bestehender Lead aktualisiert (keine Dublette angelegt)",
        **summary, **applied, "treffer": exact,
    }
    for k in ("close_link", "close_note_error"):
        if k in out:
            result[k] = out[k]
    if summary.get("close_lead_id") and "close_link" not in result:
        result["close_link"] = f"https://app.close.com/lead/{summary['close_lead_id']}/"
    if out.get("hinweise"):
        result.setdefault("hinweise", []).extend(out["hinweise"])
    if warnings:
        result["warnungen"] = warnings
    return result


def update_lead(
    lead: str, website: str = "", ort: str = "", branche: str = "", mitarbeiter: str = "",
    umsatz: str = "", kontakt_name: str = "", kontakt_email: str = "", kontakt_rolle: str = "",
    kontakt_telefon: str = "", notiz: str = "", close_status: str = "", status: str = "",
    score: str = "", aehnlich_zu: str = "", quellen: str = "", quelle: str = "Recherche",
    ueberschreiben: bool = False,
) -> dict:
    facts = _clean_facts(ort=ort, branche=branche, mitarbeiter=mitarbeiter, umsatz=umsatz)
    try:
        site, urls = _validate_common(quelle, quellen, facts, website)
    except InputError as e:
        return {"ok": False, "error": str(e)}

    name, role = split_name_role(kontakt_name, kontakt_rolle)
    email = (kontakt_email or "").strip()
    status = (status or "").strip().lower()
    score = (score or "").strip()
    if status and status not in VAULT_STATUSES:
        return {"ok": False, "error": f"status '{status}' ungültig (erlaubt: {', '.join(VAULT_STATUSES)})."}
    if score:
        try:
            float(score.replace(",", "."))
        except ValueError:
            return {"ok": False, "error": f"score '{score}' ist keine Zahl."}
        score = score.replace(",", ".")

    updates = {**facts}
    if site:
        updates["website"] = site
    if aehnlich_zu.strip():
        updates["aehnlich_zu"] = aehnlich_zu.strip()
    contact = {"name": name, "role": role, "email": email, "phone": (kontakt_telefon or "").strip()}
    notiz = (notiz or "").strip()
    if not (updates or urls or any(contact.values()) or notiz or close_status or status or score):
        return {"ok": False, "error": "Nichts zu ändern angegeben."}

    status_id = ""
    if close_status:
        try:
            status_id = close_client.status_id_for(close_status) or ""
            if not status_id:
                labels = [s.get("label") for s in close_client.list_lead_statuses()]
                return {"ok": False, "error": f"Close-Status '{close_status}' existiert nicht. Vorhanden: {', '.join(labels)}."}
        except CloseAPIError as e:
            return {"ok": False, "error": f"Close-Status konnte nicht geprüft werden: {e}"}

    try:
        resolved = resolve_strict(lead)
    except CloseAPIError as e:
        return {"ok": False, "error": f"Close nicht erreichbar: {e}"}
    if not resolved.get("ok"):
        return resolved

    vault, close, kunde = resolved["vault"], resolved["close"], resolved.get("kunde")
    if not vault and not close:
        return {"ok": False, "error": "Lead besteht nur als Kundenordner ohne Close-Eintrag - zuerst sync_lead_to_close."}
    if (status or score) and not vault:
        return {"ok": False, "error": "status/score liegen im Vault-Lead - dieser Lead existiert nur in Close (close_status nutzen)."}

    warnings = contact_warnings(name, email, site or (close or {}).get("url", ""))
    note_text = _close_note_text(quelle, notiz, aehnlich_zu.strip(), urls, warnings, {}) if (notiz or urls or aehnlich_zu.strip() or warnings) else ""

    try:
        applied = _apply_updates(
            vault, close, updates, urls=urls, overwrite=bool(ueberschreiben), contact=contact,
            notiz_text=notiz, close_status=status_id, vault_status=status, score=score, close_note=note_text,
        )
    except CloseAPIError as e:
        return {"ok": False, "error": f"Close-Fehler beim Aktualisieren: {e}", "hinweis": "Ein Teil der Änderungen kann bereits geschrieben sein - Lead prüfen."}

    summary = _entity_summary(vault, close, kunde)
    out = {"ok": True, "aktion": "aktualisiert", **summary, **applied}
    if summary["close_lead_id"]:
        out["close_link"] = f"https://app.close.com/lead/{summary['close_lead_id']}/"
    if not close and vault:
        out.setdefault("hinweise", []).append("Vault-Lead ist nicht mit Close verknüpft - Close wurde nicht geändert (sync_lead_to_close).")
    if warnings:
        out["warnungen"] = warnings
    return out


def check_companies(firmen: list[str], max_live: int = 5) -> dict:
    """Gleicht eine Firmenliste gegen Vault + Close ab. Einträge als
    'Firma' oder 'Firma | website' (auch 'Firma | website | email').
    Bis max_live Firmen live in Close suchen, darüber einmal alle Close-Leads
    laden (Snapshot, dauert beim ersten Mal ~30 s) - schneller als N
    Einzelsuchen."""
    parsed = []
    for raw in firmen or []:
        parts = [p.strip() for p in str(raw).split("|")]
        if parts and parts[0]:
            parts += [""] * (3 - len(parts))
            parsed.append({"eingabe": str(raw), "firma": parts[0], "website": parts[1], "email": parts[2]})
    if not parsed:
        return {"ok": False, "error": "Keine Firmen übergeben."}

    all_close = None
    try:
        if len(parsed) > max_live:
            all_close = close_client.search_leads("", limit=5000, cached=True)
    except CloseAPIError as e:
        return {"ok": False, "error": f"Close nicht erreichbar: {e}"}

    rows = []
    counts = {"vorhanden": 0, "aehnlich": 0, "neu": 0}
    for p in parsed:
        try:
            m = dedup.find_matches(p["firma"], p["website"], p["email"], close_candidates=all_close)
        except CloseAPIError as e:
            return {"ok": False, "error": f"Close nicht erreichbar bei '{p['firma']}': {e}"}
        ergebnis = "vorhanden" if m["exakt"] else "aehnlich" if m["aehnlich"] else "neu"
        counts[ergebnis] += 1
        rows.append({"eingabe": p["eingabe"], "ergebnis": ergebnis, "treffer": m["exakt"] or m["aehnlich"]})
    return {"ok": True, "anzahl": len(rows), "zusammenfassung": counts, "ergebnisse": rows}
