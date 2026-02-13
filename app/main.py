from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes.health import router as health_router
from app.api.routes.search import router as search_router
from app.api.routes.recommendations import router as recommendations_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="MusicBoxd API",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, tags=["health"])
    app.include_router(search_router, prefix="/api", tags=["search"])
    app.include_router(recommendations_router, prefix="/api/recommendations", tags=["recommendations"])

    return app


app = create_app()
