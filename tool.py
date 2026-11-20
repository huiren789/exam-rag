"""向后兼容入口：原版用 python tool.py 启动，这里保留同样的用法。

新代码已拆分到 examrag/ 包中；本文件只负责把仓库根目录加入 sys.path
并转交命令行入口，确保老用户的习惯不被破坏。
"""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from examrag.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
