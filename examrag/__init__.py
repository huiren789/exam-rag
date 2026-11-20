"""ExamRAG — 有据可依的复习搭档。

每个答案，都能翻回原文核对。纯 Python 标准库实现的课程 RAG 命令行工具。
"""

from .config import VERSION as __version__
from .cli import main

__all__ = ["__version__", "main"]
