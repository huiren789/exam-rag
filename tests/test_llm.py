"""LLM 层单元测试：mock 网络调用，覆盖错误翻译与成功路径。"""

import json
import unittest
import urllib.error
from unittest import mock

from examrag.llm import ExamRAGError, ask


def _fake_response(body: bytes):
    """构造支持 with 语句的假 HTTP 响应。"""
    response = mock.MagicMock()
    response.__enter__.return_value.read.return_value = body
    return response


class AskTests(unittest.TestCase):
    def test_missing_api_key(self):
        with mock.patch.dict("os.environ", {}, clear=True), \
             mock.patch("examrag.config._load_dotenv", return_value={}):
            with self.assertRaises(ExamRAGError) as ctx:
                ask("问题")
        self.assertIn("SILICONFLOW_API_KEY", str(ctx.exception))

    def test_http_401_friendly(self):
        error = urllib.error.HTTPError("http://x", 401, "Unauthorized", {}, None)
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(ExamRAGError) as ctx:
                ask("问题", api_key="sk-test")
        self.assertIn("SILICONFLOW_API_KEY", str(ctx.exception))

    def test_network_error_friendly(self):
        with mock.patch("urllib.request.urlopen",
                        side_effect=urllib.error.URLError("network down")):
            with self.assertRaises(ExamRAGError) as ctx:
                ask("问题", api_key="sk-test")
        self.assertIn("网络", str(ctx.exception))

    def test_bad_json(self):
        with mock.patch("urllib.request.urlopen",
                        return_value=_fake_response(b"not-json")):
            with self.assertRaises(ExamRAGError) as ctx:
                ask("问题", api_key="sk-test")
        self.assertIn("JSON", str(ctx.exception))

    def test_missing_choices(self):
        body = json.dumps({"unexpected": 1}).encode("utf-8")
        with mock.patch("urllib.request.urlopen", return_value=_fake_response(body)):
            with self.assertRaises(ExamRAGError) as ctx:
                ask("问题", api_key="sk-test")
        self.assertIn("choices", str(ctx.exception))

    def test_success_and_auth_header(self):
        body = json.dumps(
            {"choices": [{"message": {"content": "这是答案"}}]}
        ).encode("utf-8")
        with mock.patch("urllib.request.urlopen", return_value=_fake_response(body)) as urlopen:
            result = ask("问题", api_key="sk-test", model="test-model")
        self.assertEqual(result, "这是答案")
        request = urlopen.call_args[0][0]
        self.assertEqual(request.get_header("Authorization"), "Bearer sk-test")
        self.assertIn("test-model", request.data.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
