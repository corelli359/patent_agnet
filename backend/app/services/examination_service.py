"""
实质审查模拟服务 - Skill 4
模拟审查员审查，识别缺陷
"""

import logging
from typing import Dict, List

from shared.utils.llm_client import get_llm_client
from shared.knowledge import PatentGuidelineKnowledgeBase
from shared.db import get_database
from shared.db.models import PatentDraft, ExaminationRecord
from .patent_search_service import PatentSearchService
from .project_support import normalize_content, require_action_requirements

logger = logging.getLogger(__name__)


class ExaminationService:
    """实质审查服务"""
    
    def __init__(self, llm_provider: str = "deepseek"):
        """初始化"""
        self.llm_client = get_llm_client(llm_provider)
        self.guideline_kb = PatentGuidelineKnowledgeBase()
        self.db = get_database()
        self.search_service = PatentSearchService()
    
    def examine(self, draft_id: str) -> Dict:
        """
        执行实质审查
        
        Returns:
            Dict: {report, defects, status}
        """
        # 获取申请文件
        with self.db.get_session() as session:
            draft = session.query(PatentDraft).filter_by(id=draft_id).first()
            if not draft:
                raise ValueError(f"草稿不存在: {draft_id}")

            content = normalize_content(draft.content)
            require_action_requirements(content, "run_examination", "执行审查")
            claims = content.get('claims', '')
            specification = content.get('specification', '')
            intent = content.get('invention_intent', {})
        
        # 各项审查
        defects = []
        
        # 1. 形式审查
        formal_defects = self._formal_examination(claims, specification)
        defects.extend(formal_defects)
        
        # 2. 清楚性审查
        clarity_defects = self._clarity_examination(claims, specification)
        defects.extend(clarity_defects)
        
        # 3. 支持性/说明书支撑审查
        support_defects = self._support_examination(claims, specification)
        defects.extend(support_defects)

        # 4. 新颖性审查
        novelty_defects = self._novelty_examination(intent, claims)
        defects.extend(novelty_defects)
        
        # 生成报告
        report = self._generate_report(defects, claims, specification)
        
        # 判定状态
        status = self._determine_status(defects)
        
        # 保存审查记录
        with self.db.get_session() as session:
            exam_record = ExaminationRecord(
                draft_id=draft_id,
                examination_type='comprehensive',
                defects=defects,
                status=status,
                report_content=report
            )
            session.add(exam_record)
            session.commit()
        
        return {
            'report': report,
            'defects': defects,
            'status': status
        }
    
    def _formal_examination(self, claims: str, spec: str) -> List[Dict]:
        """形式审查"""
        defects = []
        passages = self.guideline_kb.retrieve("formal", claims + "\n" + spec, top_k=2)
        bases = self._passage_titles(passages)
        
        # 检查权利要求是否存在
        if not claims or len(claims) < 100:
            defects.append({
                'type': 'formal',
                'severity': 'fatal',
                'location': '权利要求书',
                'description': '权利要求书缺失或过短',
                'basis': bases,
            })
        
        # 检查说明书是否存在
        if not spec or len(spec) < 500:
            defects.append({
                'type': 'formal',
                'severity': 'fatal',
                'location': '说明书',
                'description': '说明书缺失或过短',
                'basis': bases,
            })
        
        # 检查独立权利要求格式
        if "其特征在于" not in claims:
            defects.append({
                'type': 'formal',
                'severity': 'serious',
                'location': '权利要求1',
                'description': '独立权利要求缺少"其特征在于"',
                'basis': bases,
            })
        
        return defects
    
    def _clarity_examination(self, claims: str, spec: str) -> List[Dict]:
        """清楚性审查"""
        passages = self.guideline_kb.retrieve("clarity", claims + "\n" + spec, top_k=3)
        basis_context = self.guideline_kb.format_passages(passages)
        prompt = f"""作为专利审查员，检查以下专利文件的清楚性问题:

《专利审查指南》依据:
{basis_context}

权利要求书:
{claims[:500]}...

说明书:
{spec[:500]}...

请识别:
1. 表述不清晰的地方
2. 术语定义不明确
3. 范围不明确

返回JSON列表: [{{"type": "clarity", "severity": "serious/general", "location": "位置", "description": "描述", "basis": ["引用的依据标题"]}}]

只返回JSON，不要其他内容。"""
        
        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.llm_client.chat(messages, temperature=0.2, max_tokens=800)
            
            import json
            defects = json.loads(response.strip().strip('```json').strip('```'))
            return self._normalize_defects(defects, "clarity", self._passage_titles(passages))
        except:
            return []

    def _support_examination(self, claims: str, spec: str) -> List[Dict]:
        """支持性/说明书公开充分审查"""
        passages = self.guideline_kb.retrieve("support", claims + "\n" + spec, top_k=3)
        basis_context = self.guideline_kb.format_passages(passages)
        prompt = f"""作为专利审查员，依据以下《专利审查指南》节选，对专利文件进行支持性审查:

{basis_context}

权利要求书:
{claims[:700]}...

说明书:
{spec[:900]}...

请识别：
1. 权利要求是否得到说明书支持
2. 关键技术特征是否公开充分
3. 是否存在仅有结果限定、没有技术手段支撑的表述

返回JSON列表: [{{"type": "support", "severity": "serious/general", "location": "位置", "description": "描述", "basis": ["引用的依据标题"]}}]

只返回JSON，不要其他内容。"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.llm_client.chat(messages, temperature=0.2, max_tokens=900)
            import json
            defects = json.loads(response.strip().strip('```json').strip('```'))
            return self._normalize_defects(defects, "support", self._passage_titles(passages))
        except Exception:
            return []
    
    def _novelty_examination(self, intent: Dict, claims: str) -> List[Dict]:
        """新颖性审查（基于检索结果和审查指南）"""
        # 使用Skill 6检索对比文件
        passages = self.guideline_kb.retrieve("novelty", claims + "\n" + str(intent), top_k=3)
        bases = self._passage_titles(passages)
        try:
            title = intent.get('title', '')
            if not title:
                return []
            
            # 简单检索
            search_results = self.search_service.search(
                query=title,
                max_results=3,
                user_id='examination'
            )
            
            if search_results['result_count'] > 0:
                top_titles = [
                    patent.get('title', '未命名对比文件')
                    for patent in search_results.get('results', [])[:3]
                ]
                description = (
                    f"检索到{search_results['result_count']}篇相似专利，"
                    f"重点对比文件包括：{'；'.join(top_titles)}。建议结合审查指南的新颖性判断标准逐项比对区别特征。"
                )
                return [{
                    'type': 'novelty',
                    'severity': 'warning',
                    'location': '整体方案',
                    'description': description,
                    'basis': bases,
                }]
        except:
            pass
        
        return []
    
    def _generate_report(self, defects: List[Dict], claims: str, spec: str) -> str:
        """生成审查报告"""
        # 分类统计
        fatal = [d for d in defects if d.get('severity') == 'fatal']
        serious = [d for d in defects if d.get('severity') == 'serious']
        general = [d for d in defects if d.get('severity') in ['general', 'warning']]
        
        report = f"""# 专利审查报告

## 审查概况

- 致命缺陷: {len(fatal)}个
- 严重缺陷: {len(serious)}个
- 一般缺陷: {len(general)}个

## 缺陷详情

"""
        
        for i, defect in enumerate(defects, 1):
            report += f"""### 缺陷{i}: {defect.get('type', '')} ({defect.get('severity', '')})

- **位置**: {defect.get('location', '')}
- **描述**: {defect.get('description', '')}
"""
            bases = defect.get('basis', [])
            if bases:
                report += f"- **依据**: {'；'.join(bases)}\n"

        # 结论
        if len(fatal) > 0:
            conclusion = "存在致命缺陷，建议修改后重新审查"
        elif len(serious) > 0:
            conclusion = "存在严重缺陷，建议修改"
        else:
            conclusion = "形式审查通过，建议进行深度新颖性/创造性分析"
        
        report += f"\n## 审查结论\n\n{conclusion}\n"
        
        return report
    
    def _determine_status(self, defects: List[Dict]) -> str:
        """判定状态"""
        fatal = [d for d in defects if d.get('severity') == 'fatal']
        serious = [d for d in defects if d.get('severity') == 'serious']
        
        if fatal:
            return 'fail'
        elif serious:
            return 'warning'
        else:
            return 'pass'

    def _passage_titles(self, passages: List[Dict]) -> List[str]:
        return [item["title"] for item in passages if item.get("title")]

    def _normalize_defects(self, defects, default_type: str, default_basis: List[str]) -> List[Dict]:
        if not isinstance(defects, list):
            return []

        normalized = []
        for defect in defects:
            if not isinstance(defect, dict):
                continue
            item = defect.copy()
            item.setdefault("type", default_type)
            item.setdefault("basis", default_basis)
            normalized.append(item)
        return normalized
