import json
from datetime import date
from pathlib import Path

from core import schedule as sc

MEMBERS = ["민수", "지은", "희연", "도윤"]


def slot(member, day, start, end, type_="available", evidence=""):
    return {"member": member, "day": day, "start": start, "end": end, "type": type_, "evidence": evidence}


def test_overlap_found():
    slots = [slot("A", "TUE", "15:00", "22:00"), slot("B", "TUE", "17:00", "19:00")]
    rec = sc.recommend(sc.build_grid(slots, ["A", "B"]), ["A", "B"], 60)
    assert rec[0]["full"] is True
    assert (rec[0]["day"], rec[0]["start"], rec[0]["end"]) == ("TUE", "17:00", "19:00")
    assert (rec[0]["meeting_start"], rec[0]["meeting_end"]) == ("17:00", "18:00")


def test_no_full_overlap_falls_back_to_n_minus_1():
    slots = [
        slot("A", "MON", "09:00", "12:00"),
        slot("B", "MON", "09:00", "12:00"),
        slot("C", "FRI", "13:00", "15:00"),
    ]
    rec = sc.recommend(sc.build_grid(slots, ["A", "B", "C"]), ["A", "B", "C"], 60)
    assert rec, "N-1 후보가 있어야 함"
    assert all(not r["full"] for r in rec)
    assert rec[0]["missing"] == ["C"]
    assert rec[0]["day"] == "MON"


def test_unavailable_overrides_available():
    slots = [slot("A", "WED", "09:00", "22:00"), slot("A", "WED", "12:00", "18:00", "unavailable")]
    grid = sc.build_grid(slots, ["A"])
    assert "A" in sc.members_at(grid, "WED", "11:30")
    assert "A" not in sc.members_at(grid, "WED", "12:00")
    assert "A" not in sc.members_at(grid, "WED", "17:30")
    assert "A" in sc.members_at(grid, "WED", "18:00")


def test_only_unavailable_means_free_elsewhere():
    slots = [slot("A", "THU", "09:00", "22:00", "unavailable")]
    grid = sc.build_grid(slots, ["A"])
    assert "A" not in sc.members_at(grid, "THU", "10:00")
    assert "A" in sc.members_at(grid, "FRI", "10:00")


def test_silent_member_default_option():
    grid_on = sc.build_grid([], ["A"], default_available=True)
    grid_off = sc.build_grid([], ["A"], default_available=False)
    assert "A" in sc.members_at(grid_on, "MON", "09:00")
    assert "A" not in sc.members_at(grid_off, "MON", "09:00")


def test_boundary_22_and_duration_too_long():
    slots = [slot("A", "SAT", "21:00", "22:00"), slot("B", "SAT", "21:00", "23:30")]
    grid = sc.build_grid(slots, ["A", "B"])
    assert sc.recommend(grid, ["A", "B"], 60)[0]["end"] == "22:00"
    assert [r for r in sc.recommend(grid, ["A", "B"], 90) if r["full"]] == []


def test_kakao_easy_expected_answer():
    data = json.loads(Path("samples/expected_kakao_easy.json").read_text(encoding="utf-8"))
    rec = sc.recommend(sc.build_grid(data["slots"], MEMBERS), MEMBERS, 60)
    exp = data["expected_top1"]
    assert rec[0]["full"] is True
    assert (rec[0]["day"], rec[0]["start"], rec[0]["end"]) == (exp["day"], exp["start"], exp["end"])


def test_validate_slots_cleans_bad_items():
    raw = [
        slot("민수", "tue", "15:00", "23:00"),
        slot("민수", "주말쯤", "15:00", "22:00"),
        slot("지은", "TUE", "19:00", "17:00"),
        slot("철수", "TUE", "10:00", "11:00"),
        {"member": "희연", "day": "수요일", "start": "9:00", "end": "12:00", "type": "available"},
    ]
    slots, warnings = sc.validate_slots(raw, MEMBERS)
    assert slots[0]["day"] == "TUE" and slots[0]["end"] == "22:00"
    assert any(s["member"] == "희연" and s["day"] == "WED" and s["start"] == "09:00" for s in slots)
    assert len(slots) == 2
    assert len(warnings) == 3


def test_next_date_and_ics():
    assert sc.next_date("TUE", date(2026, 11, 25)) == date(2026, 12, 1)
    assert sc.next_date("WED", date(2026, 11, 25)) == date(2026, 11, 25)
    ics = sc.to_ics("팀 회의", date(2026, 12, 1), "18:00", "19:00")
    assert "DTSTART:20261201T180000" in ics and "DTEND:20261201T190000" in ics
    assert ics.startswith("BEGIN:VCALENDAR") and "SUMMARY:팀 회의" in ics
