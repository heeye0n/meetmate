"""AI가 붙인 근거 문장이 원문에 실제로 있는지 확인한다 (할루시네이션 방지)."""
import re

_STRIP = re.compile(r"[\s\.,!?~·…'\"“”‘’()\[\]{}:;\-ㅋㅎㅠㅜ]+")


def normalize(text: str) -> str:
    """공백과 문장부호, ㅋㅋ·ㅠㅠ 같은 감탄 자모를 지운다."""
    return _STRIP.sub("", text or "")


def evidence_in_source(evidence: str, source: str) -> bool:
    ev = normalize(evidence)
    return bool(ev) and ev in normalize(source)
