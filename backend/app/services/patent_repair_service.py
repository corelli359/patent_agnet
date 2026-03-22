"""
专利修复服务 - Skill 5
解析审查意见，提供修改方案
"""

from datetime import datetime
import logging
import re
from typing import Dict, List, Optional, Tuple

from shared.knowledge import PatentGuidelineKnowledgeBase
from shared.utils.llm_client import get_llm_client
from shared.utils.pdf_parser import PDFParser
from shared.db import get_database
from shared.db.models import PatentDraft
from .project_support import (
    create_version_record,
    ensure_version_baseline,
    mark_document_update,
    normalize_content,
    require_action_requirements,
)

logger = logging.getLogger(__name__)


class PatentRepairService:
    """专利修复服务"""
    
    def __init__(self, llm_provider: str = "deepseek"):
        """初始化"""
        self.llm_client = get_llm_client(llm_provider)
        self.guideline_kb = PatentGuidelineKnowledgeBase()
        self.pdf_parser = PDFParser()
        self.db = get_database()
    
    def parse_opinion(self, opinion_text: str) -> Dict:
        """
        解析审查意见
        
        Returns:
            Dict: {issues: List[Dict]}
        """
        prompt = f"""解析以下审查意见通知书，提取问题点:

{opinion_text}

返回JSON格式: 
{{
  "issues": [
    {{
      "id": 1,
      "type": "clarity/novelty/support/formal",
      "severity": "fatal/serious/general",
      "location": "权利要求X/说明书段落X",
      "description": "问题描述",
      "examiner_opinion": "审查员意见原文"
    }}
  ]
}}

只返回JSON，不要其他内容。"""
        
        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.llm_client.chat(messages, temperature=0.2, max_tokens=1500)
            
            import json
            result = json.loads(response.strip().strip('```json').strip('```'))
            return result
        except Exception as e:
            logger.error(f"审查意见解析失败: {e}")
            return {'issues': []}
    
    def generate_strategies(self, issues: List[Dict], draft_id: str) -> Dict:
        """
        生成修改方案
        
        Returns:
            Dict: {strategies: List[Dict]}
        """
        # 获取原文件
        with self.db.get_session() as session:
            draft = session.query(PatentDraft).filter_by(id=draft_id).first()
            if not draft:
                raise ValueError(f"草稿不存在: {draft_id}")

            ensure_version_baseline(session, draft)
            content = normalize_content(draft.content)
            require_action_requirements(content, "generate_repair_strategies", "生成修改方案")
            claims = content.get('claims', '')
            specification = content.get('specification', '')

        if not issues:
            raise ValueError("无法生成修改方案，请先提供至少 1 个待修复问题。")
        
        # 为每个问题生成修改策略
        strategies = []
        
        for issue in issues:
            strategy = self._generate_single_strategy(issue, claims, specification)
            strategies.append(strategy)

        with self.db.get_session() as session:
            draft = session.query(PatentDraft).filter_by(id=draft_id).first()
            if draft:
                ensure_version_baseline(session, draft)
                content = normalize_content(draft.content)
                content['repair_issues'] = issues
                content['repair_strategies'] = strategies
                draft.content = content
                create_version_record(
                    session,
                    draft,
                    change_summary="生成修复策略",
                    document_key="repair_strategies",
                    changed_fields=["repair_issues", "repair_strategies"],
                )
                session.add(draft)

        return {'strategies': strategies}
    
    def _generate_single_strategy(self, issue: Dict, claims: str, spec: str) -> Dict:
        """为单个问题生成修改策略"""
        topic = issue.get('type', 'repair') or 'repair'
        passages = self.guideline_kb.retrieve(topic, claims + "\n" + spec + "\n" + str(issue), top_k=3)
        basis_context = self.guideline_kb.format_passages(passages)
        prompt = f"""作为专利代理师，针对以下审查意见问题，提供修改方案:

《专利审查指南》依据:
{basis_context}

问题类型: {issue.get('type', '')}
问题位置: {issue.get('location', '')}
问题描述: {issue.get('description', '')}
审查员意见: {issue.get('examiner_opinion', '')}

原权利要求书:
{claims[:500]}...

原说明书:
{spec[:500]}...

请提供2个修改方案（保守方案和积极方案），包括:
1. 修改位置
2. 原文
3. 修改为
4. 修改理由
5. 优劣分析

返回JSON格式: 
{{
  "issue_id": {issue.get('id', '')},
  "solutions": [
    {{
      "name": "方案1：保守修改",
      "modifications": [
        {{"location": "", "original": "", "modified": "", "reason": ""}}
      ],
      "pros": "",
      "cons": ""
    }}
  ]
}}

只返回JSON，不要其他内容。"""
        
        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.llm_client.chat(messages, temperature=0.4, max_tokens=1500)
            
            import json
            strategy = json.loads(response.strip().strip('```json').strip('```'))
            return strategy
        except Exception as e:
            logger.error(f"策略生成失败: {e}")
            return {
                'issue_id': issue.get('id', ''),
                'solutions': []
            }
    
    def generate_response(self, issues: List[Dict], strategies: List[Dict], draft_id: str) -> str:
        """
        生成答复意见书
        
        Returns:
            str: 答复意见书内容  
        """
        if not issues:
            raise ValueError("无法生成答复意见书，请先提供待回应的问题列表。")
        if not strategies:
            raise ValueError("无法生成答复意见书，请先生成修复策略。")

        with self.db.get_session() as session:
            draft = session.query(PatentDraft).filter_by(id=draft_id).first()
            if not draft:
                raise ValueError(f"草稿不存在: {draft_id}")

            ensure_version_baseline(session, draft)
            content = normalize_content(draft.content)
            require_action_requirements(content, "generate_response_opinion", "生成答复意见书")

        topics = {issue.get('type', 'repair') or 'repair' for issue in issues}
        passages = []
        for topic in topics:
            passages.extend(self.guideline_kb.retrieve(topic, str(issues) + str(strategies), top_k=2))
        # 标题去重
        unique_passages = []
        seen_titles = set()
        for passage in passages:
            title = passage.get("title")
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_passages.append(passage)
        basis_context = self.guideline_kb.format_passages(unique_passages[:4])

        prompt = f"""作为专利代理师，生成审查意见答复书:

《专利审查指南》与相关依据:
{basis_context}

审查意见问题:
{issues}

修改方案:
{strategies}

要求:
1. 逐条回应审查意见
2. 引用《专利法》和《审查指南》条款
3. 说明修改内容和理由
4. 格式规范

生成完整的答复意见书（Markdown格式）。"""
        
        messages = [{"role": "user", "content": prompt}]
        response_doc = self.llm_client.chat(messages, temperature=0.3, max_tokens=2000)
        
        # 保存到数据库
        with self.db.get_session() as session:
            draft = session.query(PatentDraft).filter_by(id=draft_id).first()
            if draft:
                ensure_version_baseline(session, draft)
                content = normalize_content(draft.content)
                content['repair_issues'] = issues
                content['repair_strategies'] = strategies
                content['response_opinion'] = response_doc
                draft.content = content
                create_version_record(
                    session,
                    draft,
                    change_summary="生成答复意见书",
                    document_key="response_opinion",
                    changed_fields=["repair_issues", "repair_strategies", "response_opinion"],
                )
                session.add(draft)
        
        return response_doc

    def apply_strategies(self, draft_id: str, mode: str = "conservative") -> Dict:
        """
        将修复策略应用到权利要求书和说明书，形成修订稿

        Returns:
            Dict: {claims, specification, application_summary}
        """
        with self.db.get_session() as session:
            draft = session.query(PatentDraft).filter_by(id=draft_id).first()
            if not draft:
                raise ValueError(f"草稿不存在: {draft_id}")

            ensure_version_baseline(session, draft)
            content = normalize_content(draft.content)
            require_action_requirements(content, "apply_repair_strategies", "应用修复策略")

            strategies = content.get("repair_strategies", [])
            issues = content.get("repair_issues", [])
            claims = content.get("claims", "")
            specification = content.get("specification", "")
            latest_response = content.get("response_opinion", "")

            if not strategies:
                raise ValueError("无法应用修复策略，请先生成修复策略。")

            selected_solutions = self._select_solutions(strategies, mode)
            if not selected_solutions:
                raise ValueError("当前修复策略中没有可应用的方案。")

            revised_claims, revised_specification, applied_items, unresolved_items = self._apply_selected_solutions(
                claims,
                specification,
                selected_solutions,
            )

            if not applied_items:
                raise ValueError("修复策略未能自动落稿，请先调整修改位置描述，或直接手工编辑文稿。")

            content["claims"] = revised_claims
            content["specification"] = revised_specification
            content["repair_application"] = {
                "applied_at": datetime.now().isoformat(),
                "mode": mode,
                "issue_count": len(issues),
                "solution_count": len(selected_solutions),
                "applied_items": applied_items,
                "unresolved_items": unresolved_items,
                "has_response_opinion": bool(latest_response),
            }
            content = mark_document_update(content, ["claims", "specification"], current_stage="examination")
            draft.content = content

            create_version_record(
                session,
                draft,
                change_summary="应用修复策略并生成修订稿",
                document_key="claims",
                changed_fields=["claims", "specification", "repair_application"],
            )
            session.add(draft)

        return {
            "draft_id": draft_id,
            "claims": revised_claims,
            "specification": revised_specification,
            "application_summary": {
                "mode": mode,
                "solution_count": len(selected_solutions),
                "applied_count": len(applied_items),
                "unresolved_count": len(unresolved_items),
                "applied_items": applied_items,
                "unresolved_items": unresolved_items,
            },
        }

    def _select_solutions(self, strategies: List[Dict], mode: str) -> List[Dict]:
        selected = []
        pick_last = mode == "aggressive"
        for strategy in strategies:
            solutions = strategy.get("solutions", [])
            if not solutions:
                continue
            solution = solutions[-1] if pick_last else solutions[0]
            selected.append(
                {
                    "issue_id": strategy.get("issue_id"),
                    "solution_name": solution.get("name", "未命名方案"),
                    "modifications": solution.get("modifications", []),
                }
            )
        return selected

    def _apply_selected_solutions(
        self,
        claims: str,
        specification: str,
        selected_solutions: List[Dict],
    ) -> Tuple[str, str, List[Dict], List[Dict]]:
        revised_claims = claims
        revised_specification = specification
        applied_items = []
        unresolved_items = []

        for item in selected_solutions:
            issue_id = item.get("issue_id")
            solution_name = item.get("solution_name", "未命名方案")
            for mod in item.get("modifications", []):
                location = mod.get("location", "")
                original = (mod.get("original") or "").strip()
                modified = (mod.get("modified") or "").strip()
                reason = mod.get("reason", "")

                target = self._resolve_target_document(location, original, revised_claims, revised_specification)
                changed = False

                if target == "claims":
                    revised_claims, changed = self._apply_single_modification(
                        revised_claims,
                        location,
                        original,
                        modified,
                        document_type="claims",
                    )
                elif target == "specification":
                    revised_specification, changed = self._apply_single_modification(
                        revised_specification,
                        location,
                        original,
                        modified,
                        document_type="specification",
                    )

                record = {
                    "issue_id": issue_id,
                    "solution_name": solution_name,
                    "location": location,
                    "reason": reason,
                    "target": target or "unknown",
                }
                if changed:
                    record["modified"] = modified
                    applied_items.append(record)
                else:
                    record["original"] = original
                    record["modified"] = modified
                    unresolved_items.append(record)

        return revised_claims, revised_specification, applied_items, unresolved_items

    def _resolve_target_document(
        self,
        location: str,
        original: str,
        claims: str,
        specification: str,
    ) -> Optional[str]:
        if "权利要求" in location:
            return "claims"
        if "说明书" in location or "段落" in location or "实施例" in location:
            return "specification"
        if original and original in claims:
            return "claims"
        if original and original in specification:
            return "specification"
        return None

    def _apply_single_modification(
        self,
        document_text: str,
        location: str,
        original: str,
        modified: str,
        document_type: str,
    ) -> Tuple[str, bool]:
        if not modified:
            return document_text, False

        if original and original in document_text:
            return document_text.replace(original, modified, 1), True

        if document_type == "claims":
            claim_no = self._extract_claim_number(location)
            if claim_no is not None:
                replaced = self._replace_claim_by_number(document_text, claim_no, modified)
                if replaced is not None:
                    return replaced, True
        else:
            paragraph_no = self._extract_paragraph_number(location)
            if paragraph_no is not None:
                replaced = self._replace_spec_paragraph(document_text, paragraph_no, modified)
                if replaced is not None:
                    return replaced, True

        return document_text, False

    def _extract_claim_number(self, location: str) -> Optional[int]:
        matched = re.search(r"权利要求\s*(\d+)", location)
        if not matched:
            return None
        return int(matched.group(1))

    def _extract_paragraph_number(self, location: str) -> Optional[str]:
        matched = re.search(r"\[(\d{4})\]", location)
        if matched:
            return matched.group(1)
        matched = re.search(r"段落\s*(\d+)", location)
        if matched:
            return matched.group(1).zfill(4)
        return None

    def _replace_claim_by_number(self, claims_text: str, claim_no: int, modified: str) -> Optional[str]:
        pattern = re.compile(rf"(?ms)^(?P<prefix>{claim_no}\.\s*)(?P<body>.*?)(?=^\d+\.\s|\Z)")
        matched = pattern.search(claims_text)
        if not matched:
            return None

        replacement_body = modified.strip()
        normalized = replacement_body
        if not replacement_body.startswith(f"{claim_no}."):
            normalized = f"{claim_no}. {replacement_body}"

        start, end = matched.span()
        return claims_text[:start] + normalized + claims_text[end:]

    def _replace_spec_paragraph(self, specification_text: str, paragraph_no: str, modified: str) -> Optional[str]:
        pattern = re.compile(rf"(?m)^\[{paragraph_no}\].*$")
        matched = pattern.search(specification_text)
        if not matched:
            return None

        replacement = modified.strip()
        if not replacement.startswith(f"[{paragraph_no}]"):
            replacement = f"[{paragraph_no}] {replacement}"

        start, end = matched.span()
        return specification_text[:start] + replacement + specification_text[end:]
