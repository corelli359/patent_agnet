"""
单人可用 P0 流程守卫测试
"""

import pytest

import backend.app.services.disclosure_service as disclosure_module
import backend.app.services.patent_drafting_service as drafting_module
import backend.app.services.examination_service as examination_module
import backend.app.services.patent_repair_service as repair_module
from shared.db.models import PatentDraft


class DummyLLMClient:
    def chat(self, messages, **kwargs):
        return "dummy"


class DummyGuidelineKB:
    def retrieve(self, topic, context_text="", top_k=3):
        return []

    def format_passages(self, passages):
        return ""


class DummySearchService:
    def search(self, **kwargs):
        return {"result_count": 0, "results": []}


def test_disclosure_generation_requires_intent(monkeypatch, test_db):
    monkeypatch.setattr(disclosure_module, "get_database", lambda: test_db)
    monkeypatch.setattr(disclosure_module, "get_llm_client", lambda provider="deepseek": DummyLLMClient())

    with test_db.get_session() as session:
        draft = PatentDraft(user_id="guard-user", patent_type="发明", title="空白项目", status="draft", content={})
        session.add(draft)
        session.flush()
        draft_id = draft.id

    service = disclosure_module.DisclosureService()
    with pytest.raises(ValueError, match="无法生成技术交底书"):
        service.generate_from_intent(draft_id)


def test_drafting_generation_requires_disclosure(monkeypatch, test_db):
    monkeypatch.setattr(drafting_module, "get_database", lambda: test_db)
    monkeypatch.setattr(drafting_module, "get_llm_client", lambda provider="deepseek": DummyLLMClient())

    with test_db.get_session() as session:
        draft = PatentDraft(
            user_id="guard-user",
            patent_type="发明",
            title="只有意图没有交底",
            status="draft",
            content={"invention_intent": {"title": "只有意图没有交底"}},
        )
        session.add(draft)
        session.flush()
        draft_id = draft.id

    service = drafting_module.PatentDraftingService()
    with pytest.raises(ValueError, match="无法生成专利申请文件"):
        service.generate_patent_files(draft_id)


def test_examination_requires_core_documents(monkeypatch, test_db):
    monkeypatch.setattr(examination_module, "get_database", lambda: test_db)
    monkeypatch.setattr(examination_module, "get_llm_client", lambda provider="deepseek": DummyLLMClient())
    monkeypatch.setattr(examination_module, "PatentGuidelineKnowledgeBase", lambda: DummyGuidelineKB())
    monkeypatch.setattr(examination_module, "PatentSearchService", lambda: DummySearchService())

    with test_db.get_session() as session:
        draft = PatentDraft(
            user_id="guard-user",
            patent_type="发明",
            title="缺少说明书",
            status="draft",
            content={"claims": "# 权利要求书\n\n1. 一种方法，其特征在于，包括采集数据。"},
        )
        session.add(draft)
        session.flush()
        draft_id = draft.id

    service = examination_module.ExaminationService()
    with pytest.raises(ValueError, match="无法执行审查"):
        service.examine(draft_id)


def test_repair_response_requires_strategies(monkeypatch, test_db):
    monkeypatch.setattr(repair_module, "get_database", lambda: test_db)
    monkeypatch.setattr(repair_module, "get_llm_client", lambda provider="deepseek": DummyLLMClient())

    with test_db.get_session() as session:
        draft = PatentDraft(
            user_id="guard-user",
            patent_type="发明",
            title="待答复项目",
            status="draft",
            content={
                "claims": "# 权利要求书\n\n1. 一种方法，其特征在于，包括采集数据。",
                "specification": "# 说明书\n\n[0001] 本发明涉及数据处理领域。",
            },
        )
        session.add(draft)
        session.flush()
        draft_id = draft.id

    service = repair_module.PatentRepairService()
    with pytest.raises(ValueError, match="无法生成答复意见书"):
        service.generate_response(
            issues=[{"id": 1, "type": "clarity", "description": "术语不清楚"}],
            strategies=[],
            draft_id=draft_id,
        )


def test_apply_repair_requires_persisted_strategies(monkeypatch, test_db):
    monkeypatch.setattr(repair_module, "get_database", lambda: test_db)
    monkeypatch.setattr(repair_module, "get_llm_client", lambda provider="deepseek": DummyLLMClient())

    with test_db.get_session() as session:
        draft = PatentDraft(
            user_id="guard-user",
            patent_type="发明",
            title="未形成策略项目",
            status="draft",
            content={
                "claims": "# 权利要求书\n\n1. 一种方法，其特征在于，包括采集数据。",
                "specification": "# 说明书\n\n[0001] 本发明涉及数据处理领域。",
            },
        )
        session.add(draft)
        session.flush()
        draft_id = draft.id

    service = repair_module.PatentRepairService()
    with pytest.raises(ValueError, match="无法应用修复策略"):
        service.apply_strategies(draft_id)
