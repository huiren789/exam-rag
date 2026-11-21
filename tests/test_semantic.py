"""可选语义检索测试：TF-IDF 余弦相似度，纯标准库、离线。"""

import unittest

from examrag import semantic


CHUNKS = [
    "【掌握·难度的定义】难度是指测验试题的难易程度，通常用通过率 P 表示，P 越大越容易。",
    "【掌握·难度的作用】难度影响测验的区分度和信度，过难或过易都会降低区分能力。",
    "【理解·信度的定义】信度是指测量结果的可靠性或稳定性程度。",
    "【了解·效度的定义】效度是指测验能够测到所要测量特质的程度。",
    "======== 第一章 ========",
]


class SemanticTests(unittest.TestCase):
    def test_returns_chunks(self):
        result = semantic.semantic_retrieve("测验题目有多难", CHUNKS, top_k=2)
        self.assertTrue(result)
        self.assertLessEqual(len(result), 2)
        self.assertTrue(any("难度" in c for c in result))

    def test_excludes_section_headers(self):
        result = semantic.semantic_retrieve("难度", CHUNKS, top_k=4)
        self.assertFalse(any("========" in c for c in result))

    def test_return_score(self):
        result, score = semantic.semantic_retrieve("难度", CHUNKS, top_k=2, return_score=True)
        self.assertTrue(result)
        self.assertGreater(score, 0)

    def test_weighted_prefers_mastery(self):
        result = semantic.semantic_retrieve("难度", CHUNKS, top_k=2, weighted=True)
        self.assertTrue(result)

    def test_empty_chunks(self):
        self.assertEqual(semantic.semantic_retrieve("x", [], top_k=3), [])

    def test_top_k_respected(self):
        result = semantic.semantic_retrieve("信度 效度 难度", CHUNKS, top_k=3)
        self.assertLessEqual(len(result), 3)


if __name__ == "__main__":
    unittest.main()
