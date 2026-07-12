import pytest
from unittest.mock import patch, MagicMock
from src.event_bus.event_bus import EventBus
from src.fetcher.fetcher_service import FetcherService


class TestFetcherService:

    def setup_method(self):
        self.bus = EventBus()
        self.fetcher = FetcherService(
            bus=self.bus,
            api_key="test-key"
        )

    def test_fetcher_inicializa_corretamente(self):
        assert self.fetcher.name == "FetcherService"
        assert self.fetcher.api_key == "test-key"

    @patch("httpx.get")
    def test_fetch_publica_evento_news_fetched(self, mock_get):
        """Testa se o FetcherService publica o evento corretamente."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "ok",
            "articles": [
                {"title": "Notícia teste", "url": "https://exemplo.com"}
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        eventos_recebidos = []
        self.bus.subscribe("news.fetched",
                          lambda e: eventos_recebidos.append(e))

        self.fetcher.fetch(limit=5)

        assert len(eventos_recebidos) == 1
        assert eventos_recebidos[0].name == "news.fetched"
        assert len(eventos_recebidos[0].payload["articles"]) == 1

    @patch("httpx.get")
    def test_fetch_por_fonte_especifica(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"articles": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        self.fetcher.fetch(source="g1")

        call_url = mock_get.call_args[0][0]
        assert "g1" in call_url

    @patch("httpx.get")
    def test_fetch_nao_quebra_com_timeout(self, mock_get):
        import httpx
        mock_get.side_effect = httpx.TimeoutException("timeout")

        try:
            self.fetcher.fetch()
        except Exception as e:
            pytest.fail(f"FetcherService quebrou com timeout: {e}")