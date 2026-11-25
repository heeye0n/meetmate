from core.evidence import evidence_in_source

SOURCE = "[지은] [오후 9:05] 나 화요일은 5시까지 수업이라 5시 이후 가능"


def test_exact_and_spacing_punctuation_ignored():
    assert evidence_in_source("5시 이후 가능", SOURCE)
    assert evidence_in_source("화요일은 5시까지 수업이라, 5시이후 가능!", SOURCE)


def test_made_up_evidence_rejected():
    assert not evidence_in_source("목요일 저녁 가능", SOURCE)


def test_empty_evidence_rejected():
    assert not evidence_in_source("", SOURCE)
