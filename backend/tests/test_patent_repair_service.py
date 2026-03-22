"""
专利修复服务测试
"""

import backend.app.services.patent_repair_service as repair_module
from shared.db.models import PatentDraft


class FakeLLMClient:
    def __init__(self):
        self.calls = []

    def chat(self, messages, temperature=0.3, max_tokens=2000, **kwargs):
        prompt = messages[0]["content"]
        self.calls.append(prompt)
        if "生成审查意见答复书" in prompt:
            return "# 答复意见书\n\n已逐条回应审查意见。"
        return '{"issue_id": 1, "solutions": [{"name": "方案1：保守修改", "modifications": [{"location": "权利要求1", "original": "原表述", "modified": "修订表述", "reason": "增强清楚性"}], "pros": "改动小", "cons": "保护范围收缩"}]}'


def test_generate_strategies_apply_and_response_persist_to_draft(monkeypatch, test_db):
    """修复策略、修订稿和答复意见书应写回当前草稿内容"""
    fake_client = FakeLLMClient()
    monkeypatch.setattr(repair_module, "get_database", lambda: test_db)
    monkeypatch.setattr(repair_module, "get_llm_client", lambda provider="deepseek": fake_client)

    with test_db.get_session() as session:
        draft = PatentDraft(
            user_id="repair-user",
            patent_type="发明",
            title="一种图像识别方法",
            status="draft",
            content={
                "claims": "# 权利要求书\n\n1. 一种图像识别方法，其特征在于，包括获取待识别图像。",
                "specification": "# 说明书\n\n[0001] 本发明涉及图像识别领域。",
            },
        )
        session.add(draft)
        session.flush()
        draft_id = draft.id

    service = repair_module.PatentRepairService()
    issues = [
        {
            "id": 1,
            "type": "clarity",
            "severity": "serious",
            "location": "权利要求1",
            "description": "术语表述不够清楚",
            "examiner_opinion": "请明确关键术语的边界。",
        }
    ]

    strategies = service.generate_strategies(issues, draft_id)
    applied = service.apply_strategies(draft_id)
    response = service.generate_response(issues, strategies["strategies"], draft_id)

    assert strategies["strategies"][0]["issue_id"] == 1
    assert applied["application_summary"]["applied_count"] == 1
    assert "修订表述" in applied["claims"]
    assert "# 答复意见书" in response

    with test_db.get_session() as session:
        draft = session.query(PatentDraft).filter_by(id=draft_id).first()
        assert draft.content["repair_issues"][0]["type"] == "clarity"
        assert draft.content["repair_strategies"][0]["solutions"][0]["name"] == "方案1：保守修改"
        assert draft.content["repair_application"]["applied_items"][0]["location"] == "权利要求1"
        assert "修订表述" in draft.content["claims"]
        assert draft.content["response_opinion"] == response
