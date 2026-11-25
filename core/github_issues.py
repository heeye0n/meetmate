"""검토한 할 일을 GitHub Issues 로 등록한다. 토큰은 .env 에서만 읽는다."""
from __future__ import annotations

import os
from datetime import date

import requests
from dotenv import load_dotenv

from core.llm import ROOT

API = "https://api.github.com/repos/{repo}/issues"


def get_github_config() -> dict:
    load_dotenv(ROOT / ".env", override=True)
    token = os.getenv("GITHUB_TOKEN", "").strip()
    repo = os.getenv("GITHUB_REPO", "").strip()
    return {"token": token, "repo": repo, "ready": bool(token and repo and "/" in repo)}


def _short(iso: str | None) -> str | None:
    if not iso:
        return None
    d = date.fromisoformat(iso)
    return f"{d.month}/{d.day}"


def build_issue(action: dict, meeting: dict) -> tuple[str, str]:
    due = _short(action.get("due"))
    title = action["task"] + (f" (~{due})" if due else "")
    due_line = action.get("due") or "미정"
    if action.get("due_text"):
        due_line += f" ({action['due_text']})"
    body = "\n".join([
        f"**담당**: {action.get('assignee') or '미정'}",
        f"**마감**: {due_line}",
        f"**우선순위**: {action.get('priority', '보통')}",
        f"**회의**: {meeting.get('date', '')} {meeting.get('title', '')}".rstrip(),
        "",
        "**근거 (회의록 원문)**",
        f"> {action.get('evidence', '')}",
        "",
        "---",
        "_MeetMate에서 자동 생성_",
    ])
    return title, body


def markdown_checklist(actions: list[dict]) -> str:
    lines = []
    for a in actions:
        who = a.get("assignee") if a.get("assignee") not in (None, "", "미정") else "담당 미정"
        due = _short(a.get("due"))
        lines.append(f"- [ ] {a['task']} — {who} · {'~' + due if due else '마감 미정'}")
    return "\n".join(lines)


def create_issue(repo: str, token: str, title: str, body: str,
                 labels: list[str] | None = None, assignee: str | None = None) -> tuple[bool, str, str]:
    """반환: (성공 여부, 이슈 URL 또는 실패 이유, 참고 메모)"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels
    if assignee and assignee != "미정":
        payload["assignees"] = [assignee]

    note = ""
    try:
        resp = requests.post(API.format(repo=repo), headers=headers, json=payload, timeout=30)
        if resp.status_code == 422 and ("assignees" in payload or "labels" in payload):
            payload.pop("assignees", None)
            payload.pop("labels", None)
            note = "담당자나 라벨을 지정할 수 없어 빼고 등록했어요. (GitHub 아이디·저장소 권한 확인)"
            resp = requests.post(API.format(repo=repo), headers=headers, json=payload, timeout=30)
    except requests.RequestException:
        return False, "GitHub에 연결하지 못했어요. 인터넷 연결을 확인하세요.", ""

    if resp.ok:
        return True, resp.json().get("html_url", ""), note
    reasons = {
        401: "GitHub 토큰이 올바르지 않거나 만료됐어요. .env 의 GITHUB_TOKEN 을 확인하세요.",
        403: "토큰에 이 저장소의 이슈를 만들 권한이 없어요 (repo 권한 필요).",
        404: f"저장소 '{repo}'를 찾을 수 없어요. GITHUB_REPO 이름과 토큰 권한을 확인하세요.",
        410: "이 저장소는 이슈 기능이 꺼져 있어요.",
    }
    return False, reasons.get(resp.status_code, f"GitHub 오류 (HTTP {resp.status_code})"), note
