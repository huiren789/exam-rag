"""HTTP API 测试：缺 fastapi/httpx 时整类跳过，不影响零依赖环境。"""

import unittest

from examrag.models import as_chunks

try:
    from fastapi.testclient import TestClient
    from examrag.api import create_app
    from examrag import service
    HAS_API_DEPS = True
except ImportError:
    HAS_API_DEPS = False

CHUNKS = as_chunks([
    "【掌握·难度的定义】难度是试题难易程度的指标，常用通过率 P 表示。",
    "【理解·信度的定义】信度是测验结果的一致性、稳定性程度。",
    "【了解·效度的定义】效度指测验测到所要测特质的程度。",
])


@unittest.skipUnless(HAS_API_DEPS, "未安装 fastapi/httpx，跳过 API 测试")
class ApiTests(unittest.TestCase):
    def setUp(self):
        stub = lambda prompt: "【测试桩】依据资料回答。"
        self.client = TestClient(create_app(chunks=CHUNKS, ask_fn=stub))

    def test_health(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")
        self.assertEqual(r.json()["chunks_available"], 3)
        # 不回传本机绝对路径
        self.assertNotIn("\\", r.json()["material"])
        self.assertNotIn("/", r.json()["material"])

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
        r = client.get("/static/index.html")
        self.assertEqual(r.status_code, 200)


if __name__ == "__main__":
    unittest.main()
