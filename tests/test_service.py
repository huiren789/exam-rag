"""共用业务层测试：纯标准库，不需要密钥、不需要 fastapi。"""

import unittest

from examrag import config, service
from examrag.models import as_chunks


CHUNKS = as_chunks([
    "【掌握·难度的定义】难度是试题难易程度的指标，常用通过率 P 表示。",
    "【理解·信度的定义】信度是测验结果的一致性、稳定性程度。",
    "【了解·效度的定义】效度指测验测到所要测特质的程度。",
    "======== 第一章 ========",
])


class PromptTests(unittest.TestCase):
    def test_question_prompt_has_guard_and_source(self):
        prompt = service.question_prompt("难度的定义", CHUNKS[:1])
        self.assertIn("资料中未提及", prompt)
        self.assertIn("注明依据", prompt)
        self.assertIn("难度的定义", prompt)

    def test_exam_prompt_requires_mastery_levels(self):
        prompt = service.exam_prompt("信度", CHUNKS[:1])
        self.assertIn("出 3 道复习题", prompt)
        self.assertIn("掌握", prompt)
        self.assertIn("不要编造", prompt)


class PrepareTests(unittest.TestCase):
    def test_prepare_question_offline(self):
        # 检索分数足够时不会调用模型；桩记录调用次数应为 0。
        calls = []

        def never_called(prompt):
            calls.append(prompt)
            return ""

        related, note, prompt = service.prepare_question(
            "难度的定义", CHUNKS, top_k=2, ask_fn=never_called
        )
        self.assertTrue(related)
        self.assertLessEqual(len(related), 2)
        self.assertIn("难度", prompt)
        self.assertEqual(calls, [], "检索命中时不应触发模型调用")

    def test_prepare_exam_uses_weighted_retrieval(self):
        related, levels, prompt = service.prepare_exam("信度", CHUNKS, top_k=2)
        self.assertIn("信度", prompt)
        # 小样本里只有「理解·信度的定义」含该词，应被优先命中；
        # 关键是出题提示词拿到了带掌握等级的块，而非断言某个固定等级。
        self.assertTrue(levels)
        self.assertTrue(related)
        self.assertTrue(any("信度" in c.text for c in related))

    def test_load_material_real_file(self):
        chunks = service.load_material()
        self.assertEqual(len(chunks), 99)


class StructuredTests(unittest.TestCase):
    def test_answer_question_structure(self):
        result = service.answer_question(
            "难度的定义", CHUNKS, top_k=2, ask_fn=lambda p: "难度是试题难易指标。"
        )
        self.assertEqual(result["question"], "难度的定义")
        self.assertIn("难度", result["answer"])
        self.assertTrue(result["sources"])
        self.assertTrue(result["chunks"])
        self.assertLessEqual(len(result["chunks"]), 3)

    def test_generate_exam_structure(self):
        result = service.generate_exam(
            "信度", CHUNKS, top_k=2, ask_fn=lambda p: "1. 什么是重测信度？"
        )
        self.assertEqual(result["topic"], "信度")
        self.assertIn("重测信度", result["answer"])
        self.assertTrue(result["sources"])

    def test_retrieve_only_is_offline(self):
        result = service.retrieve_only("信度", CHUNKS, top_k=2)
        self.assertGreaterEqual(result["count"], 1)
        self.assertLessEqual(result["count"], 2)
        self.assertIn("level", result["chunks"][0])
        self.assertIn("tag", result["chunks"][0])
        # 章节标题行不参与检索
        self.assertFalse(any("========" in c["text"] for c in result["chunks"]))

    def test_semantic_modes(self):
        r = service.retrieve_only("难度的定义", CHUNKS, top_k=2, semantic_mode=True)
        self.assertGreaterEqual(r["count"], 1)
        related, note, prompt = service.prepare_question(
            "难度的定义", CHUNKS, top_k=2, semantic_mode=True
        )
        self.assertIn("语义检索", note)
        self.assertTrue(related)
        self.assertIn("难度", prompt)
        exam_related, levels, _ = service.prepare_exam(
            "难度", CHUNKS, top_k=2, semantic_mode=True
        )
        self.assertTrue(exam_related)
        self.assertTrue(levels)

    def test_semantic_hit_does_not_trigger_rewrite(self):
        """语义分数与词面分数不同量级：命中时不应误触发查询改写。"""
        calls = []

        def never_called(prompt):
            calls.append(prompt)
            return ""

        related, note, prompt = service.prepare_question(
            "难度的定义", CHUNKS, top_k=2, ask_fn=never_called, semantic_mode=True
        )
        self.assertTrue(related)
        self.assertLessEqual(len(related), 2)
        self.assertEqual(calls, [], "语义检索已有命中时不应再调模型改写")
        self.assertNotIn("自动提取", note or "")
        self.assertIn("语义检索", note or "")

    def test_semantic_miss_still_triggers_rewrite(self):
        """没命中时查询改写仍要生效，不能被阈值修复误伤。"""
        calls = []

        def rewrite(prompt):
            calls.append(prompt)
            return "难度" if "提取" in prompt else ""

        related, note, prompt = service.prepare_question(
            "zzzzzz", CHUNKS, top_k=2, ask_fn=rewrite, semantic_mode=True
        )
        self.assertTrue(calls)
        self.assertIn("自动提取", note or "")
        self.assertTrue(related)


if __name__ == "__main__":
    unittest.main()
