"""Gemeinsame Firmennamen-Normalisierung für den Vault<->Close-Abgleich
(close_audit.py) - verhindert, dass reine Schreibweisen-Unterschiede
("F-Tronic" vs. "f-tronic GmbH", "East Side Fab" vs. "East Side Fab e.V.")
als "kein Treffer" durchgehen. Bewusst simpel (Token-Filter statt
Fuzzy-/Levenshtein-Matching) - für die überschaubare Zahl an Vault-Firmen
(Kunden/-Ordner + Leads/*.md) reicht das, echte Ambiguitäten meldet
close_audit.py ohnehin zur manuellen Bestätigung statt automatisch zu
verknüpfen."""
import re
import unicodedata

_DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")

# "e.V." zerfällt beim Zerlegen in alphanumerische Blöcke in ZWEI
# Ein-Buchstaben-Tokens ("e", "v") - vor dem Tokenisieren als eigenes Muster
# entfernen, sonst würde ein generischer Ein-Buchstaben-Filter auch echte
# Firmennamen wie "K & S" verstümmeln.
_EV_SUFFIX_RE = re.compile(r"\be\.?\s*v\.?\b", re.IGNORECASE)

# Häufige Rechtsformen/Zusätze, die bei einem Namensvergleich ignoriert werden
# sollen - als Tokens nach dem Zerlegen in alphanumerische Blöcke, nicht als
# Teilstring (sonst würde z.B. "AGentur" fälschlich "ag" verlieren).
_LEGAL_TOKENS = {
    "gmbh", "ag", "kg", "kgaa", "ohg", "gbr", "ug", "co", "se",
    "inc", "ltd", "llc", "und",
}


def strip_date_prefix(name: str) -> str:
    """Entfernt ein führendes YYYY-MM-DD- aus Lead-Dateinamen (siehe
    vault_leads.write_prospect) - eigene, öffentliche Funktion statt eines
    Zugriffs auf das private _DATE_PREFIX_RE von außen (close_audit.py)."""
    return _DATE_PREFIX_RE.sub("", name or "")


def fold(name: str) -> str:
    """Kleinschreibung + Umlaut-/Akzent-Faltung ('Günther' == 'Guenther',
    'Karré' == 'Karre'). Ohne das verschwanden Umlaute beim Tokenisieren
    ([a-z0-9]) komplett - 'Günther' wurde zu 'gnther'."""
    name = (name or "").lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    name = unicodedata.normalize("NFKD", name)
    return "".join(ch for ch in name if not unicodedata.combining(ch))


def tokens(name: str) -> list[str]:
    """Namens-Tokens ohne Datumspräfix und Rechtsformen."""
    name = strip_date_prefix(name)
    name = _EV_SUFFIX_RE.sub(" ", name)
    return [t for t in re.findall(r"[a-z0-9]+", fold(name)) if t not in _LEGAL_TOKENS]


def normalize(name: str) -> str:
    return "".join(tokens(name))
