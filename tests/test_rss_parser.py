from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest.mock import MagicMock, patch

import feedparser
import httpx
import pytest

from src.api.circuit_breaker import CircuitState
from src.api.rss_parser import RSSParser


def _rss(items):
    """Monta um RSS 2.0 mínimo. items = [(titulo, link, datetime)]."""
    body = "".join(
        f"<item><title>{t}</title><link>{link}</link>"
        f"<pubDate>{format_datetime(d)}</pubDate>"
        f"<description>desc</description></item>"
        for t, link, d in items
    )
    xml = (
        '<?xml version="1.0"?><rss version="2.0"><channel>'
        f"<title>feed</title>{body}</channel></rss>"
    )
    return xml.encode()


def _agora(**delta):
    return datetime.now(timezone.utc) - timedelta(**delta)


class TestRSSParser:

    def setup_method(self):
        self.parser = RSSParser()

    # ── Validação de URL (SSRF) ──────────────────────────────────────────

    def test_validate_url_dominio_autorizado(self):
        assert self.parser._validate_url("https://techcrunch.com/feed/") is True

    def test_validate_url_api_arxiv_autorizada(self):
        assert self.parser._validate_url("https://export.arxiv.org/api/query") is True

    def test_validate_url_localhost_bloqueado(self):
        assert self.parser._validate_url("http://localhost:8080/feed") is False

    def test_validate_url_ip_interno_bloqueado(self):
        assert self.parser._validate_url("http://192.168.1.1/feed") is False

    def test_validate_url_ip_127_bloqueado(self):
        assert self.parser._validate_url("http://127.0.0.1/feed") is False

    def test_validate_url_dominio_nao_autorizado(self):
        assert self.parser._validate_url("https://site-malicioso.com/feed") is False

    def test_validate_url_redirect_do_huggingface_bloqueado(self):
        assert self.parser._validate_url("https://huggingface.co/papers") is False

    # ── _http_get: timeout, status e redirecionamento ────────────────────

    def test_http_get_retorna_conteudo(self):
        resp = MagicMock(is_redirect=False, content=b"<rss/>")
        with patch.object(self.parser._client, "get", return_value=resp):
            assert self.parser._http_get("https://techcrunch.com/feed/") == b"<rss/>"

    def test_http_get_status_404_levanta_excecao(self):
        resp = MagicMock(is_redirect=False)
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=MagicMock()
        )
        with patch.object(self.parser._client, "get", return_value=resp):
            with pytest.raises(httpx.HTTPStatusError):
                self.parser._http_get("https://techcrunch.com/feed/")

    def test_http_get_redirect_para_dominio_fora_da_allowlist_e_bloqueado(self):
        resp = MagicMock(is_redirect=True, headers={"location": "https://evil.com/x"})
        with patch.object(self.parser._client, "get", return_value=resp) as get:
            with pytest.raises(ValueError, match="allowlist"):
                self.parser._http_get("https://techcrunch.com/feed/")
        assert get.call_count == 1  # nunca chegou a chamar o domínio malicioso

    def test_http_get_url_inicial_fora_da_allowlist_nem_conecta(self):
        with patch.object(self.parser._client, "get") as get:
            with pytest.raises(ValueError):
                self.parser._http_get("https://evil.com/feed")
        get.assert_not_called()

    def test_http_get_timeout_propaga(self):
        with patch.object(
            self.parser._client, "get", side_effect=httpx.TimeoutException("lento")
        ):
            with pytest.raises(httpx.TimeoutException):
                self.parser._http_get("https://techcrunch.com/feed/")

    # ── Datas e recência ─────────────────────────────────────────────────

    def test_entry_datetime_le_data_iso_do_atom(self):
        atom = (
            '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">'
            "<title>t</title><entry><title>x</title><id>1</id>"
            "<published>2026-10-29T17:59:29Z</published></entry></feed>"
        )
        entry = feedparser.parse(atom.encode()).entries[0]
        dt = self.parser._entry_datetime(entry)
        assert dt == datetime(2026, 10, 29, 17, 59, 29, tzinfo=timezone.utc)

    def test_entry_datetime_sem_data_retorna_none(self):
        assert self.parser._entry_datetime({"title": "x"}) is None

    def test_is_recent_noticia_de_hoje(self):
        assert self.parser._is_recent(_agora(hours=1), "techcrunch") is True

    def test_is_recent_noticia_antiga(self):
        assert self.parser._is_recent(_agora(days=3), "techcrunch") is False

    def test_is_recent_sem_data_mantem(self):
        assert self.parser._is_recent(None, "techcrunch") is True

    def test_is_recent_janela_maior_para_fonte_semanal(self):
        cinco_dias = _agora(days=5)
        assert self.parser._is_recent(cinco_dias, "techcrunch") is False
        assert self.parser._is_recent(cinco_dias, "importai") is True

    # ── Idioma, fontes e categorias ──────────────────────────────────────

    def test_detect_language(self):
        assert self.parser._detect_language("g1") == "pt"
        assert self.parser._detect_language("tecmundo") == "pt"
        assert self.parser._detect_language("techcrunch") == "en"
        assert self.parser._detect_language("arxiv_ai") == "en"

    def test_todas_as_fontes_tem_dominio_autorizado(self):
        for source, url in self.parser.FEEDS.items():
            assert self.parser._validate_url(url), f"'{source}' fora da allowlist"

    def test_categorias_referenciam_fontes_existentes(self):
        for category, sources in self.parser.CATEGORIES.items():
            for source in sources:
                assert source in self.parser.FEEDS, f"{category} -> {source}"

    def test_overrides_de_recencia_referenciam_fontes_existentes(self):
        for source in self.parser.RECENCY_OVERRIDES:
            assert source in self.parser.FEEDS

    # ── fetch ────────────────────────────────────────────────────────────

    def test_fetch_retorna_artigos_recentes(self):
        xml = _rss([("Artigo recente", "https://techcrunch.com/a", _agora(hours=1))])
        with patch.object(self.parser, "_http_get", return_value=xml):
            articles = self.parser.fetch("techcrunch", limit=5)
        assert len(articles) == 1
        assert articles[0]["title"] == "Artigo recente"
        assert articles[0]["language"] == "en"
        assert articles[0]["published_at"].startswith(str(_agora().year))

    def test_fetch_descarta_artigo_muito_antigo(self):
        xml = _rss([("Velho", "https://techcrunch.com/v", _agora(days=60))])
        with patch.object(self.parser, "_http_get", return_value=xml):
            assert self.parser.fetch("techcrunch", limit=5) == []

    def test_fonte_lenta_completa_ate_o_minimo_com_as_mais_novas(self):
        xml = _rss([
            ("Hoje", "https://techcrunch.com/0", _agora(hours=1)),
            ("Ha 5 dias", "https://techcrunch.com/1", _agora(days=5)),
            ("Ha 9 dias", "https://techcrunch.com/2", _agora(days=9)),
            ("Ha 20 dias", "https://techcrunch.com/3", _agora(days=20)),
        ])
        with patch.object(self.parser, "_http_get", return_value=xml):
            titulos = [a["title"] for a in self.parser.fetch("techcrunch", limit=10)]
        assert titulos == ["Hoje", "Ha 5 dias", "Ha 9 dias"]

    def test_nao_completa_quando_ja_tem_o_minimo_na_janela(self):
        xml = _rss(
            [(f"N{i}", f"https://techcrunch.com/{i}", _agora(hours=1)) for i in range(3)]
            + [("Velho", "https://techcrunch.com/v", _agora(days=5))]
        )
        with patch.object(self.parser, "_http_get", return_value=xml):
            titulos = [a["title"] for a in self.parser.fetch("techcrunch", limit=10)]
        assert "Velho" not in titulos
        assert len(titulos) == 3

    def test_completar_respeita_limit_menor_que_o_minimo(self):
        xml = _rss(
            [(f"V{i}", f"https://techcrunch.com/{i}", _agora(days=2 + i)) for i in range(5)]
        )
        with patch.object(self.parser, "_http_get", return_value=xml):
            assert len(self.parser.fetch("techcrunch", limit=2)) == 2

    def test_completar_ignora_o_que_passou_do_limite_de_dias(self):
        xml = _rss([
            ("Ha 10 dias", "https://krebsonsecurity.com/1", _agora(days=10)),
            ("Ha 100 dias", "https://krebsonsecurity.com/2", _agora(days=100)),
        ])
        with patch.object(self.parser, "_http_get", return_value=xml):
            titulos = [a["title"] for a in self.parser.fetch("techcrunch", limit=5)]
        assert titulos == ["Ha 10 dias"]

    def test_fetch_respeita_limite(self):
        xml = _rss(
            [(f"A{i}", f"https://techcrunch.com/{i}", _agora(hours=1)) for i in range(20)]
        )
        with patch.object(self.parser, "_http_get", return_value=xml):
            assert len(self.parser.fetch("techcrunch", limit=3)) == 3

    def test_fetch_fonte_inexistente_nao_acessa_rede(self):
        with patch.object(self.parser, "_http_get") as http:
            assert self.parser.fetch("nao_existe", limit=5) == []
        http.assert_not_called()

    # ── Resiliência ──────────────────────────────────────────────────────

    def test_feed_valido_sem_itens_nao_conta_como_falha(self):
        with patch.object(self.parser, "_http_get", return_value=_rss([])):
            assert self.parser.fetch("arxiv_ai") == []
        assert self.parser._circuits["arxiv_ai"].failure_count == 0

    def test_resposta_html_conta_como_falha(self):
        html = b"<html><body>pagina, nao um feed</body></html>"
        with patch.object(self.parser, "_http_get", return_value=html):
            assert self.parser.fetch("importai") == []
        assert self.parser._circuits["importai"].failure_count == 1

    def test_erro_de_rede_conta_como_falha(self):
        with patch.object(self.parser, "_http_get", side_effect=httpx.ConnectError("x")):
            assert self.parser.fetch("techcrunch") == []
        assert self.parser._circuits["techcrunch"].failure_count == 1

    def test_circuit_abre_apos_tres_falhas_e_para_de_chamar_a_rede(self):
        with patch.object(self.parser, "_http_get", side_effect=httpx.ConnectError("x")) as http:
            for _ in range(5):
                self.parser.fetch("krebs")
        assert self.parser._circuits["krebs"].state == CircuitState.OPEN
        assert http.call_count == 3
        assert self.parser.get_health()["krebs"]["state"] == "open"

    def test_falha_usa_ultima_coleta_boa(self):
        xml = _rss([("Boa", "https://techcrunch.com/b", _agora(hours=1))])
        with patch.object(self.parser, "_http_get", return_value=xml):
            self.parser.fetch("techcrunch")
        with patch.object(self.parser, "_http_get", side_effect=httpx.TimeoutException("x")):
            articles = self.parser.fetch("techcrunch")
        assert [a["title"] for a in articles] == ["Boa"]

    def test_fallback_expira_depois_do_limite(self):
        xml = _rss([("Boa", "https://techcrunch.com/b", _agora(hours=1))])
        with patch.object(self.parser, "_http_get", return_value=xml):
            self.parser.fetch("techcrunch")
        saved_at, articles = self.parser._source_cache["techcrunch"]
        self.parser._source_cache["techcrunch"] = (
            saved_at - self.parser.STALE_MAX_SECONDS - 1,
            articles,
        )
        with patch.object(self.parser, "_http_get", side_effect=httpx.TimeoutException("x")):
            assert self.parser.fetch("techcrunch") == []

    def test_fonte_com_falha_nao_derruba_as_outras(self):
        xml = _rss([("Ok", "https://x/ok", _agora(hours=1))])

        def fake(url):
            if "canaltech" in url:
                raise httpx.ConnectError("fora do ar")
            return xml

        with patch.object(self.parser, "_http_get", side_effect=fake):
            articles = self.parser.fetch_all(limit=5)
        fontes = {a["source_name"] for a in articles}
        assert "CANALTECH" not in fontes
        assert len(fontes) == len(self.parser.FEEDS) - 1

    def test_fetch_all_roda_em_paralelo(self):
        import time

        def lento(url):
            time.sleep(0.3)
            return _rss([("x", "https://x/1", _agora(hours=1))])

        with patch.object(self.parser, "_http_get", side_effect=lento):
            t = time.perf_counter()
            self.parser.fetch_all(limit=1)
            elapsed = time.perf_counter() - t
        sequencial = 0.3 * len(self.parser.FEEDS)
        assert elapsed < sequencial / 2

    # ── Normalização ─────────────────────────────────────────────────────

    def test_normalize_campos_obrigatorios(self):
        entry = {
            "title": "Título", "summary": "Desc",
            "link": "https://techcrunch.com/t", "published": "Fri, 12 Sep 2026 10:00:00 +0000",
        }
        result = self.parser._normalize(entry, "techcrunch")
        for campo in ("id", "title", "description", "url", "published_at",
                      "source_name", "language"):
            assert campo in result

    def test_normalize_sanitiza_xss(self):
        entry = {
            "title": "<script>alert('xss')</script>Título",
            "summary": "Descrição <b>normal</b>",
            "link": "https://techcrunch.com/t", "published": "",
        }
        result = self.parser._normalize(entry, "techcrunch")
        assert "<script>" not in result["title"]
        assert "</script>" not in result["title"]
        assert "<b>" not in result["description"]

    def test_normalize_source_name_uppercase(self):
        entry = {"title": "T", "summary": "", "link": "https://techcrunch.com/t", "published": ""}
        assert self.parser._normalize(entry, "techcrunch")["source_name"] == "TECHCRUNCH"
