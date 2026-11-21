"""评测脚本测试：小规模标注集，三种模式共用同一套指标口径。"""

import json
import tempfile
import unittest
from pathlib import Path

from examrag import evaluate
from tests.helpers import SAMPLE_CHUNKS, fake_embed

CHUNKS = SAMPLE_CHUNKS

CASES = {
    "cases": [
        {"question": "难度", "expected": ["掌握·难度的定义"]},
        {"question": "信度", "expected": ["理解·信度的定义"]},
    ]
}


class EvaluateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / "cases.json")
        Path(self.path).write_text(json.dumps(CASES, ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_lexical_metrics(self):
        summary, details = evaluate.run("lexical", self.path, chunks=CHUNKS)
        self.assertEqual(summary["cases"], 2)
        self.assertEqual(summary["hit@1"], 1.0)
        self.assertEqual(summary["hit@3"], 1.0)
        self.assertEqual(summary["mrr"], 1.0)
        self.assertEqual(len(details), 2)

    def test_semantic_metrics(self):
        summary, _ = evaluate.run("semantic", self.path, chunks=CHUNKS)
        self.assertEqual(summary["mode"], "semantic")
        self.assertEqual(summary["cases"], 2)

    def test_vector_metrics_with_stub(self):
        summary, _ = evaluate.run("vector", self.path, chunks=CHUNKS, embed_fn=fake_embed)
        self.assertEqual(summary["mode"], "vector")
        self.assertEqual(summary["hit@1"], 1.0)

    def test_unknown_mode(self):
        from examrag.llm import ExamRAGError
        with self.assertRaises(ExamRAGError):
            evaluate.run("unknown", self.path, chunks=CHUNKS)


if __name__ == "__main__":
    unittest.main()
