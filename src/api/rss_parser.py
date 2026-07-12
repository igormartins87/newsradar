import feedparser
from datetime import datetime


class RSSParser:
    """
    Responsável por consumir feeds RSS públicos e
    retornar notícias no formato padronizado do NewsRadar.

    Segue o princípio de responsabilidade única — só faz
    uma coisa: buscar e normalizar RSS.
    """

    FEEDS = {
        "g1": "https://g1.globo.com/rss/g1/",
        "bbc": "https://feeds.bbci.co.uk/portuguese/rss.xml",
        "tecmundo": "https://rss.tecmundo.com.br/feed",
    }

    def fetch(self, source: str, limit: int = 10) -> list[dict]:
        """
        Busca notícias de um feed RSS.

        Args:
            source: chave do feed (ex: 'g1', 'bbc')
            limit: quantidade máxima de notícias

        Returns:
            Lista de notícias normalizadas
        """
        url = self.FEEDS.get(source)
        if not url:
            return []

        feed = feedparser.parse(url)
        articles = []

        for entry in feed.entries[:limit]:
            articles.append({
                "id": hash(entry.get("link", "")),
                "title": entry.get("title", ""),
                "description": entry.get("summary", ""),
                "url": entry.get("link", ""),
                "published_at": entry.get("published", 
                                datetime.utcnow().isoformat()),
                "source_name": source.upper(),
            })

        return articles

    def fetch_all(self, limit: int = 10) -> list[dict]:
        """
        Busca notícias de todas as fontes disponíveis.

        Args:
            limit: quantidade por fonte

        Returns:
            Lista combinada de todas as fontes
        """
        all_articles = []
        for source in self.FEEDS:
            all_articles.extend(self.fetch(source, limit))
        return all_articles