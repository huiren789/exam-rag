"""检索评测：用人工标注的问题→应命中块，计算 hit@1 / hit@3 / MRR。

这是历史样本上的回归指标，不是模型能力或考试通过率的估计值。
支持三种模式：lexical（词面）、semantic（TF-IDF）、vector（可选 embedding）。

用法：
    python -m examrag.evaluate --mode lexical
    python -m examrag.evaluate --mode semantic
    python -m examrag.evaluate --mode vector   # 需先装 .[vector]
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import config, retrieval, semantic, service, vector
from .llm import ExamRAGError
from .models import Chunk

DEFAULT_CASES = config.ROOT / "examples" / "eval_cases.json"


def load_cases(path: Optional[str] = None) -> List[dict]:
    """读取评测集；缺文件给出明确错误。"""
    target = Path(path) if path else DEFAULT_CASES
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        raise ExamRAGError("评测集读取失败：" + str(exc)) from exc
    cases = data.get("cases") if isinstance(data, dict) else None
    if not cases:
        raise ExamRAGError("评测集为空或格式不正确。")
    return cases


def _mode_retriever(mode: str, embed_fn=None):
    if mode == "lexical":
        return retrieval.retrieve
    if mode == "semantic":
        return semantic.semantic_retrieve
    if mode == "vector":
        return vector.retriever(embed_fn=embed_fn)
    raise ExamRAGError("未知检索模式：" + mode + "（可选 lexical / semantic / vector）")


def run(
    mode: str = "lexical",
    cases_path: Optional[str] = None,
    chunks: Optional[Sequence[Chunk]] = None,
    embed_fn=None,
    top_k: int = 3,
) -> Tuple[Dict[str, Any], List[dict]]:
    """返回 (汇总指标, 逐条明细)。"""
    if top_k < 1:
        raise ExamRAGError("top_k 必须大于等于 1。")
    blocks = list(chunks) if chunks is not None else service.load_material()
    do_retrieve = _mode_retriever(mode, embed_fn)
    cases = load_cases(cases_path)

    details: List[dict] = []
    for case in cases:
        question = case["question"]
        expected = set(case["expected"])
        # 注意：检索器零分时会退回兜底块，这些块也计入 retrieved 与排名。
        # 这是刻意口径——真实使用时用户看到的正是兜底结果，指标应如实反映。
        hits = [c.tag for c in do_retrieve(question, blocks, top_k=top_k)]
        rank = next((i + 1 for i, tag in enumerate(hits) if tag in expected), 0)
        details.append({
            "question": question,
            "expected": sorted(expected),
            "retrieved": hits,
            "rank": rank,
            "hit@1": 1 if rank == 1 else 0,
            "hit@3": 1 if 0 < rank <= 3 else 0,
        })

    total = len(details)
    hit1 = sum(d["hit@1"] for d in details)
    hit3 = sum(d["hit@3"] for d in details)
    mrr = sum(1.0 / d["rank"] for d in details if d["rank"]) / total if total else 0.0
    summary = {
        "mode": mode,
        "cases": total,
        "top_k": top_k,
        "hit@1": round(hit1 / total, 3) if total else 0.0,
        "hit@3": round(hit3 / total, 3) if total else 0.0,
        "mrr": round(mrr, 3),
    }
    return summary, details


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="examrag-evaluate", description="在标注评测集上比较三种检索模式"
    )
    parser.add_argument("--mode", default="lexical", choices=["lexical", "semantic", "vector"])
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--cases", help="自定义评测集 JSON 路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON 而非表格")
    args = parser.parse_args(argv)

    try:
        summary, details = run(args.mode, args.cases, top_k=args.top_k)
    except ExamRAGError as exc:
        print("错误：" + str(exc))
        return 1

    if args.json:
        print(json.dumps({"summary": summary, "details": details}, ensure_ascii=False, indent=2))
        return 0

    print("模式 %s ｜ 用例 %d ｜ hit@1 %.3f ｜ hit@3 %.3f ｜ MRR %.3f" % (
        summary["mode"], summary["cases"], summary["hit@1"], summary["hit@3"], summary["mrr"]
    ))
    for item in details:
        mark = "√" if item["hit@3"] else "×"
        print(" %s %-24s 命中第 %s 位  期望=%s" % (
            mark, item["question"], item["rank"] or "-", "、".join(item["expected"])
        ))
    print("说明：这些是历史样本上的回归指标，不是成功率预测。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
