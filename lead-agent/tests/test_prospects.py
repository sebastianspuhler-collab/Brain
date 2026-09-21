import prospects
import vault_leads

RECHERCHE = dict(quelle="Recherche", quellen="https://www.pollmann-elektrotechnik.de/unternehmen")


def _vault_files(vault):
    return sorted(p.name for p in (vault / "Leads").rglob("*.md"))


# ── Neuanlage ────────────────────────────────────────────────────────────

def test_new_prospect_creates_vault_and_close_with_structured_fields(vault, close):
    r = prospects.save_prospect(
        "Muster Elektrotechnik GmbH", kontakt_name="Max Muster (Geschäftsführer)", kontakt_email="max.muster@muster-elektro.de",
        notiz="Passt wegen ERP-Einkauf", website="muster-elektro.de", ort="Kassel", branche="Elektrotechnik",
        mitarbeiter="~140", umsatz="10-50 Mio", aehnlich_zu="F-Tronic",
        quellen="https://muster-elektro.de/ueber-uns", **{"quelle": "Recherche"},
    )
    assert r["ok"] and r["aktion"] == "neu angelegt"
    assert r["close_lead_id"].startswith("lead_")

    lead = close.leads[r["close_lead_id"]]
    assert lead["url"] == "https://muster-elektro.de"
    assert lead["addresses"] == [{"label": "business", "city": "Kassel"}]
    assert lead["custom"] == {"Branche": "Elektrotechnik", "Mitarbeiteranzahl": 140, "Umsatz": "10-50 Mio"}
    contact = lead["contacts"][0]
    assert contact["name"] == "Max Muster" and contact["title"] == "Geschäftsführer"
    assert "warnungen" not in r
    # Startnotiz mit Quelle + Begründung in Close
    assert any("Passt wegen ERP-Einkauf" in t and "https://muster-elektro.de/ueber-uns" in t for _, t in close.notes)

    stored = vault_leads.find_lead_by_close_id(r["close_lead_id"])
    f = stored["fields"]
    assert (f["website"], f["ort"], f["branche"], f["mitarbeiter"], f["aehnlich_zu"]) == (
        "https://muster-elektro.de", "Kassel", "Elektrotechnik", "~140", "F-Tronic")
    assert f["quellen"] == "https://muster-elektro.de/ueber-uns"


def test_researched_facts_without_source_url_are_rejected_and_nothing_written(vault, close):
    r = prospects.save_prospect("Ohne Beleg GmbH", branche="Werkzeugbau", mitarbeiter="200")
    assert r["ok"] is False and "Quell-URL" in r["error"]
    assert _vault_files(vault) == [] and close.calls == []


def test_manual_source_needs_no_url(vault, close):
    r = prospects.save_prospect("Messe GmbH", kontakt_name="Eva Test", branche="Metallbau", quelle="Sebastian (manuell)")
    assert r["ok"] and r["aktion"] == "neu angelegt"


def test_invalid_website_is_rejected_before_any_write(vault, close):
    r = prospects.save_prospect("Kaputt GmbH", website="nicht gültig", **RECHERCHE)
    assert r["ok"] is False
    assert _vault_files(vault) == [] and close.calls == []


def test_contact_email_not_matching_name_produces_warning_in_result_and_close_note(vault, close):
    r = prospects.save_prospect(
        "Pollmann Elektrotechnik GmbH", kontakt_name="Hans-Joachim Pollmann (Geschäftsführer)",
        kontakt_email="sabine.schroeder@pollmann-elektrotechnik.de", website="https://www.pollmann-elektrotechnik.de",
    )
    assert r["ok"]
    assert any("passt nicht zum Kontaktnamen" in w for w in r["warnungen"])
    assert any("⚠" in t and "sabine.schroeder" in t for _, t in close.notes)


def test_generic_mailbox_and_matching_name_give_no_warning():
    assert prospects.contact_warnings("Max Muster", "info@muster.de", "muster.de") == []
    assert prospects.contact_warnings("Max Muster", "m.muster@muster.de", "muster.de") == []
    assert prospects.contact_warnings("Max Muster", "max@andere-domain.de", "muster.de") != []


# ── Keine Dubletten ──────────────────────────────────────────────────────

def test_exact_name_match_updates_existing_close_lead_instead_of_creating(vault, close):
    existing = close.add_lead("Kaiser GmbH & Co. KG", custom={"Branche": "Elektro"})
    r = prospects.save_prospect(
        "Kaiser GmbH & Co KG", website="kaiser-elektro.de", branche="Metallbau", **RECHERCHE,
    )
    assert r["ok"] and "bereits vorhanden" in r["aktion"]
    assert r["close_lead_id"] == existing["id"]
    assert close.writes("create_lead") == []
    assert len(close.leads) == 1
    assert existing["url"] == "https://kaiser-elektro.de"          # leeres Feld gefüllt
    assert existing["custom"]["Branche"] == "Elektro"               # Bestehendes NICHT überschrieben
    assert any("close.branche" in x for x in r["nicht_ueberschrieben"])


def test_same_domain_with_different_name_is_the_same_company(vault, close):
    existing = close.add_lead("Alte Firmenbezeichnung", url="https://www.beispiel-technik.de")
    r = prospects.save_prospect("Beispiel Technik Neu GmbH", website="beispiel-technik.de")
    assert "bereits vorhanden" in r["aktion"] and r["close_lead_id"] == existing["id"]
    assert close.writes("create_lead") == []


def test_similar_name_blocks_creation_until_confirmed(vault, close):
    close.add_lead("Kaiser Elektrotechnik GmbH", url="https://kaiser-elektrotechnik.de")
    r = prospects.save_prospect("Kaiser Maschinenbau GmbH", website="kaiser-maschinenbau.de")
    assert r["ok"] is False and r["duplikat_verdacht"] is True
    assert r["aehnliche"][0]["firma"] == "Kaiser Elektrotechnik GmbH"
    assert _vault_files(vault) == [] and close.writes("create_lead") == []

    r2 = prospects.save_prospect("Kaiser Maschinenbau GmbH", website="kaiser-maschinenbau.de", bestaetigt_neu=True)
    assert r2["ok"] and r2["aktion"] == "neu angelegt"
    assert len(close.leads) == 2


def test_saving_same_prospect_twice_creates_only_one_lead_and_one_vault_file(vault, close):
    a = prospects.save_prospect("Doppelt GmbH", website="doppelt.de", kontakt_name="Anna Test", kontakt_email="anna.test@doppelt.de")
    b = prospects.save_prospect("Doppelt GmbH", website="doppelt.de", notiz="zweiter Lauf")
    assert a["aktion"] == "neu angelegt" and "bereits vorhanden" in b["aktion"]
    assert len(close.leads) == 1
    assert len(_vault_files(vault)) == 1


def test_close_unreachable_blocks_creation_completely(vault, close):
    close.down = True
    r = prospects.save_prospect("Offline GmbH")
    assert r["ok"] is False and "NICHTS angelegt" in r["error"]
    assert _vault_files(vault) == []


def test_vault_lead_without_close_link_gets_close_lead_added_not_second_vault_file(vault, close):
    path = vault_leads.write_prospect("Halbfertig GmbH")
    assert vault_leads.read_lead(path)["fields"]["close_lead_id"] == ""
    r = prospects.save_prospect("Halbfertig GmbH", website="halbfertig.de")
    assert r["ok"] and r["close_lead_id"].startswith("lead_")
    assert len(_vault_files(vault)) == 1
    assert vault_leads.read_lead(path)["fields"]["close_lead_id"] == r["close_lead_id"]


def test_write_prospect_never_overwrites_existing_file(vault):
    p1 = vault_leads.write_prospect("Gleich GmbH", notiz="erste")
    p2 = vault_leads.write_prospect("Gleich GmbH", notiz="zweite")
    assert p1 != p2 and "erste" in p1.read_text(encoding="utf-8")


# ── Updates ──────────────────────────────────────────────────────────────

def test_update_lead_fills_empty_fields_in_vault_and_close_and_reports_changes(vault, close):
    r0 = prospects.save_prospect("Update GmbH", website="update-gmbh.de")
    r = prospects.update_lead(r0["close_lead_id"], ort="Köln", branche="Elektro", mitarbeiter="85", quellen="https://update-gmbh.de/impressum", notiz="Anruf geplant")
    assert r["ok"]
    lead = close.leads[r0["close_lead_id"]]
    assert lead["addresses"][0]["city"] == "Köln" and lead["custom"]["Mitarbeiteranzahl"] == 85
    assert vault_leads.find_lead_by_close_id(r0["close_lead_id"])["fields"]["ort"] == "Köln"
    assert any("close.ort" in c for c in r["geaendert"])
    assert any("Anruf geplant" in t for _, t in close.notes)


def test_update_lead_does_not_overwrite_unless_asked(vault, close):
    lead = close.add_lead("Fest GmbH", url="https://alt.de")
    r = prospects.update_lead(lead["id"], website="https://neu.de", quelle="Sebastian (manuell)")
    assert lead["url"] == "https://alt.de" and r["nicht_ueberschrieben"]
    r2 = prospects.update_lead(lead["id"], website="https://neu.de", quelle="Sebastian (manuell)", ueberschreiben=True)
    assert lead["url"] == "https://neu.de" and any("close.website" in c for c in r2["geaendert"])


def test_update_lead_sets_valid_close_status_and_rejects_unknown(vault, close):
    lead = close.add_lead("Status GmbH")
    ok = prospects.update_lead(lead["id"], close_status="termin vereinbart")
    assert ok["ok"] and lead["status_label"] == "Termin vereinbart"
    bad = prospects.update_lead(lead["id"], close_status="Heiß")
    assert bad["ok"] is False and "Nicht erreicht" in bad["error"]


def test_update_lead_adds_new_contact_and_extends_existing_by_email(vault, close):
    lead = close.add_lead("Kontakt GmbH", contacts=[{"id": "cont_x", "name": "Eva Alt", "emails": [{"email": "eva@k.de"}], "phones": []}])
    prospects.update_lead(lead["id"], kontakt_name="Eva Alt", kontakt_email="eva@k.de", kontakt_rolle="Einkaufsleiterin", kontakt_telefon="0561 123")
    c = lead["contacts"][0]
    assert c["title"] == "Einkaufsleiterin" and c["phones"] == [{"phone": "0561 123", "type": "office"}]
    prospects.update_lead(lead["id"], kontakt_name="Neu Person", kontakt_email="neu.person@k.de", quelle="Sebastian (manuell)")
    assert len(lead["contacts"]) == 2


def test_update_lead_ambiguous_name_returns_candidates_and_writes_nothing(vault, close):
    a = close.add_lead("Bock Maschinenbau GmbH")
    close.add_lead("Bock Metallbau GmbH")
    r = prospects.update_lead("Bock", notiz="x")
    assert r["ok"] is False and len(r["mehrdeutig"]) == 2
    assert close.writes("create_note") == []
    assert prospects.update_lead(a["id"], notiz="klar")["ok"]


def test_update_lead_rejects_bad_vault_status_and_empty_update(vault, close):
    lead = close.add_lead("X GmbH")
    assert prospects.update_lead(lead["id"], status="super")["ok"] is False
    assert prospects.update_lead(lead["id"])["ok"] is False


def test_update_lead_status_and_score_on_vault_lead(vault, close):
    r0 = prospects.save_prospect("Score GmbH")
    r = prospects.update_lead(r0["close_lead_id"], status="qualifiziert", score="8,5")
    assert r["ok"]
    f = vault_leads.find_lead_by_close_id(r0["close_lead_id"])["fields"]
    assert (f["status"], f["score"]) == ("qualifiziert", "8.5")


# ── Abgleich ─────────────────────────────────────────────────────────────

def test_check_companies_classifies_vorhanden_aehnlich_neu(vault, close):
    close.add_lead("F-Tronic GmbH", url="https://f-tronic.de")
    close.add_lead("Kaiser Elektrotechnik GmbH")
    r = prospects.check_companies(["f-tronic", "Kaiser Maschinenbau GmbH", "Ganz Neu AG", "Anders | https://f-tronic.de"])
    res = {x["eingabe"]: x["ergebnis"] for x in r["ergebnisse"]}
    assert res == {"f-tronic": "vorhanden", "Kaiser Maschinenbau GmbH": "aehnlich", "Ganz Neu AG": "neu", "Anders | https://f-tronic.de": "vorhanden"}
    assert r["zusammenfassung"] == {"vorhanden": 2, "aehnlich": 1, "neu": 1}


def test_check_companies_reports_close_outage_instead_of_all_new(vault, close):
    close.down = True
    assert prospects.check_companies(["A GmbH"])["ok"] is False


def test_parse_employee_count():
    assert prospects.parse_employee_count("~140") == 140
    assert prospects.parse_employee_count("ca. 1.200 Mitarbeiter") == 1200
    assert prospects.parse_employee_count("50-100") is None


def test_www_and_trailing_slash_differences_are_not_reported_as_conflict(vault, close):
    lead = close.add_lead("Gleiche Site GmbH", url="https://gleiche-site.de")
    r = prospects.update_lead(lead["id"], website="https://www.gleiche-site.de/", quelle="Sebastian (manuell)")
    assert r["ok"] and r["nicht_ueberschrieben"] == [] and lead["url"] == "https://gleiche-site.de"


# ── Korrekturen ──────────────────────────────────────────────────────────

def test_summary_is_replaced_only_with_overwrite_and_other_sections_survive(vault, close):
    r0 = prospects.save_prospect("Korrektur GmbH", kontakt_name="Anna Alt", notiz="ALTE FALSCHE ANGABE 999 MA")
    lid = r0["close_lead_id"]
    soft = prospects.update_lead(lid, zusammenfassung="Neu belegt: 120 MA", quelle="Sebastian (manuell)")
    assert soft["nicht_ueberschrieben"] and "ALTE FALSCHE" in vault_leads.find_lead_by_close_id(lid)["body"]

    hard = prospects.update_lead(lid, zusammenfassung="Neu belegt: 120 MA", quelle="Sebastian (manuell)", ueberschreiben=True)
    body = vault_leads.find_lead_by_close_id(lid)["body"]
    assert hard["ok"] and "ALTE FALSCHE" not in body and "Neu belegt: 120 MA" in body
    assert "## Kontakt" in body and "Anna Alt" in body          # anderer Abschnitt unberührt
    assert body.count("## Zusammenfassung") == 1


def test_wrong_email_can_be_removed_from_contact_and_vault_text(vault, close):
    r0 = prospects.save_prospect("Pollmann Test GmbH", kontakt_name="Hans Pollmann (Geschäftsführer)", kontakt_email="sabine.schroeder@pollmann-test.de")
    lid = r0["close_lead_id"]
    r = prospects.update_lead(lid, kontakt_email_entfernen="sabine.schroeder@pollmann-test.de", quelle="Sebastian (manuell)")
    assert r["ok"] and any("entfernt" in c for c in r["geaendert"])
    assert close.leads[lid]["contacts"][0]["emails"] == []
    assert "sabine.schroeder@" not in vault_leads.find_lead_by_close_id(lid)["body"]
    prospects.update_lead(lid, kontakt_name="Sabine Schröder", kontakt_email="sabine.schroeder@pollmann-test.de", quelle="Sebastian (manuell)")
    assert [c["name"] for c in close.leads[lid]["contacts"]] == ["Hans Pollmann", "Sabine Schröder"]


def test_replace_section_creates_missing_section(tmp_path):
    f = tmp_path / "x.md"
    f.write_text("---\na: b\n---\n\n# X\n\n## Kontakt\nAlt\n", encoding="utf-8")
    assert vault_leads.replace_section(f, "Kontakt", "Neu") is True
    assert vault_leads.replace_section(f, "Zusammenfassung", "Text") is False
    assert "Alt" not in f.read_text() and "## Zusammenfassung\nText" in f.read_text()


def test_contact_matching_ignores_role_in_existing_name_and_fixes_it_on_overwrite(vault, close):
    lead = close.add_lead("Rolle GmbH", contacts=[{"id": "cont_r", "name": "Holger Ditzer (Einkaufsleiter)", "emails": [{"email": "holger.ditzer@rolle.de"}], "phones": []}])
    prospects.update_lead(lead["id"], kontakt_name="Holger Ditzer", kontakt_rolle="Einkaufsleitung", quelle="Sebastian (manuell)", ueberschreiben=True)
    assert len(lead["contacts"]) == 1
    assert lead["contacts"][0]["name"] == "Holger Ditzer" and lead["contacts"][0]["title"] == "Einkaufsleitung"


def test_source_urls_with_commas_survive_parsing():
    url = "https://www.northdata.com/Pollmann%20Elektrotechnik%20GmbH,%20Oelde/Amtsgericht%20M%C3%BCnster%20HRB%207463"
    assert prospects.parse_sources(f"https://a.de/x, {url}, https://b.de") == ["https://a.de/x", url, "https://b.de"]


def test_email_removal_does_not_touch_newly_written_summary(vault, close):
    r0 = prospects.save_prospect("Reihenfolge GmbH", kontakt_name="Hans Alt", kontakt_email="falsch@reihenfolge.de", website="reihenfolge.de")
    lid = r0["close_lead_id"]
    prospects.update_lead(lid, kontakt_email_entfernen="falsch@reihenfolge.de", zusammenfassung="Die Adresse falsch@reihenfolge.de war falsch zugeordnet.",
                          quelle="Sebastian (manuell)", ueberschreiben=True)
    body = vault_leads.find_lead_by_close_id(lid)["body"]
    assert "Die Adresse falsch@reihenfolge.de war falsch zugeordnet." in body
