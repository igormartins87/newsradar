from src.event_bus.event import Event
from src.event_bus.event_bus import EventBus
from src.event_bus.base_service import BaseService


class ScorerService(BaseService):
    """
    Serviço responsável por calcular a relevância das notícias.

    Consome news.parsed e publica news.scored com uma
    pontuação de 0.0 a 10.0 baseada em palavras-chave de interesse.
    """

    DEFAULT_TOPICS = [
        "inteligência artificial", "concurso", "python",
        "tecnologia", "ibge", "cesgranrio", "engenharia"
    ]

    def __init__(self, bus: EventBus, topics: list[str] = None) -> None:
        super().__init__("ScorerService", bus)
        self.topics = [t.lower() for t in (topics or self.DEFAULT_TOPICS)]
        self.subscribe("news.parsed", self.handle)

    def handle(self, event: Event) -> None:
        print(f"[{self.name}] Pontuando artigos...")
        articles = event.payload.get("articles", [])

        scored = []
        for article in articles:
            score, matched = self._calculate_score(article)
            scored.append({**article, "score": score, "matched_topics": matched})

        scored.sort(key=lambda x: x["score"], reverse=True)

        self.publish(Event("news.scored", {
            "source": event.payload.get("source"),
            "total": len(scored),
            "articles": scored,
        }))

    def _calculate_score(self, article: dict) -> tuple[float, list[str]]:
        """
        Calcula o score de relevância do artigo.

        Returns:
            Tupla com (score, lista de tópicos encontrados)
        """
        text = (
            article.get("title", "") + " " +
            article.get("description", "")
        ).lower()

        matched = [t for t in self.topics if t in text]
        score = round(
            min(len(matched) * 3.0 +
                len(article.get("keywords", [])) * 0.5, 10.0), 1
        )

        return score, matched