"""纯本地检索层：把问题与资料块做词面匹配，不联网、不花 token。

这一层只依赖 Python 标准库，可完全离线测试；也是整个项目的可解释性来源——
检索到的块标签会显示给用户，答案能翻回原文核对。

检索器统一契约（retrieval.retrieve 与 semantic.semantic_retrieve 都遵守）：
    retrieve(question, chunks: Sequence[Chunk], *, top_k, weighted, return_score)
    → List[Chunk] 或 (List[Chunk], best_score)
"""

import re
from collections import Counter
from pathlib import Path
from typing import List, Sequence, Tuple, Union

from .config import FILLERS, LEVEL_WEIGHTS, NAV_KEYS
from .models import Chunk, as_chunks, parse_chunk, tag_of, tags_of  # noqa: F401 兼容导出


def clean(question: str) -> str:
    """去掉问题里的客套词，留下真正的检索关键词。

    如果去完变成空串（例如问题只有"？"），退回原始问题避免检索全空。
    """
    q = question
    for word in FILLERS:
        q = q.replace(word, "")
    return q.strip() or question


def load_chunks(path: Union[str, Path]) -> List[Chunk]:
    """读取 UTF-8 资料文件，按空行切块，并在入口处一次解析成 Chunk。"""
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    return [parse_chunk(chunk) for chunk in text.split("\n\n") if chunk.strip()]


def bigrams(text: str) -> Counter:
    """把文字切成两字词并计数；空白不计入，计数体现词频证据强度。"""
    text = re.sub(r"\s", "", text)
    return Counter(text[i:i + 2] for i in range(len(text) - 1))


def is_nav(chunk: Union[str, Chunk]) -> bool:
    """判断是否为章节标题或导航块（学习目标/导图/小结/练习等）。

    与 level_of / tags_of 一样接受裸字符串，兼容旧调用；内部统一按 Chunk 读字段。
    """
    block = chunk if isinstance(chunk, Chunk) else parse_chunk(chunk)
    if block.is_header:
        return True
    return bool(block.tag) and any(key in block.tag[:20] for key in NAV_KEYS)


def level_of(chunk: Union[str, Chunk]) -> str:
    """兼容包装：取资料块的掌握等级；无标签按「了解」。"""
    if isinstance(chunk, Chunk):
        return chunk.level
    return parse_chunk(chunk).level


def retrieve(
    question: str,
    chunks: Sequence[Chunk],
    top_k: int = 3,
    weighted: bool = False,
    return_score: bool = False,
) -> Union[List[Chunk], Tuple[List[Chunk], float]]:
    """检索与问题最相关的资料块（词面匹配）。

    计分规则：
      1. 相关性 = 问题与资料块共同两字词（bigram）的出现次数之和；
      2. 命中资料块标签额外加权 ×2（直接读 chunk.tag，不再正则）；
      3. 导航块 ×0.5（给正文让位）；
      4. weighted=True（出题模式）时再按掌握等级加权：掌握 3 / 理解 2 / 了解 1；
      5. 0 分块不参与排序，全部为 0 时退回前 top_k 块作兜底上下文。

    与 semantic.semantic_retrieve 共用同一契约，可作为 retrieve_fn 注入策略层。
    """
    blocks = as_chunks(chunks)
    query = bigrams(clean(question))
    scored: List[Tuple[float, Chunk]] = []
    for chunk in blocks:
        if chunk.is_header:
            continue  # 章节标题不参与检索
        overlap = query & bigrams(chunk.text)
        score = sum(overlap.values())

        if chunk.tag:
            score += 2 * sum((query & bigrams(chunk.tag)).values())

        if score > 0 and weighted:
            score *= LEVEL_WEIGHTS.get(chunk.level, 1)

        if is_nav(chunk):
            score *= 0.5

        scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    top = [chunk for score, chunk in scored[:top_k] if score > 0]
    best = scored[0][0] if scored else 0.0
    fallback = top if top else list(blocks[:top_k])

    if return_score:
        return fallback, best
    return fallback
