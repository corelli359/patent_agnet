"""
PDF解析工具
支持文本提取、结构识别，可选OCR功能
"""

import pdfplumber
from typing import Dict, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PDFParser:
    """PDF文档解析器"""
    
    def __init__(self, ocr_enabled: bool = False):
        """
        初始化PDF解析器
        
        Args:
            ocr_enabled: 是否启用OCR（用于扫描件）
        """
        self.ocr_enabled = ocr_enabled
        if ocr_enabled:
            try:
                import pytesseract
                self.ocr_available = True
            except ImportError:
                logger.warning("pytesseract未安装，OCR功能不可用")
                self.ocr_available = False
    
    def extract_text(self, pdf_path: str) -> str:
        """
        提取PDF全文文本
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            str: 提取的文本内容
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
        
        try:
            text = self._extract_with_pdfplumber(pdf_path)
            
            # 如果提取内容太少且启用了OCR，尝试OCR
            if len(text.strip()) < 100 and self.ocr_enabled and self.ocr_available:
                logger.info(f"文本内容较少，尝试OCR: {pdf_path}")
                text = self._extract_with_ocr(pdf_path)
            
            return self._clean_text(text)
        
        except Exception as e:
            logger.error(f"PDF解析失败: {pdf_path}, 错误: {e}")
            raise
    
    def extract_sections(self, pdf_path: str) -> Dict[str, str]:
        """
        提取PDF章节（标题-内容映射）
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            Dict[str, str]: 章节字典 {"章节标题": "章节内容"}
        """
        full_text = self.extract_text(pdf_path)
        sections = self._identify_sections(full_text)
        return sections
    
    def extract_metadata(self, pdf_path: str) -> Dict:
        """
        提取PDF元数据
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            Dict: 元数据字典
        """
        with pdfplumber.open(pdf_path) as pdf:
            metadata = pdf.metadata or {}
            return {
                'title': metadata.get('Title', ''),
                'author': metadata.get('Author', ''),
                'subject': metadata.get('Subject', ''),
                'creator': metadata.get('Creator', ''),
                'page_count': len(pdf.pages)
            }
    
    def _extract_with_pdfplumber(self, pdf_path: Path) -> str:
        """使用pdfplumber提取文本"""
        text_parts = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        
        return '\n'.join(text_parts)
    
    def _extract_with_ocr(self, pdf_path: Path) -> str:
        """使用OCR提取文本（扫描件）"""
        if not self.ocr_available:
            return ""
        
        import pytesseract
        from pdf2image import convert_from_path
        
        text_parts = []
        images = convert_from_path(pdf_path)
        
        for i, image in enumerate(images):
            logger.info(f"OCR处理第 {i+1}/{len(images)} 页")
            text = pytesseract.image_to_string(image, lang='chi_sim+eng')
            text_parts.append(text)
        
        return '\n'.join(text_parts)
    
    def _clean_text(self, text: str) -> str:
        """清洗文本内容"""
        # 移除多余空白
        lines = [line.strip() for line in text.split('\n')]
        # 移除空行
        lines = [line for line in lines if line]
        # 合并
        return '\n'.join(lines)
    
    def _identify_sections(self, text: str) -> Dict[str, str]:
        """
        识别文档章节结构
        
        基于常见的专利文档章节标题
        """
        import re
        
        # 专利文档常见章节标题
        section_patterns = [
            r'^技术领域',
            r'^背景技术',
            r'^发明内容',
            r'^附图说明',
            r'^具体实施方式',
            r'^权利要求书?',
            r'^说明书摘要',
        ]
        
        sections = {}
        current_section = "前言"
        current_content = []
        
        for line in text.split('\n'):
            # 检查是否是新章节
            is_section_title = False
            for pattern in section_patterns:
                if re.match(pattern, line.strip()):
                    # 保存前一章节
                    if current_content:
                        sections[current_section] = '\n'.join(current_content)
                    # 开始新章节
                    current_section = line.strip()
                    current_content = []
                    is_section_title = True
                    break
            
            if not is_section_title:
                current_content.append(line)
        
        # 保存最后一章节
        if current_content:
            sections[current_section] = '\n'.join(current_content)
        
        return sections


# 便捷函数
def parse_pdf(pdf_path: str, ocr: bool = False) -> str:
    """
    快捷函数：提取PDF文本
    
    Args:
        pdf_path: PDF文件路径
        ocr: 是否启用OCR
        
    Returns:
        str: 文本内容
    """
    parser = PDFParser(ocr_enabled=ocr)
    return parser.extract_text(pdf_path)
