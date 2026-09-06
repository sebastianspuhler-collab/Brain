import name_matching as svc


def test_normalize_matches_hyphen_vs_space_and_legal_suffix():
    assert svc.normalize("F-Tronic") == svc.normalize("f-tronic GmbH")


def test_normalize_matches_ev_suffix_variant():
    assert svc.normalize("East Side Fab") == svc.normalize("East Side Fab e.V.")


def test_normalize_strips_date_prefix():
    assert svc.normalize("2026-08-10-Silas-Rupp") == svc.normalize("Silas Rupp")


def test_normalize_different_companies_stay_different():
    assert svc.normalize("Schaufler") != svc.normalize("Schauenberg")


def test_normalize_is_case_insensitive():
    assert svc.normalize("SCHAUFLER TOOLING GMBH") == svc.normalize("schaufler tooling")


def test_strip_date_prefix_only_removes_leading_date():
    assert svc.strip_date_prefix("2026-09-06-Muster-GmbH") == "Muster-GmbH"
    assert svc.strip_date_prefix("Muster-GmbH") == "Muster-GmbH"
