"""共用业务层：CLI 与 HTTP API 共享的检索、提示词与结果组装逻辑。

只依赖 Python 标准库和项目内部模块，不引入任何第三方库。
把「检索 + 组装提示词」和「调用模型」分开，是因为前者可离线测试、
且 CLI 需要在调用模型前先打印检索标签，API 则需要结构化返回。

检索器选择只发生在一处（_retriever）：词面或语义都是同一契约的函数，
注入 smart_context 后，查询改写 / 重难点 / 并列拆分对两种检索器都生效。
"""

from typing import Callable, List, Optional, Sequence, Tuple

from . import config, retrieval, semantic
from .llm import ExamRAGError, ask as default_ask
from .models import Chunk, as_chunks, tags_of
from .smart import RetrieveFn, smart_context

AskFn = Callable[[str], str]


def _retriever(semantic_mode: bool) -> RetrieveFn:
    """唯一的检索器选择点：返回符合统一契约的检索函数。"""
    return semantic.semantic_retrieve if semantic_mode else retrieval.retrieve


def _hit_threshold(semantic_mode: bool) -> float:
    """检索器分数口径不同，策略层命中阈值必须跟着检索器一起切换。"""
    return config.SEMANTIC_HIT_SCORE if semantic_mode else config.LEXICAL_HIT_SCORE


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
) -> Tuple[List[Chunk], Optional[str], str]:
    """准备问答：返回 (检索到的块, 给用户看的说明, 提示词)。

    本函数不产出最终答案；模型调用由调用方执行，便于 dry-run 与测试注入。
    语义模式只是换掉注入的检索器，查询改写 / 重难点策略照常生效。
    """
    ask = ask_fn or default_ask
    related, note = smart_context(
        question, chunks, top_k=top_k, ask_fn=ask,
        retrieve_fn=_retriever(semantic_mode),
        score_threshold=_hit_threshold(semantic_mode),
    )
    if semantic_mode:
        note = (note + " " if note else "") + "（已使用 TF-IDF 语义检索挑选资料块）"
    return list(related), note, question_prompt(question, related)


def prepare_exam(
    topic: str,
    chunks: Sequence[Chunk],
    top_k: int = 3,
    semantic_mode: bool = False,
) -> Tuple[List[Chunk], str, str]:
    """准备出题：返回 (检索到的块, 掌握等级串, 提示词)。出题按掌握度加权检索。"""
    related = _retriever(semantic_mode)(topic, chunks, top_k=top_k, weighted=True)
    related_list = list(related)
    levels = "、".join(chunk.level for chunk in related_list)
    return related_list, levels, exam_prompt(topic, related_list)


def answer_question(
    question: str,
    chunks: Sequence[Chunk],
    top_k: int = 3,
    ask_fn: Optional[AskFn] = None,
    semantic_mode: bool = False,
) -> dict:
    """一步完成问答的结构化结果。CLI 与 API 共用，避免两处组装逻辑分叉。"""
    ask = ask_fn or default_ask
    related, note, prompt = prepare_question(
        question, chunks, top_k=top_k, ask_fn=ask, semantic_mode=semantic_mode
    )
    return {
        "question": question,
        "answer": ask(prompt),
        "note": note,
        "sources": [tags_of(related)] if related else [],
        "chunks": [chunk.as_dict() for chunk in related],
    }


def generate_exam(
    topic: str,
    chunks: Sequence[Chunk],
    top_k: int = 3,
    ask_fn: Optional[AskFn] = None,
    semantic_mode: bool = False,
) -> dict:
    """一步完成出题的结构化结果。CLI 与 API 共用。"""
    ask = ask_fn or default_ask
    related, levels, prompt = prepare_exam(
        topic, chunks, top_k=top_k, semantic_mode=semantic_mode
    )
    return {
        "topic": topic,
        "answer": ask(prompt),
        "levels": levels,
        "sources": [tags_of(related)] if related else [],
        "chunks": [chunk.as_dict() for chunk in related],
    }


def retrieve_only(
    question: str,
    chunks: Sequence[Chunk],
    top_k: int = 3,
    weighted: bool = False,
    semantic_mode: bool = False,
) -> dict:
    """纯本地检索：不调用模型，返回可核对的资料块标签与等级。"""
    related = _retriever(semantic_mode)(
        question, chunks, top_k=top_k, weighted=weighted
    )
    related_list = list(related)
    return {
        "question": question,
        "count": len(related_list),
        "sources": [tags_of(related_list)] if related_list else [],
        "chunks": [chunk.as_dict() for chunk in related_list],
    }
