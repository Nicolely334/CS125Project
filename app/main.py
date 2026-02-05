from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes.health import router as health_router
from app.api.routes.spotify import router as spotify_router
from app.api.routes.logs import router as logs_router
from app.api.routes.recommendations import router as recs_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Personalized Music Tracker API",
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
    app.include_router(spotify_router, prefix="/spotify", tags=["spotify"])
    app.include_router(logs_router, prefix="/logs", tags=["logs"])
    app.include_router(recs_router, prefix="/recs", tags=["recommendations"])

    return app


app = create_app()
