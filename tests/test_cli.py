"""CLI 冒烟测试：通过 subprocess 验证入口与离线 dry-run。"""

import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(*args):
    """在仓库根目录运行命令，并清除密钥相关环境变量。"""
    env = os.environ.copy()
    for key in ("SILICONFLOW_API_KEY", "EXAMRAG_BASE_URL", "EXAMRAG_MODEL", "EXAMRAG_MATERIAL"):
        env.pop(key, None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable] + list(args),
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )


class CliTests(unittest.TestCase):
    def test_module_version(self):
        result = _run("-m", "examrag", "--version")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("0.3.0", result.stdout)

    def test_tool_shim_version(self):
        result = _run("tool.py", "--version")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("0.3.0", result.stdout)

    def test_dry_run_without_api_key(self):
        result = _run("-m", "examrag", "-q", "难度的定义", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("检索到", result.stdout)
        self.assertIn("难度", result.stdout)
        self.assertIn("已跳过 API 调用", result.stdout)

    def test_exam_dry_run(self):
        result = _run("-m", "examrag", "--exam", "信度", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("出 3 道", result.stdout)
        self.assertIn("已跳过 API 调用", result.stdout)

    def test_custom_material(self):
        result = _run("-m", "examrag", "-q", "信度", "--dry-run", "--material", "data/material.txt")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("检索到", result.stdout)

    def test_semantic_dry_run(self):
        result = _run("-m", "examrag", "-q", "信度", "--dry-run", "--semantic")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("语义检索", result.stdout)
        self.assertIn("检索到", result.stdout)


if __name__ == "__main__":
    unittest.main()
