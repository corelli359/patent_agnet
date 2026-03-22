"""
Google Patents高级检索爬虫
完整支持Search Tools功能
"""

from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import List, Dict, Optional
import re
import time
import logging

logger = logging.getLogger(__name__)


class GooglePatentsCrawler:
    """兼容旧测试与脚本的轻量爬虫"""

    def __init__(self, delay: float = 1.0):
        self.base_url = "https://patents.google.com"
        self.delay = delay
        self.session = requests.Session()

    def _build_search_url(
        self,
        query: str,
        country: Optional[str] = None,
        before: Optional[str] = None,
        after: Optional[str] = None,
        language: str = "zh-CN",
        num: int = 20,
    ) -> str:
        params = [f"q={query}", f"hl={language}", f"num={num}"]
        if country:
            params.append(f"country={country}")
        if before:
            params.append(f"before={before}")
        if after:
            params.append(f"after={after}")

        return f"{self.base_url}/?{'&'.join(params)}"

    def _extract_patent_id_from_url(self, url: str) -> Optional[str]:
        match = re.search(r"/patent/([^/]+)/?", url or "")
        return match.group(1) if match else None

    def _parse_date_simple(self, raw_date: Optional[str]) -> Optional[str]:
        if not raw_date:
            return None

        value = raw_date.strip()
        patterns = [
            (r"^(\d{4})-(\d{2})-(\d{2})$", "{0}-{1}-{2}"),
            (r"^(\d{4})(\d{2})(\d{2})$", "{0}-{1}-{2}"),
            (r"^(\d{4})/(\d{1,2})/(\d{1,2})$", "{0}-{1:0>2}-{2:0>2}"),
        ]
        for pattern, template in patterns:
            match = re.match(pattern, value)
            if match:
                return template.format(*match.groups())

        return None

    def search(
        self,
        query: str,
        country: Optional[str] = None,
        before: Optional[str] = None,
        after: Optional[str] = None,
        language: str = "zh-CN",
        num: int = 20,
    ) -> List[Dict]:
        url = self._build_search_url(
            query=query,
            country=country,
            before=before,
            after=after,
            language=language,
            num=num,
        )
        response = self.session.get(url)
        response.raise_for_status()
        time.sleep(self.delay)

        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        for item in soup.select("search-result-item"):
            link_elem = item.select_one("a")
            title_elem = item.select_one("h3") or link_elem
            snippet_elem = item.select_one(".snippet")
            date_elem = item.select_one(".date")

            patent_url = link_elem.get("href", "") if link_elem else ""
            patent_id = self._extract_patent_id_from_url(patent_url)
            results.append(
                {
                    "patent_id": patent_id,
                    "patent_number": patent_id,
                    "title": title_elem.get_text(strip=True) if title_elem else "",
                    "snippet": snippet_elem.get_text(strip=True) if snippet_elem else "",
                    "publication_date": self._parse_date_simple(date_elem.get_text(strip=True)) if date_elem else None,
                    "link": f"{self.base_url}{patent_url}" if patent_url.startswith("/") else patent_url,
                }
            )

        return results

    def get_patent_detail(self, patent_id: str) -> Dict:
        url = f"{self.base_url}/patent/{patent_id}/"
        response = self.session.get(url)
        response.raise_for_status()
        time.sleep(self.delay)

        soup = BeautifulSoup(response.text, "html.parser")
        title = self._meta_content(soup, "DC.title")
        description = self._meta_content(soup, "DC.description")
        pub_date = self._parse_date_simple(self._meta_content(soup, "DC.date"))
        ipc_code = self._meta_content(soup, "DC.subject")

        return {
            "patent_id": patent_id,
            "title": title,
            "abstract": description,
            "publication_date": pub_date,
            "ipc_classifications": [ipc_code] if ipc_code else [],
        }

    def _meta_content(self, soup: BeautifulSoup, name: str) -> str:
        elem = soup.find("meta", attrs={"name": name})
        return elem.get("content", "") if elem else ""


class GooglePatentsAdvancedCrawler:
    """Google Patents高级检索爬虫"""
    
    def __init__(self, headless: bool = True, delay: float = 3.0):
        """初始化"""
        self.base_url = "https://patents.google.com"
        self.delay = delay
        self.headless = headless
        self.driver = None
        self._init_driver()
        logger.info(f"Google Patents Advanced爬虫初始化完成")
    
    def _init_driver(self):
        """初始化WebDriver（反检测）"""
        options = Options()
        
        # 基础配置
        if self.headless:
            options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--start-maximized')
        
        # 反检测配置
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # User-Agent
        options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # 语言
        options.add_argument('--lang=zh-CN')
        options.add_experimental_option('prefs', {
            'intl.accept_languages': 'zh-CN,zh;q=0.9,en;q=0.8'
        })
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.set_page_load_timeout(60)
        self.driver.set_script_timeout(30)
        
        # 移除WebDriver特征
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.navigator.chrome = {
                    runtime: {}
                };
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en']
                });
            '''
        })
    
    def search(
        self,
        keywords: Optional[List[Dict[str, str]]] = None,  # [{"term": "区块链", "scope": "CL"}]
        ipc_classes: Optional[List[str]] = None,  # ["G06F", "H04L"]
        cpc_classes: Optional[List[str]] = None,
        after_date: Optional[str] = None,
        before_date: Optional[str] = None,
        num: int = 20,
        max_retries: int = 3
    ) -> List[Dict]:
        """
        高级检索
        
        Args:
            keywords: 关键词列表 [{"term": "AI", "scope": "CL"}]
                scope可选: TI(标题), AB(摘要), CL(权利要求), TAC(全文)
            ipc_classes: IPC分类号列表
            cpc_classes: CPC分类号列表
            after_date: 起始日期 YYYY-MM-DD
            before_date: 截止日期 YYYY-MM-DD
            num: 结果数量
            max_retries: 最大重试次数
        """
        # 构建查询字符串
        query_str = self._build_query_string(keywords, ipc_classes, cpc_classes)
        logger.info(f"Advanced Search Query: {query_str}")
        
        for attempt in range(max_retries):
            try:
                search_url = self._build_search_url(query_str, after_date, before_date)
                logger.info(f"访问URL (尝试 {attempt + 1}/{max_retries})")
                
                self.driver.get(search_url)
                
                # 等待加载
                logger.info(f"等待页面加载...")
                wait = WebDriverWait(self.driver, 20)
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "search-result-item")))
                
                time.sleep(self.delay)
                
                # 提取结果
                patents = self._extract_results()
                logger.info(f"找到 {len(patents)} 个结果")
                
                return patents[:num]
            
            except Exception as e:
                logger.warning(f"尝试 {attempt + 1} 失败: {e}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"所有重试均失败")
                    raise
    
    def _build_query_string(
        self,
        keywords: Optional[List[Dict[str, str]]],
        ipc_classes: Optional[List[str]],
        cpc_classes: Optional[List[str]]
    ) -> str:
        """构建Google Patents查询字符串"""
        parts = []
        
        # 关键词部分
        if keywords:
            for kw in keywords:
                term = kw.get('term', '').strip()
                scope = kw.get('scope', 'TAC').upper()  # 默认全文
                
                if term:
                    # 根据scope添加前缀
                    if scope == 'TI':  # 标题
                        parts.append(f'TI=({term})')
                    elif scope == 'AB':  # 摘要
                        parts.append(f'AB=({term})')
                    elif scope == 'CL':  # 权利要求
                        parts.append(f'CL=({term})')
                    elif scope == 'TAC':  # 全文
                        parts.append(f'({term})')
                    else:
                        parts.append(f'({term})')
        
        # IPC分类
        if ipc_classes:
            for ipc in ipc_classes:
                parts.append(f'IPC={ipc}')
        
        # CPC分类
        if cpc_classes:
            for cpc in cpc_classes:
                parts.append(f'CPC={cpc}')
        
        # 用空格连接（Google Patents的AND逻辑）
        return ' '.join(parts) if parts else ''
    
    def _build_search_url(
        self,
        query: str,
        after_date: Optional[str],
        before_date: Optional[str]
    ) -> str:
        """构造搜索URL"""
        from urllib.parse import quote
        
        url = f"{self.base_url}/?q={quote(query)}" if query else f"{self.base_url}/"
        
        if after_date:
            after_clean = after_date.replace('-', '')
            url += f"&after=pub:{after_clean}"
        
        if before_date:
            before_clean = before_date.replace('-', '')
            url += f"&before=pub:{before_clean}"
        
        return url
    
    def _extract_results(self) -> List[Dict]:
        """提取检索结果"""
        script = """
        const items = Array.from(document.querySelectorAll('search-result-item'));
        
        return items.map(item => {
            const titleElem = item.querySelector('h3 [id="title"]') || item.querySelector('h3 span');
            const title = titleElem ? titleElem.innerText : '';
            
            const pdfLinkElem = item.querySelector('.pdfLink span') || item.querySelector('.pdfLink');
            const patentId = pdfLinkElem ? pdfLinkElem.innerText.trim() : '';
            
            const metadataElem = item.querySelector('#metadata');
            const metadata = metadataElem ? metadataElem.innerText : '';
            
            const publishedMatch = metadata.match(/Published (\\d{4}-\\d{2}-\\d{2})/);
            const publishedDate = publishedMatch ? publishedMatch[1] : null;
            
            const abstractElem = item.querySelector('#abstract');
            const abstract = abstractElem ? abstractElem.innerText : '';
            
            const link = patentId ? `https://patents.google.com/patent/${patentId}/en` : '';
            
            // 提取PDF链接
            const pdfLink = item.querySelector('.pdfLink');
            const pdfUrl = pdfLink ? pdfLink.href : '';
            
            return {
                patent_id: patentId,
                patent_number: patentId,
                title: title,
                link: link,
                pdf_url: pdfUrl,
                publication_date: publishedDate,
                snippet: abstract.substring(0, 200)
            };
        });
        """
        
        try:
            results = self.driver.execute_script(script)
            logger.info(f"JavaScript提取到 {len(results)} 个结果")
            
            valid_results = [r for r in results if r.get('patent_id')]
            logger.info(f"有效结果: {len(valid_results)} 个")
            
            return valid_results
        
        except Exception as e:
            logger.error(f"JavaScript提取失败: {e}")
            return []
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            logger.info("浏览器已关闭")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
