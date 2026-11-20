# ExamRAG

[![tests](https://github.com/huiren789/exam-rag/actions/workflows/tests.yml/badge.svg)](https://github.com/huiren789/exam-rag/actions/workflows/tests.yml)
![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue)
![MIT](https://img.shields.io/badge/license-MIT-green)

一个课程资料检索和复习工具。它把本地资料切成块，用两字词频找出相关内容，再把这几块交给大模型回答或出题。工具会打印检索到了哪些块，回答也会标出依据，方便回原文核对。

## 解决什么问题

备考时有两个麻烦：直接问大模型，答案可能看着像真的，其实是编的；自己翻教材，又很难快速定位到要找的那一块。

ExamRAG 把「找资料」这一步放在本地完成。检索不联网、不花钱，结果也看得见；只有筛出来的几块资料会发给模型。提示词要求模型只使用这些资料，并在回答末尾写出依据；资料里没有的内容，要回答「资料中未提及」。

## 主要功能

- 本地检索：按两字词出现次数匹配，标题命中加权，目录和小结类块降权。
- 分层出题：按【掌握】【理解】【了解】标签加权检索，优先从掌握级内容出题。
- 查询改写：检索分数偏低时，让模型提取关键词再检索一次。
- 重难点汇总：问「信度的重难点」这类问题时，让模型从标题清单里挑相关块。
- 并列概念拆分：问「信度和难度」时，拆成两段分别检索再合并结果。
- 离线演示：`--dry-run` 不调用模型，只打印检索结果和提示词，不需要密钥。
- 零第三方依赖：只用 Python 标准库。31 个离线测试，CI 覆盖 Python 3.8 / 3.11 / 3.13。

## 安装方法

需要 Python 3.8 或更高版本。克隆之后可以直接运行，不需要安装依赖：

```bash
git clone https://github.com/huiren789/exam-rag.git
cd exam-rag
python -m examrag
```

旧入口 `python tool.py` 也能用。

如果要真正调用模型，需要准备一个 API Key。默认接的是硅基流动，也可以用其他 OpenAI 兼容接口：

```bash
cp .env.example .env        # Windows PowerShell: Copy-Item .env.example .env
```

编辑 `.env`，把 `SILICONFLOW_API_KEY` 改成自己的密钥。也可以不建文件，直接设环境变量 `SILICONFLOW_API_KEY`。`.env` 已在 `.gitignore` 里，不会被提交。

可选：装成本地命令 `examrag`。如果 pip 报 `Cannot import 'setuptools.build_meta'`，说明当前 Python 没装 setuptools，跳过这一步即可，不影响使用。

```bash
pip install -e .
examrag --version
```

## 使用方法

交互模式：

```bash
python -m examrag
```

进入后可以直接提问，也可以输入 `出题 信度`、`信度的重难点`，输入 `退出` 结束。

单次命令：

```bash
python -m examrag -q "难度的定义"              # 问一个问题
python -m examrag --exam 信度                  # 出题
python -m examrag --topic "信度的重难点"        # 汇总重难点
python -m examrag -q "难度的定义" --dry-run     # 离线看检索结果和提示词
python -m examrag -q "效度" --top-k 5          # 取 5 块资料
python -m examrag -q "信度" --material my.txt  # 换一份资料
```

| 参数 | 说明 |
| --- | --- |
| `-q`, `--question` | 单次提问，回答后退出 |
| `--exam [主题]` | 出题模式，主题可直接跟在后面 |
| `--topic` | 查询某主题的知识点或重难点 |
| `--top-k N` | 检索几块资料，默认 3 |
| `--material PATH` | 指定资料文件 |
| `--dry-run` | 只显示检索结果和提示词，不联网 |
| `--version` | 查看版本 |

退出码：`0` 成功，`1` 配置、网络或资料错误，`130` 用户按 Ctrl+C 中断。

## 输入 / 输出案例

### 提问

```bash
python -m examrag -q "难度的定义是什么"
```

```text
（检索到：掌握·难度的定义、理解·信度的定义、理解·效度的定义）

AI：难度是衡量试题难易程度的指标，通常用通过率 P 表示，P=x̄/w，P 越大越容易。
    另一种写法是 q=1−P，q 越大越难。报告难度时应说明用的是哪一种。
依据：【掌握·难度的定义】
```

检索行是程序的真实输出；AI 回答是一次生成示例，实际措辞取决于所配模型。

### 出题

```bash
python -m examrag --exam 信度
```

```text
（检索到：掌握·重测信度、掌握·重测信度的局限与适用、掌握·复本信度｜等级：掌握、掌握、掌握）

AI：1.（简答）重测信度的误差变异来源是什么？适用于哪类测验？
    2.（概念辨析）等值性系数和等值稳定性系数有什么区别？
    3.（列举）使用重测信度有哪些局限？
```

检索行是程序的真实输出，题目同样是生成示例。

### 离线 dry-run

```bash
python -m examrag -q "难度的定义" --dry-run
```

```text
（检索到：掌握·难度的定义、理解·信度的定义、理解·效度的定义）

--- 真实模式下将发送给模型的提示词 ---
只根据以下资料回答问题。资料里没有的，就回答「资料中未提及」。回答后注明依据了哪段资料。

资料：
【掌握·难度的定义】难度是指测验试题或测量项目的难易程度……
（此处省略其余资料块）
问题：难度的定义
--- （已跳过 API 调用，dry-run 模式）---
```

这一段是从实际运行输出里摘录的，省略了过长的资料正文。更多示例在 `examples/demo_question.txt` 和 `examples/demo_exam.txt`。

## 配置

| 配置项 | 读取顺序（高到低） | 说明 |
| --- | --- | --- |
| `SILICONFLOW_API_KEY` | 环境变量 → `.env` | 模型密钥，只在调用模型时需要 |
| `EXAMRAG_BASE_URL` | 环境变量 → `.env` → 默认硅基流动地址 | 换其他 OpenAI 兼容接口 |
| `EXAMRAG_MODEL` | 环境变量 → `.env` → `Qwen/Qwen3-8B` | 换模型 |
| `EXAMRAG_MATERIAL` | 环境变量 → `.env` → `data/material.txt` | 换资料文件；相对路径按仓库根算 |
| `--material` | 命令行 | 优先级最高 |

## 代码结构

```text
examrag/
  config.py      环境变量、.env、路径和常量
  retrieval.py   本地检索
  llm.py         模型调用和错误处理
  smart.py       查询改写、重难点、并列概念拆分
  cli.py         命令行参数和交互循环
data/material.txt   内置资料，99 块
tests/              31 个离线测试
examples/           示例输出
UPLOAD.md           上传 GitHub 的步骤
tool.py             旧入口
```

## 测试

```bash
python -m unittest discover -s tests -v
```

31 个测试，不需要密钥，也不需要联网。GitHub Actions 在每次 push 和 pull request 时运行同一套测试。

## 资料范围

内置《教育测量与评价》资料 99 块，覆盖第一、二、四、五、六章的内容块和章末小结、练习，块名带【掌握 / 理解 / 了解】标签。现有资料里第三章没有正文块，第六章也没有单独的章节标题行，这里如实说明，没有改动原始资料。

## 已知限制

- 检索是词面匹配，不理解语义。不带主题词的提问，命中率不如直接写关键词。
- 资料要按格式手工整理，目前不能直接导入 PDF 或 Word。
- 不支持追问上下文，每个问题都独立检索。
- 只有命令行界面。
- 回答质量取决于所配的模型；调用链已用本地模拟接口测过，但没有用真实密钥调用商业服务。
- 资料如果来自不可信来源，可能存在提示词注入风险，不要把密钥放进资料文件。

## Roadmap

- [x] 关键词检索、出题、分层加权、查询改写
- [x] 单元测试、CI、环境变量配置、dry-run
- [ ] 向量语义检索
- [ ] Web 界面
- [ ] 导入 PDF / Word 资料

## License

[MIT](LICENSE) © 2026 huiren789
