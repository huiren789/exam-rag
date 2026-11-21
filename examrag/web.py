"""Web 演示界面：在 API 之上提供单页界面，便于在线展示。

默认 API 仍只监听 127.0.0.1（见 api.py）；本模块提供 web 入口，
通过环境变量 PORT / HOST 控制监听地址，供在线部署使用。
本地运行：python -m examrag.web    然后访问 http://127.0.0.1:8000
"""

import os
from typing import Any

from . import api as api_module
from . import config


STATIC_DIR = config.ROOT / "examrag" / "static"


def create_web_app() -> Any:
    """构造带静态页面的应用：根路径是演示页，其余是 /health、/ask 等 API。"""
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    app = api_module.create_app()

    index = STATIC_DIR / "index.html"

    @app.get("/", include_in_schema=False)
    def index_page():
        return FileResponse(str(index))

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    return app


def main() -> None:
    """Web 服务入口：监听 PORT（默认 8000）与 HOST（默认 127.0.0.1）。"""
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "缺少 uvicorn。请先运行：pip install -e \".[api]\""
        ) from exc
    port_env = os.environ.get("PORT")
    port = int(port_env) if port_env else 8000
    # 本地默认只绑本机；部署环境会注入 PORT，此时对外绑定 0.0.0.0。
    default_host = "0.0.0.0" if port_env else "127.0.0.1"
    host = os.environ.get("HOST", default_host)
    uvicorn.run(create_web_app(), host=host, port=port)


if __name__ == "__main__":
    main()
