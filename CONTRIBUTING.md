# 参与贡献

欢迎提 issue 或 PR。这个项目的核心约束是「核心零依赖、每个答案都能翻回原文核对」，改动前请先看一遍 [docs/adr](docs/adr) 里的取舍，避免无意中破坏这两条。

## 本地开发

```bash
git clone https://github.com/huiren789/exam-rag.git
cd exam-rag
python -m unittest discover -s tests          # 全部离线，不需要密钥
python -m examrag -q "难度的定义" --dry-run      # 冒烟
python -m examrag.evaluate --mode lexical      # 检索评测
```

可选能力按需安装：

```bash
pip install -e ".[api]"       # HTTP API / Web
pip install -e ".[vector]"    # embedding 检索，首次会下载模型
```

## 提交前自检

- `python -m unittest discover -s tests` 全绿。
- 新增代码兼容 Python 3.8（项目 CI 会跑 3.8 / 3.11 / 3.13）。
- 没有把第三方依赖引入 `import examrag` 的导入链。
- 没有引入真实密钥、个人邮箱或本机绝对路径。
- 若改了行为，同步更新 README 与相关 ADR；若改了接口，更新 `examples/api_examples.txt`。

## 怎么加一种新的检索器

1. 实现与 `retrieval.retrieve` / `semantic.semantic_retrieve` / `vector.vector_retrieve` 相同的契约：

   ```python
   retrieve(question, chunks, *, top_k, weighted, return_score)
   ```

2. 在 `service._retriever()` 加一个分支，并在 `_hit_threshold()` 里给该检索器一个符合其分数口径的阈值。
3. 用注入桩写测试，不要依赖真实模型或网络。
4. 如果它是默认开启的，先更新 ADR 说明为什么值得改默认值。

## 怎么改评测集

`examples/eval_cases.json` 里的每条用例都是人工标注的「问题 → 应命中块」。新增用例请同时说明判断依据，避免把个人偏好当成客观标准。评测结果只反映这份历史样本，不要在 README 或 issue 里外推为真实成功率。
