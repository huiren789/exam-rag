# 1. 核心保持零第三方依赖

- 状态：已采纳
- 日期：2026-11-21

## 背景

项目是个人作品集项目，使用环境不可控：用户可能只有 Python 3.8，没有 pip 安装权限；在线演示环境不配置模型密钥。早期原型只依赖标准库，这是它最容易运行、也最容易讲清楚的地方。

## 决策

核心包 `examrag` 的 CLI、词面检索、TF-IDF 检索、提示词拼装、评测脚本全部只用 Python 标准库。需要第三方库的能力做成可选依赖：

- `pip install -e ".[api]"`：FastAPI / uvicorn / httpx，提供 HTTP API 与 Web 页；
- `pip install -e ".[vector]"`：sentence-transformers，提供 embedding 向量检索。

不安装任何额外依赖时，`python -m examrag`、`--dry-run`、`--semantic`、`python -m examrag.evaluate` 都能跑。

## 影响

- 正面：安装门槛低，离线可用，CI 核心 job 可在 3.8 / 3.11 / 3.13 全矩阵跑。
- 代价：API 与向量能力需要用户主动安装；向量首次使用要下载模型。
- 约束：新功能默认不得把第三方库引入核心导入链；`import examrag` 必须始终成功。
