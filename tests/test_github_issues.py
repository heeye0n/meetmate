from core import github_issues as gh

ACTION = {"task": "API 명세서 정리", "assignee": "희연", "due": "2026-11-30", "due_text": "다음 주 월요일까지",
          "priority": "보통", "evidence": "희연은 API 명세서를 다음 주 월요일까지 정리"}
MEETING = {"date": "2026-11-25", "title": "중간 발표 피드백 회의"}


def test_build_issue():
    title, body = gh.build_issue(ACTION, MEETING)
    assert title == "API 명세서 정리 (~11/30)"
    assert "희연" in body and "2026-11-30" in body and "> 희연은 API 명세서를" in body and "2026-11-25" in body


def test_checklist():
    md = gh.markdown_checklist([ACTION, {**ACTION, "task": "발표 자료", "assignee": "미정", "due": None}])
    assert md.splitlines()[0] == "- [ ] API 명세서 정리 — 희연 · ~11/30"
    assert md.splitlines()[1] == "- [ ] 발표 자료 — 담당 미정 · 마감 미정"


class FakeResp:
    def __init__(self, code, data):
        self.status_code, self._data = code, data
        self.ok = 200 <= code < 300

    def json(self):
        return self._data


def test_create_issue_retries_without_assignee(monkeypatch):
    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append(json)
        if "assignees" in json:
            return FakeResp(422, {"message": "Validation Failed"})
        return FakeResp(201, {"html_url": "https://github.com/o/r/issues/1"})

    monkeypatch.setattr(gh.requests, "post", fake_post)
    ok, result, note = gh.create_issue("o/r", "tok", "t", "b", assignee="nobody")
    assert ok and result.endswith("/issues/1")
    assert len(calls) == 2 and "담당자" in note


def test_create_issue_bad_token(monkeypatch):
    monkeypatch.setattr(gh.requests, "post", lambda *a, **k: FakeResp(401, {}))
    ok, result, _ = gh.create_issue("o/r", "bad", "t", "b")
    assert not ok and "토큰" in result
