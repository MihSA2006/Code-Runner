from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel, field_validator
from typing import Optional
import time

from app.core.executor import execute_code, execute_and_wait, LANGUAGE_IMAGES
from app.core.security import validate_code
from app.db.database import get_execution, delete_execution, cleanup_expired
from app.core.config import settings

router  = APIRouter()
limiter = Limiter(key_func=get_remote_address)


# ──────────────────────────────────────────
# Schémas
# ──────────────────────────────────────────

class ExecuteRequest(BaseModel):
    language: str
    code: str

    @field_validator("language")
    @classmethod
    def language_must_be_supported(cls, v):
        if v not in settings.SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Langage '{v}' non supporté. "
                f"Disponibles : {settings.SUPPORTED_LANGUAGES}"
            )
        return v

    @field_validator("code")
    @classmethod
    def code_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Le code ne peut pas être vide")
        if len(v) > settings.MAX_CODE_LENGTH:
            raise ValueError(
                f"Code trop long ({len(v)} > {settings.MAX_CODE_LENGTH} caractères)"
            )
        return v


class ExecuteResponse(BaseModel):
    token: str
    status: str
    message: str


class ResultResponse(BaseModel):
    token:          str
    status:         str
    language:       str
    output:         Optional[str]
    error:          Optional[str]
    execution_time: Optional[float]


# ──────────────────────────────────────────
# POST /execute/wait  ← NOUVEAU (recommandé)
# ──────────────────────────────────────────

@router.post(
    "/execute/wait",
    response_model=ResultResponse,
    summary="Exécuter et attendre le résultat (recommandé)",
    tags=["Execution"]
)
@limiter.limit(settings.RATE_LIMIT_EXECUTE)
async def execute_wait(request: Request, body: ExecuteRequest):
    """
    Soumet un code et **attend** le résultat directement.
    Pas besoin de polling — un seul appel suffit.
    Idéal pour une plateforme de contest algo.
    """
    await cleanup_expired()

    result = await execute_and_wait(body.code, body.language)

    if result["status"] == "rejected":
        raise HTTPException(status_code=400, detail=f"Code refusé : {result['error']}")

    return ResultResponse(**result)


# ──────────────────────────────────────────
# POST /execute  (async, retourne token)
# ──────────────────────────────────────────

@router.post(
    "/execute",
    response_model=ExecuteResponse,
    summary="Soumettre un code (retourne un token)",
    tags=["Execution"]
)
@limiter.limit(settings.RATE_LIMIT_EXECUTE)
async def execute(request: Request, body: ExecuteRequest):
    """
    Soumet un code, retourne immédiatement un token.
    Utiliser `GET /result/{token}` pour récupérer le résultat.
    """
    await cleanup_expired()

    is_safe, reason = validate_code(body.code, body.language)
    if not is_safe:
        raise HTTPException(status_code=400, detail=f"Code refusé : {reason}")

    token, is_valid, error_msg = await execute_code(body.code, body.language)

    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Code refusé : {error_msg}")

    return ExecuteResponse(
        token=token,
        status="pending",
        message=f"Résultat disponible sur GET /result/{token}"
    )


# ──────────────────────────────────────────
# GET /result/{token}
# ──────────────────────────────────────────

@router.get(
    "/result/{token}",
    response_model=ResultResponse,
    summary="Récupérer le résultat d'une exécution",
    tags=["Execution"]
)
@limiter.limit(settings.RATE_LIMIT_RESULT)
async def get_result(request: Request, token: str):
    execution = await get_execution(token)

    if execution is None:
        raise HTTPException(
            status_code=404,
            detail=f"Token '{token}' introuvable ou expiré"
        )

    execution_time = None
    if execution.completed_at and execution.created_at:
        execution_time = round(execution.completed_at - execution.created_at, 3)

    return ResultResponse(
        token=execution.token,
        status=execution.status,
        language=execution.language,
        output=execution.output,
        error=execution.error,
        execution_time=execution_time
    )


# ──────────────────────────────────────────
# DELETE /result/{token}
# ──────────────────────────────────────────

@router.delete(
    "/result/{token}",
    summary="Supprimer un token manuellement",
    tags=["Execution"]
)
async def delete_result(request: Request, token: str):
    execution = await get_execution(token)

    if execution is None:
        raise HTTPException(status_code=404, detail=f"Token '{token}' introuvable")

    await delete_execution(token)
    return JSONResponse(content={"message": f"Token '{token}' supprimé"}, status_code=200)


# ──────────────────────────────────────────
# GET /languages
# ──────────────────────────────────────────

@router.get("/languages", summary="Lister les langages supportés", tags=["Info"])
async def get_languages():
    return {
        "languages": [
            {"name": lang, "image": image}
            for lang, image in LANGUAGE_IMAGES.items()
        ]
    }


# ──────────────────────────────────────────
# GET /health
# ──────────────────────────────────────────

@router.get("/health", summary="Vérifier l'état de l'API", tags=["Info"])
async def health_check():
    import docker
    docker_status  = "ok"
    docker_version = None

    try:
        client         = docker.from_env()
        docker_version = client.version()["Version"]
    except Exception as e:
        docker_status = f"error: {str(e)}"

    return {
        "status":         "ok",
        "app":            settings.APP_NAME,
        "version":        settings.APP_VERSION,
        "docker":         docker_status,
        "docker_version": docker_version,
        "limits": {
            "max_execution_time": settings.MAX_EXECUTION_TIME,
            "max_memory":         settings.MAX_MEMORY,
            "max_cpu":            settings.MAX_CPU,
            "max_code_length":    settings.MAX_CODE_LENGTH,
            "rate_limit_execute": settings.RATE_LIMIT_EXECUTE,
        },
        "timestamp": time.time()
    }
