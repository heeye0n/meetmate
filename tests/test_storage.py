from core import storage


def test_save_load_update(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    mid = storage.save_meeting({"date": "2026-11-25", "title": "회의", "actions": [{"task": "A"}, {"task": "B"}]})
    meetings = storage.load_meetings()
    assert len(meetings) == 1 and meetings[0]["actions"][0]["status"] == "할 일"

    assert storage.update_action(mid, 1, status="완료")
    assert storage.load_meetings()[0]["actions"][1]["status"] == "완료"
    assert not storage.update_action(mid, 5, status="완료")

    storage.save_meeting({**storage.load_meetings()[0], "title": "수정"})  # 같은 id → 덮어쓰기
    assert len(storage.load_meetings()) == 1 and storage.load_meetings()[0]["title"] == "수정"

    storage.delete_meeting(mid)
    assert storage.load_meetings() == []


def test_members_mapping(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    storage.save_members({"희연": "heeye0n", "민수": ""})
    assert storage.load_members() == {"희연": "heeye0n"}


def test_broken_file_returns_default(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    (tmp_path / "meetings.json").write_text("{깨진", encoding="utf-8")
    assert storage.load_meetings() == []
