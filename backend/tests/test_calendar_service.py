import re


def _extract_title(line: str) -> str:
    return re.sub(r"^\s*-\s*\[[ xX]?\]\s*", "", line.split("(")[0]).strip()


def test_checkbox_prefix_stripped_without_mangling_title():
    line = "- [ ] Webinar 5. Juli 2026 vorbereiten (DEADLINE: 5.7.)"
    assert _extract_title(line) == "Webinar 5. Juli 2026 vorbereiten"


def test_done_checkbox_prefix_stripped():
    line = "- [x] Angebot fixieren (5.7.)"
    assert _extract_title(line) == "Angebot fixieren"


def test_spaces_and_x_letters_preserved_in_title():
    line = "- [ ] Nexus Fixkosten prüfen (5.7.)"
    title = _extract_title(line)
    assert title == "Nexus Fixkosten prüfen"
    assert " " in title
