"""资料块的领域模型：把「标签 / 掌握等级 / 正文」建成对象，解析一次全链路复用。

此前资料块一路以裸字符串传递，tag 与 level 在 retrieval / smart / service /
api / cli 里各用正则解析一遍（共 6 处），既重复又容易不一致。
现在 load_chunks 时解析成 Chunk 对象，后续只读字段，不再正则。
"""

import re
from collections import Counter
from dataclasses import dataclass
from typing import List, Optional, Sequence, Union

from .config import FILLERS

HEADER_PREFIX = "========"
LEVEL_PATTERN = re.compile(r"【(掌握|理解|了解)")
TAG_PATTERN = re.compile(r"【([^】]*)】")


@dataclass(frozen=True)
class Chunk:
    """一块课程资料。frozen 保证检索与展示过程中不被意外修改。

    tag   —— 【】里的完整标签，如「掌握·难度的定义」；章节标题行无标签时为 ""。
    level —— 掌握 / 理解 / 了解；无标签的块按最低档「了解」。
    text  —— 原始整块文本（含【标签】前缀），用于提示词与"翻回原文核对"。
    """

    tag: str
    level: str
    text: str

    @property
    def is_header(self) -> bool:
        """章节标题行不参与检索。"""
        return self.text.startswith(HEADER_PREFIX)

    def __str__(self) -> str:
        """转成原文，保证提示词与展示格式与重构前完全一致。"""
        return self.text

    def as_dict(self) -> dict:
        """API 返回用的结构。"""
        return {"tag": self.tag, "level": self.level, "text": self.text}


def parse_chunk(raw: str) -> Chunk:
    """从原始文本解析出 Chunk；tag/level 缺失时给安全默认。"""
    text = raw.strip()
    tag_match = TAG_PATTERN.match(text)
    level_match = LEVEL_PATTERN.match(text)
    tag = tag_match.group(1) if tag_match else ""
    level = level_match.group(1) if level_match else "了解"
    return Chunk(tag=tag, level=level, text=text)


def as_chunks(items: Sequence[Union[str, Chunk]]) -> List[Chunk]:
    """兼容层：把可能混着裸字符串的输入统一转成 Chunk。

    老测试与外部调用仍可能传 List[str]；有了这个函数，核心逻辑只处理 Chunk。
    """
    return [item if isinstance(item, Chunk) else parse_chunk(item) for item in items]


def tag_of(chunk: Chunk) -> str:
    """显示用的标签：有 tag 用 tag，无标签（章节标题）退回正文前 12 字。"""
    return chunk.tag or chunk.text[:12]


def tags_of(chunks: Sequence[Union[str, Chunk]]) -> str:
    """把多个块的标签拼成展示串，如「掌握·难度、理解·信度」。"""
    return "、".join(tag_of(c) for c in as_chunks(chunks))


def bigrams(text: str) -> Counter:
    """字符 bigram 计数，忽略空白。全项目唯一实现：
    词面检索 / TF-IDF 语义检索 / 证据句重合度共用同一口径。
    """
    text = re.sub(r"\s", "", text)
    return Counter(text[i:i + 2] for i in range(len(text) - 1))


def strip_fillers(text: str, fallback: Optional[str] = None) -> str:
    """去掉问题里的客套词，留下检索关键词；去完为空白时退回原文避免检索全空。

    fallback 保持三处历史调用点的原语义：retrieval.clean 退回原始问题、
    semantic._tokens 与 evidence_sentences 退回各自的上文对象。
    """
    q = text
    for word in FILLERS:
        q = q.replace(word, "")
    return q.strip() or (fallback if fallback is not None else text)


def evidence_sentences(text: str, question: str, top_n: int = 1) -> List[dict]:
    """从资料块里挑出与问题最相关的原句，返回 [{"text", "score"}]。

    score 是问题与句子共同两字词的出现次数（词面重合度），不是模型打分；
    它只用于排序和展示，回答仍然只依据整块原文。
    """
    body = re.sub(r"^【[^】]*】", "", text.strip()).strip()
    parts = [p.strip() for p in re.split(r"[。！？!?；;\n]+", body) if len(p.strip()) >= 4]
    if not parts:
        parts = [body or text.strip()]

    query_bigrams = bigrams(strip_fillers(question, question).strip() or question)

    scored = []
    for part in parts:
        overlap = query_bigrams & bigrams(part)
        scored.append({"text": part, "score": sum(overlap.values())})
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_n]
