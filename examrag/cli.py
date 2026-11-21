"""命令行界面：argparse 单次查询 + 原交互式 REPL + 离线 dry-run。"""

import argparse
from typing import Callable, List, Sequence

from . import config, service
from .llm import ExamRAGError, ask as default_ask
from .models import Chunk
from .retrieval import tags_of

AskFn = Callable[[str], str]

INTRO = (
    "输入问题直接问知识点；「出题 <主题>」出复习题；「XX的重难点」列考试重点；"
    "输入「退出」结束。资料没有的答「未提及」。详情见 README。"
)


def build_parser() -> argparse.ArgumentParser:
    """构造命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="examrag",
        description="ExamRAG — 有据可依的复习搭档。只依据本地资料作答，每个答案都能翻回原文核对。",
    )
    parser.add_argument("-q", "--question", metavar="问题", help="单次提问，回答后退出")
    parser.add_argument(
        "--exam", nargs="?", const="", default=None, metavar="主题",
        help="出题模式；可直接跟主题，例如 --exam 信度",
    )
    parser.add_argument("--topic", metavar="主题", help="查询某主题的知识点或重难点")
    parser.add_argument("--top-k", type=int, default=3, metavar="N", help="检索资料块数量（默认 3）")
    parser.add_argument("--material", metavar="路径", help="自定义资料文件路径（覆盖环境变量）")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="只显示检索结果与提示词，不调用模型；无需 API Key，可离线演示",
    )
    parser.add_argument(
        "--semantic", action="store_true",
        help="用 TF-IDF 语义检索挑块（默认词面匹配）；同为离线、零依赖",
    )
    parser.add_argument(
        "--vector", action="store_true",
        help="用 embedding 向量检索（需先 pip install -e '.[vector]'，首次会下载模型）",
    )
    parser.add_argument("--version", action="version", version="ExamRAG " + config.VERSION)
    return parser


def _print_evidence(question: str, related: Sequence[Chunk]) -> None:
    """打印逐句依据，方便用户翻回原文核对。"""
    items = service.evidence_for_question(question, related)
    if not items:
        return
    lines = []
    for item in items:
        sentence = item["sentence"]
        if len(sentence) > 42:
            sentence = sentence[:42] + "…"
        lines.append(item["tag"] + "：" + sentence + "（重合 " + str(item["score"]) + "）")
    print("（依据句：" + "；".join(lines) + "）")


def _dry_run_ask(prompt: str) -> str:
    """dry-run 的模型桩：打印提示词，返回空串，绝不联网。"""
    print("\n--- 真实模式下将发送给模型的提示词 ---")
    print(prompt)
    print("--- （已跳过 API 调用，dry-run 模式）---\n")
    return ""


def _run_exam(
    topic: str,
    chunks: Sequence[Chunk],
    top_k: int,
    ask_fn: AskFn,
    dry_run: bool,
    semantic_mode: bool = False,
    vector_mode: bool = False,
) -> None:
    """出题模式：按掌握等级加权检索，再让模型出题。"""
    related, levels, prompt = service.prepare_exam(
        topic, chunks, top_k=top_k,
        semantic_mode=semantic_mode, vector_mode=vector_mode,
    )
    print("（检索到：" + tags_of(related) + "｜等级：" + levels + "）")
    _print_evidence(topic, related)
    answer = ask_fn(prompt)
    if not dry_run:
        print("\nAI：", answer, "\n")


def _run_question(
    question: str,
    chunks: Sequence[Chunk],
    top_k: int,
    ask_fn: AskFn,
    dry_run: bool,
    semantic_mode: bool = False,
    vector_mode: bool = False,
) -> None:
    """普通问答：检索上下文、拼提示词、输出回答。"""
    related, note, prompt = service.prepare_question(
        question, chunks, top_k=top_k, ask_fn=ask_fn,
        semantic_mode=semantic_mode, vector_mode=vector_mode,
    )
    if note:
        print(note)
    print("（检索到：" + tags_of(related) + "）")
    _print_evidence(question, related)
    answer = ask_fn(prompt)
    if not dry_run:
        print("\nAI：", answer, "\n")


def _repl(chunks: List[Chunk], top_k: int, ask_fn: AskFn, dry_run: bool,
          semantic_mode: bool = False, vector_mode: bool = False) -> None:
    """交互式命令行循环，保留原版使用习惯。"""
    print("已加载 %d 块资料。" % len(chunks))
    print(INTRO)
    while True:
        try:
            cmd = input("你：").strip()
        except EOFError:
            break
        if not cmd:
            continue
        if cmd == "退出":
            break
        if cmd.startswith("出题"):
            topic = cmd[2:].strip()
            if not topic:
                print("请在「出题」后写上主题，例如：出题 信度")
                continue
            _run_exam(topic, chunks, top_k, ask_fn, dry_run, semantic_mode, vector_mode)
        else:
            _run_question(cmd, chunks, top_k, ask_fn, dry_run, semantic_mode, vector_mode)


def main(argv: List[str] = None) -> int:
    """程序入口；返回进程退出码，便于 python -m examrag 使用。"""
    args = build_parser().parse_args(argv)
    if args.top_k < 1:
        print("错误：--top-k 必须大于等于 1。")
        return 1

    ask_fn: AskFn = _dry_run_ask if args.dry_run else default_ask
    try:
        chunks = service.load_material(args.material)

        if args.exam is not None:
            topic = (args.exam or args.topic or args.question or "").strip()
            if not topic:
                raise ExamRAGError("请提供出题主题，例如：--exam 信度")
            _run_exam(topic, chunks, args.top_k, ask_fn, args.dry_run,
                      args.semantic, args.vector)
        elif args.question:
            _run_question(args.question, chunks, args.top_k, ask_fn, args.dry_run,
                          args.semantic, args.vector)
        elif args.topic:
            _run_question(args.topic, chunks, args.top_k, ask_fn, args.dry_run,
                          args.semantic, args.vector)
        else:
            _repl(chunks, args.top_k, ask_fn, args.dry_run,
                  args.semantic, args.vector)
    except (ExamRAGError, FileNotFoundError) as exc:
        print("错误：" + str(exc))
        return 1
    except KeyboardInterrupt:
        print("\n已中断。")
        return 130
    return 0
