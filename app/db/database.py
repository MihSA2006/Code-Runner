import aiosqlite
import time
from typing import Optional
from app.db.models import Execution
from app.core.config import settings

DB_PATH = settings.DATABASE_URL


# ──────────────────────────────────────────
# Initialisation
# ──────────────────────────────────────────

async def init_db():
    """Crée la table et les index si nécessaire."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS executions (
                token        TEXT PRIMARY KEY,
                status       TEXT NOT NULL DEFAULT 'pending',
                language     TEXT NOT NULL,
                output       TEXT,
                error        TEXT,
                created_at   REAL NOT NULL,
                completed_at REAL
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_executions_created_at
            ON executions(created_at)
        """)
        await db.commit()
    print("✅ Base de données initialisée")


# ──────────────────────────────────────────
# Créer un token
# ──────────────────────────────────────────

async def create_execution(token: str, language: str) -> Execution:
    """Enregistre un nouveau token avec statut 'pending'."""
    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO executions (token, status, language, created_at)
            VALUES (?, ?, ?, ?)
        """, (token, "pending", language, now))
        await db.commit()

    return Execution(
        token=token,
        status="pending",
        language=language,
        created_at=now
    )


# ──────────────────────────────────────────
# Mettre à jour le statut
# ──────────────────────────────────────────

async def update_execution(
    token: str,
    status: str,
    output: Optional[str] = None,
    error: Optional[str] = None
):
    """Met à jour le résultat d'une exécution."""
    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE executions
            SET status = ?,
                output = ?,
                error  = ?,
                completed_at = ?
            WHERE token = ?
        """, (status, output, error, now, token))
        await db.commit()


# ──────────────────────────────────────────
# Récupérer un résultat
# ──────────────────────────────────────────

async def get_execution(token: str) -> Optional[Execution]:
    """Récupère une exécution par son token."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM executions WHERE token = ?
        """, (token,)) as cursor:
            row = await cursor.fetchone()

    if row is None:
        return None

    return Execution(
        token=row["token"],
        status=row["status"],
        language=row["language"],
        output=row["output"],
        error=row["error"],
        created_at=row["created_at"],
        completed_at=row["completed_at"],
    )


# ──────────────────────────────────────────
# Supprimer un token
# ──────────────────────────────────────────

async def delete_execution(token: str):
    """Supprime un token de la base."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            DELETE FROM executions WHERE token = ?
        """, (token,))
        await db.commit()


# ──────────────────────────────────────────
# Nettoyage automatique des tokens expirés
# ──────────────────────────────────────────

async def cleanup_expired():
    """Supprime les tokens plus vieux que TOKEN_EXPIRY secondes."""
    expiry_limit = time.time() - settings.TOKEN_EXPIRY
    async with aiosqlite.connect(DB_PATH) as db:
        result = await db.execute("""
            DELETE FROM executions WHERE created_at < ?
        """, (expiry_limit,))
        await db.commit()
        deleted = result.rowcount

    if deleted > 0:
        print(f"🧹 {deleted} token(s) expiré(s) supprimé(s)")
