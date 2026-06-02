from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from core.logging import configure_logging
from utils.config import DEBUG, PORT, PROJECT_ROOT
from utils.middlewares import register_middlewares
from utils.routes import router


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Backup Hub", version="1.0.0", debug=DEBUG)
    register_middlewares(app)
    app.mount("/static", StaticFiles(directory=str(PROJECT_ROOT / "static")), name="static")
    app.include_router(router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        reload=DEBUG,
    )
