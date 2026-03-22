"""
实质审查服务测试
"""

import backend.app.services.examination_service as exam_module


class FakeLLMClient:
    def __init__(self):
        self.last_prompt = ""

    def chat(self, messages, temperature=0.2, max_tokens=800, **kwargs):
        self.last_prompt = messages[0]["content"]
        return '[{"severity": "serious", "location": "权利要求1", "description": "术语表述不清"}]'


class FakeGuidelineKB:
    def retrieve(self, topic, context_text="", top_k=3):
        return [
            {
                "title": "第二部分 实质审查 > 第二章 说明书和权利要求书",
                "content": "权利要求应当清楚、简要地限定要求保护的范围。",
                "excerpt": "权利要求应当清楚、简要地限定要求保护的范围。",
                "score": 10,
            }
        ]

    def format_passages(self, passages):
        return "[依据1] 第二部分 实质审查 > 第二章 说明书和权利要求书\n权利要求应当清楚、简要地限定要求保护的范围。"


class FakeSearchService:
    def search(self, **kwargs):
        return {"result_count": 0, "results": []}


def test_clarity_examination_uses_guideline_context(monkeypatch):
    """清楚性审查应把审查指南依据注入提示词，并回填依据标题"""
    fake_llm = FakeLLMClient()

    monkeypatch.setattr(exam_module, "get_llm_client", lambda provider="deepseek": fake_llm)
    monkeypatch.setattr(exam_module, "PatentGuidelineKnowledgeBase", lambda: FakeGuidelineKB())
    monkeypatch.setattr(exam_module, "PatentSearchService", lambda: FakeSearchService())

    service = exam_module.ExaminationService()
    defects = service._clarity_examination(
        "1. 一种方法，其特征在于包括识别模块。",
        "[0001] 本发明涉及图像识别领域。[0002] 说明书描述了识别模块。",
    )

    assert "《专利审查指南》依据" in fake_llm.last_prompt
    assert "权利要求应当清楚、简要地限定要求保护的范围" in fake_llm.last_prompt
    assert defects[0]["type"] == "clarity"
    assert defects[0]["basis"] == ["第二部分 实质审查 > 第二章 说明书和权利要求书"]
