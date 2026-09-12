import feedparser
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse


class RSSParser:
    """
    Responsável por consumir feeds RSS públicos em PT e EN
    e retornar notícias no formato padronizado do NewsRadar.

    Aplica filtro de recência (12h) e top N por score
    para garantir qualidade sobre quantidade.
    """

    FEEDS = {
        # 🇧🇷 Brasil
        "g1":        "https://g1.globo.com/rss/g1/tecnologia/",
        "canaltech":  "https://canaltech.com.br/rss/",
        "tecmundo":   "https://rss.tecmundo.com.br/feed",

        # 🌎 Tecnologia
        "arstechnica": "https://feeds.arstechnica.com/arstechnica/index",
        "techcrunch":  "https://techcrunch.com/feed/",
        "theverge":    "https://www.theverge.com/rss/index.xml",
        "wired":       "https://www.wired.com/feed/rss",
        "mit":         "https://www.technologyreview.com/feed/",

        # 🤖 IA
        "paperswithcode": "https://paperswithcode.com/rss",
        "importai":       "https://importai.substack.com/feed",
        "thebatch":       "https://www.deeplearning.ai/the-batch/rss/",

        # 🔬 Pesquisa
        "arxiv_ai": "https://arxiv.org/rss/cs.AI",
        "arxiv_lg": "https://arxiv.org/rss/cs.LG",

        # 🔐 Segurança
        "krebs": "https://krebsonsecurity.com/feed/",
    }

    CATEGORIES = {
        "brasil":     ["g1", "canaltech", "tecmundo"],
        "tecnologia": ["arstechnica", "techcrunch", "theverge", "wired", "mit"],
        "inteligencia_artificial": ["paperswithcode", "importai", "thebatch",
                                    "arxiv_ai", "arxiv_lg", "techcrunch"],
        "pesquisa":   ["arxiv_ai", "arxiv_lg", "paperswithcode"],
        "seguranca":  ["krebs", "arstechnica", "theverge"],
        "tendencias": ["wired", "mit", "theverge", "arstechnica"],
    }

    ALLOWED_DOMAINS = {
        "g1.globo.com", "canaltech.com.br", "rss.tecmundo.com.br",
        "feeds.arstechnica.com", "techcrunch.com", "www.theverge.com",
        "www.wired.com", "www.technologyreview.com",
        "paperswithcode.com", "importai.substack.com", "www.deeplearning.ai",
        "arxiv.org", "krebsonsecurity.com",
    }

    RECENCY_HOURS = 24

    def _validate_url(self, url: str) -> bool:
        """Valida URL para prevenir SSRF."""
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

    def _is_recent(self, published_at: str) -> bool:
        """
        Verifica se a notícia foi publicada nas últimas 24h.

        Args:
            published_at: data de publicação em string

        Returns:
            True se a notícia é recente
        """
        if not published_at:
            return True
        try:
            import email.utils
            parsed = email.utils.parsedate_to_datetime(published_at)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            cutoff = datetime.now(timezone.utc) - timedelta(hours=self.RECENCY_HOURS)
            return parsed >= cutoff
        except Exception:
            return True

    def _normalize(self, entry, source: str) -> dict:
        """Normaliza um entry do feedparser para o formato padrão."""
        import bleach

        title = bleach.clean(entry.get("title", "").strip(), tags=[], strip=True)
        description = bleach.clean(entry.get("summary", "").strip(), tags=[], strip=True)
        url = entry.get("link", "").strip()
        published_at = entry.get("published", "")

        return {
            "id": hash(f"{url}{title}"),
            "title": title,
            "description": description,
            "url": url,
            "published_at": published_at,
            "source_name": source.upper(),
            "language": self._detect_language(source),
        }

    def _detect_language(self, source: str) -> str:
        """Detecta o idioma baseado na fonte."""
        pt_sources = {"g1", "canaltech", "tecmundo"}
        return "pt" if source in pt_sources else "en"

    def fetch(self, source: str, limit: int = 10) -> list[dict]:
        """Busca notícias de um feed RSS com filtro de recência."""
        url = self.FEEDS.get(source)
        if not url:
            return []

        if not self._validate_url(url):
            return []

        try:
            feed = feedparser.parse(url)
            articles = []

            for entry in feed.entries:
                article = self._normalize(entry, source)

                if not self._is_recent(article["published_at"]):
                    continue

                articles.append(article)

                if len(articles) >= limit:
                    break

            print(f"[RSSParser] '{source}' → {len(articles)} notícias recentes.")
            return articles
        except Exception as e:
            print(f"[RSSParser] Erro ao buscar '{source}': {e}")
            return []

    def fetch_all(self, limit: int = 10) -> list[dict]:
        """Busca notícias de todas as fontes com filtro de recência."""
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