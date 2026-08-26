from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NewsScheduler:
    """
    Scheduler responsável por manter o cache atualizado
    e o servidor Render acordado automaticamente.

    Executa duas tarefas:
    - A cada 25 minutos: atualiza o cache de notícias
    - A cada 10 minutos: ping para manter o Render acordado
    """

    API_URL = "https://newsradar-api-s8id.onrender.com"

    def __init__(self) -> None:
        self.scheduler = BackgroundScheduler()
        self._setup_jobs()

    def _setup_jobs(self) -> None:
        """Configura os jobs do scheduler."""

        # Job 1 — Atualiza cache a cada 25 minutos
        self.scheduler.add_job(
            func=self._refresh_cache,
            trigger=IntervalTrigger(minutes=25),
            id="refresh_cache",
            name="Atualiza cache de notícias",
            replace_existing=True,
        )

        # Job 2 — Ping a cada 10 minutos para manter Render acordado
        self.scheduler.add_job(
            func=self._keep_alive,
            trigger=IntervalTrigger(minutes=10),
            id="keep_alive",
            name="Keep alive do Render",
            replace_existing=True,
        )

    def _refresh_cache(self) -> None:
        """
        Atualiza o cache buscando notícias fresvas.
        Chamada automaticamente pelo scheduler.
        """
        try:
            logger.info("[Scheduler] Atualizando cache de notícias...")
            response = httpx.get(
                f"{self.API_URL}/news/public?limit=10",
                timeout=60,
            )
            if response.status_code == 200:
                data = response.json()
                total = len(data.get("articles", []))
                logger.info(f"[Scheduler] Cache atualizado — {total} notícias.")
            else:
                logger.warning(f"[Scheduler] Erro ao atualizar cache: {response.status_code}")
        except Exception as e:
            logger.error(f"[Scheduler] Falha ao atualizar cache: {e}")

    def _keep_alive(self) -> None:
        """
        Faz ping na API para manter o Render acordado.
        """
        try:
            response = httpx.get(f"{self.API_URL}/", timeout=30)
            logger.info(f"[Scheduler] Keep alive — status: {response.status_code}")
        except Exception as e:
            logger.error(f"[Scheduler] Keep alive falhou: {e}")

    def start(self) -> None:
        """Inicia o scheduler."""
        self.scheduler.start()
        logger.info("[Scheduler] Iniciado — jobs ativos:")
        for job in self.scheduler.get_jobs():
            logger.info(f"  → {job.name}")

    def stop(self) -> None:
        """Para o scheduler graciosamente."""
        self.scheduler.shutdown()
        logger.info("[Scheduler] Parado.")