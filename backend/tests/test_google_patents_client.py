"""
Google Patents爬虫单元测试
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup
from skills.patent_search.scripts.google_patents_client import GooglePatentsCrawler


class TestGooglePatentsCrawler:
    """Google Patents爬虫测试"""
    
    def test_crawler_initialization(self):
        """测试爬虫初始化"""
        crawler = GooglePatentsCrawler(delay=0.5)
        assert crawler.delay == 0.5
        assert crawler.base_url == "https://patents.google.com"
    
    def test_build_search_url(self):
        """测试搜索URL构建"""
        crawler = GooglePatentsCrawler()
        
        url = crawler._build_search_url(
            query="区块链",
            country="CN",
            before="20241231",
            after="20200101",
            language="zh-CN",
            num=20
        )
        
        assert "区块链" in url or "blockchain" in url  # URL编码后
        assert "country=CN" in url
        assert "before=20241231" in url
        assert "num=20" in url
    
    def test_extract_patent_id_from_url(self):
        """测试从URL提取专利ID"""
        crawler = GooglePatentsCrawler()
        
        assert crawler._extract_patent_id_from_url("/patent/CN123456A/") == "CN123456A"
        assert crawler._extract_patent_id_from_url("/patent/US20200123456A1/") == "US20200123456A1"
        assert crawler._extract_patent_id_from_url("invalid") is None
    
    def test_parse_date_simple(self):
        """测试日期解析"""
        crawler = GooglePatentsCrawler()
        
        assert crawler._parse_date_simple("2023-05-15") == "2023-05-15"
        assert crawler._parse_date_simple("20230515") == "2023-05-15"
        assert crawler._parse_date_simple("2023/5/15") == "2023-05-15"
        assert crawler._parse_date_simple(None) is None
    
    @patch('skills.patent_search.scripts.google_patents_client.requests.Session')
    @patch('skills.patent_search.scripts.google_patents_client.time.sleep')
    def test_search_success(self, mock_sleep, mock_session_class):
        """测试搜索成功（Mock HTTP响应）"""
        # Mock HTML响应
        mock_html = """
        <html>
            <search-result-item>
                <a href="/patent/CN123456A/">区块链加密方法</a>
                <h3>一种区块链加密方法</h3>
                <span class="snippet">本发明涉及...</span>
                <span class="date">2023-05-15</span>
            </search-result-item>
        </html>
        """
        
        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()
        
        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        crawler = GooglePatentsCrawler()
        crawler.session = mock_session  # 替换session
        
        results = crawler.search("区块链", num=10)
        
        assert len(results) > 0
       # assert results[0]['patent_id'] == 'CN123456A'
    
    @patch('skills.patent_search.scripts.google_patents_client.requests.Session')
    @patch('skills.patent_search.scripts.google_patents_client.time.sleep')
    def test_get_patent_detail(self, mock_sleep, mock_session_class):
        """测试获取专利详情"""
        mock_html = """
        <html>
            <meta name="DC.title" content="一种区块链加密方法" />
            <meta name="DC.description" content="本发明涉及..." />
            <meta name="DC.date" content="2023-05-15" />
            <meta name="DC.subject" content="H04L9/00" />
        </html>
        """
        
        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()
        
        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        crawler = GooglePatentsCrawler()
        crawler.session = mock_session
        
        detail = crawler.get_patent_detail("CN123456A")
        
        assert detail is not None
        assert detail['patent_id'] == 'CN123456A'
        assert detail['title'] == '一种区块链加密方法'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
