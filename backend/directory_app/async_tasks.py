import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Executor pour exécuter les tâches réseau secondaires (envois SMS, Push, Mails) hors thread HTTP principal
executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="agrilink_async_worker")


def run_async(func, *args, **kwargs):
    """Soumet une fonction à l'exécuteur arrière-plan de manière non bloquante."""
    def wrapper():
        try:
            func(*args, **kwargs)
        except Exception as exc:
            logger.error("Erreur lors de l'exécution asynchrone de %s: %s", func.__name__, exc)

    return executor.submit(wrapper)
