"""检索策略层：查询改写、重难点汇总与并列概念拆分。

这些策略会调用模型，但通过 ask_fn 注入网络调用——
因此测试与 --dry-run 可以用桩函数替换，完全离线运行。
"""

import re
from typing import Callable, List, Optional, Sequence, Tuple

from .config import FOCUS_KEYS
from .llm import ExamRAGError, ask as default_ask
from .retrieval import retrieve

AskFn = Callable[[str], str]


def focus_retrieve(
    question: str,
    chunks: Sequence[str],
    top_k: int = 6,
    ask_fn: Optional[AskFn] = None,
) -> List[str]:
    """重难点检索：让模型从标题清单中挑出最相关的掌握级块。

    问"整门课/整本书"时名额放宽到 8 块；模型返回空或格式异常时返回空列表，
    由 smart_context 回退到普通检索。
    """
    ask = ask_fn or default_ask
    if any(key in question for key in ("整门课", "整本书", "全课程", "所有章", "课程的重难点")):
        top_k = 8

    idx_map: List[int] = []
    lines: List[str] = []
    for index, chunk in enumerate(chunks):
        if chunk.startswith("========"):
            continue
        match = re.match(r"【([^】]*)】", chunk)
        lines.append(str(len(idx_map)) + ":" + (match.group(1) if match else chunk[:12]))
        idx_map.append(index)

    if not idx_map:
        return []

    try:
        ids = ask(
            "下面是一份课程资料的块标题列表。用户的问题是：" + question + "\n"
            "请挑出与问题所问主题最相关、最能代表考试重点的块（优先掌握级，"
            "导图和小结也很有用），最多 " + str(top_k) + " 个。"
            "只输出编号，用空格分隔，不要输出其他内容：\n" + "\n".join(lines)
        )
    except ExamRAGError:
        return []

    picked = []
    for token in (ids or "").split():
        if token.isdigit() and int(token) < len(idx_map):
            picked.append(chunks[idx_map[int(token)]])
    return picked[:top_k]


def multi_retrieve(
    question: str,
    chunks: Sequence[str],
    top_k: int = 3,
    ask_fn: Optional[AskFn] = None,
) -> List[str]:
    """并列概念拆分：如"信度和难度"分成两段各检索一次，再与整题结果合并去重。

    本函数不调用模型，ask_fn 参数只为与策略层统一签名。
    """
    del ask_fn  # 保留参数以统一策略层接口，当前实现不需要模型
    parts = [
        part for part in re.split(r"和|与|以及|[，,。；;？！?!、]+", question)
        if len(part.strip()) >= 2
    ]
    base, best = retrieve(question, chunks, return_score=True)
    if best < 5 or len(parts) < 2:
        return base if base else list(chunks[:top_k])

    per = [retrieve(part, chunks, top_k=1) for part in parts[:4]]
    merged: List[str] = []
    seen = set()
    candidates = ([base[0]] if base else []) + [hit[0] for hit in per if hit] + list(base[1:])
    for chunk in candidates:
        if chunk not in seen:
            seen.add(chunk)
            merged.append(chunk)
        if len(merged) >= top_k:
            break
    return merged


def smart_context(
    question: str,
    chunks: Sequence[str],
    top_k: int = 3,
    ask_fn: Optional[AskFn] = None,
) -> Tuple[List[str], Optional[str]]:
    """为问题挑选上下文，并返回一句给用户看的说明（无说明则为 None）。

    流程：重难点类问题走专用挑选；检索得分 < 5 时让模型提取关键词重试；
    否则走并列概念拆分。模型不可用时一律回退普通检索。
    """
    ask = ask_fn or default_ask
    related, best = retrieve(question, chunks, return_score=True)

    if any(key in question for key in FOCUS_KEYS):
        picked = focus_retrieve(question, chunks, ask_fn=ask)
        if picked:
            return picked, "（检测到重难点类问题，已按资料块的掌握级标签挑选内容）"

    if best < 5:
        try:
            keywords = ask(
                "从下面的提问里提取2到4个适合检索课程资料的关键词，"
                "只输出关键词，用空格分隔，不要输出其他内容：\n" + question
            )
        except ExamRAGError:
            return related if related else list(chunks[:top_k]), None
        if keywords and keywords.strip():
            related2, best2 = retrieve(keywords.strip(), chunks, return_score=True)
            if best2 > best:
                note = "（问题里没检索到关键词，已自动提取「" + " ".join(keywords.split()[:4]) + "」重试）"
                return related2, note
        return related if related else list(chunks[:top_k]), None

    return multi_retrieve(question, chunks, top_k=top_k, ask_fn=ask), None
