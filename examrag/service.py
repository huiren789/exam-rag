"""共用业务层：CLI 与 HTTP API 共享的检索、提示词与结果组装逻辑。

只依赖 Python 标准库和项目内部模块，不引入任何第三方库。
把「检索 + 组装提示词」和「调用模型」分开，是因为前者可离线测试、
且 CLI 需要在调用模型前先打印检索标签，API 则需要结构化返回。
"""

from typing import Callable, List, Optional, Sequence, Tuple

from . import config
from .llm import ExamRAGError, ask as default_ask
from .retrieval import level_of, load_chunks, retrieve, tags_of
from .smart import smart_context

AskFn = Callable[[str], str]


def question_prompt(question: str, related: Sequence[str]) -> str:
    """普通问答的提示词：只依据资料回答，并注明依据块。"""
    context = "\n\n".join(related)
    return (
        "只根据以下资料回答问题。资料里没有的，就回答「资料中未提及」。"
        "回答后注明依据了哪段资料。\n\n资料：\n" + context + "\n\n问题：" + question
    )


def exam_prompt(topic: str, related: Sequence[str]) -> str:
    """出题提示词：按掌握等级分布出题。"""
    context = "\n\n".join(related)
    return (
        "根据以下资料，出 3 道复习题并给出答案，题型可以是简答题、"
        "概念辨析题、列举题。资料块标签里标了掌握等级，"
        "尽量把题出在「掌握」级内容上，「了解」级内容最多出 1 道。"
        "只依据资料，不要编造。\n\n资料：\n" + context
    )


def load_material(override: Optional[str] = None) -> List[str]:
    """解析并加载资料块；空资料视为配置错误。"""
    chunks = load_chunks(config.resolve_material(override))
    if not chunks:
        raise ExamRAGError("资料文件为空，请检查资料路径。")
    return chunks


def prepare_question(
    question: str,
    chunks: Sequence[str],
    top_k: int = 3,
    ask_fn: Optional[AskFn] = None,
) -> Tuple[List[str], Optional[str], str]:
    """准备问答：返回 (检索到的块, 给用户看的说明, 提示词)。

    本函数不产出最终答案；模型调用由调用方执行，便于 dry-run 与测试注入。
    """
    ask = ask_fn or default_ask
    related, note = smart_context(question, chunks, top_k=top_k, ask_fn=ask)
    return list(related), note, question_prompt(question, related)


def prepare_exam(
    topic: str,
    chunks: Sequence[str],
    top_k: int = 3,
) -> Tuple[List[str], str, str]:
    """准备出题：返回 (检索到的块, 掌握等级串, 提示词)。出题按掌握度加权检索。"""
    related = retrieve(topic, chunks, top_k=top_k, weighted=True)
    levels = "、".join(level_of(chunk) for chunk in related)
    return list(related), levels, exam_prompt(topic, related)


def answer_question(
    question: str,
    chunks: Sequence[str],
    top_k: int = 3,
    ask_fn: Optional[AskFn] = None,
) -> dict:
    """一步完成问答，返回结构化结果（供 HTTP API 使用）。"""
    ask = ask_fn or default_ask
    related, note, prompt = prepare_question(question, chunks, top_k=top_k, ask_fn=ask)
    answer = ask(prompt)
    return {
        "question": question,
        "answer": answer,
        "note": note,
        "sources": [tags_of(related)] if related else [],
        "chunks": related,
    }


def generate_exam(
    topic: str,
    chunks: Sequence[str],
    top_k: int = 3,
    ask_fn: Optional[AskFn] = None,
) -> dict:
    """一步完成出题，返回结构化结果（供 HTTP API 使用）。"""
    ask = ask_fn or default_ask
    related, levels, prompt = prepare_exam(topic, chunks, top_k=top_k)
    answer = ask(prompt)
    return {
        "topic": topic,
        "answer": answer,
        "levels": levels,
        "sources": [tags_of(related)] if related else [],
        "chunks": related,
    }


def retrieve_only(
    question: str,
    chunks: Sequence[str],
    top_k: int = 3,
    weighted: bool = False,
) -> dict:
    """纯本地检索：不调用模型，返回可核对的资料块标签与等级。"""
    related = retrieve(question, chunks, top_k=top_k, weighted=weighted)
    return {
        "question": question,
        "count": len(related),
        "sources": [tags_of(related)] if related else [],
        "chunks": [
            {"tag": tags_of([chunk]), "level": level_of(chunk), "text": chunk}
            for chunk in related
        ],
    }
