from src.event_bus.event import Event
from src.event_bus.event_bus import EventBus
from src.parser.parser_service import ParserService


class TestParserService:

    def setup_method(self):
        self.bus = EventBus()
        self.parser = ParserService(bus=self.bus)

    def test_parser_inicializa_e_se_inscreve(self):
        assert self.parser.name == "ParserService"
        assert "news.fetched" in self.bus._subscribers

    def test_parser_publica_news_parsed(self):
        eventos_recebidos = []
        self.bus.subscribe("news.parsed",
                           lambda e: eventos_recebidos.append(e))

        self.bus.publish(Event("news.fetched", {
            "source": "g1",
            "articles": [
                {"title": "Notícia teste", "url": "https://exemplo.com",
                 "description": "Desc", "published_at": "", "source_name": "G1"}
            ]
        }))

        assert len(eventos_recebidos) == 1
        assert eventos_recebidos[0].name == "news.parsed"

    def test_parser_remove_duplicatas(self):
        eventos_recebidos = []
        self.bus.subscribe("news.parsed",
                           lambda e: eventos_recebidos.append(e))

        self.bus.publish(Event("news.fetched", {
            "source": "g1",
            "articles": [
                {"title": "Notícia A", "url": "https://exemplo.com/a",
                 "description": "", "published_at": "", "source_name": "G1"},
                {"title": "Notícia A", "url": "https://exemplo.com/a",
                 "description": "", "published_at": "", "source_name": "G1"},
            ]
        }))

        articles = eventos_recebidos[0].payload["articles"]
        assert len(articles) == 1

    def test_parser_remove_artigos_sem_titulo(self):
        eventos_recebidos = []
        self.bus.subscribe("news.parsed",
                           lambda e: eventos_recebidos.append(e))

        self.bus.publish(Event("news.fetched", {
            "source": "g1",
            "articles": [
                {"title": "", "url": "https://exemplo.com/a",
                 "description": "", "published_at": "", "source_name": "G1"},
            ]
        }))

        articles = eventos_recebidos[0].payload["articles"]
        assert len(articles) == 0

    def test_parser_extrai_keywords(self):
        keywords = self.parser._extract_keywords(
            "OpenAI lança modelo inteligência artificial"
        )
        assert "openai" in keywords
        assert "modelo" in keywords
        assert "lança" in keywords