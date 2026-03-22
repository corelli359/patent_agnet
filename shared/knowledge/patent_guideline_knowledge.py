"""
《专利审查指南》知识检索层
将 PDF 解析为可复用的章节块，供审查模拟和修复服务引用。
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional
import json
import logging
import re

from shared.utils.pdf_parser import PDFParser

logger = logging.getLogger(__name__)


class PatentGuidelineKnowledgeBase:
    """专利审查指南轻量知识库"""

    TOPIC_KEYWORDS = {
        "formal": ["初步审查", "形式", "说明书", "权利要求书", "摘要", "撰写", "格式"],
        "clarity": ["清楚", "明确", "说明书", "权利要求书", "术语", "保护范围", "简明"],
        "support": ["说明书", "支持", "实施方式", "公开充分", "权利要求", "记载"],
        "novelty": ["新颖性", "现有技术", "抵触申请", "公开", "单独对比"],
        "inventiveness": ["创造性", "显而易见", "技术启示", "区别特征", "技术问题"],
        "practicality": ["实用性", "能够制造", "能够使用", "积极效果"],
        "repair": ["答复", "审查意见", "修改", "陈述意见", "复审", "缺陷"],
        "claims": ["权利要求书", "独立权利要求", "从属权利要求", "保护范围"],
    }

    HEADING_PATTERNS = [
        re.compile(r"^(第[一二三四五六七八九十百]+部分.*)$"),
        re.compile(r"^(第[一二三四五六七八九十百]+章.*)$"),
        re.compile(r"^(第[一二三四五六七八九十百]+节.*)$"),
    ]

    def __init__(
        self,
        pdf_path: str = "docs/专利审查指南.pdf",
        cache_path: str = "data/cache/patent_guideline_chunks.json",
        parser: Optional[PDFParser] = None,
        source_text: Optional[str] = None,
    ):
        self.pdf_path = Path(pdf_path)
        self.cache_path = Path(cache_path)
        self.parser = parser or PDFParser()
        self.source_text = source_text
        self._chunks: Optional[List[Dict]] = None

    def retrieve(self, topic: str, context_text: str = "", top_k: int = 3) -> List[Dict]:
        """按主题与上下文检索相关条文块"""
        chunks = self._load_chunks()
        if not chunks:
            return []

        keywords = self._build_keywords(topic, context_text)
        scored = []
        for chunk in chunks:
            score = self._score_chunk(chunk, keywords)
            if score > 0:
                scored.append(
                    {
                        "title": chunk["title"],
                        "content": chunk["content"],
                        "excerpt": self._build_excerpt(chunk["content"], keywords),
                        "score": score,
                    }
                )

        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:top_k]

    def format_passages(self, passages: List[Dict]) -> str:
        """格式化为可直接放入提示词的依据片段"""
        if not passages:
            return "未检索到《专利审查指南》相关依据。"

        parts = []
        for idx, passage in enumerate(passages, start=1):
            parts.append(
                f"[依据{idx}] {passage['title']}\n"
                f"{passage['excerpt']}"
            )
        return "\n\n".join(parts)

    def _load_chunks(self) -> List[Dict]:
        if self._chunks is not None:
            return self._chunks

        if self._should_use_cache():
            try:
                self._chunks = json.loads(self.cache_path.read_text(encoding="utf-8"))
                return self._chunks
            except Exception as exc:  # pragma: no cover - 仅缓存损坏时触发
                logger.warning("审查指南缓存读取失败，将重新构建: %s", exc)

        text = self._extract_source_text()
        if not text:
            self._chunks = []
            return self._chunks

        self._chunks = self._build_chunks(text)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps(self._chunks, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return self._chunks

    def _should_use_cache(self) -> bool:
        if not self.cache_path.exists():
            return False
        if self.source_text is not None:
            return True
        if not self.pdf_path.exists():
            return False
        return self.cache_path.stat().st_mtime >= self.pdf_path.stat().st_mtime

    def _extract_source_text(self) -> str:
        if self.source_text is not None:
            return self.source_text
        if not self.pdf_path.exists():
            logger.warning("未找到审查指南 PDF: %s", self.pdf_path)
            return ""
        logger.info("开始解析审查指南 PDF: %s", self.pdf_path)
        return self.parser.extract_text(str(self.pdf_path))

    def _build_chunks(self, text: str) -> List[Dict]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        chunks: List[Dict] = []
        title_stack: List[str] = []
        buffer: List[str] = []

        def flush_buffer():
            if not buffer:
                return
            content = "\n".join(buffer).strip()
            if not content:
                return
            base_title = " > ".join(title_stack) if title_stack else "专利审查指南"
            chunks.extend(self._split_large_chunk(base_title, content))

        for line in lines:
            heading = self._match_heading(line)
            if heading:
                flush_buffer()
                buffer = []
                title_stack = self._update_title_stack(title_stack, heading)
            else:
                buffer.append(line)

        flush_buffer()
        return chunks

    def _split_large_chunk(self, title: str, content: str, chunk_size: int = 1200) -> List[Dict]:
        if len(content) <= chunk_size:
            return [{"title": title, "content": content}]

        pieces = []
        paragraphs = re.split(r"(?<=。)\n|(?<=；)\n|(?<=：)\n", content)
        current = []
        current_len = 0

        for paragraph in paragraphs:
            piece = paragraph.strip()
            if not piece:
                continue
            if current_len + len(piece) > chunk_size and current:
                pieces.append({"title": title, "content": "\n".join(current)})
                current = [piece]
                current_len = len(piece)
            else:
                current.append(piece)
                current_len += len(piece)

        if current:
            pieces.append({"title": title, "content": "\n".join(current)})

        return pieces

    def _match_heading(self, line: str) -> Optional[str]:
        for pattern in self.HEADING_PATTERNS:
            matched = pattern.match(line)
            if matched:
                return matched.group(1)
        return None

    def _update_title_stack(self, current: List[str], heading: str) -> List[str]:
        if heading.startswith("第") and "部分" in heading:
            return [heading]
        if heading.startswith("第") and "章" in heading:
            return current[:1] + [heading]
        if heading.startswith("第") and "节" in heading:
            return current[:2] + [heading]
        return current + [heading]

    def _build_keywords(self, topic: str, context_text: str) -> List[str]:
        base = list(self.TOPIC_KEYWORDS.get(topic, []))
        base.extend(self._extract_context_keywords(context_text))
        # 去重并保持顺序
        seen = set()
        result = []
        for word in base:
            normalized = word.strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(normalized)
        return result

    def _extract_context_keywords(self, text: str) -> List[str]:
        if not text:
            return []

        matched = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,12}", text)
        domain_words = [
            word for word in matched
            if word in {
                "权利要求", "权利要求书", "说明书", "实施方式", "摘要", "术语",
                "新颖性", "创造性", "清楚", "支持", "公开", "保护范围",
                "技术问题", "区别特征", "现有技术", "实施例", "从属权利要求",
            }
        ]
        return domain_words[:8]

    def _score_chunk(self, chunk: Dict, keywords: List[str]) -> int:
        haystack = f"{chunk['title']}\n{chunk['content']}"
        score = 0
        for keyword in keywords:
            occurrences = haystack.count(keyword)
            if not occurrences:
                continue
            score += occurrences * (4 if keyword in chunk["title"] else 2)
        return score

    def _build_excerpt(self, content: str, keywords: List[str], max_len: int = 280) -> str:
        if not content:
            return ""

        best_pos = None
        for keyword in keywords:
            pos = content.find(keyword)
            if pos >= 0:
                best_pos = pos
                break

        if best_pos is None:
            return content[:max_len]

        start = max(best_pos - 60, 0)
        end = min(best_pos + max_len, len(content))
        excerpt = content[start:end]
        if start > 0:
            excerpt = "..." + excerpt
        if end < len(content):
            excerpt += "..."
        return excerpt
