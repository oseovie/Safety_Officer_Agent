from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, reports, safety
from app.core.config import get_settings


settings = get_settings()

app = FastAPI(
    title=f"{settings.app_name} API",
    version="1.0.0",
    description="AI-powered safety management and risk automation SaaS platform.",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(settings.frontend_origin)],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(safety.router, prefix=settings.api_v1_prefix)
app.include_router(reports.router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
