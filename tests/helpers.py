"""共享测试夹具：资料块、模型桩与向量桩。

test_api / test_evaluate / test_vector 三处原本各自定义近似重复的
CHUNKS 与 embed 桩，统一收到这里，改口径只动一个文件。
"""

from examrag.models import as_chunks

# 三块最小资料样本：掌握·难度 / 理解·信度 / 了解·效度。
SAMPLE_CHUNKS = as_chunks([
    "【掌握·难度的定义】难度是试题难易程度的指标，常用通过率 P 表示。",
    "【理解·信度的定义】信度是测验结果的一致性、稳定性程度。",
    "【了解·效度的定义】效度指测验测到所要测特质的程度。",
])


def stub_ask(prompt: str) -> str:
    """ask 桩：返回固定文案，绝不联网。"""
    return "【测试桩】依据资料回答。"


def fake_embed(texts):
    """向量桩：难度 / 信度 / 效度各占一维。

    无关键词命中的文本给非零兜底向量，避免余弦全为 0 的退化情形。
    """
    result = []
    for text in texts:
        vec = [
            1.0 if "难度" in text else 0.0,
            1.0 if "信度" in text else 0.0,
            1.0 if "效度" in text else 0.0,
        ]
        result.append(vec if any(vec) else [0.1, 0.1, 0.1])
    return result
