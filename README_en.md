# ExamRAG

[![tests](https://github.com/huiren789/exam-rag/actions/workflows/tests.yml/badge.svg)](https://github.com/huiren789/exam-rag/actions/workflows/tests.yml)
![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue)
![MIT](https://img.shields.io/badge/license-MIT-green)
[![Live demo](https://img.shields.io/badge/demo-live-green)](https://examrag-demo.app.workbuddy.host/?sharecode=YTW7YFIS3R)

<div align="center">

<img src="assets/demo.png" alt="ExamRAG demo: ask, retrieve, cite" width="880">

**A course reviewer you can check against the source**

Answers point back to the exact sentence they came from. Retrieval runs locally, and the reading material is yours to replace.

[Live demo (no API key)](https://examrag-demo.app.workbuddy.host/?sharecode=YTW7YFIS3R) ·
[The problem](#the-problem) ·
[Use your own course in 30 seconds](#use-your-own-course-in-30-seconds)

</div>

**Language**: [中文](README.md) · **English** · [日本語](README_ja.md) · [한국어](README_ko.md) · [Español](README_es.md)

> The bundled *Educational Measurement* text is a sample. Replace `data/material.txt` and the same pipeline works for any course. Core retrieval needs only the Python standard library. The author used it for their own revision and ran four rounds of changes against a self-built question set.

## The problem

Ask a model straight away and the answer reads well but has no traceable source. Read the textbook yourself and you spend the time hunting for the right paragraph.

ExamRAG keeps the "find the material" step on your machine. Retrieval is offline and visible; only the selected chunks go to the model. The prompt requires the model to use only those chunks, name the source at the end, and answer "not mentioned in the material" when the data doesn't cover the question.

## Use your own course in 30 seconds

The included material is just an example. Your notes need to be plain text with the tags the parser recognizes. Keep the tag names in Chinese:

```text
【掌握·Concept name】One idea per paragraph.
【理解·Another concept】...
【了解·A third concept】...
```

The three tags — 掌握 / 理解 / 了解 (mastered / understood / familiar) — set how heavily each chunk is weighted when generating questions. Then:

```bash
python -m examrag -q "your question" --material my.txt
```

Or set `EXAMRAG_MATERIAL=my.txt` once instead of passing the flag each time. Swap the file and everything downstream keeps working: retrieval, citations, weighted question generation, the Web UI. The tool isn't tied to one course. See [Material format](#material-format) for the details.

## Features

- **Local lexical retrieval**: bigram counts, title boost, lower weight for table-of-contents and summary blocks. Python standard library only.
- **TF-IDF retrieval**: `--semantic`, also offline and dependency-free.
- **Vector retrieval**: `--vector`, with cached embeddings. Install `pip install -e ".[vector]"` and download a model on first use.
- **Sentence-level evidence**: results name the matched source sentences and their lexical overlap. In the Web UI, clicking a source or evidence line highlights the corresponding chunk in the results.
- **Weighted question generation**: 掌握 chunks at ×3, 理解 at ×2, 了解 at ×1.
- **Query rewriting, key-point summaries, split-concept retrieval**: all run through one `retrieve_fn` contract, so every retrieval mode gets them.
- **Offline dry-run**: `--dry-run` prints the retrieval results and the assembled prompt without a network call or API key. `--vector` still works offline with a deterministic stub.
- **Web UI and FastAPI**: three tabs (ask / quiz / retrieve-only) and five endpoints with auto-generated Swagger docs.
- **89 offline tests**, CI on Python 3.8 / 3.11 / 3.13, plus ruff linting.

## Quick start

```bash
git clone https://github.com/huiren789/exam-rag.git
cd exam-rag
python -m examrag -q "What is difficulty?" --dry-run   # offline, no key
python -m examrag                                       # interactive mode
```

To call a real model, copy `.env.example` to `.env` and set `SILICONFLOW_API_KEY`. Any OpenAI-compatible endpoint works through `EXAMRAG_BASE_URL`. The [live demo](https://examrag-demo.app.workbuddy.host/?sharecode=YTW7YFIS3R) uses WorkBuddy Cloud for generation, so no key is needed there; retrieval and citation still come from the local backend.

## Evaluation

Nine hand-labeled questions and their expected chunks live in `examples/eval_cases.json`. Run `python -m examrag.evaluate --mode lexical|semantic|vector`.

| Mode | hit@1 | hit@3 | MRR |
| --- | --- | --- | --- |
| Lexical (default) | 0.778 | 0.889 | 0.815 |
| TF-IDF | 0.556 | 1.000 | 0.741 |

These are regression numbers on a historical sample. They say nothing about how often the tool is right during real revision.

## Material format

Write one concept per paragraph and mark each block with 掌握 / 理解 / 了解. The bundled *Educational Measurement* material has 99 blocks covering chapters 1, 2, 4, 5 and 6, plus end-of-chapter summaries and exercises. Chapter 3 has no body blocks in the source material, and chapter 6 has no separate heading line. That's how the source is; it hasn't been filled in artificially.

## Known limitations

- Default retrieval matches words. TF-IDF helps with different phrasing; embeddings are needed for synonym-level recall.
- Evidence sentences are split on Chinese punctuation. Very long or cross-sentence claims may be located imprecisely.
- Material must be formatted by hand — no PDF or Word import yet.
- No conversation history; each question is retrieved independently.
- The HTTP API binds to 127.0.0.1 with no authentication. Add auth and rate limiting before exposing it.
- Answer quality depends on the model. The call chain is covered by stub functions and a local mock server; no commercial API has been called with a real key.
- Don't put API keys in material files. Untrusted material can carry prompt injection.

## Docs

[中文完整文档](README.md) · [Architecture decisions](docs/adr) · [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)

## License

[MIT](LICENSE) © 2026 huiren789
