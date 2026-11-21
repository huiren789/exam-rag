"""可选的语义检索增强：字符 bigram 的 TF-IDF + 余弦相似度。

与 retrieval.py 的词面精确匹配互补：
  - 词面匹配：共同 bigram 出现次数，精确但受措辞影响大；
  - 语义检索：TF-IDF 加权 + 余弦相似度，缓解高频词干扰、对长资料更稳。

实现只用 Python 标准库（math / collections），不引入任何第三方依赖，
因此不会影响项目"核心零依赖"的定位。资料块少（99 块）时性能足够。
"""

import math
import re
from collections import Counter
from typing import Dict, List, Sequence, Tuple

from .config import FILLERS, LEVEL_WEIGHTS
from .retrieval import level_of


def _bigrams(text: str) -> Counter:
    """字符 bigram 计数，忽略空白。与 retrieval.bigrams 同一口径。"""
    text = re.sub(r"\s", "", text)
    return Counter(text[i:i + 2] for i in range(len(text) - 1))


def _tokens(text: str) -> Counter:
    for word in FILLERS:
        text = text.replace(word, "")
    return _bigrams(text.strip() or text)


def _idf(chunks: Sequence[str]) -> Dict[str, float]:
    """计算逆文档频率：出现在越少资料块里的词，权重越高。"""
    n = len(chunks)
    doc_freq: Counter = Counter()
    for chunk in chunks:
        for token in _bigrams(chunk):
            doc_freq[token] += 1
    return {
        token: math.log((n + 1) / (freq + 1)) + 1.0
        for token, freq in doc_freq.items()
    }


def _vector(text: str, idf: Dict[str, float]) -> Dict[str, float]:
    """TF-IDF 向量：词频 × 逆文档频率。"""
    tf = _tokens(text)
    return {token: count * idf.get(token, 1.0) for token, count in tf.items()}


def _cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
    """稀疏向量余弦相似度。"""
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    dot = sum(value * b.get(token, 0.0) for token, value in a.items())
    if dot <= 0:
        return 0.0
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb)


def semantic_retrieve(
    question: str,
    chunks: Sequence[str],
    top_k: int = 3,
    weighted: bool = False,
    return_score: bool = False,
):
    """语义检索：返回与问题最相关的资料块（接口对齐 retrieval.retrieve）。

    章节标题行（========）不参与检索，与词面检索一致。
    weighted=True 时按掌握等级加权，供出题场景使用。
    return_score=True 时返回 (块列表, 最高相似度)。
    """
    if not chunks:
        return ([], 0.0) if return_score else []

    candidates = [c for c in chunks if not c.startswith("========")]
    if not candidates:
        candidates = list(chunks)

    idf = _idf(candidates)
    q_vec = _vector(question, idf)
    scored: List[Tuple[float, str]] = []
    for chunk in candidates:
        score = _cosine(q_vec, _vector(chunk, idf))
        if score > 0 and weighted:
            score *= LEVEL_WEIGHTS.get(level_of(chunk), 1)
        scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    best = scored[0][0] if scored else 0.0
    top = [chunk for score, chunk in scored[:top_k] if score > 0]
    if not top:
        top = [chunk for _, chunk in scored[:top_k]]
    if return_score:
        return top, best
    return top
