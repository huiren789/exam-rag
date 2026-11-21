"""可选的 HTTP API 层（FastAPI）。

核心 CLI 保持零第三方依赖；只有显式安装 `examrag[api]` 并运行本模块时
才需要 FastAPI / uvicorn。模块顶层不 import fastapi，避免污染 `import examrag`。

启动：
    pip install -e ".[api]"
    python -m examrag.api            # 或 uvicorn examrag.api:app --reload
访问 http://127.0.0.1:8000/docs 查看自动生成的接口文档。
"""

from typing import Any, Callable, Dict, List, Optional

from . import config, service
from .llm import ExamRAGError, ask as default_ask
from .retrieval import tags_of


def _require_fastapi():
    """惰性导入 FastAPI；缺依赖时给出可操作的中文提示。"""
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel
    except ImportError as exc:
        raise RuntimeError(
            "HTTP API 需要额外依赖。请先运行：pip install -e \".[api]\"\n"
            "（CLI 不需要这一步，仍可零依赖使用。）"
        ) from exc
    return FastAPI, HTTPException, BaseModel


def create_app(
    chunks: Optional[List[str]] = None,
    ask_fn: Optional[Callable[[str], str]] = None,
) -> Any:
    """构造 FastAPI 应用。

    参数注入让测试可以传入固定资料与模型桩，无需联网或真实密钥。
    """
    FastAPI, HTTPException, BaseModel = _require_fastapi()

    class AskBody(BaseModel):
        question: str
        top_k: int = 3
        material: Optional[str] = None
        semantic: bool = False

    class ExamBody(BaseModel):
        topic: str
        top_k: int = 3
        material: Optional[str] = None
        semantic: bool = False

    class RetrieveBody(BaseModel):
        question: str
        top_k: int = 3
        weighted: bool = False
        material: Optional[str] = None
        semantic: bool = False

    app = FastAPI(
        title="ExamRAG API",
        description="有据可依的课程复习工具：本地检索 + 可溯源回答。/docs 可交互调试。",
        version=config.VERSION,
    )

    def _chunks(override: Optional[str]) -> List[str]:
        if chunks is not None and not override:
            return chunks
        return service.load_material(override)

    def _call_model(prompt: str) -> str:
        fn = ask_fn or default_ask
        try:
            return fn(prompt)
        except ExamRAGError as exc:
            # 401/无密钥等错误转为 400，message 已是面向用户的中文提示；
            # 这里只回传消息，绝不回传密钥或请求头。
            raise HTTPException(status_code=400, detail=str(exc))

    def _check_top_k(value: int) -> None:
        if value < 1:
            raise HTTPException(status_code=400, detail="top_k 必须大于等于 1。")

    @app.get("/health")
    def health() -> Dict[str, Any]:
        """健康检查：只读一次本地资料，不暴露密钥或本机绝对路径。"""
        try:
            available = len(_chunks(None))
            material_error = None
        except (ExamRAGError, FileNotFoundError) as exc:
            available, material_error = 0, str(exc)
        return {
            "status": "ok" if material_error is None else "degraded",
            "version": config.VERSION,
            "chunks_available": available,
            # 只暴露资料文件名，不回传本机绝对路径。
            "material": config.resolve_material().name,
            "material_error": material_error,
            "model": config.get_model(),
            "api_key_configured": bool(config.get_api_key()),
        }

    @app.post("/retrieve")
    def retrieve_endpoint(body: RetrieveBody) -> Dict[str, Any]:
        """纯本地检索，无需密钥：返回命中的资料块、标签和掌握等级。"""
        _check_top_k(body.top_k)
        try:
            data = service.retrieve_only(
                body.question, _chunks(body.material),
                top_k=body.top_k, weighted=body.weighted,
                semantic_mode=body.semantic,
            )
        except (ExamRAGError, FileNotFoundError) as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return data

    @app.post("/ask")
    def ask_endpoint(body: AskBody) -> Dict[str, Any]:
        """提问：检索相关资料后调用模型，回答注明依据。需要 API Key。"""
        _check_top_k(body.top_k)
        try:
            picked = _chunks(body.material)
            related, note, prompt = service.prepare_question(
                body.question, picked, top_k=body.top_k, ask_fn=ask_fn,
                semantic_mode=body.semantic,
            )
        except (ExamRAGError, FileNotFoundError) as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        answer = _call_model(prompt)
        return {
            "question": body.question,
            "answer": answer,
            "note": note,
            "sources": [tags_of(related)] if related else [],
            "chunks": related,
        }

    @app.post("/exam")
    def exam_endpoint(body: ExamBody) -> Dict[str, Any]:
        """出题：按掌握等级加权检索后让模型出题。需要 API Key。"""
        _check_top_k(body.top_k)
        try:
            picked = _chunks(body.material)
            related, levels, prompt = service.prepare_exam(
                body.topic, picked, top_k=body.top_k, semantic_mode=body.semantic
            )
        except (ExamRAGError, FileNotFoundError) as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        answer = _call_model(prompt)
        return {
            "topic": body.topic,
            "answer": answer,
            "levels": levels,
            "sources": [tags_of(related)] if related else [],
            "chunks": related,
        }

    return app


# 供 uvicorn / `python -m examrag.api` 使用的默认实例；惰性构造，
# 只有真正运行 API 时才要求安装 fastapi。
_app: Any = None


def get_app() -> Any:
    """默认 ASGI app：带演示页。uvicorn examrag.api:app 与在线部署都用它。"""
    global _app
    if _app is None:
        # 延迟导入 web，避免与 web.py 循环导入。
        from .web import create_web_app
        _app = create_web_app()
    return _app


def __getattr__(name: str) -> Any:
    """让 `uvicorn examrag.api:app` 能取到 app，同时保持惰性加载。

    Python 在模块上找不到属性时调用本函数；只有真正访问 `app`（启动服务）
    才会构造应用并检查依赖，普通的 `import examrag` 完全不触发。
    """
    if name == "app":
        return get_app()
    raise AttributeError("module %r has no attribute %r" % (__name__, name))


def main() -> None:
    """CLI 入口：python -m examrag.api 启动开发服务器。"""
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "缺少 uvicorn。请先运行：pip install -e \".[api]\""
        ) from exc
    uvicorn.run(get_app(), host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
