"""
专利分析报告生成器
整合关键词分析、IPC分类、生成Markdown报告
"""

from typing import List, Dict
import logging
from datetime import datetime

from .keyword_analyzer import KeywordAnalyzer
from .ipc_classifier import IPCClassifier

logger = logging.getLogger(__name__)


class PatentAnalysisReporter:
    """专利分析报告生成器"""
    
    def __init__(self):
        """初始化报告生成器"""
        self.keyword_analyzer = KeywordAnalyzer()
        self.ipc_classifier = IPCClassifier()
    
    def generate_report(
        self,
        query: str,
        patents: List[Dict],
        search_id: str = None
    ) -> str:
        """
        生成完整的专利分析报告
        
        Args:
            query: 检索关键词
            patents: 专利列表
            search_id: 检索ID
            
        Returns:
            str: Markdown格式的报告
        """
        logger.info(f"生成分析报告：{len(patents)} 个专利")
        
        if not patents:
            return self._generate_empty_report(query)
        
        # 1. 提取共性关键词
        keywords = self.keyword_analyzer.extract_common_keywords(patents, top_k=15)
        
        # 2. 分析IPC分类
        ipc_analysis = self.ipc_classifier.analyze_ipc_distribution(patents)
        
        # 3. 生成推荐检索语句
        keyword_suggestions = self.keyword_analyzer.suggest_queries(keywords, max_suggestions=5)
        ipc_suggestions = self.ipc_classifier.suggest_ipc_queries(ipc_analysis['ipc_stats'], top_k=3)
        
        # 4. 生成报告
        report = self._build_markdown_report(
            query=query,
            search_id=search_id,
            patent_count=len(patents),
            patents=patents[:10],  # 只显示前10个
            keywords=keywords,
            ipc_analysis=ipc_analysis,
            keyword_suggestions=keyword_suggestions,
            ipc_suggestions=ipc_suggestions
        )
        
        return report
    
    def _build_markdown_report(
        self,
        query: str,
        search_id: str,
        patent_count: int,
        patents: List[Dict],
        keywords: List[Dict],
        ipc_analysis: Dict,
        keyword_suggestions: List[str],
        ipc_suggestions: List[str]
    ) -> str:
        """构建Markdown报告"""
        
        report_parts = []
        
        # 标题
        report_parts.append(f"# 专利技术分析报告\n")
        report_parts.append(f"**检索关键词**: {query}\n")
        report_parts.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        if search_id:
            report_parts.append(f"**检索ID**: `{search_id}`\n")
        report_parts.append(f"**专利数量**: {patent_count} 篇\n")
        report_parts.append("\n---\n")
        
        # 检索概况
        report_parts.append("\n## 📊 检索概况\n")
        report_parts.append(f"- 检索关键词：`{query}`\n")
        report_parts.append(f"- 结果数量：{patent_count} 篇\n")
        report_parts.append(f"- 分析范围：前 {len(patents)} 篇（详细展示）\n")
        
        # 共性关键词分析
        report_parts.append("\n## 🔑 共性关键词分析\n")
        if keywords:
            report_parts.append("\n| 关键词 | 频率 | 权重 | 覆盖率 |\n")
            report_parts.append("|--------|------|------|--------|\n")
            for kw in keywords[:10]:
                report_parts.append(f"| {kw['word']} | {kw['frequency']} | {kw['weight']:.2f} | {kw['coverage']:.0%} |\n")
            
            report_parts.append("\n### 💡 推荐进一步检索\n")
            for suggestion in keyword_suggestions:
                report_parts.append(f"- `{suggestion}`\n")
        else:
            report_parts.append("\n*未提取到有效关键词*\n")
        
        # IPC分类分析
        report_parts.append("\n## 🏷️ IPC分类分布\n")
        if ipc_analysis['ipc_stats']:
            report_parts.append("\n### 详细分类\n")
            report_parts.append("\n| IPC代码 | 数量 | 占比 | 分类名称 |\n")
            report_parts.append("|---------|------|------|----------|\n")
            for ipc in ipc_analysis['ipc_stats'][:10]:
                report_parts.append(f"| `{ipc['code']}` | {ipc['count']} | {ipc['percentage']:.1f}% | {ipc['name']} |\n")
            
            report_parts.append("\n### 大类分布\n")
            for section, count in ipc_analysis['section_stats'].items():
                report_parts.append(f"- **{section}**: {count} 篇\n")
            
            report_parts.append("\n### 🎯 推荐IPC检索\n")
            for suggestion in ipc_suggestions:
                report_parts.append(f"- `{suggestion}`\n")
        else:
            report_parts.append("\n*未提取到IPC分类信息*\n")
        
        # 专利列表
        report_parts.append("\n## 📄 专利列表（前10篇）\n")
        for idx, patent in enumerate(patents, 1):
            report_parts.append(f"\n### {idx}. {patent.get('title', '无标题')}\n")
            report_parts.append(f"- **专利号**: `{patent.get('patent_number', 'N/A')}`\n")
            if patent.get('publication_date'):
                report_parts.append(f"- **公开日期**: {patent['publication_date']}\n")
            if patent.get('link'):
                report_parts.append(f"- **链接**: [查看详情]({patent['link']})\n")
            if patent.get('snippet'):
                snippet = patent['snippet'][:200] + '...' if len(patent['snippet']) > 200 else patent['snippet']
                report_parts.append(f"- **摘要**: {snippet}\n")
        
        # 结论
        report_parts.append("\n---\n")
        report_parts.append("\n## ✅ 分析结论\n")
        
        if keywords:
            top_keywords = ', '.join([kw['word'] for kw in keywords[:5]])
            report_parts.append(f"1. **核心技术关键词**: {top_keywords}\n")
        
        if ipc_analysis['section_stats']:
            top_section = max(ipc_analysis['section_stats'].items(), key=lambda x: x[1])
            report_parts.append(f"2. **主要技术领域**: {top_section[0]} ({top_section[1]}篇)\n")
        
        report_parts.append(f"3. **建议**: 基于共性关键词和IPC分类，可进一步精准检索以获取更相关的专利\n")
        
        return ''.join(report_parts)
    
    def _generate_empty_report(self, query: str) -> str:
        """生成空结果报告"""
        return f"""# 专利技术分析报告

**检索关键词**: {query}
**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**专利数量**: 0 篇

---

## ⚠️ 检索结果为空

未找到与关键词 `{query}` 相关的专利。

### 建议：
1. 尝试使用更通用的关键词
2. 检查关键词拼写
3. 尝试使用同义词或相关术语
"""


# 便捷函数
def generate_analysis_report(query: str, patents: List[Dict]) -> str:
    """
    便捷函数：生成分析报告
    
    Args:
        query: 检索关键词
        patents: 专利列表
        
    Returns:
        str: Markdown报告
    """
    reporter = PatentAnalysisReporter()
    return reporter.generate_report(query, patents)
