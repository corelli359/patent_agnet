"""
专利审查指南知识库测试
"""

from shared.knowledge import PatentGuidelineKnowledgeBase


def test_guideline_knowledge_retrieves_relevant_passages(tmp_path):
    """应能从审查指南文本中检索到与主题相关的条文片段"""
    source_text = """
第二部分 实质审查
第二章 说明书和权利要求书
权利要求应当清楚、简要地限定要求保护的范围。
说明书应当对发明作出清楚、完整的说明，以所属技术领域的技术人员能够实现为准。
第三章 新颖性
新颖性，是指该发明不属于现有技术，也没有任何单位或者个人就同样的发明在申请日以前向国务院专利行政部门提出过申请。
"""

    kb = PatentGuidelineKnowledgeBase(
        pdf_path=str(tmp_path / "guide.pdf"),
        cache_path=str(tmp_path / "guide_cache.json"),
        source_text=source_text,
    )

    passages = kb.retrieve("clarity", "权利要求书术语不够清楚", top_k=2)

    assert passages
    assert "说明书和权利要求书" in passages[0]["title"]
    assert "清楚" in passages[0]["excerpt"]

    context = kb.format_passages(passages)
    assert "依据1" in context
    assert "权利要求应当清楚" in context
