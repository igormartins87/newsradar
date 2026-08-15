from unittest.mock import patch
from src.event_bus.event import Event
from src.event_bus.event_bus import EventBus
from src.dashboard.dashboard_service import DashboardService


class TestDashboardService:

    def setup_method(self):
        self.bus = EventBus()
        self.dashboard = DashboardService(bus=self.bus, top_n=5)

    def test_dashboard_inicializa_e_se_inscreve(self):
        assert self.dashboard.name == "DashboardService"
        assert "news.scored" in self.bus._subscribers

    def test_dashboard_top_n_configuravel(self):
        assert self.dashboard.top_n == 5

    @patch("src.dashboard.dashboard_service.console")
    def test_dashboard_renderiza_sem_erros(self, mock_console):
        self.bus.publish(Event("news.scored", {
            "source": "g1",
            "articles": [
                {"title": "Notícia teste", "url": "https://exemplo.com",
                 "score": 7.0, "matched_topics": ["python"],
                 "source_name": "G1"}
            ]
        }))
        assert mock_console.print.called

    @patch("src.dashboard.dashboard_service.console")
    def test_dashboard_exibe_mensagem_sem_noticias(self, mock_console):
        self.dashboard._render([])
        mock_console.print.assert_called()

    @patch("src.dashboard.dashboard_service.console")
    def test_dashboard_respeita_top_n(self, mock_console):
        articles = [
            {"title": f"Notícia {i}", "url": f"https://exemplo.com/{i}",
             "score": float(i), "matched_topics": [], "source_name": "G1"}
            for i in range(10)
        ]
        self.dashboard._render(articles[:self.dashboard.top_n])
        assert mock_console.print.called