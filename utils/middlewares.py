from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from utils.config import CORS_ALLOWEDS


def register_middlewares(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ALLOWEDS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
