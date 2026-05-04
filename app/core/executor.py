import uuid
import asyncio
import docker
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from docker.errors import DockerException, ImageNotFound
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
    "cpp":        "coderunner-cpp",
    "java":       "coderunner-java",
}

LANGUAGE_COMMANDS = {
    "python":     ["python3", "/code/main.py"],
    "javascript": ["node", "/code/main.js"],
    "c":          ["sh", "-c", "gcc /code/main.c -o /tmp/main 2>&1 && /tmp/main"],
    "cpp":        ["sh", "-c", "g++ /code/main.cpp -o /tmp/main 2>&1 && /tmp/main"],
    "java":       ["sh", "-c", "cp /code/main.java /tmp/Main.java && "
                               "javac /tmp/Main.java -d /tmp 2>&1 && "
                               "java -cp /tmp Main"],
}

LANGUAGE_EXTENSIONS = {
    "python":     "main.py",
    "javascript": "main.js",
    "c":          "main.c",
    "cpp":        "main.cpp",
    "java":       "main.java",
}

WORK_DIR = os.path.join(os.path.expanduser("~"), ".coderunner_tmp")

# ThreadPool dédié pour les exécutions Docker (max 5 simultanées)
_executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="docker_worker")


# ──────────────────────────────────────────
# Init
# ──────────────────────────────────────────

def init_work_dir():
    os.makedirs(WORK_DIR, exist_ok=True)
    print(f"📁 Dossier de travail : {WORK_DIR}")


# ──────────────────────────────────────────
# Exécution Docker
# ──────────────────────────────────────────

def _run_container(image: str, command: list, code: str, filename: str) -> Tuple[str, str, int]:
    client  = docker.from_env()
    job_id  = str(uuid.uuid4()).replace("-", "")
    job_dir = os.path.join(WORK_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    code_file = os.path.join(job_dir, filename)

    try:
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(code)

        if not os.path.exists(code_file):
            return "", f"Erreur : impossible de créer {code_file}", 1

        container = client.containers.run(
            image=image,
            command=command,
            detach=True,
            volumes={job_dir: {"bind": "/code", "mode": "ro"}},
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
