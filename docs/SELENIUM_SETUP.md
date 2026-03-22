# Selenium + Google Patents快速开始

## 安装依赖

### 1. 安装Python包
```bash
cd backend
pip install -r requirements.txt
```

### 2. 安装ChromeDriver

#### Mac
```bash
brew install chromedriver
```

#### Linux
```bash
# Ubuntu/Debian
sudo apt-get install chromium-chromedriver

# 或下载二进制文件
wget https://chromedriver.storage.googleapis.com/LATEST_RELEASE
# 下载对应版本
```

#### Windows
1. 访问 https://chromedriver.chromium.org/
2. 下载与Chrome版本匹配的driver
3. 添加到PATH环境变量

### 3. 验证安装
```bash
chromedriver --version
```

## 使用示例

### 基础用法
```python
from skills.patent_search.scripts import GooglePatentsSeleniumCrawler

# 使用上下文管理器（推荐）
with GooglePatentsSeleniumCrawler(headless=True) as crawler:
    results = crawler.search("blockchain", country="CN", num=10)
    
    for patent in results:
        print(patent['patent_number'], patent['title'])
```

### 完整示例
```python
# 创建爬虫实例
crawler = GooglePatentsSeleniumCrawler(
    headless=True,  # 无头模式（不显示浏览器）
    delay=3.0       # 页面加载等待时间（秒）
)

try:
    # 搜索专利
    results = crawler.search(
        query="区块链 加密",
        country="CN",
        num=20
    )
    
    # 获取详情
    if results:
        detail = crawler.get_patent_detail(results[0]['patent_number'])
        print(detail)

finally:
    # 关闭浏览器
    crawler.close()
```

## 测试
```bash
python scripts/test_google_patents.py
```

## 性能说明
- **速度**: 每次搜索约3-5秒（等待JavaScript渲染）
- **资源**: 约150-200MB内存（Chrome进程）
- **并发**: 不建议并发，容易被Google检测

## 常见问题

### ChromeDriver版本不匹配
```
错误: session not created: This version of ChromeDriver only supports Chrome version XX
```
**解决**: 升级ChromeDriver或Chrome到匹配版本

### 无法启动浏览器
```
错误: WebDriver initialization failed
```
**解决**: 
1. 检查ChromeDriver是否在PATH中
2. Mac安全设置：`xattr -d com.apple.quarantine /path/to/chromedriver`

### 找不到元素
```
警告: 未找到search-result-item元素
```
**解决**: 增加`delay`参数，给页面更多加载时间

## 生产环境建议
1. **使用代理池**: 避免IP被封
2. **限流**: 每次请求间隔3-5秒
3. **错误重试**: 自动重试失败的请求
4. **定期更新ChromeDriver**: 匹配Chrome版本
