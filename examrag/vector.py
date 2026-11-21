"""可选 embedding 向量检索：真正的稠密语义向量，纯可选依赖。

核心 CLI 与词面 / TF-IDF 检索仍然零依赖；只有显式启用 `--vector` /
`"vector": true` 时才需要安装 `sentence-transformers` 并首次下载模型。

设计要点：
  - 与 retrieval.retrieve / semantic.semantic_retrieve 同一函数契约，
    可作为 retrieve_fn 注入策略层，查询改写 / 重难点 / 并列拆分照常生效；
  - 向量按「模型名 + 原文」哈希缓存到本地 JSON，重复检索不再重算；
  - embed_fn 可注入，测试可用桩函数完全离线覆盖，不必下载模型。

注意：这里计算的是 embedding 余弦相似度，和 TF-IDF 的稀疏向量不是一回事。
"""

import hashlib
import json
import math
from functools import partial
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple, Union

from . import config
from .config import LEVEL_WEIGHTS
from .llm import ExamRAGError
from .models import Chunk, as_chunks
from .retrieval import is_nav

EmbedFn = Callable[[List[str]], List[List[float]]]
Vector = List[float]


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """稀疏/稠密通用的余弦相似度，只用标准库。"""
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    dot = sum(x * y for x, y in zip(a, b))
    if dot <= 0:
        return 0.0
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _cache_file(path: Optional[Union[str, Path]] = None) -> Path:
    if path:
        return Path(path)
    return Path(config.get_vector_cache_path())


def _cache_key(model: str, text: str) -> str:
    return hashlib.sha256((model + "\0" + text).encode("utf-8")).hexdigest()[:24]


def _read_cache(path: Path) -> Dict[str, List[float]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, UnicodeDecodeError):
        return {}


def _write_cache(path: Path, data: Dict[str, List[float]]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except OSError:
        # 缓存写不进去不影响检索，只是下次要重算。
        pass


def get_embed_fn(model_name: Optional[str] = None) -> EmbedFn:
    """惰性加载 sentence-transformers；缺依赖时给出可操作的中文提示。"""
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
    except ImportError as exc:
        raise ExamRAGError(
            "向量检索需要额外依赖。请先运行：pip install -e \".[vector]\"\n"
            "首次使用还会下载 embedding 模型；不想装依赖可继续用词面或 TF-IDF 检索。"
        ) from exc

    model = SentenceTransformer(model_name or config.get_vector_model())

    def embed(texts: List[str]) -> List[List[float]]:
        raw = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [[float(x) for x in vector] for vector in raw]

    return embed


def embed_texts(
    texts: Sequence[str],
    embed_fn: Optional[EmbedFn] = None,
    model_name: Optional[str] = None,
    cache_path: Optional[Union[str, Path]] = None,
) -> List[Vector]:
    """批量取向量；命中缓存的原文不再重复计算。"""
    if not texts:
        return []
    model_name = model_name or config.get_vector_model()
    fn = embed_fn or get_embed_fn(model_name)
    path = _cache_file(cache_path)
    cache = _read_cache(path)
    keys = [_cache_key(model_name, text) for text in texts]
    missing = [text for text, key in zip(texts, keys) if key not in cache]

    if missing:
        vectors = fn(missing)
        if len(vectors) != len(missing):
            raise ExamRAGError("向量模型返回的向量数量与输入文本数量不一致。")
        for text, vector in zip(missing, vectors):
            cache[_cache_key(model_name, text)] = [float(x) for x in vector]
        _write_cache(path, cache)

    return [cache[key] for key in keys]


def vector_retrieve(
    question: str,
    chunks: Sequence[Chunk],
    top_k: int = 3,
    weighted: bool = False,
    return_score: bool = False,
    embed_fn: Optional[EmbedFn] = None,
    model_name: Optional[str] = None,
    cache_path: Optional[Union[str, Path]] = None,
) -> Union[List[Chunk], Tuple[List[Chunk], float]]:
    """用 embedding 余弦相似度检索，与另两种检索器共用同一契约。"""
    model_name = model_name or config.get_vector_model()
    blocks = as_chunks(chunks)
    if not blocks:
        return ([], 0.0) if return_score else []

    candidates = [c for c in blocks if not c.is_header] or list(blocks)
    vectors = embed_texts(
        [question] + [c.text for c in candidates],
        embed_fn=embed_fn, model_name=model_name, cache_path=cache_path,
    )
    query_vector = vectors[0]
    scored: List[Tuple[float, Chunk]] = []
    for chunk, vector in zip(candidates, vectors[1:]):
        score = _cosine(query_vector, vector)
        if score > 0 and weighted:
            score *= LEVEL_WEIGHTS.get(chunk.level, 1)
        if score > 0 and is_nav(chunk):
            score *= 0.5  # 与另外两种检索器同口径
        scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    best = scored[0][0] if scored else 0.0
    top = [chunk for score, chunk in scored[:top_k] if score > 0]
    fallback = top if top else [chunk for _, chunk in scored[:top_k]]

    if return_score:
        return fallback, best
    return fallback


def retriever(
    embed_fn: Optional[EmbedFn] = None,
    model_name: Optional[str] = None,
    cache_path: Optional[Union[str, Path]] = None,
) -> Callable[..., Union[List[Chunk], Tuple[List[Chunk], float]]]:
    """构造可注入策略层的检索器；把向量相关参数固化进去。"""
    return partial(
        vector_retrieve, embed_fn=embed_fn,
        model_name=model_name, cache_path=cache_path,
    )


__all__ = [
    "EmbedFn", "Vector", "embed_texts", "get_embed_fn",
    "vector_retrieve", "retriever",
]
