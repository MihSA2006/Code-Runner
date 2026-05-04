from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
import asyncio
import time

from app.api.routes import router
from app.db.database import init_db
from app.core.config import settings
from app.core.cleanup import start_cleanup_scheduler
from app.core.executor import init_work_dir

limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"\n🚀 {settings.APP_NAME} v{settings.APP_VERSION} démarrage...")
    await init_db()
    init_work_dir()
    cleanup_task = asyncio.create_task(start_cleanup_scheduler())
    print("✅ Prêt\n")
    yield
    cleanup_task.cancel()
    print(f"\n🛑 {settings.APP_NAME} arrêt...")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## CodeRunner API

Exécutez du code dans un sandbox Docker isolé.

### Langages supportés
- 🐍 **Python** 3.11
- ☕ **Java** 21
- 🟨 **JavaScript** (Node.js 20)
- 🔵 **C** (GCC)
- 🔵 **C++** (G++)

### Workflow
1. `POST /api/v1/execute` → Soumettre un code, recevoir un **token**
2. `GET /api/v1/result/{token}` → Récupérer le **résultat**
    """,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_response_time(request: Request, call_next):
    start    = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 2)
    response.headers["X-Response-Time"] = f"{duration}ms"
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "Erreur interne", "detail": str(exc)}
    )

app.include_router(router, prefix="/api/v1")

@app.get("/", tags=["Info"])
async def root():
    return {
        "app":     settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs":    "/docs",
        "health":  "/api/v1/health"
    }
