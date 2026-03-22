"""
发明意图服务测试
"""

import backend.app.services.invention_intent_service as intent_module
from shared.db.models import PatentDraft


class FakeConversationManager:
    def __init__(self, user_id, llm_provider):
        self.user_id = user_id
        self.llm_provider = llm_provider
        self.session_id = None
        self.extracted_info = {"technical_field": "智能风控"}

    def get_history(self):
        return [
            {"role": "user", "content": "我希望做一种面向风控的异常交易检测方案。"},
            {"role": "assistant", "content": "请补充异常评分和模型更新逻辑。"},
        ]


class FakeIntentExtractor:
    def __init__(self, llm_provider):
        self.llm_provider = llm_provider

    def extract_intent(self, history, extracted_info):
        return {
            "title": "一种异常交易检测方法",
            "technical_field": extracted_info["technical_field"],
            "technical_problem": "现有规则无法及时识别新型欺诈行为。",
            "solution": "结合图特征和异常评分模型识别异常交易。",
            "effect": "提升识别精度并降低误报。",
            "key_steps": ["采集交易图谱", "构建异常评分模型", "动态更新阈值"],
        }


class FakeDocumentGenerator:
    def generate(self, intent):
        return "# 发明意图文档\n\n围绕异常评分、图特征与动态阈值控制展开。"


def test_generate_document_updates_existing_project(monkeypatch, test_db):
    """生成发明意图时应能直接写回现有项目"""
    monkeypatch.setattr(intent_module, "get_database", lambda: test_db)
    monkeypatch.setattr(intent_module, "ConversationManager", FakeConversationManager)
    monkeypatch.setattr(intent_module, "IntentExtractor", FakeIntentExtractor)
    monkeypatch.setattr(intent_module, "DocumentGenerator", FakeDocumentGenerator)

    with test_db.get_session() as session:
        draft = PatentDraft(
            user_id="intent-user",
            patent_type="发明",
            title="未命名专利项目",
            status="draft",
            content={"project_profile": {}, "workflow": {"current_stage": "invention_intent"}},
        )
        session.add(draft)
        session.flush()
        draft_id = draft.id

    service = intent_module.InventionIntentService()
    result = service.generate_document(session_id="session-1", user_id="intent-user", draft_id=draft_id)

    assert result["draft_id"] == draft_id
    assert result["intent"]["title"] == "一种异常交易检测方法"
    assert "# 发明意图文档" in result["document"]

    with test_db.get_session() as session:
        updated = session.query(PatentDraft).filter_by(id=draft_id).first()
        assert updated.title == "一种异常交易检测方法"
        assert updated.content["workflow"]["current_stage"] == "prior_art_search"
        assert updated.content["project_profile"]["technical_field"] == "智能风控"
        assert updated.content["invention_intent"]["technical_problem"] == "现有规则无法及时识别新型欺诈行为。"
