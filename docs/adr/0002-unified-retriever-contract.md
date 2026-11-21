# 2. 统一检索器契约并注入策略层

- 状态：已采纳
- 日期：2026-11-21

## 背景

最初语义检索模式直接调用 `semantic_retrieve`，绕过了查询改写、重难点汇总和并列概念拆分整套策略层。同时，资料块的标签和掌握等级在多个模块里被重复正则解析，检索器一多就会出现行为分叉。

## 决策

1. 建立 `Chunk(tag, level, text)` 领域模型，资料在加载入口解析一次，后续只读字段。
2. 三种检索器遵守同一个契约：

   ```text
   retrieve(question, chunks, *, top_k, weighted, return_score)
     -> List[Chunk] | (List[Chunk], best_score)
   ```

3. `smart_context(..., retrieve_fn, score_threshold)` 通过注入选择检索器；服务层 `_retriever()` 是唯一选择点。
4. 命中阈值随检索器切换：词面 5、TF-IDF 0.08、embedding 0.25。分数口径不同，不能共用一个阈值。

## 影响

- 新增第四种检索器只需实现同一契约，不必改策略层或 API。
- `prepare_question` / `prepare_exam` / `retrieve_only` 对三种模式行为一致。
- 代价：所有检索器都必须返回 `Chunk` 而不是裸字符串；旧调用由 `as_chunks()` 兼容。
