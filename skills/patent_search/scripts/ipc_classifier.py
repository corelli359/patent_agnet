"""
IPC分类分析器
分析专利的IPC分类号分布，识别技术聚类
"""

from collections import Counter
from typing import List, Dict, Optional
import re
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class IPCClassifier:
    """IPC分类号分析器"""
    
    def __init__(self, ipc_db_path: Optional[str] = None):
        """
        初始化分析器
        
        Args:
            ipc_db_path: IPC分类数据库路径（JSON格式）
        """
        self.ipc_db = self._load_ipc_db(ipc_db_path)
        logger.info("IPC分类分析器初始化完成")
    
    def extract_ipc_codes(self, patent: Dict) -> List[str]:
        """
        从专利元数据中提取IPC分类号
        
        Args:
            patent: 专利字典
            
        Returns:
            List[str]: IPC分类号列表
        """
        # 策略1：从ipc_classifications字段获取
        if 'ipc_classifications' in patent:
            codes = patent['ipc_classifications']
            if isinstance(codes, list):
                return codes
            elif isinstance(codes, str):
                return [codes]
        
        # 策略2：从文本中正则提取
        text_fields = [
            patent.get('title', ''),
            patent.get('abstract', ''),
            patent.get('snippet', '')
        ]
        text = ' '.join(text_fields)
        
        # IPC格式：H04L 9/00, G06F21/60
        ipc_pattern = r'\b([A-H]\d{2}[A-Z]\s?\d{1,3}/\d{2,4})\b'
        matches = re.findall(ipc_pattern, text)
        
        # 标准化格式（去除空格）
        return [match.replace(' ', '') for match in matches]
    
    def analyze_ipc_distribution(self, patents: List[Dict]) -> Dict:
        """
        分析IPC分类分布
        
        Args:
            patents: 专利列表
            
        Returns:
            Dict: {ipc_stats, section_stats, class_stats}
        """
        if not patents:
            return {'ipc_stats': [], 'section_stats': {}, 'class_stats': {}}
        
        logger.info(f"开始分析 {len(patents)} 篇专利的IPC分类")
        
        # 1. 提取所有IPC代码
        all_ipc_codes = []
        for patent in patents:
            codes = self.extract_ipc_codes(patent)
            all_ipc_codes.extend(codes)
        
        if not all_ipc_codes:
            logger.warning("未提取到IPC分类号")
            return {'ipc_stats': [], 'section_stats': {}, 'class_stats': {}}
        
        # 2. IPC分类统计（完整代码）
        ipc_counter = Counter(all_ipc_codes)
        ipc_stats = []
        for code, count in ipc_counter.most_common():
            ipc_stats.append({
                'code': code,
                'count': count,
                'name': self._get_ipc_name(code),
                'percentage': round(count / len(all_ipc_codes) * 100, 1)
            })
        
        # 3. Section统计（大类：A-H）
        sections = [code[0] for code in all_ipc_codes if code]
        section_counter = Counter(sections)
        section_stats = {
            f"{sec} ({self._get_section_name(sec)})": count
            for sec, count in section_counter.most_common()
        }
        
        # 4. Class统计（小类：前4位）
        classes = [code[:4] for code in all_ipc_codes if len(code) >= 4]
        class_counter = Counter(classes)
        class_stats = {
            cls: {
                'count': count,
                'name': self._get_class_name(cls)
            }
            for cls, count in class_counter.most_common(10)
        }
        
        logger.info(f"分析完成：{len(ipc_stats)} 个IPC分类，{len(section_stats)} 个大类")
        
        return {
            'ipc_stats': ipc_stats,
            'section_stats': section_stats,
            'class_stats': class_stats
        }
    
    def suggest_ipc_queries(self, ipc_stats: List[Dict], top_k: int = 3) -> List[str]:
        """
        基于IPC分类统计生成推荐检索语句
        
        Args:
            ipc_stats: IPC统计结果
            top_k: 推荐Top K分类
            
        Returns:
            List[str]: 推荐检索语句
        """
        if not ipc_stats:
            return []
        
        suggestions = []
        for ipc in ipc_stats[:top_k]:
            code = ipc['code']
            # 生成IPC过滤查询
            suggestions.append(f"IPC:{code}")
            
            # 生成主组查询（前7位）
            if len(code) >= 7:
                main_group = code[:7]  # 例如：H04L9/0
                suggestions.append(f"IPC:{main_group}*")
        
        return suggestions[:top_k * 2]
    
    def _get_ipc_name(self, code: str) -> str:
        """
        查询IPC分类名称
        
        Args:
            code: IPC代码（如 H04L9/00）
            
        Returns:
            str: 分类名称
        """
        # 尝试从数据库查询
        if code in self.ipc_db:
            return self.ipc_db[code]
        
        # 尝试查询主组
        if '/' in code:
            main_group = code.split('/')[0]
            if main_group in self.ipc_db:
                return self.ipc_db[main_group]
        
        # 返回未知
        return "未知分类"
    
    def _get_section_name(self, section: str) -> str:
        """IPC大类（Section）名称"""
        mapping = {
            'A': '人类生活必需',
            'B': '作业、运输',
            'C': '化学、冶金',
            'D': '纺织、造纸',
            'E': '固定建筑物',
            'F': '机械工程',
            'G': '物理',
            'H': '电学'
        }
        return mapping.get(section, '未知')
    
    def _get_class_name(self, class_code: str) -> str:
        """获取小类名称（前4位）"""
        # 从数据库查询
        if class_code in self.ipc_db:
            return self.ipc_db[class_code]
        return "未知小类"
    
    def _load_ipc_db(self, path: Optional[str] = None) -> Dict:
        """
        加载IPC分类数据库
        
        Args:
            path: JSON文件路径
            
        Returns:
            Dict: {IPC代码: 名称}
        """
        # 默认IPC数据库（常见分类）
        default_db = {
            # Section H - 电学
            'H04L': '数字信息传输',
            'H04L9': '保密或安全通信装置',
            'H04L9/00': '密码编排；加密或解密装置',
            'H04L9/08': '密钥分配',
            'H04L9/32': '包括对用于因特网、远程通信或计算机网络的安全协议的配置',
            
            # Section G - 物理
            'G06F': '电数字数据处理',
            'G06F21': '防止对计算机或计算机系统未授权操作的安全装置',
            'G06F21/60': '保护计算机中数据或数据集或程序的完整性',
            'G06Q': '专门适用于行政、商业、金融、管理、监督或预测目的的数据处理系统或方法',
            'G06Q20': '支付体系结构、方案或协议',
            
            # Section B - 作业、运输
            'B60': '一般车辆',
            'B60W': '不同类型或不同功能的车辆子系统的联合控制',
            
            # Section A - 人类生活必需
            'A61': '医学或兽医学；卫生学',
            'A61B': '诊断；外科；鉴定',
        }
        
        if path and Path(path).exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    custom_db = json.load(f)
                return {**default_db, **custom_db}
            except Exception as e:
                logger.warning(f"加载IPC数据库失败: {e}，使用默认数据库")
        
        return default_db


# 便捷函数
def analyze_ipc(patents: List[Dict]) -> Dict:
    """
    便捷函数：分析IPC分类
    
    Args:
        patents: 专利列表
        
    Returns:
        Dict: IPC分析结果
    """
    classifier = IPCClassifier()
    return classifier.analyze_ipc_distribution(patents)
