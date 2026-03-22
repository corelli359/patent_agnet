"""
项目草稿公共辅助方法
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Optional

from shared.db.models import PatentDraft, PatentDraftVersion


DOCUMENT_LABELS = {
    "invention_intent_doc": "发明意图文档",
    "search_report": "检索报告",
    "disclosure_doc": "技术交底书",
    "claims": "权利要求书",
    "specification": "说明书",
    "abstract": "摘要",
    "exam_report": "审查报告",
    "repair_strategies": "修复策略",
    "response_opinion": "答复意见书",
    "delivery_package": "交付包",
}

EDITABLE_DOCUMENT_KEYS = {
    "invention_intent_doc",
    "disclosure_doc",
    "claims",
    "specification",
    "abstract",
    "response_opinion",
}

CORE_DRAFT_DOCUMENT_KEYS = {
    "claims",
    "specification",
    "abstract",
}

ACTION_REQUIREMENTS = {
    "generate_disclosure": [
        ("invention_intent", "结构化发明意图"),
        ("invention_intent_doc", "发明意图文档"),
    ],
    "generate_drafting": [
        ("invention_intent", "结构化发明意图"),
        ("disclosure", "技术交底结构"),
        ("disclosure_doc", "技术交底书"),
    ],
    "run_examination": [
        ("claims", "权利要求书"),
        ("specification", "说明书"),
        ("abstract", "摘要"),
    ],
    "generate_repair_strategies": [
        ("claims", "权利要求书"),
        ("specification", "说明书"),
    ],
    "generate_response_opinion": [
        ("claims", "权利要求书"),
        ("specification", "说明书"),
        ("repair_strategies", "修复策略"),
    ],
    "apply_repair_strategies": [
        ("claims", "权利要求书"),
        ("specification", "说明书"),
        ("repair_strategies", "修复策略"),
    ],
}


def normalize_content(content: Optional[Dict]) -> Dict:
    return deepcopy(content) if isinstance(content, dict) else {}


def get_document_label(document_key: str) -> str:
    return DOCUMENT_LABELS.get(document_key, document_key)


def build_snapshot(draft: PatentDraft) -> Dict:
    return {
        "title": draft.title or "",
        "patent_type": draft.patent_type or "",
        "status": draft.status or "",
        "version": draft.version or 1,
        "content": normalize_content(draft.content),
    }


def apply_snapshot(draft: PatentDraft, snapshot: Dict, document_key: Optional[str] = None) -> None:
    snapshot_content = normalize_content(snapshot.get("content"))
    current_content = normalize_content(draft.content)

    if document_key:
        current_content[document_key] = snapshot_content.get(document_key, "")
        draft.content = current_content
        return

    draft.title = snapshot.get("title") or draft.title
    draft.patent_type = snapshot.get("patent_type") or draft.patent_type
    draft.status = snapshot.get("status") or draft.status
    draft.content = snapshot_content


def ensure_version_baseline(session, draft: PatentDraft, change_summary: str = "初始化项目") -> PatentDraftVersion:
    version_number = draft.version or 1
    existing = (
        session.query(PatentDraftVersion)
        .filter_by(draft_id=draft.id, version_number=version_number)
        .first()
    )
    if existing:
        return existing

    version = PatentDraftVersion(
        draft_id=draft.id,
        version_number=version_number,
        title=draft.title,
        patent_type=draft.patent_type,
        status=draft.status,
        document_key="project",
        change_summary=change_summary,
        changed_fields=["project"],
        snapshot=build_snapshot(draft),
    )
    session.add(version)
    session.flush()
    return version


def create_version_record(
    session,
    draft: PatentDraft,
    change_summary: str,
    document_key: str = "project",
    changed_fields: Optional[List[str]] = None,
) -> PatentDraftVersion:
    next_version = (draft.version or 1) + 1
    draft.version = next_version
    version = PatentDraftVersion(
        draft_id=draft.id,
        version_number=next_version,
        title=draft.title,
        patent_type=draft.patent_type,
        status=draft.status,
        document_key=document_key,
        change_summary=change_summary,
        changed_fields=changed_fields or [document_key],
        snapshot=build_snapshot(draft),
    )
    session.add(draft)
    session.add(version)
    session.flush()
    return version


def missing_action_requirements(content: Dict, action_key: str) -> List[str]:
    requirements = ACTION_REQUIREMENTS.get(action_key, [])
    missing = []
    for field_name, label in requirements:
        if not content.get(field_name):
            missing.append(label)
    return missing


def require_action_requirements(content: Dict, action_key: str, action_label: str) -> None:
    missing = missing_action_requirements(content, action_key)
    if missing:
        raise ValueError(f"无法{action_label}，请先补齐：{'、'.join(missing)}。")


def mark_document_update(
    content: Dict,
    document_keys: List[str],
    current_stage: Optional[str] = None,
) -> Dict:
    normalized = normalize_content(content)
    workflow = dict(normalized.get("workflow") or {})

    if any(key in CORE_DRAFT_DOCUMENT_KEYS for key in document_keys):
        workflow["drafting_last_updated_at"] = datetime.now().isoformat()
        workflow["current_stage"] = current_stage or "examination"

    normalized["workflow"] = workflow
    normalized.pop("delivery_package", None)
    return normalized
