"""命令行界面：argparse 单次查询 + 原交互式 REPL + 离线 dry-run。"""

import argparse
from typing import Callable, List, Sequence

from . import config
from .llm import ExamRAGError, ask as default_ask
from .retrieval import level_of, load_chunks, retrieve, tags_of
from .smart import smart_context

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
    parser.add_argument("--version", action="version", version="ExamRAG " + config.VERSION)
    return parser


def _dry_run_ask(prompt: str) -> str:
    """dry-run 的模型桩：打印提示词，返回空串，绝不联网。"""
    print("\n--- 真实模式下将发送给模型的提示词 ---")
    print(prompt)
    print("--- （已跳过 API 调用，dry-run 模式）---\n")
    return ""


def _exam_prompt(topic: str, related: Sequence[str]) -> str:
    context = "\n\n".join(related)
    return (
        "根据以下资料，出 3 道复习题并给出答案，题型可以是简答题、"
        "概念辨析题、列举题。资料块标签里标了掌握等级，"
        "尽量把题出在「掌握」级内容上，「了解」级内容最多出 1 道。"
        "只依据资料，不要编造。\n\n资料：\n" + context
    )


def _question_prompt(question: str, related: Sequence[str]) -> str:
    context = "\n\n".join(related)
    return (
        "只根据以下资料回答问题。资料里没有的，就回答「资料中未提及」。"
        "回答后注明依据了哪段资料。\n\n资料：\n" + context + "\n\n问题：" + question
    )


def _run_exam(
    topic: str,
    chunks: Sequence[str],
    top_k: int,
    ask_fn: AskFn,
    dry_run: bool,
) -> None:
    """出题模式：按掌握等级加权检索，再让模型出题。"""
    related = retrieve(topic, chunks, top_k=top_k, weighted=True)
    levels = "、".join(level_of(chunk) for chunk in related)
    print("（检索到：" + tags_of(related) + "｜等级：" + levels + "）")
    answer = ask_fn(_exam_prompt(topic, related))
    if not dry_run:
        print("\nAI：", answer, "\n")


def _run_question(
    question: str,
    chunks: Sequence[str],
    top_k: int,
    ask_fn: AskFn,
    dry_run: bool,
) -> None:
    """普通问答：检索上下文、拼提示词、输出回答。"""
    related, note = smart_context(question, chunks, top_k=top_k, ask_fn=ask_fn)
    if note:
        print(note)
    print("（检索到：" + tags_of(related) + "）")
    answer = ask_fn(_question_prompt(question, related))
    if not dry_run:
        print("\nAI：", answer, "\n")


def _repl(chunks: List[str], top_k: int, ask_fn: AskFn, dry_run: bool) -> None:
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
            _run_exam(topic, chunks, top_k, ask_fn, dry_run)
        else:
            _run_question(cmd, chunks, top_k, ask_fn, dry_run)


def main(argv: List[str] = None) -> int:
    """程序入口；返回进程退出码，便于 python -m examrag 使用。"""
    args = build_parser().parse_args(argv)
    if args.top_k < 1:
        print("错误：--top-k 必须大于等于 1。")
        return 1

    ask_fn: AskFn = _dry_run_ask if args.dry_run else default_ask
    try:
        chunks = load_chunks(config.resolve_material(args.material))
        if not chunks:
            raise ExamRAGError("资料文件为空，请检查 --material 指向的文件。")

        if args.exam is not None:
            topic = (args.exam or args.topic or args.question or "").strip()
            if not topic:
                raise ExamRAGError("请提供出题主题，例如：--exam 信度")
            _run_exam(topic, chunks, args.top_k, ask_fn, args.dry_run)
        elif args.question:
            _run_question(args.question, chunks, args.top_k, ask_fn, args.dry_run)
        elif args.topic:
            _run_question(args.topic, chunks, args.top_k, ask_fn, args.dry_run)
        else:
            _repl(chunks, args.top_k, ask_fn, args.dry_run)
    except (ExamRAGError, FileNotFoundError) as exc:
        print("错误：" + str(exc))
        return 1
    except KeyboardInterrupt:
        print("\n已中断。")
        return 130
    return 0
