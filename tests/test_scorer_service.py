from src.event_bus.event import Event
from src.event_bus.event_bus import EventBus
from src.score.scorer_service import ScorerService


class TestScorerService:

    def setup_method(self):
        self.bus = EventBus()
        self.scorer = ScorerService(bus=self.bus, topics=["python", "concurso"])

    def test_scorer_inicializa_e_se_inscreve(self):
        assert self.scorer.name == "ScorerService"
        assert "news.parsed" in self.bus._subscribers

    def test_scorer_publica_news_scored(self):
        eventos_recebidos = []
        self.bus.subscribe("news.scored", lambda e: eventos_recebidos.append(e))

        self.bus.publish(Event("news.parsed", {
            "source": "g1",
            "articles": [
                {"title": "Python é tendência", "description": "",
                 "url": "https://exemplo.com", "keywords": ["python"]}
            ]
        }))

        assert len(eventos_recebidos) == 1
        assert eventos_recebidos[0].name == "news.scored"

    def test_scorer_calcula_score_com_topico_encontrado(self):
        score, matched = self.scorer._calculate_score({
            "title": "Novo concurso público aberto",
            "description": "",
            "keywords": ["concurso"]
        })
        assert score > 0
        assert "concurso" in matched

    def test_scorer_score_zero_sem_topicos(self):
        score, matched = self.scorer._calculate_score({
            "title": "Notícia sem relevância",
            "description": "",
            "keywords": []
        })
        assert matched == []

    def test_scorer_ordena_por_score(self):
        eventos_recebidos = []
        self.bus.subscribe("news.scored", lambda e: eventos_recebidos.append(e))

        self.bus.publish(Event("news.parsed", {
            "source": "g1",
            "articles": [
                {"title": "Notícia irrelevante", "description": "",
                 "url": "https://exemplo.com/1", "keywords": []},
                {"title": "Concurso python aberto", "description": "python",
                 "url": "https://exemplo.com/2", "keywords": ["python", "concurso"]},
            ]
        }))

        articles = eventos_recebidos[0].payload["articles"]
        assert articles[0]["score"] >= articles[1]["score"]