"""配置层单元测试：环境变量、.env 解析与资料路径。"""

import os
import tempfile
import unittest
from unittest import mock

from examrag import config


class ConfigTests(unittest.TestCase):
    def test_get_api_key_from_env(self):
        with mock.patch.dict(os.environ, {"SILICONFLOW_API_KEY": "sk-env"}, clear=True):
            self.assertEqual(config.get_api_key(), "sk-env")

    def test_get_api_key_from_dotenv(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write("# 这是注释\nSILICONFLOW_API_KEY=sk-file\nEXAMRAG_MODEL=test-model\n")
            path = handle.name
        try:
            values = config._load_dotenv(path)
            self.assertEqual(values["SILICONFLOW_API_KEY"], "sk-file")
            self.assertEqual(values["EXAMRAG_MODEL"], "test-model")
            self.assertEqual(len(values), 2)
        finally:
            os.unlink(path)

    def test_resolve_material_override(self):
        self.assertEqual(str(config.resolve_material("x.txt")), "x.txt")

    def test_resolve_material_default(self):
        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch("examrag.config._load_dotenv", return_value={}):
            self.assertEqual(config.resolve_material(), config.DEFAULT_MATERIAL)

    def test_env_material_relative_to_root(self):
        with mock.patch.dict(os.environ, {"EXAMRAG_MATERIAL": "data/material.txt"}, clear=True), \
             mock.patch("examrag.config._load_dotenv", return_value={}):
            self.assertEqual(config.resolve_material(), config.DEFAULT_MATERIAL)


if __name__ == "__main__":
    unittest.main()
