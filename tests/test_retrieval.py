"""检索层单元测试：全部离线，不需要 API Key。"""

import os
import tempfile
import unittest
from pathlib import Path

from examrag import config
from examrag.retrieval import (
    bigrams, clean, is_nav, level_of, load_chunks, retrieve, tags_of,
)


class CleanTests(unittest.TestCase):
    def test_removes_fillers(self):
        self.assertEqual(clean("什么是信度"), "信度")
        self.assertEqual(clean("请介绍一下难度"), "难度")

    def test_falls_back_when_empty(self):
        self.assertEqual(clean("？"), "？")


class BigramTests(unittest.TestCase):
    def test_counts_repeats(self):
        self.assertEqual(bigrams("信度信度")["信度"], 2)

    def test_ignores_whitespace(self):
        self.assertEqual(bigrams("信 度"), bigrams("信度"))

    def test_single_char(self):
        self.assertEqual(len(bigrams("信")), 0)


class ChunkTests(unittest.TestCase):
    def test_load_chunks_from_temp_file(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write("A\n\nB\n\n\nC")
            path = handle.name
        try:
            self.assertEqual(load_chunks(path), ["A", "B", "C"])
        finally:
            os.unlink(path)

    def test_load_real_material(self):
        chunks = load_chunks(config.DEFAULT_MATERIAL)
        self.assertEqual(len(chunks), 99)
        self.assertTrue(all(chunk.strip() for chunk in chunks))

    def test_level_of(self):
        self.assertEqual(level_of("【掌握·X】正文"), "掌握")
        self.assertEqual(level_of("【理解·X】正文"), "理解")
        self.assertEqual(level_of("【了解·X】正文"), "了解")
        self.assertEqual(level_of("普通文本"), "了解")

    def test_is_nav(self):
        self.assertTrue(is_nav("======== 第一章 ========"))
        self.assertTrue(is_nav("【第一章·学习目标】..."))
        self.assertFalse(is_nav("【掌握·难度】正文"))

    def test_tags_of(self):
        self.assertEqual(tags_of(["【掌握·信度】a", "【理解·效度】b"]), "掌握·信度、理解·效度")
        self.assertEqual(tags_of(["一段没有标签的正文"]), "一段没有标签的正文"[:12])


class RetrieveTests(unittest.TestCase):
    def test_exact_title_hit_ranks_first(self):
        chunks = [
            "【了解·其他】信度效度都是测量指标",
            "【掌握·难度】难度是题目难易程度的指标",
        ]
        self.assertEqual(retrieve("难度的定义", chunks)[0], chunks[1])

    def test_weighted_semantics(self):
        """锁定 dead-parameter 修复：加权只在出题模式生效。

        了解级块词面重叠更高（7 分），掌握级块重叠较低（4 分）。
        不加权时前者在前；乘以等级权重后 4*3=12 > 7，后者在前。
        """
        broad = "【了解·信度】信度信度信度信度"
        focused = "【掌握·信度】信度"
        chunks = [broad, focused]
        self.assertEqual(retrieve("信度", chunks, weighted=False)[0], broad)
        self.assertEqual(retrieve("信度", chunks, weighted=True)[0], focused)

    def test_top_k_and_return_score(self):
        chunks = ["【掌握·甲】甲甲", "【掌握·乙】乙乙", "【了解·丙】丙丙"]
        result = retrieve("甲甲", chunks, top_k=1)
        self.assertEqual(len(result), 1)
        top, best = retrieve("甲甲", chunks, return_score=True)
        self.assertIsInstance(best, (int, float))
        self.assertEqual(len(top), 1)  # 只有一块命中；全不命中时才用前 top_k 块兜底

    def test_default_path_exists(self):
        self.assertTrue(Path(config.DEFAULT_MATERIAL).is_file())


if __name__ == "__main__":
    unittest.main()
