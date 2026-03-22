# Google Patents爬虫技术问题报告

## 问题描述
Google Patents（`patents.google.com`）使用JavaScript渲染的单页应用（SPA），直接用`requests`只能获取到空壳HTML。

## 技术分析

### 当前HTML结构
```html
<search-app>
  <!-- 内容由JavaScript动态加载 -->
</search-app>
<script src="//www.gstatic.com/patent-search/frontend/.../search-app-vulcanized.js"></script>
```

- 使用Polymer框架
- Web Components
- 完全依赖JavaScript渲染

### 测试结果
- HTTP响应：200 OK
- HTML大小：仅4149字符
- 专利数据：0条（需JavaScript执行后加载）

## 解决方案对比

### ✅ 方案1：Selenium + ChromeDriver（推荐）
**实现**：
```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--headless')  # 无头模式
driver = webdriver.Chrome(options=options)
driver.get(url)
time.sleep(3)  # 等待加载
html = driver.page_source
```

**优点**：
- 完整渲染JavaScript
- 稳定可靠
- 可模拟用户交互

**缺点**：
- 需要安装ChromeDriver
- 慢（每次检索3-5秒）
- 资源占用高

**依赖**：
```bash
pip install selenium
brew install chromedriver  # Mac
```

---

### ⚡ 方案2：Google Patents Public Data（推荐用于大规模）
**实现**：通过BigQuery访问Google专利公开数据集

**优点**：
- 官方数据
- SQL查询，速度快
- 完整数据

**缺点**：
- 需要Google Cloud账号
- 可能产生费用
- 学习成本

---

### 🔌 方案3：第三方API
**选项**：
- **EPO OPS API**：欧洲专利局官方API，免费但有配额
- **USPTO API**：美国专利商标局API
- **Patent2Net**：开源专利分析工具

**优点**：官方/稳定
**缺点**：配额限制，覆盖范围不同

---

## 建议

### 短期（快速上线）
使用**Selenium**实现爬虫，虽然慢但稳定可用。

### 长期（生产环境）
1. **主力**：BigQuery公开数据集（批量检索）
2. **补充**：Selenium（实时检索最新专利）
3. **缓存**：本地数据库存储，减少重复检索

---

## 下一步行动

需要您决定：
1. **现在实现Selenium版本**（约30分钟）
2. **研究BigQuery方案**（需要您提供Google Cloud配置）
3. **使用第三方API**（如EPO OPS）

请告知您的选择！
