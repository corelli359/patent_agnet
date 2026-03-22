"""
Markdown格式化工具
用于专利文档格式化、模板渲染
"""

import re
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, Template
import os
import logging

logger = logging.getLogger(__name__)


class MarkdownFormatter:
    """Markdown格式化器"""
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        初始化
        
        Args:
            templates_dir: 模板目录路径
        """
        self.templates_dir = templates_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'data', 'templates'
        )
        
        # 初始化Jinja2环境
        if os.path.exists(self.templates_dir):
            self.env = Environment(loader=FileSystemLoader(self.templates_dir))
        else:
            logger.warning(f"模板目录不存在: {self.templates_dir}")
            self.env = None
    
    def format_patent_doc(self, content: str, doc_type: str = "specification") -> str:
        """
        格式化专利文档
        
        Args:
            content: 原始内容
            doc_type: 文档类型 (specification/claims/abstract)
            
        Returns:
            str: 格式化后的内容
        """
        if doc_type == "specification":
            # 说明书需要段落编号
            return self.auto_number_paragraphs(content)
        elif doc_type == "claims":
            # 权利要求书需要检查单句表达
            return self.format_claims(content)
        else:
            return content
    
    def auto_number_paragraphs(self, content: str) -> str:
        """
        自动给说明书段落编号 [0001], [0002], ...
        
        Args:
            content: 原始内容
            
        Returns:
            str: 编号后的内容
        """
        lines = content.split('\n')
        result = []
        paragraph_num = 1
        
        for line in lines:
            # 跳过空行和标题
            if not line.strip() or line.strip().startswith('#'):
                result.append(line)
                continue
            
            # 检查是否已有编号
            if re.match(r'^\[\d{4}\]', line.strip()):
                result.append(line)
                # 更新计数器
                match = re.match(r'^\[(\d{4})\]', line.strip())
                if match:
                    paragraph_num = int(match.group(1)) + 1
            else:
                # 添加编号
                numbered_line = f"[{paragraph_num:04d}] {line.strip()}"
                result.append(numbered_line)
                paragraph_num += 1
        
        return '\n'.join(result)
    
    def format_claims(self, content: str) -> str:
        """
        格式化权利要求书
        
        Args:
            content: 原始权利要求内容
            
        Returns:
            str: 格式化后的权利要求
        """
        lines = content.split('\n')
        result = []
        
        for line in lines:
            # 保留标题和空行
            if not line.strip() or line.strip().startswith('#'):
                result.append(line)
                continue
            
            # 检查权利要求编号
            claim_match = re.match(r'^(\d+)\.\s*(.+)', line.strip())
            if claim_match:
                claim_num = claim_match.group(1)
                claim_content = claim_match.group(2)
                
                # 确保独立权利要求包含"其特征在于"
                if claim_num == "1" and "其特征在于" not in claim_content:
                    logger.warning("独立权利要求缺少'其特征在于'")
                
                result.append(line)
            else:
                result.append(line)
        
        return '\n'.join(result)
    
    def render_template(self, template_name: str, **kwargs) -> str:
        """
        渲染模板
        
        Args:
            template_name: 模板文件名
            **kwargs: 模板变量
            
        Returns:
            str: 渲染后的内容
        """
        if not self.env:
            logger.error("模板环境未初始化")
            return ""
        
        try:
            template = self.env.get_template(template_name)
            return template.render(**kwargs)
        except Exception as e:
            logger.error(f"模板渲染失败: {e}")
            return ""
    
    def render_template_string(self, template_str: str, **kwargs) -> str:
        """
        渲染模板字符串
        
        Args:
            template_str: 模板字符串
            **kwargs: 模板变量
            
        Returns:
            str: 渲染后的内容
        """
        try:
            template = Template(template_str)
            return template.render(**kwargs)
        except Exception as e:
            logger.error(f"模板字符串渲染失败: {e}")
            return ""
    
    def validate_claims_format(self, claims: str) -> Dict[str, Any]:
        """
        校验权利要求格式
        
        Args:
            claims: 权利要求内容
            
        Returns:
            Dict: 校验结果 {valid: bool, errors: List[str]}
        """
        errors = []
        
        # 检查是否有独立权利要求（权利要求1）
        if not re.search(r'^1\.\s+', claims, re.MULTILINE):
            errors.append("缺少独立权利要求（权利要求1）")
        
        # 检查独立权利要求是否包含"其特征在于"
        claim_1_match = re.search(r'^1\.(.+?)(?=\n\d+\.|\Z)', claims, re.MULTILINE | re.DOTALL)
        if claim_1_match:
            claim_1_content = claim_1_match.group(1)
            if "其特征在于" not in claim_1_content:
                errors.append("独立权利要求缺少'其特征在于'")
        
        # 检查从属权利要求是否正确引用
        dependent_claims = re.findall(r'^(\d+)\.\s*根据权利要求(\d+)', claims, re.MULTILINE)
        for claim_num, ref_num in dependent_claims:
            if int(ref_num) >= int(claim_num):
                errors.append(f"权利要求{claim_num}引用了后续的权利要求{ref_num}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def extract_claims_list(self, claims: str) -> list:
        """
        提取权利要求列表
        
        Args:
            claims: 权利要求内容
            
        Returns:
            List[Dict]: 权利要求列表 [{num: 1, content: "...", type: "independent"}, ...]
        """
        results = []
        
        # 匹配所有权利要求
        claim_pattern = re.compile(r'^(\d+)\.\s*(.+?)(?=\n\d+\.|\Z)', re.MULTILINE | re.DOTALL)
        matches = claim_pattern.findall(claims)
        
        for num, content in matches:
            claim_type = "independent" if num == "1" else "dependent"
            
            # 检查是否引用了其他权利要求
            if re.search(r'根据权利要求\d+', content):
                claim_type = "dependent"
            
            results.append({
                'num': int(num),
                'content': content.strip(),
                'type': claim_type
            })
        
        return results


# 便捷函数
def get_formatter(templates_dir: Optional[str] = None) -> MarkdownFormatter:
    """
    获取格式化器实例
    
    Args:
        templates_dir: 模板目录
        
    Returns:
        MarkdownFormatter: 格式化器实例
    """
    return MarkdownFormatter(templates_dir=templates_dir)
