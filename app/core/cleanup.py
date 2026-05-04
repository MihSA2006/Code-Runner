import asyncio
from app.db.database import cleanup_expired
from app.core.config import settings


async def start_cleanup_scheduler():
    """
    Lance une tâche de fond qui nettoie
    les tokens expirés toutes les X secondes.
    """
    print(f"🧹 Nettoyage automatique démarré "
          f"(interval: {settings.CLEANUP_INTERVAL}s, "
          f"TTL: {settings.TOKEN_EXPIRY}s)")

    while True:
        await asyncio.sleep(settings.CLEANUP_INTERVAL)
        await cleanup_expired()
