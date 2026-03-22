"""
文档生成器 - Skill 1: 发明意图总结
基于提取的意图生成Markdown格式的发明意图文档
"""

import logging
from typing import Dict, Any
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class DocumentGenerator:
    """文档生成器"""
    
    def __init__(self):
        """初始化"""
        pass
    
    def generate(self, intent: Dict[str, Any], output_path: str = None) -> str:
        """
        生成发明意图文档
        
        Args:
            intent: 发明意图字典
            output_path: 输出文件路径（可选）
            
        Returns:
            str: Markdown格式的文档内容
        """
        # 生成文档内容
        doc_content = self._render_document(intent)
        
        # 如果指定了输出路径，保存文件
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(doc_content)
            logger.info(f"发明意图文档已保存: {output_path}")
        
        return doc_content
    
    def _render_document(self, intent: Dict[str, Any]) -> str:
        """渲染文档"""
        # 模板
        template = """# 发明意图文档

> 生成时间: {timestamp}

## 发明名称

{title}

## 技术领域

{technical_field}

## 技术问题

{technical_problem}

## 现有技术的不足

{prior_art_defects}

## 解决方案

{solution}

{key_steps_section}

## 预期效果

{effect}

## 创新点

{innovation_points}

---

**说明**: 本文档由AI辅助生成，仅供参考。在正式申请前，请咨询专业专利代理人。
"""
        
        # 准备数据
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 格式化关键步骤
        key_steps = intent.get('key_steps', [])
        if isinstance(key_steps, list) and key_steps:
            key_steps_section = "### 关键技术步骤\n\n"
            for i, step in enumerate(key_steps, 1):
                key_steps_section += f"{i}. {step}\n"
        else:
            key_steps_section = ""
        
        # 格式化创新点
        innovation_points = intent.get('innovation_points', [])
        if isinstance(innovation_points, list) and innovation_points:
            innovation_str = "\n".join([f"- {point}" for point in innovation_points])
        else:
            innovation_str = str(innovation_points) if innovation_points else "（待补充）"
        
        # 格式化现有技术不足
        prior_art_defects = intent.get('prior_art_defects', '')
        if isinstance(prior_art_defects, list):
            prior_art_str = "\n".join([f"- {defect}" for defect in prior_art_defects])
        else:
            prior_art_str = prior_art_defects
        
        # 格式化预期效果
        effect = intent.get('effect', '')
        if isinstance(effect, list):
            effect_str = "\n".join([f"- {e}" for e in effect])
        else:
            effect_str = effect
        
        # 渲染
        doc = template.format(
            timestamp=timestamp,
            title=intent.get('title', '（待补充）'),
            technical_field=intent.get('technical_field', '（待补充）'),
            technical_problem=intent.get('technical_problem', '（待补充）'),
            prior_art_defects=prior_art_str or '（待补充）',
            solution=intent.get('solution', '（待补充）'),
            key_steps_section=key_steps_section,
            effect=effect_str or '（待补充）',
            innovation_points=innovation_str
        )
        
        return doc
