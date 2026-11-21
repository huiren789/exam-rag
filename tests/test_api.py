"""HTTP API 测试：缺 fastapi/httpx 时整类跳过，不影响零依赖环境。"""

import os
import unittest
from unittest import mock

from examrag.models import as_chunks  # noqa: F401 供外部复用本模块时参考
from tests.helpers import SAMPLE_CHUNKS, fake_embed, stub_ask

try:
    from fastapi.testclient import TestClient
    from examrag.api import create_app
    from examrag import service
    HAS_API_DEPS = True
except ImportError:
    HAS_API_DEPS = False

CHUNKS = SAMPLE_CHUNKS


@unittest.skipUnless(HAS_API_DEPS, "未安装 fastapi/httpx，跳过 API 测试")
class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app(chunks=CHUNKS, ask_fn=stub_ask))

    def test_health(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")
        self.assertEqual(r.json()["chunks_available"], 3)
        self.assertIn("vector_available", r.json())
        # 不回传本机绝对路径
        self.assertNotIn("\\", r.json()["material"])
        self.assertNotIn("/", r.json()["material"])

    def test_vector_retrieve(self):
        client = TestClient(create_app(chunks=CHUNKS, embed_fn=fake_embed))
        r = client.post("/retrieve", json={
            "question": "难度", "top_k": 2, "vector": True,
        })
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertGreaterEqual(data["count"], 1)
        self.assertTrue(data["evidence"])
        self.assertEqual(data["chunks"][0]["tag"], "掌握·难度的定义")

    def test_vector_ask_and_exam(self):
        client = TestClient(create_app(chunks=CHUNKS, embed_fn=fake_embed, ask_fn=stub_ask))
        r = client.post("/ask", json={"question": "难度", "top_k": 2, "vector": True})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["evidence"])
        r = client.post("/exam", json={"topic": "难度", "top_k": 2, "vector": True})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["evidence"])

    def test_evidence_in_answer(self):
        r = self.client.post("/ask", json={"question": "难度的定义", "top_k": 2})
        self.assertEqual(r.status_code, 200)
        evidence = r.json()["evidence"]
        self.assertTrue(evidence)
        self.assertIn("sentence", evidence[0])

    def test_retrieve_offline(self):
        r = self.client.post("/retrieve", json={"question": "难度的定义", "top_k": 2})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["count"], 2)
        self.assertIn("tag", data["chunks"][0])

    def test_retrieve_weighted(self):
        r = self.client.post("/retrieve", json={
            "question": "信度", "top_k": 2, "weighted": True,
        })
        self.assertEqual(r.status_code, 200)

    def test_ask(self):
        r = self.client.post("/ask", json={"question": "难度的定义是什么", "top_k": 2})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("测试桩", data["answer"])
        self.assertTrue(data["sources"])
        self.assertEqual(data["question"], "难度的定义是什么")

    def test_exam(self):
        r = self.client.post("/exam", json={"topic": "信度", "top_k": 2})
        self.assertEqual(r.status_code, 200)
        self.assertIn("测试桩", r.json()["answer"])

    def test_semantic_retrieve(self):
        r = self.client.post("/retrieve", json={
            "question": "测验题目有多难", "top_k": 2, "semantic": True,
        })
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(r.json()["count"], 1)

    def test_semantic_ask(self):
        r = self.client.post("/ask", json={
            "question": "难度", "top_k": 2, "semantic": True,
        })
        self.assertEqual(r.status_code, 200)
        self.assertIn("语义检索", r.json()["note"])

    def test_invalid_top_k(self):
        r = self.client.post("/retrieve", json={"question": "x", "top_k": 0})
        self.assertEqual(r.status_code, 400)
        self.assertIn("top_k", r.json()["detail"])

    def test_missing_material_never_leaks_path(self):
        """资料路径错误时，错误响应必须不含本机绝对路径（H1 回归测试）。"""
        missing = "data/no_such_material_for_test.txt"

        for endpoint, payload in (
            ("/retrieve", {"question": "难度"}),
            ("/ask", {"question": "难度"}),
            ("/exam", {"topic": "难度"}),
        ):
            r = self.client.post(endpoint, json={**payload, "material": missing})
            self.assertEqual(r.status_code, 400, msg=endpoint)
            detail = r.json()["detail"]
            # 不含盘符、反斜杠、仓库根目录等任何文件系统痕迹
            self.assertNotIn("\\", detail, msg=detail)
            self.assertNotIn("no_such_material", detail, msg=detail)
            self.assertIn("EXAMRAG_MATERIAL", detail, msg=detail)

        # /health 在资料缺失时同样只给固定文案（app 不注入 chunks 才会真读文件）
        with mock.patch.dict(os.environ, {"EXAMRAG_MATERIAL": missing}, clear=False):
            client = TestClient(create_app(ask_fn=stub_ask))
            r = client.get("/health")
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertEqual(data["status"], "degraded")
            self.assertEqual(data["material_error"], "资料文件不可读")
            self.assertNotIn("\\", data["material_error"])
            # material 字段只允许文件名（相对名），不允许出现路径分隔符或盘符
            self.assertNotIn("\\", data["material"])
            self.assertNotIn("/", data["material"])
            self.assertNotIn(":", data["material"])

    def test_model_error_becomes_400(self):
        def broken(prompt):
            from examrag.llm import ExamRAGError
            raise ExamRAGError("未检测到 API Key")

        client = TestClient(create_app(chunks=CHUNKS, ask_fn=broken))
        r = client.post("/ask", json={"question": "难度", "top_k": 2})
        self.assertEqual(r.status_code, 400)
        self.assertIn("API Key", r.json()["detail"])

    def test_openapi_docs(self):
        r = self.client.get("/docs")
        self.assertEqual(r.status_code, 200)
        r = self.client.get("/openapi.json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("/ask", r.json()["paths"])

    def test_web_index(self):
        from examrag.web import create_web_app
        client = TestClient(create_web_app())
        r = client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("ExamRAG", r.text)
        self.assertIn("只看检索", r.text)
        # 新增交互结构：主题切换按钮 / 检索历史容器 / 溯源 data-tag 渲染逻辑
        self.assertIn("theme-btn", r.text)
        self.assertIn('id="history"', r.text)
        self.assertIn("data-tag", r.text)
        self.assertIn("examrag-theme", r.text)
        r = client.get("/static/index.html")
        self.assertEqual(r.status_code, 200)


if __name__ == "__main__":
    unittest.main()
