"""
专利全流程工作流服务
将现有 Skill 串联为面向项目的统一工作流。
"""

from __future__ import annotations

from datetime import datetime
import json
from typing import Dict, List, Optional, Tuple
import difflib
import logging
import re

from shared.db import get_database
from shared.db.models import ExaminationRecord, PatentDraft, PatentDraftVersion, SearchHistory
from shared.db.repositories import PatentRepository
from skills.patent_search.scripts.analysis_reporter import PatentAnalysisReporter
from .project_support import (
    CORE_DRAFT_DOCUMENT_KEYS,
    EDITABLE_DOCUMENT_KEYS,
    apply_snapshot,
    create_version_record,
    ensure_version_baseline,
    get_document_label,
    mark_document_update,
    missing_action_requirements,
    normalize_content,
)

logger = logging.getLogger(__name__)


class PatentWorkflowService:
    """统一的专利项目工作流服务"""

    STAGE_DEFINITIONS: List[Tuple[str, str, str]] = [
        ("project_intake", "项目立项", "明确标题、类型、技术方向和目标场景"),
        ("invention_intent", "发明意图", "沉淀技术问题、方案、效果与创新点"),
        ("prior_art_search", "现有技术检索", "挂接检索结果，形成对比分析依据"),
        ("disclosure", "技术交底书", "生成适合代理师继续加工的交底材料"),
        ("application_drafting", "申请文件起草", "形成权利要求书、说明书、摘要"),
        ("examination", "审查模拟", "从形式、清楚性、新颖性角度体检"),
        ("repair", "修复与答复", "根据缺陷或审查意见形成修订策略"),
        ("delivery", "交付打包", "输出完整交付包和下一步申报建议"),
    ]

    PLACEHOLDER_TITLE = "未命名专利项目"

    def __init__(self):
        self.db = get_database()
        self.analysis_reporter = PatentAnalysisReporter()

    def create_project(
        self,
        user_id: str = "default_user",
        title: Optional[str] = None,
        patent_type: str = "发明",
        technical_field: Optional[str] = None,
        summary: Optional[str] = None,
        initial_notes: Optional[str] = None,
    ) -> Dict:
        """创建新的专利项目"""
        normalized_title = title.strip() if title and title.strip() else self.PLACEHOLDER_TITLE
        content = {
            "project_profile": {
                "technical_field": technical_field or "",
                "summary": summary or "",
                "initial_notes": initial_notes or "",
                "created_at": datetime.now().isoformat(),
            },
            "workflow": {
                "current_stage": "project_intake",
                "linked_search_ids": [],
                "milestones": [],
            },
        }

        with self.db.get_session() as session:
            draft = PatentDraft(
                user_id=user_id,
                patent_type=patent_type or "发明",
                title=normalized_title,
                status="draft",
                content=content,
            )
            session.add(draft)
            session.flush()
            ensure_version_baseline(session, draft)
            draft_id = draft.id

        logger.info("创建专利项目成功: %s", draft_id)
        return self.get_project_overview(draft_id)

    def list_projects(self, user_id: str = "default_user", limit: int = 20) -> Dict:
        """获取用户项目列表"""
        with self.db.get_session() as session:
            drafts = (
                session.query(PatentDraft)
                .filter_by(user_id=user_id)
                .order_by(PatentDraft.updated_at.desc(), PatentDraft.created_at.desc())
                .limit(limit)
                .all()
            )

            items = []
            for draft in drafts:
                content = self._ensure_content(draft.content)
                latest_exam = self._get_latest_exam(session, draft.id)
                stages = self._build_stage_statuses(content, latest_exam)
                items.append(
                    {
                        "draft_id": draft.id,
                        "title": draft.title,
                        "patent_type": draft.patent_type,
                        "status": draft.status,
                        "current_stage": self._resolve_current_stage(stages),
                        "progress": self._calculate_progress(stages),
                        "quality_score": self._build_quality_checks(draft.title, content, latest_exam)["score"],
                        "updated_at": draft.updated_at.isoformat() if draft.updated_at else None,
                    }
                )

        return {
            "items": items,
            "total": len(items),
        }

    def get_project_overview(self, draft_id: str) -> Dict:
        """获取项目总览、阶段状态与质量检查"""
        with self.db.get_session() as session:
            draft = self._get_draft(session, draft_id)
            ensure_version_baseline(session, draft)
            content = self._ensure_content(draft.content)
            latest_exam = self._get_latest_exam(session, draft_id)

            stages = self._build_stage_statuses(content, latest_exam)
            current_stage = self._resolve_current_stage(stages)
            deliverables = self._build_deliverables(content, latest_exam)
            quality_checks = self._build_quality_checks(draft.title, content, latest_exam)
            risks = self._build_risks(draft.title, content, latest_exam, quality_checks)
            next_actions = self._build_next_actions(stages, quality_checks, latest_exam, content)
            progress = self._calculate_progress(stages)
            documents = self._build_document_views(content, latest_exam)
            examination = self._build_examination_summary(latest_exam, content)
            repair = self._build_repair_summary(content)
            versions = (
                session.query(PatentDraftVersion)
                .filter_by(draft_id=draft_id)
                .order_by(PatentDraftVersion.version_number.desc())
                .all()
            )

            workflow = content.setdefault("workflow", {})
            workflow["current_stage"] = current_stage
            workflow["linked_search_ids"] = self._collect_linked_search_ids(content)
            draft.content = content

            overview = {
                "draft_id": draft.id,
                "title": draft.title,
                "patent_type": draft.patent_type,
                "status": draft.status,
                "version": draft.version,
                "current_stage": current_stage,
                "progress": progress,
                "project_profile": content.get("project_profile", {}),
                "stages": stages,
                "deliverables": deliverables,
                "documents": documents,
                "examination": examination,
                "repair": repair,
                "quality_checks": quality_checks,
                "risks": risks,
                "next_actions": next_actions,
                "action_guards": self._build_action_guards(content, latest_exam),
                "editable_documents": sorted(EDITABLE_DOCUMENT_KEYS),
                "version_count": len(versions),
                "linked_search_ids": workflow["linked_search_ids"],
                "updated_at": draft.updated_at.isoformat() if draft.updated_at else None,
            }

        return overview

    def attach_search_to_project(self, draft_id: str, search_id: str) -> Dict:
        """将检索结果挂接到专利项目，并生成项目级分析快照"""
        with self.db.get_session() as session:
            draft = self._get_draft(session, draft_id)
            ensure_version_baseline(session, draft)
            content = self._ensure_content(draft.content)

            history = session.query(SearchHistory).filter_by(id=search_id).first()
            if not history:
                raise ValueError(f"检索记录不存在: {search_id}")

            repo = PatentRepository(session)
            raw_results = repo.get_search_results(search_id)
            patents = [item["patent"] for item in raw_results]
            analysis_report = self.analysis_reporter.generate_report(
                query=history.query,
                patents=patents,
                search_id=search_id,
            )

            search_bucket = content.setdefault("prior_art_search", {})
            searches = search_bucket.setdefault("searches", [])
            snapshot = {
                "search_id": history.id,
                "query": history.query,
                "filters": history.filters or {},
                "source": history.source,
                "result_count": history.result_count,
                "attached_at": datetime.now().isoformat(),
                "results": patents,
                "analysis_report": analysis_report,
            }

            updated = False
            for idx, item in enumerate(searches):
                if item.get("search_id") == search_id:
                    searches[idx] = snapshot
                    updated = True
                    break
            if not updated:
                searches.append(snapshot)

            search_bucket["last_attached_search_id"] = search_id
            workflow = content.setdefault("workflow", {})
            workflow["linked_search_ids"] = self._collect_linked_search_ids(content)

            draft.content = content
            create_version_record(
                session,
                draft,
                change_summary=f"挂接检索结果 {search_id}",
                document_key="search_report",
                changed_fields=["prior_art_search"],
            )
            session.add(draft)
            attached_search = {
                "search_id": search_id,
                "query": history.query,
                "result_count": history.result_count,
                "analysis_report": analysis_report,
            }

        logger.info("挂接检索结果成功: draft=%s search=%s", draft_id, search_id)
        return {
            "attached_search": attached_search,
            "project_overview": self.get_project_overview(draft_id),
        }

    def build_delivery_package(self, draft_id: str, persist: bool = True) -> Dict:
        """生成项目交付包，便于最终专利输出与复核"""
        overview = self.get_project_overview(draft_id)

        with self.db.get_session() as session:
            draft = self._get_draft(session, draft_id)
            ensure_version_baseline(session, draft)
            content = self._ensure_content(draft.content)
            latest_exam = self._get_latest_exam(session, draft_id)

            package_markdown = self._render_delivery_package(overview, draft, content, latest_exam)
            missing_items = self._required_delivery_gaps(content, latest_exam)
            checklist = self._build_submission_checklist(overview, content, latest_exam)
            package = {
                "generated_at": datetime.now().isoformat(),
                "readiness": len(missing_items) == 0,
                "missing_items": missing_items,
                "checklist": checklist,
                "markdown": package_markdown,
            }

            if persist:
                content["delivery_package"] = package
                content.setdefault("workflow", {})["current_stage"] = overview["current_stage"]
                draft.content = content
                create_version_record(
                    session,
                    draft,
                    change_summary="生成项目交付包",
                    document_key="delivery_package",
                    changed_fields=["delivery_package"],
                )
                session.add(draft)

        return {
            "draft_id": draft_id,
            "package": package,
            "project_overview": self.get_project_overview(draft_id),
        }

    def prepare_delivery_export(self, draft_id: str) -> Dict:
        """准备可下载的交付包文件集合"""
        overview = self.get_project_overview(draft_id)

        with self.db.get_session() as session:
            draft = self._get_draft(session, draft_id)
            content = self._ensure_content(draft.content)
            latest_exam = self._get_latest_exam(session, draft_id)
            package = content.get("delivery_package")
            if not package:
                package = self.build_delivery_package(draft_id, persist=True)["package"]
                content = self._ensure_content(self._get_draft(session, draft_id).content)

            checklist = package.get("checklist") or self._build_submission_checklist(overview, content, latest_exam)
            files = self._build_delivery_export_files(draft, overview, content, latest_exam, checklist)
            manifest = {
                "draft_id": draft.id,
                "title": draft.title,
                "patent_type": draft.patent_type,
                "version": draft.version,
                "generated_at": datetime.now().isoformat(),
                "readiness": package.get("readiness", False),
                "missing_items": package.get("missing_items", []),
                "files": list(files.keys()),
            }
            files["manifest.json"] = json.dumps(manifest, ensure_ascii=False, indent=2)

        return {
            "filename": f"patent-delivery-{draft_id}.zip",
            "manifest": manifest,
            "files": files,
        }

    def update_project_document(
        self,
        draft_id: str,
        document_key: str,
        document_content: str,
        change_summary: Optional[str] = None,
    ) -> Dict:
        """手工更新项目文档，并生成版本快照"""
        if document_key not in EDITABLE_DOCUMENT_KEYS:
            raise ValueError(f"当前文档不支持直接编辑: {document_key}")

        with self.db.get_session() as session:
            draft = self._get_draft(session, draft_id)
            ensure_version_baseline(session, draft)
            content = self._ensure_content(draft.content)
            content[document_key] = document_content or ""
            content = mark_document_update(content, [document_key])
            draft.content = content
            version = create_version_record(
                session,
                draft,
                change_summary=change_summary or f"手工更新{get_document_label(document_key)}",
                document_key=document_key,
                changed_fields=[document_key],
            )
            version_number = version.version_number

        return {
            "draft_id": draft_id,
            "version": version_number,
            "document_key": document_key,
            "project_overview": self.get_project_overview(draft_id),
        }

    def list_project_versions(
        self,
        draft_id: str,
        document_key: Optional[str] = None,
        limit: int = 20,
    ) -> Dict:
        """获取项目版本列表，可按文档过滤"""
        with self.db.get_session() as session:
            draft = self._get_draft(session, draft_id)
            ensure_version_baseline(session, draft)
            current_version = draft.version
            versions = (
                session.query(PatentDraftVersion)
                .filter_by(draft_id=draft_id)
                .order_by(PatentDraftVersion.version_number.desc())
                .all()
            )

            if document_key:
                versions = [
                    item for item in versions
                    if item.document_key == document_key or document_key in (item.changed_fields or [])
                ]

            items = [
                {
                    "version_id": item.id,
                    "version_number": item.version_number,
                    "document_key": item.document_key,
                    "document_label": get_document_label(item.document_key or "project"),
                    "change_summary": item.change_summary,
                    "changed_fields": item.changed_fields or [],
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                }
                for item in versions[:limit]
            ]

        return {
            "draft_id": draft_id,
            "current_version": current_version,
            "items": items,
            "total": len(items),
        }

    def get_project_version_diff(
        self,
        draft_id: str,
        version_id: str,
        document_key: str,
        compare_target: str = "current",
    ) -> Dict:
        """查看版本文档差异，默认与当前版本对比"""
        with self.db.get_session() as session:
            draft = self._get_draft(session, draft_id)
            ensure_version_baseline(session, draft)
            version = session.query(PatentDraftVersion).filter_by(id=version_id, draft_id=draft_id).first()
            if not version:
                raise ValueError(f"版本不存在: {version_id}")

            version_text = self._extract_snapshot_document(version.snapshot, document_key)
            base_version_id = version.id
            base_version_number = version.version_number
            base_change_summary = version.change_summary
            compare_version_number = draft.version
            compare_label = f"当前版本 v{draft.version}"
            compare_text = self._extract_snapshot_document(
                {"content": normalize_content(draft.content)},
                document_key,
            )

            if compare_target == "previous":
                previous = (
                    session.query(PatentDraftVersion)
                    .filter(
                        PatentDraftVersion.draft_id == draft_id,
                        PatentDraftVersion.version_number < base_version_number,
                    )
                    .order_by(PatentDraftVersion.version_number.desc())
                    .first()
                )
                if previous:
                    compare_version_number = previous.version_number
                    compare_label = f"前一版本 v{previous.version_number}"
                    compare_text = self._extract_snapshot_document(previous.snapshot, document_key)
                else:
                    compare_version_number = 0
                    compare_label = "空白基线"
                    compare_text = ""

            diff_lines = difflib.unified_diff(
                version_text.splitlines(),
                compare_text.splitlines(),
                fromfile=f"v{base_version_number}",
                tofile=compare_label,
                lineterm="",
            )

        return {
            "draft_id": draft_id,
            "document_key": document_key,
            "document_label": get_document_label(document_key),
            "base_version": {
                "version_id": base_version_id,
                "version_number": base_version_number,
                "change_summary": base_change_summary,
            },
            "compare_version": {
                "version_number": compare_version_number,
                "label": compare_label,
            },
            "base_content": version_text,
            "compare_content": compare_text,
            "diff": "\n".join(diff_lines),
        }

    def restore_project_version(
        self,
        draft_id: str,
        version_id: str,
        document_key: Optional[str] = None,
        change_summary: Optional[str] = None,
    ) -> Dict:
        """恢复某个版本，可按单文档恢复"""
        with self.db.get_session() as session:
            draft = self._get_draft(session, draft_id)
            ensure_version_baseline(session, draft)
            version = session.query(PatentDraftVersion).filter_by(id=version_id, draft_id=draft_id).first()
            if not version:
                raise ValueError(f"版本不存在: {version_id}")

            apply_snapshot(draft, version.snapshot or {}, document_key=document_key)
            if document_key:
                draft.content = mark_document_update(self._ensure_content(draft.content), [document_key])
            else:
                draft.content = mark_document_update(
                    self._ensure_content(draft.content),
                    list(CORE_DRAFT_DOCUMENT_KEYS),
                )
            restored_key = document_key or "project"
            version_record = create_version_record(
                session,
                draft,
                change_summary=change_summary or f"恢复到版本 v{version.version_number}",
                document_key=restored_key,
                changed_fields=[restored_key],
            )
            version_number = version_record.version_number

        return {
            "draft_id": draft_id,
            "version": version_number,
            "project_overview": self.get_project_overview(draft_id),
        }

    def _get_draft(self, session, draft_id: str) -> PatentDraft:
        draft = session.query(PatentDraft).filter_by(id=draft_id).first()
        if not draft:
            raise ValueError(f"专利项目不存在: {draft_id}")
        return draft

    def _get_latest_exam(self, session, draft_id: str) -> Optional[ExaminationRecord]:
        return (
            session.query(ExaminationRecord)
            .filter_by(draft_id=draft_id)
            .order_by(ExaminationRecord.created_at.desc())
            .first()
        )

    def _ensure_content(self, content: Optional[Dict]) -> Dict:
        return normalize_content(content)

    def _extract_snapshot_document(self, snapshot: Optional[Dict], document_key: str) -> str:
        content = normalize_content((snapshot or {}).get("content"))
        if document_key == "search_report":
            searches = content.get("prior_art_search", {}).get("searches", [])
            latest_search = searches[-1] if searches else {}
            return latest_search.get("analysis_report", "")
        if document_key == "repair_strategies":
            return self._render_repair_strategy_markdown(content.get("repair_strategies", []))
        if document_key == "delivery_package":
            return content.get("delivery_package", {}).get("markdown", "")
        return content.get(document_key, "")

    def _drafting_last_updated_at(self, content: Dict) -> Optional[datetime]:
        timestamp = content.get("workflow", {}).get("drafting_last_updated_at")
        if not timestamp:
            return None
        try:
            return datetime.fromisoformat(timestamp)
        except ValueError:
            return None

    def _exam_is_stale(self, content: Dict, latest_exam: Optional[ExaminationRecord]) -> bool:
        if not latest_exam:
            return False
        draft_updated_at = self._drafting_last_updated_at(content)
        if not draft_updated_at:
            return False
        exam_created_at = latest_exam.created_at
        if not exam_created_at:
            return True
        return draft_updated_at > exam_created_at

    def _build_stage_statuses(self, content: Dict, latest_exam: Optional[ExaminationRecord]) -> List[Dict]:
        invention_ready = bool(content.get("invention_intent") or content.get("invention_intent_doc"))
        search_ready = bool(content.get("prior_art_search", {}).get("searches"))
        disclosure_ready = bool(content.get("disclosure_doc"))
        draft_files = self._has_application_files(content)
        exam_ready = latest_exam is not None and not self._exam_is_stale(content, latest_exam)
        repair_ready = bool(content.get("response_opinion") or content.get("repair_application", {}).get("applied_at"))
        delivery_ready = bool(content.get("delivery_package"))

        partial_drafting = any(content.get(key) for key in ("claims", "specification", "abstract"))
        repair_in_progress = bool(content.get("repair_strategies")) or (
            latest_exam is not None and latest_exam.status in {"fail", "warning"}
        )

        stage_status_map = {
            "project_intake": "completed",
            "invention_intent": "completed" if invention_ready else "pending",
            "prior_art_search": "completed" if search_ready else "pending",
            "disclosure": "completed" if disclosure_ready else "pending",
            "application_drafting": (
                "completed" if draft_files else ("in_progress" if partial_drafting else "pending")
            ),
            "examination": "completed" if exam_ready else ("in_progress" if draft_files else "pending"),
            "repair": "completed" if repair_ready else ("in_progress" if repair_in_progress else "pending"),
            "delivery": "completed" if delivery_ready else ("in_progress" if draft_files else "pending"),
        }

        stages = []
        for key, label, description in self.STAGE_DEFINITIONS:
            stages.append(
                {
                    "key": key,
                    "label": label,
                    "description": description,
                    "status": stage_status_map[key],
                }
            )

        return stages

    def _build_deliverables(self, content: Dict, latest_exam: Optional[ExaminationRecord]) -> List[Dict]:
        prior_art_searches = content.get("prior_art_search", {}).get("searches", [])
        delivery_package = content.get("delivery_package", {})
        repair_required = latest_exam is not None and latest_exam.status in {"fail", "warning"}
        repair_applied = content.get("repair_application", {}).get("applied_at")

        return [
            self._deliverable("invention_intent_doc", "发明意图文档", bool(content.get("invention_intent_doc")), required=True),
            self._deliverable(
                "prior_art_search",
                "检索分析快照",
                bool(prior_art_searches),
                f"{len(prior_art_searches)} 次挂接",
                required=True,
            ),
            self._deliverable("disclosure_doc", "技术交底书", bool(content.get("disclosure_doc")), required=True),
            self._deliverable("claims", "权利要求书", bool(content.get("claims")), required=True),
            self._deliverable("specification", "说明书", bool(content.get("specification")), required=True),
            self._deliverable("abstract", "摘要", bool(content.get("abstract")), required=True),
            self._deliverable("examination_report", "审查报告", latest_exam is not None, required=False),
            self._deliverable("repair_application", "修订稿", bool(repair_applied), required=repair_required),
            self._deliverable("response_opinion", "答复意见书", bool(content.get("response_opinion")), required=repair_required),
            self._deliverable("delivery_package", "交付包", bool(delivery_package.get("markdown")), required=False),
        ]

    def _deliverable(
        self,
        key: str,
        label: str,
        ready: bool,
        detail: Optional[str] = None,
        required: bool = False,
    ) -> Dict:
        return {
            "key": key,
            "label": label,
            "ready": ready,
            "required": required,
            "detail": detail or ("已具备" if ready else "待生成"),
        }

    def _build_quality_checks(
        self,
        title: str,
        content: Dict,
        latest_exam: Optional[ExaminationRecord],
    ) -> Dict:
        checks = []

        checks.append(
            self._quality_check(
                "title_ready",
                "标题是否明确",
                "pass" if self._title_ready(title) else "warning",
                "已具备明确标题" if self._title_ready(title) else "建议先明确发明名称，避免后续文档多次返工",
            )
        )

        invention_ready = bool(content.get("invention_intent") and content.get("invention_intent_doc"))
        checks.append(
            self._quality_check(
                "intent_ready",
                "发明意图是否成型",
                "pass" if invention_ready else "warning",
                "技术问题、方案、效果已沉淀" if invention_ready else "先完成 Skill 1，避免直接起草权利要求",
            )
        )

        search_ready = bool(content.get("prior_art_search", {}).get("searches"))
        checks.append(
            self._quality_check(
                "search_ready",
                "现有技术检索是否挂接",
                "pass" if search_ready else "warning",
                "已有现有技术支撑" if search_ready else "缺少检索依据，新颖性和创造性判断偏弱",
            )
        )

        disclosure_ready = bool(content.get("disclosure_doc"))
        checks.append(
            self._quality_check(
                "disclosure_ready",
                "技术交底书是否具备",
                "pass" if disclosure_ready else "warning",
                "交底书已生成" if disclosure_ready else "建议先形成交底书，再进入正式申请文件起草",
            )
        )

        drafting_ready = self._has_application_files(content)
        checks.append(
            self._quality_check(
                "drafting_ready",
                "申请文件是否齐全",
                "pass" if drafting_ready else "warning",
                "权利要求书、说明书、摘要齐全" if drafting_ready else "三份核心文件尚未齐全",
            )
        )

        claims_status, claims_detail = self._check_claims_quality(content.get("claims", ""))
        checks.append(self._quality_check("claims_format", "权利要求格式检查", claims_status, claims_detail))

        if self._exam_is_stale(content, latest_exam):
            exam_status = "warning"
            exam_detail = "申请文件在最近一次审查后已被修订，当前审查结果已过期，建议重新审查"
        else:
            exam_status = "pass" if latest_exam else ("warning" if drafting_ready else "not_ready")
            exam_detail = (
                f"最近一次审查状态: {latest_exam.status}" if latest_exam else "起草完成后建议立即执行 Skill 4"
            )
        checks.append(self._quality_check("examination_ready", "审查闭环", exam_status, exam_detail))

        delivery_ready = not self._required_delivery_gaps(content, latest_exam)
        checks.append(
            self._quality_check(
                "delivery_ready",
                "最终交付准备度",
                "pass" if delivery_ready else "warning",
                "可以整理最终交付包" if delivery_ready else "仍缺少关键交付件，不适合进入最终申报准备",
            )
        )

        applicable_checks = [item for item in checks if item["status"] != "not_ready"]
        pass_count = len([item for item in applicable_checks if item["status"] == "pass"])
        score = round((pass_count / max(len(applicable_checks), 1)) * 100)

        return {
            "score": score,
            "items": checks,
        }

    def _quality_check(self, key: str, label: str, status: str, detail: str) -> Dict:
        return {
            "key": key,
            "label": label,
            "status": status,
            "detail": detail,
        }

    def _build_risks(
        self,
        title: str,
        content: Dict,
        latest_exam: Optional[ExaminationRecord],
        quality_checks: Dict,
    ) -> List[Dict]:
        risks = []

        if not self._title_ready(title):
            risks.append(self._risk("high", "标题仍为占位符，后续检索和撰写容易偏离真实保护主题"))

        if not content.get("prior_art_search", {}).get("searches"):
            risks.append(self._risk("high", "尚未挂接现有技术检索结果，无法为新颖性与创造性论证提供证据"))

        if not content.get("disclosure_doc"):
            risks.append(self._risk("medium", "技术交底书缺失，申请文件将缺少结构化的中间层"))

        claims_check = next(
            (item for item in quality_checks["items"] if item["key"] == "claims_format"),
            None,
        )
        if claims_check and claims_check["status"] == "fail":
            risks.append(self._risk("high", claims_check["detail"]))

        if latest_exam and latest_exam.status in {"fail", "warning"} and not content.get("repair_application", {}).get("applied_at"):
            risks.append(self._risk("medium", "已有审查缺陷，但尚未形成修复策略或答复意见书"))
        elif self._exam_is_stale(content, latest_exam):
            risks.append(self._risk("medium", "修订稿已生成，但尚未执行新一轮审查，当前结论不能代表最新文稿质量"))

        return risks

    def _risk(self, level: str, description: str) -> Dict:
        return {
            "level": level,
            "description": description,
        }

    def _build_next_actions(
        self,
        stages: List[Dict],
        quality_checks: Dict,
        latest_exam: Optional[ExaminationRecord],
        content: Dict,
    ) -> List[str]:
        actions = []
        status_map = {stage["key"]: stage["status"] for stage in stages}

        if status_map["invention_intent"] != "completed":
            actions.append("启动 Skill 1，对技术问题、解决方案、创新点进行多轮澄清并生成发明意图文档。")
        elif status_map["prior_art_search"] != "completed":
            actions.append("执行 Skill 6 检索并将至少 1 组检索结果挂接到项目，形成现有技术分析基线。")
        elif status_map["disclosure"] != "completed":
            actions.append("基于发明意图生成技术交底书，补齐实施方式、背景技术和有益效果。")
        elif status_map["application_drafting"] != "completed":
            actions.append("生成权利要求书、说明书和摘要，并重点复核独立权利要求的保护边界。")
        elif status_map["examination"] != "completed":
            if self._exam_is_stale(content, latest_exam):
                actions.append("修订稿已落地，请立即执行新一轮审查，确认缺陷是否已被消除。")
            else:
                actions.append("执行 Skill 4 审查模拟，尽早暴露清楚性、形式和新颖性风险。")
        elif latest_exam and latest_exam.status in {"fail", "warning"} and not content.get("repair_strategies"):
            actions.append("针对审查缺陷运行 Skill 5，形成修复策略和答复意见书。")
        elif content.get("repair_strategies") and not content.get("repair_application", {}).get("applied_at"):
            actions.append("将修复策略应用到权利要求书/说明书，生成修订稿，避免停留在建议层。")
        elif status_map["delivery"] != "completed":
            actions.append("生成交付包，整理项目概览、检索证据和正式申请文件，准备最终提交。")

        low_score_items = [item for item in quality_checks["items"] if item["status"] in {"warning", "fail"}]
        if low_score_items:
            actions.append(f"优先处理质量检查中的薄弱项，当前待关注项数量：{len(low_score_items)}。")

        return actions[:4]

    def _resolve_current_stage(self, stages: List[Dict]) -> str:
        for stage in stages:
            if stage["status"] != "completed":
                return stage["key"]
        return "delivery"

    def _calculate_progress(self, stages: List[Dict]) -> int:
        completed = len([stage for stage in stages if stage["status"] == "completed"])
        return round((completed / max(len(stages), 1)) * 100)

    def _collect_linked_search_ids(self, content: Dict) -> List[str]:
        searches = content.get("prior_art_search", {}).get("searches", [])
        return [item.get("search_id") for item in searches if item.get("search_id")]

    def _build_document_views(self, content: Dict, latest_exam: Optional[ExaminationRecord]) -> Dict:
        searches = content.get("prior_art_search", {}).get("searches", [])
        latest_search = searches[-1] if searches else {}
        delivery_package = content.get("delivery_package", {})

        return {
            "invention_intent_doc": content.get("invention_intent_doc", ""),
            "search_report": latest_search.get("analysis_report", ""),
            "disclosure_doc": content.get("disclosure_doc", ""),
            "claims": content.get("claims", ""),
            "specification": content.get("specification", ""),
            "abstract": content.get("abstract", ""),
            "exam_report": latest_exam.report_content if latest_exam else "",
            "repair_strategies": self._render_repair_strategy_markdown(content.get("repair_strategies", [])),
            "response_opinion": content.get("response_opinion", ""),
            "delivery_package": delivery_package.get("markdown", ""),
        }

    def _build_submission_checklist(
        self,
        overview: Dict,
        content: Dict,
        latest_exam: Optional[ExaminationRecord],
    ) -> List[Dict]:
        checks = []
        delivery_gaps = set(self._required_delivery_gaps(content, latest_exam))
        repair_application = content.get("repair_application", {})

        definitions = [
            ("title_ready", "发明名称已确定", self._title_ready(overview.get("title")), "避免后续导出材料使用占位标题"),
            ("search_ready", "已挂接检索分析", bool(content.get("prior_art_search", {}).get("searches")), "建议至少保留 1 组用于论证的检索快照"),
            ("claims_ready", "权利要求书已定稿", bool(content.get("claims")), "核心提交文件"),
            ("spec_ready", "说明书已定稿", bool(content.get("specification")), "核心提交文件"),
            ("abstract_ready", "摘要已定稿", bool(content.get("abstract")), "核心提交文件"),
            ("exam_fresh", "审查结论与当前文稿一致", latest_exam is not None and not self._exam_is_stale(content, latest_exam), "若文稿有改动，应重新体检"),
            ("repair_applied", "修复建议已落稿", bool(repair_application.get("applied_at")) or not content.get("repair_strategies"), "若已有策略，建议落到正文而不是仅停留在建议层"),
            ("response_ready", "答复意见书已准备", bool(content.get("response_opinion")) or not delivery_gaps.intersection({"答复意见书"}), "如存在审查缺陷，建议同步输出答复意见"),
        ]

        for key, label, ready, detail in definitions:
            checks.append(
                {
                    "key": key,
                    "label": label,
                    "ready": bool(ready),
                    "detail": detail,
                }
            )

        return checks

    def _build_delivery_export_files(
        self,
        draft: PatentDraft,
        overview: Dict,
        content: Dict,
        latest_exam: Optional[ExaminationRecord],
        checklist: List[Dict],
    ) -> Dict[str, str]:
        documents = self._build_document_views(content, latest_exam)
        checklist_lines = ["# 提交前检查清单", ""]
        for item in checklist:
            status = "已完成" if item["ready"] else "待确认"
            checklist_lines.append(f"- {item['label']}: {status}；{item['detail']}")

        summary_lines = [
            "# 项目概览",
            "",
            f"- 项目ID: `{draft.id}`",
            f"- 发明名称: {draft.title}",
            f"- 专利类型: {draft.patent_type}",
            f"- 当前版本: v{draft.version}",
            f"- 当前阶段: {overview['current_stage']}",
            f"- 完成度: {overview['progress']}%",
            f"- 质量评分: {overview['quality_checks']['score']}",
            "",
        ]

        files = {
            "00_overview.md": "\n".join(summary_lines),
            "01_intent.md": documents.get("invention_intent_doc") or "尚未生成发明意图文档。",
            "02_search_report.md": documents.get("search_report") or "尚未挂接检索分析。",
            "03_disclosure.md": documents.get("disclosure_doc") or "尚未生成技术交底书。",
            "04_claims.md": documents.get("claims") or "尚未生成权利要求书。",
            "05_specification.md": documents.get("specification") or "尚未生成说明书。",
            "06_abstract.md": documents.get("abstract") or "尚未生成摘要。",
            "07_examination.md": documents.get("exam_report") or "尚未执行审查模拟。",
            "08_repair_strategies.md": documents.get("repair_strategies") or "尚未生成修复策略。",
            "09_response_opinion.md": documents.get("response_opinion") or "尚未生成答复意见书。",
            "10_submission_checklist.md": "\n".join(checklist_lines),
            "11_delivery_package.md": documents.get("delivery_package") or "尚未生成交付包。",
        }
        return files

    def _build_examination_summary(self, latest_exam: Optional[ExaminationRecord], content: Dict) -> Dict:
        if not latest_exam:
            return {
                "available": False,
                "status": None,
                "defects": [],
                "report": "",
                "created_at": None,
                "stale": False,
            }

        return {
            "available": True,
            "status": latest_exam.status,
            "defects": latest_exam.defects or [],
            "report": latest_exam.report_content or "",
            "created_at": latest_exam.created_at.isoformat() if latest_exam.created_at else None,
            "stale": self._exam_is_stale(content, latest_exam),
        }

    def _build_repair_summary(self, content: Dict) -> Dict:
        issues = content.get("repair_issues", [])
        strategies = content.get("repair_strategies", [])
        response = content.get("response_opinion", "")
        application = content.get("repair_application", {})

        return {
            "issues": issues,
            "strategies": strategies,
            "strategy_count": len(strategies),
            "has_response": bool(response),
            "applied": bool(application.get("applied_at")),
            "application": application,
        }

    def _build_action_guards(self, content: Dict, latest_exam: Optional[ExaminationRecord]) -> Dict:
        guards = {}

        definitions = [
            ("generate_disclosure", "生成交底书", True),
            ("generate_drafting", "生成申请文件", True),
            ("run_examination", "执行审查", True),
            ("generate_repair_strategies", "生成修复策略", True),
            ("apply_repair_strategies", "应用修复策略", True),
            ("generate_response_opinion", "生成答复意见书", True),
        ]

        for action_key, label, strict in definitions:
            missing = missing_action_requirements(content, action_key)
            guards[action_key] = {
                "label": label,
                "ready": len(missing) == 0,
                "missing_items": missing,
                "message": (
                    f"可直接{label}"
                    if not missing
                    else f"暂不可{label}，请先补齐：{'、'.join(missing)}。"
                ),
                "strict": strict,
            }

        if guards["run_examination"]["ready"] and self._exam_is_stale(content, latest_exam):
            guards["run_examination"]["message"] = "申请文件已在上一轮审查后发生变化，建议立即重新审查。"

        delivery_missing = self._required_delivery_gaps(content, latest_exam)
        guards["build_delivery_package"] = {
            "label": "生成交付包",
            "ready": True,
            "missing_items": delivery_missing,
            "message": (
                "可生成交付包预览。"
                if not delivery_missing
                else f"可先生成交付包预览，但仍缺少：{'、'.join(delivery_missing)}。"
            ),
            "strict": False,
        }
        return guards

    def _render_repair_strategy_markdown(self, strategies: List[Dict]) -> str:
        if not strategies:
            return ""

        lines = ["# 修复策略建议", ""]
        for index, strategy in enumerate(strategies, start=1):
            lines.append(f"## 问题 {index}")
            lines.append("")
            lines.append(f"- 问题ID: `{strategy.get('issue_id', 'N/A')}`")
            lines.append("")

            solutions = strategy.get("solutions", [])
            if not solutions:
                lines.append("- 暂未生成可用方案")
                lines.append("")
                continue

            for solution in solutions:
                lines.append(f"### {solution.get('name', '未命名方案')}")
                lines.append("")
                lines.append(f"- 优点: {solution.get('pros', '未说明')}")
                lines.append(f"- 风险: {solution.get('cons', '未说明')}")
                lines.append("")
                modifications = solution.get("modifications", [])
                for mod in modifications:
                    lines.append(f"- 修改位置: {mod.get('location', '未说明')}")
                    lines.append(f"  原文: {mod.get('original', '未提供')}")
                    lines.append(f"  修改为: {mod.get('modified', '未提供')}")
                    lines.append(f"  理由: {mod.get('reason', '未提供')}")
                lines.append("")

        return "\n".join(lines)

    def _has_application_files(self, content: Dict) -> bool:
        return all(content.get(key) for key in ("claims", "specification", "abstract"))

    def _required_delivery_gaps(self, content: Dict, latest_exam: Optional[ExaminationRecord]) -> List[str]:
        deliverables = self._build_deliverables(content, latest_exam)
        return [item["label"] for item in deliverables if item["required"] and not item["ready"]]

    def _title_ready(self, title: Optional[str]) -> bool:
        if not title:
            return False
        return title.strip() != self.PLACEHOLDER_TITLE

    def _check_claims_quality(self, claims: str) -> Tuple[str, str]:
        if not claims:
            return "not_ready", "尚未生成权利要求书"

        if not re.search(r"^1\.\s+", claims, re.MULTILINE):
            return "fail", "缺少独立权利要求 1"

        claim_one = re.search(r"^1\.(.+?)(?=\n\d+\.|\Z)", claims, re.MULTILINE | re.DOTALL)
        if claim_one and "其特征在于" not in claim_one.group(1):
            return "fail", "独立权利要求缺少“其特征在于”，格式不符合常规专利写法"

        dependent_count = len(re.findall(r"^\d+\.\s*根据权利要求\d+", claims, re.MULTILINE))
        if dependent_count == 0:
            return "warning", "已生成独立权利要求，但从属权利要求不足，保护层次偏薄"

        return "pass", f"检测到独立权利要求和 {dependent_count} 条从属权利要求"

    def _render_delivery_package(
        self,
        overview: Dict,
        draft: PatentDraft,
        content: Dict,
        latest_exam: Optional[ExaminationRecord],
    ) -> str:
        prior_art_searches = content.get("prior_art_search", {}).get("searches", [])
        latest_search = prior_art_searches[-1] if prior_art_searches else {}
        risks = overview.get("risks", [])
        next_actions = overview.get("next_actions", [])

        lines = [
            "# 专利项目交付包",
            "",
            "## 项目概览",
            "",
            f"- 项目ID: `{draft.id}`",
            f"- 发明名称: {draft.title}",
            f"- 专利类型: {draft.patent_type}",
            f"- 当前状态: {draft.status}",
            f"- 当前阶段: {overview['current_stage']}",
            f"- 完成度: {overview['progress']}%",
            f"- 质量评分: {overview['quality_checks']['score']}",
            "",
            "## 阶段完成情况",
            "",
        ]

        for stage in overview["stages"]:
            lines.append(f"- {stage['label']}: {stage['status']}")

        lines.extend(
            [
                "",
                "## 关键交付件",
                "",
            ]
        )

        for item in overview["deliverables"]:
            status = "已完成" if item["ready"] else "待补齐"
            lines.append(f"- {item['label']}: {status}；{item['detail']}")

        lines.extend(
            [
                "",
                "## 创意与技术概要",
                "",
                content.get("invention_intent_doc") or "尚未生成发明意图文档。",
                "",
                "## 检索与对比分析",
                "",
                latest_search.get("analysis_report") or "尚未挂接检索分析报告。",
                "",
                "## 技术交底书",
                "",
                content.get("disclosure_doc") or "尚未生成技术交底书。",
                "",
                "## 权利要求书",
                "",
                content.get("claims") or "尚未生成权利要求书。",
                "",
                "## 说明书",
                "",
                content.get("specification") or "尚未生成说明书。",
                "",
                "## 摘要",
                "",
                content.get("abstract") or "尚未生成摘要。",
                "",
                "## 审查与修复",
                "",
                latest_exam.report_content if latest_exam else "尚未执行审查模拟。",
                "",
                self._render_repair_strategy_markdown(content.get("repair_strategies", [])) or "尚未生成修复策略。",
                "",
                content.get("response_opinion") or "尚未生成答复意见书。",
                "",
                "## 主要风险",
                "",
            ]
        )

        if risks:
            for risk in risks:
                lines.append(f"- [{risk['level']}] {risk['description']}")
        else:
            lines.append("- 当前未识别到高优先级风险。")

        lines.extend(
            [
                "",
                "## 下一步建议",
                "",
            ]
        )

        if next_actions:
            for action in next_actions:
                lines.append(f"- {action}")
        else:
            lines.append("- 已形成相对完整的交付包，可进入人工复核与正式申报准备。")

        lines.append("")
        return "\n".join(lines)
