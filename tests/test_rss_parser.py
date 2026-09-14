from unittest.mock import patch, MagicMock
from src.api.rss_parser import RSSParser


class TestRSSParser:

    def setup_method(self):
        self.parser = RSSParser()

    # ── Validação de URL ─────────────────────────────────────────────────

    def test_validate_url_dominio_autorizado(self):
        assert self.parser._validate_url("https://techcrunch.com/feed/") is True

    def test_validate_url_localhost_bloqueado(self):
        assert self.parser._validate_url("http://localhost:8080/feed") is False

    def test_validate_url_ip_interno_bloqueado(self):
        assert self.parser._validate_url("http://192.168.1.1/feed") is False

    def test_validate_url_dominio_nao_autorizado(self):
        assert self.parser._validate_url("https://site-malicioso.com/feed") is False

    def test_validate_url_ip_127_bloqueado(self):
        assert self.parser._validate_url("http://127.0.0.1/feed") is False

    # ── Filtro de recência ───────────────────────────────────────────────

    def test_is_recent_noticia_de_hoje(self):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
        assert self.parser._is_recent(now) is True

    def test_is_recent_noticia_antiga(self):
        assert self.parser._is_recent("Mon, 01 Jan 2020 00:00:00 +0000") is False

    def test_is_recent_sem_data_retorna_true(self):
        assert self.parser._is_recent("") is True
        assert self.parser._is_recent(None) is True

    # ── Detecção de idioma ───────────────────────────────────────────────

    def test_detect_language_pt(self):
        assert self.parser._detect_language("g1") == "pt"
        assert self.parser._detect_language("canaltech") == "pt"
        assert self.parser._detect_language("tecmundo") == "pt"

    def test_detect_language_en(self):
        assert self.parser._detect_language("techcrunch") == "en"
        assert self.parser._detect_language("arxiv_ai") == "en"
        assert self.parser._detect_language("krebs") == "en"

    # ── Fontes e categorias ──────────────────────────────────────────────

    def test_todas_as_fontes_tem_url(self):
        for source, url in self.parser.FEEDS.items():
            assert url.startswith("http"), f"URL inválida para '{source}': {url}"

    def test_todas_as_fontes_tem_dominio_autorizado(self):
        for source, url in self.parser.FEEDS.items():
            assert self.parser._validate_url(url), \
                f"Fonte '{source}' com domínio não autorizado: {url}"

    def test_categorias_referenciam_fontes_existentes(self):
        for category, sources in self.parser.CATEGORIES.items():
            for source in sources:
                assert source in self.parser.FEEDS, \
                    f"Categoria '{category}' referencia fonte inexistente: '{source}'"

    # ── Fetch com mock ───────────────────────────────────────────────────

    @patch("feedparser.parse")
    def test_fetch_retorna_artigos_recentes(self, mock_parse):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
        entry = {
            "title": "Artigo recente",
            "summary": "Descrição do artigo",
            "link": "https://techcrunch.com/artigo",
            "published": now,
        }
        mock_feed = MagicMock()
        mock_feed.entries = [entry]
        mock_parse.return_value = mock_feed

        articles = self.parser.fetch("techcrunch", limit=5)
        assert len(articles) == 1
        assert articles[0]["title"] == "Artigo recente"
        assert articles[0]["language"] == "en"

    @patch("feedparser.parse")
    def test_fetch_filtra_artigos_antigos(self, mock_parse):
        entry = {
            "title": "Artigo antigo",
            "summary": "Descrição",
            "link": "https://techcrunch.com/antigo",
            "published": "Mon, 01 Jan 2020 00:00:00 +0000",
        }
        mock_feed = MagicMock()
        mock_feed.entries = [entry]
        mock_parse.return_value = mock_feed

        articles = self.parser.fetch("techcrunch", limit=5)
        assert len(articles) == 0

    @patch("feedparser.parse")
    def test_fetch_fonte_inexistente_retorna_lista_vazia(self, mock_parse):
        articles = self.parser.fetch("fonte_que_nao_existe", limit=5)
        assert articles == []
        mock_parse.assert_not_called()

    @patch("feedparser.parse")
    def test_fetch_erro_retorna_lista_vazia(self, mock_parse):
        mock_parse.side_effect = Exception("Erro de rede")
        articles = self.parser.fetch("techcrunch", limit=5)
        assert articles == []

    @patch("feedparser.parse")
    def test_fetch_respeita_limite(self, mock_parse):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
        entries = [
            {
                "title": f"Artigo {i}",
                "summary": "",
                "link": f"https://techcrunch.com/{i}",
                "published": now,
            }
            for i in range(20)
        ]
        mock_feed = MagicMock()
        mock_feed.entries = entries
        mock_parse.return_value = mock_feed

        articles = self.parser.fetch("techcrunch", limit=3)
        assert len(articles) == 3

    # ── Normalização ─────────────────────────────────────────────────────

    def test_normalize_campos_obrigatorios(self):
        entry = {
            "title": "Título teste",
            "summary": "Descrição teste",
            "link": "https://techcrunch.com/teste",
            "published": "Fri, 12 Sep 2026 10:00:00 +0000",
        }
        result = self.parser._normalize(entry, "techcrunch")
        assert "id" in result
        assert "title" in result
        assert "description" in result
        assert "url" in result
        assert "published_at" in result
        assert "source_name" in result
        assert "language" in result

    def test_normalize_sanitiza_xss(self):
        entry = {
            "title": "<script>alert('xss')</script>Título",
            "summary": "Descrição <b>normal</b>",
            "link": "https://techcrunch.com/teste",
            "published": "Fri, 12 Sep 2026 10:00:00 +0000",
        }
        result = self.parser._normalize(entry, "techcrunch")
        assert "<script>" not in result["title"]
        assert "</script>" not in result["title"]
        assert "<b>" not in result["description"]

    def test_normalize_source_name_uppercase(self):
        entry = {
            "title": "Título",
            "summary": "",
            "link": "https://techcrunch.com/teste",
            "published": "",
        }
        result = self.parser._normalize(entry, "techcrunch")
        assert result["source_name"] == "TECHCRUNCH"