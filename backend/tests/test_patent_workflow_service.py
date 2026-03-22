"""
专利项目工作流服务测试
"""

import pytest

import backend.app.services.patent_workflow_service as workflow_module
from shared.db.models import ExaminationRecord, PatentDraft, PatentMetadata, SearchHistory, SearchResult


@pytest.fixture
def workflow_service(test_db, monkeypatch):
    """使用测试数据库初始化工作流服务"""
    monkeypatch.setattr(workflow_module, "get_database", lambda: test_db)
    return workflow_module.PatentWorkflowService()


def test_create_project_returns_stage_overview(workflow_service):
    """创建项目后应返回项目总览和下一步动作"""
    overview = workflow_service.create_project(
        user_id="user-1",
        title="一种面向边缘设备的低功耗推理方法",
        patent_type="发明",
        technical_field="边缘计算",
        summary="在边缘设备侧动态切换模型精度，以降低能耗。",
    )

    assert overview["title"] == "一种面向边缘设备的低功耗推理方法"
    assert overview["progress"] > 0
    assert overview["current_stage"] == "invention_intent"
    assert overview["stages"][0]["status"] == "completed"
    assert any("Skill 1" in action for action in overview["next_actions"])


def test_list_projects_returns_latest_project_summaries(workflow_service):
    """项目列表应返回进度、阶段与质量概览"""
    first = workflow_service.create_project(user_id="user-list", title="项目A")
    second = workflow_service.create_project(user_id="user-list", title="项目B")

    result = workflow_service.list_projects(user_id="user-list", limit=10)

    assert result["total"] == 2
    returned_ids = {item["draft_id"] for item in result["items"]}
    assert returned_ids == {first["draft_id"], second["draft_id"]}
    assert all(item["current_stage"] == "invention_intent" for item in result["items"])
    assert all("quality_score" in item for item in result["items"])


def test_attach_search_to_project_persists_analysis(workflow_service, test_db):
    """挂接检索结果后，项目应记录检索快照并更新阶段状态"""
    overview = workflow_service.create_project(
        user_id="user-2",
        title="一种工业视觉缺陷识别方法",
        summary="结合多尺度特征与异常评分进行缺陷识别。",
    )
    draft_id = overview["draft_id"]

    with test_db.get_session() as session:
        history = SearchHistory(
            user_id="user-2",
            query="工业视觉 缺陷识别",
            filters={"country": "CN"},
            source="google_patents",
            result_count=2,
            status="success",
        )
        patent_a = PatentMetadata(
            patent_number="CN100000001A",
            title="一种工业视觉缺陷检测方法",
            abstract="本发明公开了一种用于工业表面检测的视觉分析方法。",
            ipc_classifications=["G06T7/00"],
            source="google_patents",
        )
        patent_b = PatentMetadata(
            patent_number="CN100000002A",
            title="一种异常评分驱动的缺陷识别系统",
            abstract="该系统利用特征嵌入和异常评分识别缺陷样本。",
            ipc_classifications=["G06N3/08"],
            source="google_patents",
        )
        session.add_all([history, patent_a, patent_b])
        session.flush()

        session.add_all(
            [
                SearchResult(search_id=history.id, patent_id=patent_a.id, rank=1),
                SearchResult(search_id=history.id, patent_id=patent_b.id, rank=2),
            ]
        )
        search_id = history.id

    result = workflow_service.attach_search_to_project(draft_id, search_id)

    assert result["attached_search"]["search_id"] == search_id
    assert result["project_overview"]["current_stage"] in {"invention_intent", "disclosure"}
    assert search_id in result["project_overview"]["linked_search_ids"]
    search_stage = next(
        stage for stage in result["project_overview"]["stages"] if stage["key"] == "prior_art_search"
    )
    assert search_stage["status"] == "completed"

    with test_db.get_session() as session:
        draft = session.query(PatentDraft).filter_by(id=draft_id).first()
        searches = draft.content["prior_art_search"]["searches"]
        assert len(searches) == 1
        assert searches[0]["search_id"] == search_id
        assert "# 专利技术分析报告" in searches[0]["analysis_report"]


def test_build_delivery_package_generates_markdown_summary(workflow_service, test_db):
    """交付包应汇总核心文档，并在核心材料齐备时标记为可交付"""
    overview = workflow_service.create_project(
        user_id="user-3",
        title="一种面向物流分拣的动态路径规划方法",
        summary="根据包裹拥塞与设备负载动态规划分拣路径。",
    )
    draft_id = overview["draft_id"]

    with test_db.get_session() as session:
        draft = session.query(PatentDraft).filter_by(id=draft_id).first()
        draft.content = {
            "project_profile": {
                "technical_field": "智能物流",
                "summary": "根据包裹拥塞与设备负载动态规划分拣路径。",
            },
            "workflow": {
                "current_stage": "delivery",
                "linked_search_ids": ["search-1"],
            },
            "invention_intent": {
                "title": draft.title,
                "technical_problem": "现有分拣路线固定，无法及时响应拥塞。",
                "solution": "构建动态路径评分模型并实时调整目标路径。",
            },
            "invention_intent_doc": "# 发明意图文档\n\n围绕动态路径评分与拥塞控制展开。",
            "prior_art_search": {
                "searches": [
                    {
                        "search_id": "search-1",
                        "query": "物流 分拣 动态路径",
                        "result_count": 3,
                        "analysis_report": "# 专利技术分析报告\n\n- 关键词：动态路径、分拣调度",
                    }
                ]
            },
            "disclosure_doc": "# 技术交底书\n\n详细描述动态路径评分、路径切换条件和实施方式。",
            "claims": "# 权利要求书\n\n1. 一种动态路径规划方法，其特征在于，包括采集拥塞数据并计算路径评分。\n2. 根据权利要求1所述的方法，其特征在于，根据设备负载调整路径权重。",
            "specification": "# 说明书\n\n[0001] 本发明涉及智能物流分拣领域。",
            "abstract": "# 摘要\n\n本发明提出一种面向物流分拣的动态路径规划方法。",
        }
        session.add(
            ExaminationRecord(
                draft_id=draft_id,
                examination_type="comprehensive",
                defects=[],
                status="pass",
                report_content="# 专利审查报告\n\n未发现明显致命缺陷。",
            )
        )

    result = workflow_service.build_delivery_package(draft_id)

    assert result["package"]["readiness"] is True
    assert result["package"]["missing_items"] == []
    assert result["package"]["checklist"]
    assert "# 专利项目交付包" in result["package"]["markdown"]
    assert "## 权利要求书" in result["package"]["markdown"]
    assert "## 检索与对比分析" in result["package"]["markdown"]

    with test_db.get_session() as session:
        draft = session.query(PatentDraft).filter_by(id=draft_id).first()
        assert "delivery_package" in draft.content
        assert draft.content["delivery_package"]["readiness"] is True


def test_prepare_delivery_export_includes_structured_files(workflow_service, test_db):
    """导出交付包时应生成结构化文件集合，便于下载归档"""
    overview = workflow_service.create_project(
        user_id="user-export",
        title="一种库存预测方法",
        summary="基于销量波动与补货周期进行库存预测。",
    )
    draft_id = overview["draft_id"]

    with test_db.get_session() as session:
        draft = session.query(PatentDraft).filter_by(id=draft_id).first()
        draft.content = {
            "workflow": {"current_stage": "delivery"},
            "invention_intent_doc": "# 发明意图文档\n\n围绕库存预测展开。",
            "prior_art_search": {"searches": [{"analysis_report": "# 检索报告\n\n已有对比结论。"}]},
            "disclosure_doc": "# 技术交底书\n\n完整交底。",
            "claims": "# 权利要求书\n\n1. 一种库存预测方法，其特征在于，包括获取销量数据。",
            "specification": "# 说明书\n\n[0001] 本发明涉及库存预测领域。",
            "abstract": "# 摘要\n\n本发明涉及库存预测。",
        }

    workflow_service.build_delivery_package(draft_id)
    exported = workflow_service.prepare_delivery_export(draft_id)

    assert exported["filename"].endswith(".zip")
    assert "00_overview.md" in exported["files"]
    assert "10_submission_checklist.md" in exported["files"]
    assert "11_delivery_package.md" in exported["files"]
    assert exported["manifest"]["draft_id"] == draft_id


def test_update_document_tracks_versions_and_supports_restore(workflow_service, test_db):
    """手工编辑文档后应生成版本记录，并支持按文档恢复旧版本"""
    overview = workflow_service.create_project(
        user_id="user-4",
        title="一种动态调度方法",
        summary="围绕任务优先级与资源负载进行调度。",
    )
    draft_id = overview["draft_id"]

    workflow_service.update_project_document(
        draft_id,
        "claims",
        "# 权利要求书\n\n1. 一种动态调度方法，其特征在于，包括计算任务优先级。",
    )
    workflow_service.update_project_document(
        draft_id,
        "claims",
        "# 权利要求书\n\n1. 一种动态调度方法，其特征在于，包括计算任务优先级。\n2. 根据权利要求1所述的方法，其特征在于，根据资源负载调整调度顺序。",
    )

    versions = workflow_service.list_project_versions(draft_id, document_key="claims", limit=10)
    assert versions["current_version"] == 3
    assert [item["version_number"] for item in versions["items"][:2]] == [3, 2]

    diff = workflow_service.get_project_version_diff(
        draft_id,
        versions["items"][1]["version_id"],
        "claims",
    )
    assert "根据权利要求1所述的方法" in diff["compare_content"]
    assert "根据权利要求1所述的方法" not in diff["base_content"]

    workflow_service.restore_project_version(
        draft_id,
        versions["items"][1]["version_id"],
        document_key="claims",
    )

    with test_db.get_session() as session:
        draft = session.query(PatentDraft).filter_by(id=draft_id).first()
        assert draft.version == 4
        assert "根据权利要求1所述的方法" not in draft.content["claims"]


def test_project_overview_exposes_action_guards(workflow_service):
    """项目总览应返回前置条件守卫，供前端禁用不合理操作"""
    overview = workflow_service.create_project(
        user_id="user-5",
        title="一种视频摘要生成方法",
    )

    guards = overview["action_guards"]
    assert guards["generate_disclosure"]["ready"] is False
    assert "结构化发明意图" in guards["generate_disclosure"]["missing_items"]
    assert guards["apply_repair_strategies"]["ready"] is False
    assert guards["build_delivery_package"]["ready"] is True


def test_overview_marks_examination_stale_after_claim_update(workflow_service, test_db):
    """如果申请文件在审查后被修改，项目总览应标记审查结果已过期"""
    overview = workflow_service.create_project(
        user_id="user-6",
        title="一种流量调度方法",
    )
    draft_id = overview["draft_id"]

    with test_db.get_session() as session:
        draft = session.query(PatentDraft).filter_by(id=draft_id).first()
        draft.content = {
            "workflow": {"current_stage": "examination", "drafting_last_updated_at": "2099-03-11T20:00:00"},
            "claims": "# 权利要求书\n\n1. 一种流量调度方法，其特征在于，包括获取负载数据。",
            "specification": "# 说明书\n\n[0001] 本发明涉及流量调度领域。",
            "abstract": "# 摘要\n\n本发明涉及流量调度。",
        }
        session.add(
            ExaminationRecord(
                draft_id=draft_id,
                examination_type="comprehensive",
                defects=[],
                status="pass",
                report_content="# 专利审查报告\n\n通过。",
            )
        )

    latest = workflow_service.get_project_overview(draft_id)

    assert latest["examination"]["stale"] is True
    assert latest["action_guards"]["run_examination"]["ready"] is True
    assert "建议立即重新审查" in latest["action_guards"]["run_examination"]["message"]
