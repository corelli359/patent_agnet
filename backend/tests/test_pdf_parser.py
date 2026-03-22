"""
PDF解析器单元测试
"""

import pytest
from pathlib import Path
from shared.utils.pdf_parser import PDFParser, parse_pdf


class TestPDFParser:
    """PDF解析器测试"""
    
    @pytest.fixture
    def parser(self):
        """创建解析器实例"""
        return PDFParser(ocr_enabled=False)
    
    @pytest.fixture
    def sample_pdf_path(self, tmp_path):
        """创建测试PDF文件"""
        # 这里应该使用真实的测试PDF文件
        # 为了演示，使用临时路径
        pdf_path = tmp_path / "test.pdf"
        # 实际测试中应该复制一个真实的PDF文件到这里
        return str(pdf_path)
    
    def test_parser_initialization(self, parser):
        """测试解析器初始化"""
        assert parser is not None
        assert parser.ocr_enabled == False
    
    def test_extract_text_file_not_found(self, parser):
        """测试文件不存在的情况"""
        with pytest.raises(FileNotFoundError):
            parser.extract_text("nonexistent.pdf")
    
    def test_clean_text(self, parser):
        """测试文本清洗"""
        dirty_text = "  Line 1  \n\n  Line 2  \n\n\n  Line 3  "
        clean = parser._clean_text(dirty_text)
        assert clean == "Line 1\nLine 2\nLine 3"
    
    def test_identify_sections(self, parser):
        """测试章节识别"""
        text = """
        一些前言内容
        技术领域
        本发明涉及数据安全
        背景技术
        现有技术存在问题
        发明内容
        本发明提供一种方法
        """
        sections = parser._identify_sections(text.strip())
        assert "技术领域" in sections
        assert "背景技术" in sections
        assert "发明内容" in sections


def test_parse_pdf_convenience_function():
    """测试便捷函数"""
    # 需要真实的PDF文件路径
    # text = parse_pdf("path/to/test.pdf")
    # assert len(text) > 0
    pass  # 占位


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
