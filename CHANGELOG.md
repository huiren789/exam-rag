# 更新记录

所有显著变更都记录在这里。格式参考 Keep a Changelog，版本遵循语义化版本。

## [0.5.1] - 2026-11-22

### 新增
- `EXAMRAG_VECTOR_MODEL` / `EXAMRAG_VECTOR_CACHE` 环境变量，可覆盖 embedding 模型与向量缓存路径。
- `CONTRIBUTING.md`、`CHANGELOG.md`。
- 打包元数据：keywords、classifiers、项目链接。

### 测试
- 测试 78 → 82；新增向量模型/缓存配置、API 向量问答与出题、CLI 缺依赖提示的覆盖。

## [0.5.0] - 2026-11-21

### 新增
- 可选 embedding 向量检索：`--vector` / API `vector` 字段，与词面、TF-IDF 共用同一检索器契约；核心仍零依赖。
- 向量缓存：按「模型名 + 原文」哈希缓存到 `.cache/vectors.json`，不入库。
- 逐句依据：结构化结果新增 `evidence` 字段，标出命中原句与词面重合度；CLI / API / Web 三端展示。
- 检索评测：`examples/eval_cases.json` 与 `python -m examrag.evaluate`，输出 hit@1 / hit@3 / MRR。
- 架构决策记录：`docs/adr` 四篇。

### 测试
- 测试 62 → 78；向量、评测与依据句均有覆盖，向量测试用注入桩不下载模型。

## [0.4.0] - 2026-11-21

### 重构
- 新增 `Chunk` 领域模型，标签 / 掌握等级 / 正文只解析一次，替换原先散落在 6 处的重复正则。
- 词面与 TF-IDF 检索统一为同一函数契约；策略层通过 `retrieve_fn` 注入检索器。
- API 的 `/ask`、`/exam` 复用 `service` 层，CLI 与 Web/API 不再各写一套组装逻辑。

### 修复
- 语义模式绕过查询改写 / 重难点 / 并列拆分策略的问题；三种检索器分别设命中阈值。
- `--top-k` 在问答策略层未透传的问题。
- 导航块在语义检索中同样降权，排序口径与词面一致。

## [0.3.0] - 2026-11-21

### 新增
- Web 演示界面与在线预览。
- 可选 TF-IDF 语义检索（`--semantic` / API `semantic` 字段），纯标准库。
- `examples/api_examples.txt` API 示例。

## [0.2.0] - 2026-11-21

### 新增
- 可选 FastAPI HTTP 层：`/health`、`/retrieve`、`/ask`、`/exam`，带自动 Swagger 文档。
- `service` 共用业务层，CLI 与 API 共享检索与提示词组装。

## [0.1.0] - 2026-11-20

### 新增
- 首个可用版本：本地词面检索、可溯源回答、分层出题、查询改写、`--dry-run` 离线演示、环境变量密钥管理。
