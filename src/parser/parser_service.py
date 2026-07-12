from src.event_bus.event import Event
from src.event_bus.event_bus import EventBus
from src.event_bus.base_service import BaseService


class ParserService(BaseService):
    """
    Serviço responsável por normalizar e limpar as notícias brutas.

    Consome o evento news.fetched e publica news.parsed
    com os dados padronizados e sem duplicatas.
    """

    def __init__(self, bus: EventBus) -> None:
        super().__init__("ParserService", bus)
        self.subscribe("news.fetched", self.handle)

    def handle(self, event: Event) -> None:
        """
        Processa o evento news.fetched.

        Args:
            event: Evento com artigos brutos
        """
        print(f"[{self.name}] Processando evento '{event.name}'")
        articles = event.payload.get("articles", [])

        parsed = self._parse(articles)

        self.publish(Event("news.parsed", {
            "source": event.payload.get("source"),
            "total": len(parsed),
            "articles": parsed,
        }))

    def _parse(self, articles: list[dict]) -> list[dict]:
        """
        Limpa, normaliza e remove duplicatas dos artigos.

        Args:
            articles: Lista de artigos brutos

        Returns:
            Lista de artigos normalizados sem duplicatas
        """
        seen_urls = set()
        parsed = []

        for article in articles:
            title = article.get("title", "").strip()
            url = article.get("url", "").strip()

            if not title or not url:
                continue

            if url in seen_urls:
                continue

            seen_urls.add(url)

            parsed.append({
                "id": article.get("id"),
                "title": title,
                "description": article.get("description", ""),
                "url": url,
                "published_at": article.get("published_at", ""),
                "source_name": article.get("source_name", ""),
                "keywords": self._extract_keywords(title),
            })

        print(f"[{self.name}] {len(parsed)} artigos após limpeza.")
        return parsed

    def _extract_keywords(self, title: str) -> list[str]:
        """
        Extrai palavras-chave do título ignorando palavras curtas.

        Args:
            title: Título do artigo

        Returns:
            Lista de palavras-chave em minúsculo
        """
        stopwords = {
            "de", "da", "do", "das", "dos", "em", "no", "na",
            "nos", "nas", "com", "por", "para", "que", "se",
            "um", "uma", "os", "as", "e", "é", "a", "o"
        }
        words = title.lower().split()
        return [w for w in words if w not in stopwords and len(w) > 3]