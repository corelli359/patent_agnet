"""
关键词分析器
提取专利中的共性关键词，用于技术方案对比
"""

import jieba.analyse
from collections import Counter
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class KeywordAnalyzer:
    """共性关键词分析器"""
    
    def __init__(self, stopwords_path: Optional[str] = None):
        """
        初始化分析器
        
        Args:
            stopwords_path: 停用词文件路径（可选）
        """
        self.stopwords = self._load_stopwords(stopwords_path)
        logger.info("关键词分析器初始化完成")
    
    def extract_common_keywords(
        self,
        patents: List[Dict],
        top_k: int = 10,
        min_frequency: int = 2
    ) -> List[Dict]:
        """
        提取多篇专利的共性关键词
        
        Args:
            patents: 专利列表（需包含title和abstract字段）
            top_k: 返回Top K关键词
            min_frequency: 最小出现频率
            
        Returns:
            List[Dict]: [{word, frequency, weight}, ...]
        """
        if not patents:
            return []
        
        logger.info(f"开始分析 {len(patents)} 篇专利的共性关键词")
        
        all_keywords = []
        
        # 1. 提取每篇专利的关键词
        for patent in patents:
            text = self._get_patent_text(patent)
            if not text:
                continue
            
            # 使用jieba提取关键词（TF-IDF算法）
            keywords = jieba.analyse.extract_tags(
                text,
                topK=20,
                withWeight=True,
                allowPOS=('n', 'nr', 'ns', 'nt', 'nz', 'vn')  # 只保留名词和动名词
            )
            
            # 过滤停用词
            keywords = [
                (word, weight) for word, weight in keywords
                if word not in self.stopwords and len(word) > 1  # 过滤单字
            ]
            
            all_keywords.extend(keywords)
        
        # 2. 统计词频
        word_freq = Counter([word for word, _ in all_keywords])
        
        # 3. 计算平均权重
        word_weights = {}
        for word, weight in all_keywords:
            if word not in word_weights:
                word_weights[word] = []
            word_weights[word].append(weight)
        
        # 4. 生成结果
        result = []
        for word, freq in word_freq.most_common():
            if freq < min_frequency:  # 过滤低频词
                continue
            
            avg_weight = sum(word_weights[word]) / len(word_weights[word])
            result.append({
                'word': word,
                'frequency': freq,
                'weight': round(avg_weight, 3),
                'coverage': round(freq / len(patents), 2)  # 覆盖率
            })
        
        logger.info(f"提取到 {len(result)} 个共性关键词")
        return result[:top_k]
    
    def suggest_queries(
        self,
        common_keywords: List[Dict],
        max_suggestions: int = 5
    ) -> List[str]:
        """
        基于共性关键词生成推荐检索语句
        
        Args:
            common_keywords: 共性关键词列表
            max_suggestions: 最大推荐数
            
        Returns:
            List[str]: 推荐检索语句
        """
        if not common_keywords:
            return []
        
        suggestions = []
        top_words = [kw['word'] for kw in common_keywords[:5]]
        
        # 策略1：二元组合
        for i in range(min(3, len(top_words))):
            for j in range(i + 1, min(4, len(top_words))):
                suggestions.append(f"{top_words[i]} {top_words[j]}")
        
        # 策略2：三元组合（高权重词）
        if len(top_words) >= 3:
            suggestions.append(f"{top_words[0]} {top_words[1]} {top_words[2]}")
        
        return suggestions[:max_suggestions]
    
    def compare_keywords(
        self,
        patents_a: List[Dict],
        patents_b: List[Dict]
    ) -> Dict:
        """
        对比两组专利的关键词差异
        
        Args:
            patents_a: 第一组专利
            patents_b: 第二组专利
            
        Returns:
            Dict: 对比结果
        """
        keywords_a = self.extract_common_keywords(patents_a, top_k=20)
        keywords_b = self.extract_common_keywords(patents_b, top_k=20)
        
        words_a = set([kw['word'] for kw in keywords_a])
        words_b = set([kw['word'] for kw in keywords_b])
        
        return {
            'common': list(words_a & words_b),  # 共同关键词
            'unique_to_a': list(words_a - words_b),  # A独有
            'unique_to_b': list(words_b - words_a),  # B独有
            'similarity': len(words_a & words_b) / max(len(words_a | words_b), 1)  # 相似度
        }
    
    def _get_patent_text(self, patent: Dict) -> str:
        """获取专利文本（标题 + 摘要）"""
        title = patent.get('title', '')
        abstract = patent.get('abstract', '') or patent.get('snippet', '')
        return f"{title} {abstract}".strip()
    
    def _load_stopwords(self, path: Optional[str] = None) -> set:
        """
        加载停用词表
        
        Args:
            path: 停用词文件路径
            
        Returns:
            set: 停用词集合
        """
        # 默认停用词
        default_stopwords = {
            '的', '是', '在', '和', '与', '等', '及', '或', '有', '为',
            '中', '其', '该', '一种', '本发明', '所述', '包括', '通过',
            '方法', '系统', '装置', '设备', '技术', '实现', '进行', '提供'
        }
        
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    custom_stopwords = set(line.strip() for line in f if line.strip())
                return default_stopwords | custom_stopwords
            except Exception as e:
                logger.warning(f"加载停用词文件失败: {e}，使用默认停用词")
        
        return default_stopwords


# 便捷函数
def analyze_keywords(patents: List[Dict], top_k: int = 10) -> List[Dict]:
    """
    便捷函数：分析专利关键词
    
    Args:
        patents: 专利列表
        top_k: 返回Top K
        
    Returns:
        List[Dict]: 关键词列表
    """
    analyzer = KeywordAnalyzer()
    return analyzer.extract_common_keywords(patents, top_k=top_k)
