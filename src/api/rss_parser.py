import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlparse

import bleach
import feedparser
import httpx

from src.api.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class RSSParser:
    """
    Consome feeds RSS/Atom públicos e devolve notícias normalizadas.

    Resiliência:
    - Timeout real por fonte (httpx), com falha explícita em HTTP 4xx/5xx
    - Circuit breaker por fonte, que agora enxerga as falhas de rede
    - Fallback: última coleta boa da fonte, por no máximo 6 horas
    - Coleta em paralelo, com limite de workers
    - Mínimo de 3 artigos por fonte saudável, mesmo fora da janela de recência
    - Redirecionamentos validados contra a allowlist (SSRF)
    """

    FEEDS = {
        # Brasil
        "g1": "https://g1.globo.com/rss/g1/tecnologia/",
        "canaltech": "https://canaltech.com.br/rss/",
        "tecmundo": "https://rss.tecmundo.com.br/feed",
        # Tecnologia
        "arstechnica": "https://feeds.arstechnica.com/arstechnica/index",
        "techcrunch": "https://techcrunch.com/feed/",
        "theverge": "https://www.theverge.com/rss/index.xml",
        "wired": "https://www.wired.com/feed/rss",
        "mit": "https://www.technologyreview.com/feed/",
        # IA
        "importai": "https://importai.substack.com/feed",
        # Pesquisa (API do arXiv: sempre devolve os mais recentes)
        "arxiv_ai": (
            "https://export.arxiv.org/api/query?search_query=cat:cs.AI"
            "&sortBy=submittedDate&sortOrder=descending&max_results=30"
        ),
        "arxiv_lg": (
            "https://export.arxiv.org/api/query?search_query=cat:cs.LG"
            "&sortBy=submittedDate&sortOrder=descending&max_results=30"
        ),
        # Segurança
        "krebs": "https://krebsonsecurity.com/feed/",
    }

    CATEGORIES = {
        "brasil": ["g1", "canaltech", "tecmundo"],
        "tecnologia": ["arstechnica", "techcrunch", "theverge", "wired", "mit"],
        "inteligencia_artificial": ["importai", "arxiv_ai", "arxiv_lg", "techcrunch"],
        "pesquisa": ["arxiv_ai", "arxiv_lg"],
        "seguranca": ["krebs", "arstechnica", "theverge"],
        "tendencias": ["wired", "mit", "theverge", "arstechnica"],
    }

    ALLOWED_DOMAINS = {
        "g1.globo.com", "canaltech.com.br", "rss.tecmundo.com.br",
        "feeds.arstechnica.com", "techcrunch.com", "www.theverge.com",
        "www.wired.com", "www.technologyreview.com",
        "importai.substack.com", "export.arxiv.org", "krebsonsecurity.com",
    }

    # Janela de recência: padrão 24h, com exceções por frequência de publicação
    RECENCY_HOURS = 24
    RECENCY_OVERRIDES = {
        "mit": 72,
        "importai": 168,   # semanal
        "krebs": 240,      # poucos posts por semana
        "arxiv_ai": 72,    # não publica no fim de semana
        "arxiv_lg": 72,
    }

    # Fonte saudável mas lenta (semanal, fim de semana) não pode sumir:
    # se tiver menos de MIN_ARTICLES na janela, completa com as mais novas
    # fora dela, até MAX_FALLBACK_DAYS atrás.
    MIN_ARTICLES = 3
    MAX_FALLBACK_DAYS = 30

    FETCH_TIMEOUT = 8.0
    CONNECT_TIMEOUT = 3.0
    MAX_REDIRECTS = 3
    MAX_WORKERS = 6
    STALE_MAX_SECONDS = 6 * 3600
    # O arXiv pede no máximo 1 requisição a cada 3 segundos
    HOST_MIN_INTERVAL = {"export.arxiv.org": 3.0}

    def __init__(self) -> None:
        self._circuits: dict[str, CircuitBreaker] = {
            source: CircuitBreaker(source=source) for source in self.FEEDS
        }
        self._source_cache: dict[str, tuple[float, list[dict]]] = {}
        self._client = httpx.Client(
            timeout=httpx.Timeout(self.FETCH_TIMEOUT, connect=self.CONNECT_TIMEOUT),
            headers={"User-Agent": "NewsRadar/2.0"},
        )
        self._host_locks = {h: threading.Lock() for h in self.HOST_MIN_INTERVAL}
        self._last_call: dict[str, float] = {}

    # ── Segurança ────────────────────────────────────────────────────────

    def _validate_url(self, url: str) -> bool:
        """Valida a URL contra SSRF: IPs internos e domínios fora da allowlist."""
        try:
            host = urlparse(url).hostname or ""
            blocked = ["localhost", "127.", "0.0.0.0", "10.", "172.16.", "192.168.", "::1"]
            if any(host.startswith(b) for b in blocked):
                return False
            return host in self.ALLOWED_DOMAINS
        except Exception:
            return False

    # ── Rede ─────────────────────────────────────────────────────────────

    def _respect_rate_limit(self, url: str) -> None:
        host = urlparse(url).hostname or ""
        interval = self.HOST_MIN_INTERVAL.get(host)
        if not interval:
            return
        with self._host_locks[host]:
            last = self._last_call.get(host)
            if last is not None:
                wait = interval - (time.monotonic() - last)
                if wait > 0:
                    time.sleep(wait)
            self._last_call[host] = time.monotonic()

    def _http_get(self, url: str) -> bytes:
        """
        Baixa o feed com timeout real. Cada redirecionamento é validado
        contra a allowlist. HTTP 4xx/5xx viram exceção.
        """
        current = url
        for _ in range(self.MAX_REDIRECTS + 1):
            if not self._validate_url(current):
                raise ValueError(f"URL bloqueada pela allowlist: {current}")
            self._respect_rate_limit(current)
            response = self._client.get(current)
            if response.is_redirect:
                current = urljoin(current, response.headers["location"])
                continue
            response.raise_for_status()
            return response.content
        raise ValueError("Redirecionamentos demais")

    # ── Datas ────────────────────────────────────────────────────────────

    @staticmethod
    def _entry_datetime(entry) -> datetime | None:
        """Data da entrada via feedparser, que entende RSS e Atom (ISO 8601)."""
        parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        if not parsed:
            return None
        return datetime(*parsed[:6], tzinfo=timezone.utc)

    def _is_recent(self, published: datetime | None, source: str = "") -> bool:
        """Sem data legível, a entrada é mantida (não dá para julgar)."""
        if published is None:
            return True
        hours = self.RECENCY_OVERRIDES.get(source, self.RECENCY_HOURS)
        return published >= datetime.now(timezone.utc) - timedelta(hours=hours)

    # ── Normalização ─────────────────────────────────────────────────────

    def _detect_language(self, source: str) -> str:
        return "pt" if source in {"g1", "canaltech", "tecmundo"} else "en"

    def _normalize(self, entry, source: str) -> dict:
        title = bleach.clean(entry.get("title", "").strip(), tags=[], strip=True)
        description = bleach.clean(entry.get("summary", "").strip(), tags=[], strip=True)
        url = entry.get("link", "").strip()
        published = self._entry_datetime(entry)
        published_at = published.isoformat() if published else entry.get("published", "")
        return {
            "id": hash(f"{url}{title}"),
            "title": title,
            "description": description,
            "url": url,
            "published_at": published_at,
            "source_name": source.upper(),
            "language": self._detect_language(source),
        }

    # ── Coleta ───────────────────────────────────────────────────────────

    def _fetch_raw(self, source: str, limit: int) -> list[dict]:
        content = self._http_get(self.FEEDS[source])
        feed = feedparser.parse(content)

        # Página HTML ou erro no lugar de um feed: falha de verdade.
        # Feed válido sem itens (ex.: arXiv fora do ciclo) não é falha.
        if not feed.entries and not feed.get("version"):
            raise ValueError("resposta não é um feed RSS/Atom")

        recent, older = [], []
        for entry in feed.entries:
            published = self._entry_datetime(entry)
            if self._is_recent(published, source):
                recent.append(entry)
            else:
                older.append((published, entry))  # published nunca é None aqui

        selected = recent[:limit]

        missing = min(self.MIN_ARTICLES, limit) - len(selected)
        if missing > 0:
            oldest_allowed = datetime.now(timezone.utc) - timedelta(
                days=self.MAX_FALLBACK_DAYS
            )
            candidates = [(p, e) for p, e in older if p >= oldest_allowed]
            candidates.sort(key=lambda item: item[0], reverse=True)
            selected += [e for _, e in candidates[:missing]]

        return [self._normalize(e, source) for e in selected]

    def _stale(self, source: str) -> list[dict]:
        saved = self._source_cache.get(source)
        if not saved:
            return []
        saved_at, articles = saved
        if time.monotonic() - saved_at > self.STALE_MAX_SECONDS:
            return []
        logger.warning("[RSSParser] '%s' falhou, usando última coleta", source)
        return articles

    def fetch(self, source: str, limit: int = 10) -> list[dict]:
        if source not in self.FEEDS:
            return []

        circuit = self._circuits[source]
        result = circuit.call(self._fetch_raw, source, limit)

        if result:
            self._source_cache[source] = (time.monotonic(), result)
            return result
        # Lista vazia com falhas registradas: usa a última coleta boa.
        # Lista vazia sem falhas: a fonte está saudável e não tem nada novo.
        if circuit.failure_count > 0:
            return self._stale(source)
        return []

    def _fetch_many(self, sources: list[str], limit: int) -> list[dict]:
        articles: list[dict] = []
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as pool:
            for batch in pool.map(lambda s: self.fetch(s, limit), sources):
                articles.extend(batch)
        return articles

    def fetch_all(self, limit: int = 10) -> list[dict]:
        return self._fetch_many(list(self.FEEDS), limit)

    def fetch_by_category(self, category: str, limit: int = 10) -> list[dict]:
        return self._fetch_many(self.CATEGORIES.get(category, []), limit)

    def get_health(self) -> dict:
        return {s: c.get_status() for s, c in self._circuits.items()}
