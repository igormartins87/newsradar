import feedparser
import logging
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from src.api.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class RSSParser:
    """
    Responsável por consumir feeds RSS públicos em PT e EN.

    Implementa 4 estratégias de resiliência:
    1. Timeout por fonte — fonte lenta não trava o sistema
    2. Circuit Breaker — fonte quebrada não é chamada desnecessariamente
    3. Cache por fonte — dashboard sempre tem conteúdo
    4. Health check — status de cada fonte disponível
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
    FETCH_TIMEOUT = 8  # segundos por fonte

    def __init__(self) -> None:
        # Circuit breaker por fonte
        self._circuits: dict[str, CircuitBreaker] = {
            source: CircuitBreaker(source=source)
            for source in self.FEEDS
        }
        # Cache por fonte — fallback quando fonte falha
        self._source_cache: dict[str, list[dict]] = {}

    def _validate_url(self, url: str) -> bool:
        """Valida URL para prevenir SSRF."""
        try:
            parsed = urlparse(url)
            host = parsed.hostname or ""
            blocked = ["localhost", "127.", "0.0.0.0", "10.", "172.16.", "192.168.", "::1"]
            if any(host.startswith(b) for b in blocked):
                return False
            return host in self.ALLOWED_DOMAINS
        except Exception:
            return False

    def _is_recent(self, published_at: str) -> bool:
        """Verifica se a notícia foi publicada nas últimas 24h."""
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
        """Normaliza e sanitiza um entry do feedparser."""
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
        pt_sources = {"g1", "canaltech", "tecmundo"}
        return "pt" if source in pt_sources else "en"

    def _fetch_raw(self, source: str, limit: int) -> list[dict]:
        """
        Busca RSS com timeout — chamada protegida pelo circuit breaker.
        """
        url = self.FEEDS.get(source)
        if not url or not self._validate_url(url):
            return []

        feed = feedparser.parse(url, request_headers={
            "User-Agent": "NewsRadar/2.0",
            "Connection": "close",
        })

        articles = []
        for entry in feed.entries:
            article = self._normalize(entry, source)
            if not self._is_recent(article["published_at"]):
                continue
            articles.append(article)
            if len(articles) >= limit:
                break

        return articles

    def fetch(self, source: str, limit: int = 10) -> list[dict]:
        """
        Busca notícias de uma fonte com circuit breaker e cache fallback.

        Se a fonte falhar:
        1. Circuit breaker registra a falha
        2. Retorna cache da última busca bem-sucedida
        3. Se não houver cache, retorna []
        """
        if source not in self.FEEDS:
            return []

        circuit = self._circuits[source]
        result = circuit.call(self._fetch_raw, source, limit)

        if result:
            self._source_cache[source] = result
            logger.info(f"[RSSParser] '{source}' → {len(result)} notícias")
        elif source in self._source_cache:
            cached = self._source_cache[source]
            logger.warning(f"[RSSParser] '{source}' falhou → usando cache ({len(cached)} notícias)")
            return cached

        return result

    def fetch_all(self, limit: int = 10) -> list[dict]:
        """Busca de todas as fontes com resiliência."""
        all_articles = []
        for source in self.FEEDS:
            all_articles.extend(self.fetch(source, limit))
        return all_articles

    def fetch_by_category(self, category: str, limit: int = 10) -> list[dict]:
        """Busca por categoria com resiliência."""
        sources = self.CATEGORIES.get(category, [])
        articles = []
        for source in sources:
            articles.extend(self.fetch(source, limit))
        return articles

    def get_health(self) -> dict:
        """
        Retorna o status de saúde de todas as fontes.
        Usado pelo endpoint /news/sources/health
        """
        return {
            source: circuit.get_status()
            for source, circuit in self._circuits.items()
        }