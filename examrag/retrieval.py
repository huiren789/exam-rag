"""纯本地检索层：把问题与资料块做词面匹配，不联网、不花 token。

这一层只依赖 Python 标准库，可完全离线测试；也是整个项目的可解释性来源——
检索到的块标签会显示给用户，答案能翻回原文核对。
"""

import re
from collections import Counter
from pathlib import Path
from typing import List, Sequence, Tuple, Union

from .config import FILLERS, LEVEL_WEIGHTS, NAV_KEYS


def clean(question: str) -> str:
    """去掉问题里的客套词，留下真正的检索关键词。

    如果去完变成空串（例如问题只有"？"），退回原始问题避免检索全空。
    """
    q = question
    for word in FILLERS:
        q = q.replace(word, "")
    return q.strip() or question


def load_chunks(path: Union[str, Path]) -> List[str]:
    """读取 UTF-8 资料文件，按空行切成资料块。"""
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    return [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]


def bigrams(text: str) -> Counter:
    """把文字切成两字词并计数；空白不计入，计数体现词频证据强度。"""
    text = re.sub(r"\s", "", text)
    return Counter(text[i:i + 2] for i in range(len(text) - 1))


def is_nav(chunk: str) -> bool:
    """判断是否为章节标题或导航块（学习目标/导图/小结/练习等）。"""
    if chunk.startswith("========"):
        return True
    return chunk.startswith("【") and any(key in chunk[:20] for key in NAV_KEYS)


def level_of(chunk: str) -> str:
    """读取资料块开头的掌握等级；没有标签的块按最低档"了解"算。"""
    match = re.match(r"【(掌握|理解|了解)", chunk)
    return match.group(1) if match else "了解"


def retrieve(
    question: str,
    chunks: Sequence[str],
    top_k: int = 3,
    weighted: bool = False,
    return_score: bool = False,
) -> Union[List[str], Tuple[List[str], float]]:
    """检索与问题最相关的资料块。

    计分规则：
      1. 相关性 = 问题与资料块共同两字词（bigram）的出现次数之和；
      2. 命中资料块标题标签额外加权 ×2；
      3. 导航块 ×0.5（给正文让位）；
      4. weighted=True（出题模式）时再按掌握等级加权：掌握 3 / 理解 2 / 了解 1；
      5. 0 分块不参与排序，全部为 0 时退回前 top_k 块作兜底上下文。

    return_score=True 时返回 (资料块列表, 最高分)，供查询改写判断是否需要重试。
    """
    query = bigrams(clean(question))
    scored = []
    for chunk in chunks:
        if chunk.startswith("========"):
            continue  # 章节标题不参与检索
        overlap = query & bigrams(chunk)
        score = sum(overlap.values())

        title = re.match(r"【([^】]*)】", chunk)
        if title:
            score += 2 * sum((query & bigrams(title.group(1))).values())

        if score > 0 and weighted:
            score *= LEVEL_WEIGHTS.get(level_of(chunk), 1)

        if is_nav(chunk):
            score *= 0.5

        scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    top = [chunk for score, chunk in scored[:top_k] if score > 0]
    best = scored[0][0] if scored else 0.0

    if return_score:
        return (top if top else list(chunks[:top_k])), best
    return top if top else list(chunks[:top_k])


def tags_of(chunks: Sequence[str]) -> str:
    """抽取每块的【标签】，用于显示"检索到了哪几块"。"""
    names = []
    for chunk in chunks:
        match = re.match(r"【([^】]*)】", chunk)
        names.append(match.group(1) if match else chunk[:12])
    return "、".join(names)
