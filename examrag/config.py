"""ExamRAG 的集中配置：环境变量、路径解析与所有常量。

设计原则：配置读取不产生副作用。缺少 API Key 时模块仍可导入，
检索与 dry-run 模式完全离线可用；只有真正调用模型时才校验密钥。
"""

import os
from pathlib import Path
from typing import Dict, Optional

VERSION = "0.6.0"

# 仓库根目录：无论从哪个工作目录启动，都能找到内置资料。
ROOT = Path(__file__).resolve().parent.parent

DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1/chat/completions"
DEFAULT_MODEL = "Qwen/Qwen3-8B"
DEFAULT_MATERIAL = ROOT / "data" / "material.txt"

# 角色提示词：只影响回答风格，铁律是"只依据资料、不编造"。
SYSTEM_PROMPT = (
    "你是一位《教育测量与评价》课程的辅导老师，讲解经验丰富。"
    "回答问题时遵循以下规则："
    "1.先给一句话结论，再展开解释，必要时引用资料中的例子；"
    "2.专业术语首次出现时用一句话通俗解释；"
    "3.只依据用户提供的资料回答，资料里没有的内容必须明确回答「资料中未提及」，绝不编造；"
    "4.回答末尾注明依据了哪块资料（如：依据【掌握·难度的定义】）；"
    "5.使用简体中文，语气友好但简洁，不堆砌客套话。"
)

# 问题里的客套词，检索前先去掉，免得干扰匹配。
FILLERS = [
    "是什么", "什么是", "有什么", "哪些", "介绍", "简述", "区别",
    "联系", "的意思", "请", "一下", "怎么样", "如何", "分别", "？",
]

# 目录、小结这类块关键词密集但没有正文，检索时降权。
NAV_KEYS = ("学习目标", "导图", "小结", "练习", "使用说明", "待收")

# 三级掌握度对应的权重（只在出题模式启用，见 retrieval.retrieve）。
LEVEL_WEIGHTS: Dict[str, int] = {"掌握": 3, "理解": 2, "了解": 1}

# 汇总型问题的触发词。
FOCUS_KEYS = ("重难点", "重点", "考点", "必考")

# 「整门课 / 整本书」类汇总问题的触发词：命中后重难点检索名额放宽到 8 块。
COURSE_SCOPE_KEYS = ("整门课", "整本书", "全课程", "所有章", "课程的重难点")

# 策略层判断「这次检索是否命中」的最低分。两种检索器分数口径不同：
# 词面检索是共同 bigram 出现次数（可达几十），语义检索是余弦相似度（0~1），
# 因此必须分别设阈值，不能共用一个 5，否则语义模式每次都会误触发查询改写。
LEXICAL_HIT_SCORE = 5.0
SEMANTIC_HIT_SCORE = 0.08
VECTOR_HIT_SCORE = 0.25

# 可选 embedding 检索：模型名与向量缓存位置（缓存不入 git）。
# 可用 EXAMRAG_VECTOR_MODEL / EXAMRAG_VECTOR_CACHE 覆盖，见下方函数。
VECTOR_MODEL = "BAAI/bge-small-zh-v1.5"
VECTOR_CACHE_PATH = ROOT / ".cache" / "vectors.json"


def get_vector_model() -> str:
    """embedding 模型名：环境变量 → .env → 默认 bge-small-zh。"""
    return (
        os.environ.get("EXAMRAG_VECTOR_MODEL", "").strip()
        or _load_dotenv().get("EXAMRAG_VECTOR_MODEL", "").strip()
        or VECTOR_MODEL
    )


def get_vector_cache_path() -> Path:
    """向量缓存路径：环境变量 → .env → 默认仓库根 .cache/vectors.json。"""
    env_path = (
        os.environ.get("EXAMRAG_VECTOR_CACHE", "").strip()
        or _load_dotenv().get("EXAMRAG_VECTOR_CACHE", "").strip()
    )
    if env_path:
        candidate = Path(env_path).expanduser()
        if not candidate.is_absolute():
            candidate = ROOT / candidate
        return candidate
    return VECTOR_CACHE_PATH


def _load_dotenv(path: Optional[Path] = None) -> Dict[str, str]:
    """用标准库解析根目录的 .env 文件（KEY=VALUE，# 开头为注释）。

    .env 不需要存在；解析失败的行会被忽略，不影响程序运行。
    """
    env_path = Path(path) if path is not None else ROOT / ".env"
    values: Dict[str, str] = {}
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return values

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def get_api_key() -> str:
    """读取模型 API Key：环境变量优先，其次 .env，最后为空串。

    惰性校验——这里不抛异常，让离线检索和 dry-run 无需密钥。
    """
    env_key = os.environ.get("SILICONFLOW_API_KEY", "").strip()
    if env_key:
        return env_key
    return _load_dotenv().get("SILICONFLOW_API_KEY", "").strip()


def get_base_url() -> str:
    """OpenAI 兼容接口地址，可用 EXAMRAG_BASE_URL 覆盖。"""
    return (
        os.environ.get("EXAMRAG_BASE_URL", "").strip()
        or _load_dotenv().get("EXAMRAG_BASE_URL", "").strip()
        or DEFAULT_BASE_URL
    )


def get_model() -> str:
    """模型名，可用 EXAMRAG_MODEL 覆盖。"""
    return (
        os.environ.get("EXAMRAG_MODEL", "").strip()
        or _load_dotenv().get("EXAMRAG_MODEL", "").strip()
        or DEFAULT_MODEL
    )


def resolve_material(override: Optional[str] = None) -> Path:
    """解析资料文件路径：--material > EXAMRAG_MATERIAL > 内置 data/material.txt。"""
    if override:
        candidate = Path(override).expanduser()
    else:
        env_path = (
            os.environ.get("EXAMRAG_MATERIAL", "").strip()
            or _load_dotenv().get("EXAMRAG_MATERIAL", "").strip()
        )
        candidate = Path(env_path).expanduser() if env_path else DEFAULT_MATERIAL
        if not candidate.is_absolute():
            # 相对环境变量路径以仓库根为基准，避免依赖当前工作目录。
            candidate = ROOT / candidate
    return candidate
