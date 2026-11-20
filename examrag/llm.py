"""网络与生成层：唯一会联网、会花 token 的模块。

所有异常都在这里转换成面向用户的中文提示（ExamRAGError），
避免把 urllib 的 traceback 暴露给命令行用户。
"""

import json
import socket
import urllib.error
import urllib.request
from typing import Optional

from . import config


class ExamRAGError(Exception):
    """可预期的、可以直接展示给用户的错误。"""


def ask(
    prompt: str,
    *,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    timeout: int = 30,
) -> str:
    """把提示词发给 OpenAI 兼容接口，返回模型回复正文。

    密钥采用惰性校验：只有调用本函数时才要求 SILICONFLOW_API_KEY，
    这样未配置密钥也能运行检索与 --dry-run。
    """
    key = api_key if api_key is not None else config.get_api_key()
    if not key:
        raise ExamRAGError(
            "未检测到 API Key。请设置环境变量 SILICONFLOW_API_KEY，"
            "或复制 .env.example 为 .env 并在其中填写；"
            "只想看检索效果可加 --dry-run，无需密钥。"
        )

    endpoint = base_url or config.get_base_url()
    model_name = model or config.get_model()
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": config.SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise ExamRAGError(
                "API Key 无效或没有权限（HTTP %s）。请检查环境变量 "
                "SILICONFLOW_API_KEY 或 .env 中的密钥。" % exc.code
            ) from exc
        if exc.code == 429:
            raise ExamRAGError("请求过于频繁（HTTP 429），请稍后重试。") from exc
        if 500 <= exc.code < 600:
            raise ExamRAGError(
                "模型服务暂时不可用（HTTP %s），请稍后重试。" % exc.code
            ) from exc
        raise ExamRAGError("模型接口返回 HTTP %s，请检查配置。" % exc.code) from exc
    except urllib.error.URLError as exc:
        raise ExamRAGError(
            "连接模型服务失败：%s。请检查网络或 EXAMRAG_BASE_URL。" % exc.reason
        ) from exc
    except (TimeoutError, socket.timeout) as exc:
        # Python 3.8 的 socket.timeout 还不是 TimeoutError 的别名，两者都要接。
        raise ExamRAGError("请求模型服务超时，请稍后重试。") from exc

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ExamRAGError("模型返回内容不是合法 JSON，无法解析。") from exc

    try:
        content = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ExamRAGError("模型返回结构异常，缺少 choices[0].message.content。") from exc

    if not isinstance(content, str):
        raise ExamRAGError("模型返回内容格式异常（content 不是文本）。")
    return content
