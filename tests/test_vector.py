"""可选 embedding 检索测试：用注入桩函数，无需下载模型、无需第三方依赖。"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from examrag import config, service
from examrag.llm import ExamRAGError
from examrag.models import as_chunks, evidence_sentences
from examrag.vector import embed_texts, get_embed_fn, vector_retrieve
from tests.helpers import fake_embed


CHUNKS = as_chunks([
    "【掌握·难度的定义】难度是试题难易程度的指标。常用通过率 P 表示。",
    "【了解·信度的定义】信度是测量结果的一致性程度。重测信度最常用。",
    "【了解·效度的定义】效度指测验测到所要测特质的程度。",
])


class VectorTests(unittest.TestCase):
    def test_same_contract(self):
        result = vector_retrieve("难度", CHUNKS, top_k=2, embed_fn=fake_embed)
        self.assertLessEqual(len(result), 2)
        self.assertEqual(result[0].tag, "掌握·难度的定义")

    def test_return_score(self):
        result, score = vector_retrieve(
            "难度", CHUNKS, top_k=2, return_score=True, embed_fn=fake_embed
        )
        self.assertTrue(result)
        self.assertGreater(score, 0)

    def test_weighted_prefers_mastery(self):
        blocks = as_chunks([
            "【了解·信度】信度信度",
            "【掌握·信度】信度",
        ])
        result = vector_retrieve("信度", blocks, top_k=1, weighted=True, embed_fn=fake_embed)
        self.assertEqual(result[0].level, "掌握")

    def test_empty_chunks(self):
        self.assertEqual(vector_retrieve("x", [], embed_fn=fake_embed), [])

    def test_cache_reuses_vectors(self):
        calls = []

        def counting_embed(texts):
            calls.append(list(texts))
            return fake_embed(texts)

        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "vectors.json")
            embed_texts(["难度", "信度"], counting_embed, cache_path=path)
            embed_texts(["难度", "效度"], counting_embed, cache_path=path)
            self.assertEqual(calls[0], ["难度", "信度"])
            self.assertEqual(calls[1], ["效度"])  # 只有新增文本需要计算

    def test_stub_without_cache_path_skips_default_cache(self):
        """注入向量桩且未指定缓存路径时，绝不读写默认缓存文件。

        回归背景：CI 上 dry-run 离线桩向量曾写进默认缓存，污染后续
        fake_embed 测试（桩向量与真实向量共用同一键空间）。
        """
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "vectors.json"
            with mock.patch.object(config, "get_vector_cache_path", return_value=target):
                vector_retrieve("难度", CHUNKS, embed_fn=fake_embed)
            self.assertFalse(target.exists())

    def test_missing_dependency_is_friendly(self):
        with mock.patch.dict(sys.modules, {"sentence_transformers": None}):
            with self.assertRaises(ExamRAGError) as ctx:
                get_embed_fn()
        self.assertIn("pip install", str(ctx.exception))


class VectorConfigTests(unittest.TestCase):
    def test_env_overrides_model_and_cache(self):
        import os
        from examrag import config as cfg

        old_model = os.environ.get("EXAMRAG_VECTOR_MODEL")
        old_cache = os.environ.get("EXAMRAG_VECTOR_CACHE")
        try:
            os.environ["EXAMRAG_VECTOR_MODEL"] = "custom/model"
            os.environ["EXAMRAG_VECTOR_CACHE"] = "tmp/vectors.json"
            self.assertEqual(cfg.get_vector_model(), "custom/model")
            self.assertEqual(cfg.get_vector_cache_path(), cfg.ROOT / "tmp" / "vectors.json")
        finally:
            if old_model is None:
                os.environ.pop("EXAMRAG_VECTOR_MODEL", None)
            else:
                os.environ["EXAMRAG_VECTOR_MODEL"] = old_model
            if old_cache is None:
                os.environ.pop("EXAMRAG_VECTOR_CACHE", None)
            else:
                os.environ["EXAMRAG_VECTOR_CACHE"] = old_cache

    def test_defaults_fall_back_to_constants(self):
        from examrag import config as cfg

        self.assertEqual(cfg.get_vector_model(), cfg.VECTOR_MODEL)
        self.assertEqual(cfg.get_vector_cache_path(), cfg.VECTOR_CACHE_PATH)


class VectorServiceTests(unittest.TestCase):
    def test_vector_mode_note_and_no_rewrite(self):
        calls = []

        def never_called(prompt):
            calls.append(prompt)
            return ""

        related, note, prompt = service.prepare_question(
            "难度", CHUNKS, top_k=2, ask_fn=never_called,
            vector_mode=True, embed_fn=fake_embed,
        )
        self.assertTrue(related)
        self.assertIn("embedding", note or "")
        self.assertNotIn("自动提取", note or "")
        self.assertEqual(calls, [])

    def test_retrieve_only_vector_has_evidence(self):
        data = service.retrieve_only(
            "难度", CHUNKS, top_k=2, vector_mode=True, embed_fn=fake_embed
        )
        self.assertGreaterEqual(data["count"], 1)
        self.assertLessEqual(data["count"], 2)
        self.assertTrue(data["evidence"])
        self.assertIn("sentence", data["evidence"][0])
        self.assertGreaterEqual(data["evidence"][0]["score"], 0)

    def test_vector_threshold_is_separate(self):
        self.assertNotEqual(config.VECTOR_HIT_SCORE, config.LEXICAL_HIT_SCORE)
        self.assertNotEqual(config.VECTOR_HIT_SCORE, config.SEMANTIC_HIT_SCORE)


class EvidenceTests(unittest.TestCase):
    def test_picks_sentence_with_overlap(self):
        chunk = "【掌握·难度的定义】难度是试题难易程度的指标。常用通过率 P 表示。"
        picked = evidence_sentences(chunk, "难度的定义", top_n=1)
        self.assertEqual(len(picked), 1)
        self.assertIn("难度", picked[0]["text"])
        self.assertGreater(picked[0]["score"], 0)
        self.assertNotIn("【", picked[0]["text"])


if __name__ == "__main__":
    unittest.main()
