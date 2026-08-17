from src.event_bus.base_service import BaseService
from src.event_bus.event import Event
from src.event_bus.event_bus import EventBus



class NotifierService(BaseService):
    """
    Serviço responsável por alertar sobre notícias relevantes.

    Consome news.scored e publica news.alert quando
    o score do artigo ultrapassa o limiar configurado.
    """

    DEFAULT_THRESHOLD = 6.0

    def __init__(self, bus: EventBus, threshold: float | None = None) -> None:
        super().__init__("NotifierService", bus)
        self.threshold = threshold or self.DEFAULT_THRESHOLD
        self.alerts_sent: list[dict] = []
        self.subscribe("news.scored", self.handle)

    def handle(self, event: Event) -> None:
        print(f"[{self.name}] Verificando artigos com score >= {self.threshold}")
        articles = event.payload.get("articles", [])

        for article in articles:
            if article.get("score", 0) >= self.threshold:
                self._send_alert(article)

    def _send_alert(self, article: dict) -> None:
        """
        Envia alerta para artigo relevante.

        Args:
            article: Artigo que ultrapassou o limiar
        """
        alert_level = "high" if article["score"] >= 8.0 else "medium"

        payload = {
            "alert_level": alert_level,
            "article": {
                "title": article.get("title"),
                "url": article.get("url"),
                "score": article.get("score"),
                "matched_topics": article.get("matched_topics", []),
            }
        }

        self.alerts_sent.append(payload)

        print(
            f"[{self.name}] 🔔 ALERTA [{alert_level.upper()}] "
            f"Score {article['score']} — {article.get('title')}"
        )

        self.publish(Event("news.alert", payload))

    def get_alerts(self) -> list[dict]:
        """Retorna todos os alertas enviados."""
        return self.alerts_sent.copy()