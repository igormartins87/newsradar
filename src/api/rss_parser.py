import feedparser
from datetime import datetime
from urllib.parse import urlparse


class RSSParser:
    """
    Responsável por consumir feeds RSS públicos em PT e EN
    e retornar notícias no formato padronizado do NewsRadar.
    """

    FEEDS = {
        # Português
        "g1": "https://g1.globo.com/rss/g1/",
        "bbc": "https://feeds.bbci.co.uk/portuguese/rss.xml",
        "tecmundo": "https://rss.tecmundo.com.br/feed",
        "canaltech": "https://canaltech.com.br/rss/",
        # Inglês — Tecnologia
        "techcrunch": "https://techcrunch.com/feed/",
        "wired": "https://www.wired.com/feed/rss",
        # Inglês — IA e Ciência
        "mit": "https://www.technologyreview.com/feed/",
        "sciencedaily": "https://www.sciencedaily.com/rss/top/science.xml",
        # Inglês — Espaço
        "nasa": "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        "spacenews": "https://spacenews.com/feed/",
    }

    CATEGORIES = {
        "tecnologia": ["g1", "bbc", "tecmundo", "canaltech", "techcrunch", "wired"],
        "inteligencia_artificial": ["mit", "techcrunch"],
        "ciencia": ["sciencedaily", "g1"],
        "espaco": ["nasa", "spacenews"],
        "tendencias": ["wired", "bbc", "tecmundo"],
    }

    ALLOWED_DOMAINS = {
        "g1.globo.com", "feeds.bbci.co.uk", "rss.tecmundo.com.br",
        "canaltech.com.br", "techcrunch.com", "www.wired.com",
        "www.technologyreview.com", "www.sciencedaily.com",
        "www.nasa.gov", "spacenews.com",
    }

    def _validate_url(self, url: str) -> bool:
        """
        Valida a URL do feed para prevenir SSRF.

        Bloqueia requisições para IPs internos, localhost
        e domínios não autorizados.
        """
        try:
            parsed = urlparse(url)
            host = parsed.hostname or ""

            blocked = ["localhost", "127.", "0.0.0.0", "10.", "172.16.", "192.168.", "::1"]
            if any(host.startswith(b) for b in blocked):
                print(f"[RSSParser] SSRF bloqueado: {url}")
                return False

            if host not in self.ALLOWED_DOMAINS:
                print(f"[RSSParser] Domínio não autorizado: {host}")
                return False

            return True
        except Exception:
            return False

    def fetch(self, source: str, limit: int = 10) -> list[dict]:
        """Busca notícias de um feed RSS específico."""
        url = self.FEEDS.get(source)
        if not url:
            return []

        if not self._validate_url(url):
            print(f"[RSSParser] URL bloqueada por SSRF: {url}")
            return []

        try:
            feed = feedparser.parse(url)
            articles = []
            for entry in feed.entries[:limit]:
                articles.append(self._normalize(entry, source))
            return articles
        except Exception as e:
            print(f"[RSSParser] Erro ao buscar '{source}': {e}")
            return []

    def fetch_all(self, limit: int = 10) -> list[dict]:
        """Busca notícias de todas as fontes disponíveis."""
        all_articles = []
        for source in self.FEEDS:
            all_articles.extend(self.fetch(source, limit))
        return all_articles

    def fetch_by_category(self, category: str, limit: int = 10) -> list[dict]:
        """Busca notícias de uma categoria específica."""
        sources = self.CATEGORIES.get(category, [])
        articles = []
        for source in sources:
            articles.extend(self.fetch(source, limit))
        return articles

    def _normalize(self, entry, source: str) -> dict:
        """Normaliza um entry do feedparser para o formato padrão."""
        import bleach

        title = bleach.clean(entry.get("title", "").strip(), tags=[], strip=True)
        description = bleach.clean(entry.get("summary", "").strip(), tags=[], strip=True)
        url = entry.get("link", "").strip()

        return {
            "id": hash(f"{url}{title}"),
            "title": title,
            "description": description,
            "url": url,
            "published_at": entry.get("published", datetime.utcnow().isoformat()),
            "source_name": source.upper(),
            "language": self._detect_language(source),
        }

    def _detect_language(self, source: str) -> str:
        """Detecta o idioma baseado na fonte."""
        pt_sources = {"g1", "bbc", "tecmundo", "canaltech"}
        return "pt" if source in pt_sources else "en"