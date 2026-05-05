import uuid
import asyncio
import docker
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from docker.errors import DockerException, ImageNotFound
from docker.types import Mount
from typing import Tuple, Optional
from app.db.database import create_execution, update_execution
from app.core.config import settings
from app.core.security import validate_code, truncate_output

# ──────────────────────────────────────────
# Config
# ──────────────────────────────────────────

LANGUAGE_IMAGES = {
    "python":     "coderunner-python",
    "javascript": "coderunner-javascript",
    "c":          "coderunner-c",
}

LANGUAGE_COMMANDS = {
    "python":     ["python3", "/code/main.py"],
    "javascript": ["node", "/code/main.js"],
    "c":          ["sh", "-c", "gcc /code/main.c -o /tmp/main 2>&1 && /tmp/main"],
}

LANGUAGE_EXTENSIONS = {
    "python":     "main.py",
    "javascript": "main.js",
    "c":          "main.c",
}

WORK_DIR = os.path.join(os.path.expanduser("~"), ".coderunner_tmp")

# Docker client singleton
_docker_client: Optional[docker.DockerClient] = None

# Semaphore pour contrôler la concurrence
_semaphore: Optional[asyncio.Semaphore] = None

# ThreadPool dédié pour les exécutions Docker
_executor = ThreadPoolExecutor(
    max_workers=settings.MAX_CONCURRENT_EXECUTIONS,
    thread_name_prefix="docker_worker"
)


# ──────────────────────────────────────────
# Init
# ──────────────────────────────────────────

def init_work_dir():
    os.makedirs(WORK_DIR, exist_ok=True)
    print(f"📁 Dossier de travail : {WORK_DIR}")


def get_docker_client() -> docker.DockerClient:
    """Retourne un client Docker singleton pour éviter les reconnexions."""
    global _docker_client
    if _docker_client is None:
        _docker_client = docker.from_env()
    return _docker_client


def get_semaphore() -> asyncio.Semaphore:
    """Retourne le semaphore pour contrôler la concurrence."""
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_EXECUTIONS)
    return _semaphore


# ──────────────────────────────────────────
# Exécution Docker
# ──────────────────────────────────────────

def _adjust_command(command: list, job_id: str, filename: str) -> list:
    """Replace /code placeholders with actual job path in the volume."""
    path = f"/root/.coderunner_tmp/{job_id}/{filename}"
    adjusted = []
    for arg in command:
        if arg == "/code/main.py":
            adjusted.append(path)
        elif arg == "/code/main.js":
            adjusted.append(path)
        elif arg == "/code/main.c":
            adjusted.append(path)
        elif "/code/main" in arg:
            adjusted.append(arg.replace("/code/main.c", path).replace("/code/main.py", path).replace("/code/main.js", path))
        else:
            adjusted.append(arg)
    return adjusted


def _run_container(image: str, command: list, code: str, filename: str) -> Tuple[str, str, int]:
    client  = get_docker_client()
    job_id  = str(uuid.uuid4()).replace("-", "")
    job_dir = os.path.join(WORK_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    code_file = os.path.join(job_dir, filename)

    try:
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(code)

        if not os.path.exists(code_file):
            return "", f"Erreur : impossible de créer {code_file}", 1

        adjusted_command = _adjust_command(command, job_id, filename)

        container = client.containers.run(
            image=image,
            command=adjusted_command,
            detach=True,
            mounts=[
                Mount(
                    source="work_dir",
                    target="/root/.coderunner_tmp",
                    type="volume",
                    read_only=True
                )
            ],
            network_disabled=True,
            user="runner",
            cap_drop=["ALL"],
            mem_limit=settings.MAX_MEMORY,
            nano_cpus=int(settings.MAX_CPU * 1e9),
            pids_limit=50,
            ulimits=[
                docker.types.Ulimit(name="fsize", soft=10_000_000, hard=10_000_000),
            ],
            remove=False,
        )

        try:
            result    = container.wait(timeout=settings.MAX_EXECUTION_TIME)
            exit_code = result.get("StatusCode", 1)
            stdout    = container.logs(stdout=True,  stderr=False).decode("utf-8", errors="replace")
            stderr    = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
            return stdout, stderr, exit_code
        finally:
            try:
                container.remove(force=True)
            except Exception:
                pass
    finally:
        try:
            shutil.rmtree(job_dir, ignore_errors=True)
        except Exception:
            pass


# ──────────────────────────────────────────
# execute_code : async, retourne token
# ──────────────────────────────────────────

async def execute_code(code: str, language: str) -> Tuple[Optional[str], bool, Optional[str]]:
    is_safe, reason = validate_code(code, language)
    if not is_safe:
        return None, False, reason

    token = str(uuid.uuid4())
    await create_execution(token, language)
    asyncio.create_task(_execute_task(token, code, language))
    return token, True, None


# ──────────────────────────────────────────
# execute_and_wait : attend le résultat
# ──────────────────────────────────────────

async def execute_and_wait(code: str, language: str) -> dict:
    """
    Exécute le code et attend le résultat directement.
    Retourne le résultat complet sans polling.
    """
    is_safe, reason = validate_code(code, language)
    if not is_safe:
        return {
            "token":          None,
            "status":         "rejected",
            "language":       language,
            "output":         None,
            "error":          reason,
            "execution_time": None,
        }

    token = str(uuid.uuid4())
    await create_execution(token, language)

    import time
    start = time.time()

    try:
        image    = LANGUAGE_IMAGES[language]
        command  = LANGUAGE_COMMANDS[language]
        filename = LANGUAGE_EXTENSIONS[language]

        loop = asyncio.get_event_loop()

        async with get_semaphore():
            stdout, stderr, exit_code = await asyncio.wait_for(
                loop.run_in_executor(_executor, _run_container, image, command, code, filename),
                timeout=settings.MAX_EXECUTION_TIME + 5
            )

        exec_time = round(time.time() - start, 3)
        status    = "done" if exit_code == 0 else "error"
        output    = truncate_output(stdout.strip()) if stdout.strip() else None
        error     = truncate_output(stderr.strip()) if stderr.strip() else None

        await update_execution(token, status, output, error)

        return {
            "token":          token,
            "status":         status,
            "language":       language,
            "output":         output,
            "error":          error,
            "execution_time": exec_time,
        }

    except asyncio.TimeoutError:
        msg = f"Timeout : exécution dépassée ({settings.MAX_EXECUTION_TIME}s)"
        await update_execution(token, "error", None, msg)
        return {
            "token":          token,
            "status":         "error",
            "language":       language,
            "output":         None,
            "error":          msg,
            "execution_time": settings.MAX_EXECUTION_TIME,
        }

    except Exception as e:
        msg = f"Erreur interne : {str(e)}"
        await update_execution(token, "error", None, msg)
        return {
            "token":          token,
            "status":         "error",
            "language":       language,
            "output":         None,
            "error":          msg,
            "execution_time": None,
        }


# ──────────────────────────────────────────
# Tâche interne (pour execute_code async)
# ──────────────────────────────────────────

async def _execute_task(token: str, code: str, language: str):
    await update_execution(token, "running")
    try:
        image    = LANGUAGE_IMAGES[language]
        command  = LANGUAGE_COMMANDS[language]
        filename = LANGUAGE_EXTENSIONS[language]

        loop = asyncio.get_event_loop()

        async with get_semaphore():
            stdout, stderr, exit_code = await asyncio.wait_for(
                loop.run_in_executor(_executor, _run_container, image, command, code, filename),
                timeout=settings.MAX_EXECUTION_TIME + 5
            )

        status = "done" if exit_code == 0 else "error"
        output = truncate_output(stdout.strip()) if stdout.strip() else None
        error  = truncate_output(stderr.strip()) if stderr.strip() else None
        await update_execution(token, status, output, error)

    except asyncio.TimeoutError:
        await update_execution(token, "error", None,
            f"Timeout : exécution dépassée ({settings.MAX_EXECUTION_TIME}s)")
    except ImageNotFound:
        await update_execution(token, "error", None,
            f"Image Docker '{LANGUAGE_IMAGES.get(language)}' introuvable")
    except DockerException as e:
        await update_execution(token, "error", None, f"Erreur Docker : {str(e)}")
    except Exception as e:
        await update_execution(token, "error", None, f"Erreur interne : {str(e)}")
