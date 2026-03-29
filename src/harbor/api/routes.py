"""Harbor API — application factory that assembles all routers."""

from fastapi import FastAPI

from harbor.api import agents, audit, discovery, health, policies, reviews
from harbor.api.deps import Services


def create_app(services: Services | None = None) -> FastAPI:
    """Create and wire the FastAPI application."""
    app = FastAPI(title="Harbor", description="Agent Platform Management", version="0.3.0")
    svc = services or Services()

    app.include_router(agents.create_router(svc))
    app.include_router(discovery.create_router(svc))
    app.include_router(health.create_router(svc))
    app.include_router(audit.create_router(svc))
    app.include_router(policies.create_router(svc))
    app.include_router(reviews.create_router(svc))

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok", "service": "harbor"}

    return app
