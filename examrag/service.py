"""共用业务层：CLI、HTTP API 与 Web 共用的检索、提示词与结果组装逻辑。

只依赖 Python 标准库和项目内部模块；embedding 检索器虽然在本层可选注入，
但真正下载模型只在用户显式启用 `--vector` 时发生。

检索器选择只发生在一处（_retriever）：词面 / TF-IDF / embedding 三种检索器
都是同一契约的函数，注入 smart_context 后，查询改写 / 重难点 / 并列拆分
对三种模式一视同仁。
"""

from typing import Callable, List, Optional, Sequence, Tuple

from . import config, retrieval, semantic, vector
from .llm import ExamRAGError, ask as default_ask
from .models import Chunk, as_chunks, evidence_sentences, tags_of
from .smart import RetrieveFn, smart_context
from .vector import EmbedFn

AskFn = Callable[[str], str]


def _retriever(
    semantic_mode: bool = False,
    vector_mode: bool = False,
    embed_fn: Optional[EmbedFn] = None,
) -> RetrieveFn:
    """唯一的检索器选择点：返回符合统一契约的检索函数。"""
    if vector_mode:
        return vector.retriever(embed_fn=embed_fn)
    if semantic_mode:
        return semantic.semantic_retrieve
    return retrieval.retrieve


def _hit_threshold(semantic_mode: bool = False, vector_mode: bool = False) -> float:
    """三种检索器分数口径不同，策略层命中阈值必须跟着检索器切换。"""
    if vector_mode:
        return config.VECTOR_HIT_SCORE
    if semantic_mode:
        return config.SEMANTIC_HIT_SCORE
    return config.LEXICAL_HIT_SCORE


def _mode_note(semantic_mode: bool, vector_mode: bool) -> str:
    if vector_mode:
        return "（已使用 embedding 向量检索挑选资料块）"
    if semantic_mode:
        return "（已使用 TF-IDF 语义检索挑选资料块）"
    return ""


def evidence_for_question(question: str, related: Sequence[Chunk]) -> List[dict]:
    """返回可展示的依据句：块标签 + 最相关的原句 + 词面重合度。"""
    items: List[dict] = []
    for chunk in related:
        picked = evidence_sentences(chunk.text, question, top_n=1)
        if not picked:
            continue
        items.append({
            "tag": chunk.tag,
            "level": chunk.level,
            "sentence": picked[0]["text"],
            "score": picked[0]["score"],
        })
    return items


def question_prompt(question: str, related: Sequence[Chunk]) -> str:
    """普通问答的提示词：只依据资料回答，并注明依据块。"""
    context = "\n\n".join(str(chunk) for chunk in as_chunks(related))
    return (
        "只根据以下资料回答问题。资料里没有的，就回答「资料中未提及」。"
        "回答后注明依据了哪段资料。\n\n资料：\n" + context + "\n\n问题：" + question
    )


def exam_prompt(topic: str, related: Sequence[Chunk]) -> str:
    """出题提示词：按掌握等级分布出题。"""
    context = "\n\n".join(str(chunk) for chunk in as_chunks(related))
    return (
        "根据以下资料，出 3 道复习题并给出答案，题型可以是简答题、"
        "概念辨析题、列举题。资料块标签里标了掌握等级，"
        "尽量把题出在「掌握」级内容上，「了解」级内容最多出 1 道。"
        "只依据资料，不要编造。\n\n资料：\n" + context
    )


def load_material(override: Optional[str] = None) -> List[Chunk]:
    """解析并加载资料块；空资料视为配置错误。"""
    chunks = retrieval.load_chunks(config.resolve_material(override))
    if not chunks:
        raise ExamRAGError("资料文件为空，请检查资料路径。")
    return chunks


def prepare_question(
    question: str,
    chunks: Sequence[Chunk],
    top_k: int = 3,
    ask_fn: Optional[AskFn] = None,
    semantic_mode: bool = False,
    vector_mode: bool = False,
    embed_fn: Optional[EmbedFn] = None,
) -> Tuple[List[Chunk], Optional[str], str]:
    """准备问答：返回 (检索到的块, 给用户看的说明, 提示词)。

    本函数不产出最终答案；模型调用由调用方执行，便于 dry-run 与测试注入。
    语义 / 向量模式只是换掉注入的检索器，查询改写 / 重难点策略照常生效。
    """
    ask = ask_fn or default_ask
    related, note = smart_context(
        question, chunks, top_k=top_k, ask_fn=ask,
        retrieve_fn=_retriever(semantic_mode, vector_mode, embed_fn),
        score_threshold=_hit_threshold(semantic_mode, vector_mode),
    )
    mode_note = _mode_note(semantic_mode, vector_mode)
    if mode_note:
        note = (note + " " if note else "") + mode_note
    return list(related), note, question_prompt(question, related)


def prepare_exam(
    topic: str,
    chunks: Sequence[Chunk],
    top_k: int = 3,
    semantic_mode: bool = False,
    vector_mode: bool = False,
    embed_fn: Optional[EmbedFn] = None,
) -> Tuple[List[Chunk], str, str]:
    """准备出题：返回 (检索到的块, 掌握等级串, 提示词)。出题按掌握度加权检索。"""
    related = _retriever(semantic_mode, vector_mode, embed_fn)(
        topic, chunks, top_k=top_k, weighted=True
    )
    related_list = list(related)
    levels = "、".join(chunk.level for chunk in related_list)
    return related_list, levels, exam_prompt(topic, related_list)


def answer_question(
    question: str,
    chunks: Sequence[Chunk],
    top_k: int = 3,
    ask_fn: Optional[AskFn] = None,
    semantic_mode: bool = False,
    vector_mode: bool = False,
    embed_fn: Optional[EmbedFn] = None,
) -> dict:
    """一步完成问答的结构化结果。CLI 与 API 共用，避免两处组装逻辑分叉。"""
    ask = ask_fn or default_ask
    related, note, prompt = prepare_question(
        question, chunks, top_k=top_k, ask_fn=ask,
        semantic_mode=semantic_mode, vector_mode=vector_mode, embed_fn=embed_fn,
    )
    return {
        "question": question,
        "answer": ask(prompt),
        "note": note,
        "sources": [tags_of(related)] if related else [],
        "chunks": [chunk.as_dict() for chunk in related],
        "evidence": evidence_for_question(question, related),
    }


def generate_exam(
    topic: str,
    chunks: Sequence[Chunk],
    top_k: int = 3,
    ask_fn: Optional[AskFn] = None,
    semantic_mode: bool = False,
    vector_mode: bool = False,
    embed_fn: Optional[EmbedFn] = None,
) -> dict:
    """一步完成出题的结构化结果。CLI 与 API 共用。"""
    ask = ask_fn or default_ask
    related, levels, prompt = prepare_exam(
        topic, chunks, top_k=top_k, semantic_mode=semantic_mode,
        vector_mode=vector_mode, embed_fn=embed_fn,
    )
    return {
        "topic": topic,
        "answer": ask(prompt),
        "levels": levels,
        "sources": [tags_of(related)] if related else [],
        "chunks": [chunk.as_dict() for chunk in related],
        "evidence": evidence_for_question(topic, related),
    }


def retrieve_only(
    question: str,
    chunks: Sequence[Chunk],
    top_k: int = 3,
    weighted: bool = False,
    semantic_mode: bool = False,
    vector_mode: bool = False,
    embed_fn: Optional[EmbedFn] = None,
) -> dict:
    """纯本地检索：不调用模型，返回可核对的资料块标签、等级与依据句。"""
    related = _retriever(semantic_mode, vector_mode, embed_fn)(
        question, chunks, top_k=top_k, weighted=weighted
    )
    related_list = list(related)
    return {
        "question": question,
        "count": len(related_list),
        "sources": [tags_of(related_list)] if related_list else [],
        "chunks": [chunk.as_dict() for chunk in related_list],
        "evidence": evidence_for_question(question, related_list),
    }
