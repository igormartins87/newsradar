from src.event_bus.event import Event
from src.event_bus.event_bus import EventBus
from src.notifier.notifier_service import NotifierService


class TestNotifierService:

    def setup_method(self):
        self.bus = EventBus()
        self.notifier = NotifierService(bus=self.bus, threshold=6.0)

    def test_notifier_inicializa_e_se_inscreve(self):
        assert self.notifier.name == "NotifierService"
        assert "news.scored" in self.bus._subscribers

    def test_notifier_publica_alerta_para_score_alto(self):
        alertas = []
        self.bus.subscribe("news.alert", lambda e: alertas.append(e))

        self.bus.publish(Event("news.scored", {
            "source": "g1",
            "articles": [
                {"title": "Concurso aberto", "url": "https://exemplo.com",
                 "score": 7.0, "matched_topics": ["concurso"]}
            ]
        }))

        assert len(alertas) == 1
        assert alertas[0].name == "news.alert"

    def test_notifier_nao_alerta_para_score_baixo(self):
        alertas = []
        self.bus.subscribe("news.alert", lambda e: alertas.append(e))

        self.bus.publish(Event("news.scored", {
            "source": "g1",
            "articles": [
                {"title": "Notícia irrelevante", "url": "https://exemplo.com",
                 "score": 2.0, "matched_topics": []}
            ]
        }))

        assert len(alertas) == 0

    def test_notifier_nivel_high_para_score_acima_de_8(self):
        self.bus.publish(Event("news.scored", {
            "source": "g1",
            "articles": [
                {"title": "Python concurso", "url": "https://exemplo.com",
                 "score": 9.0, "matched_topics": ["python"]}
            ]
        }))

        assert self.notifier.alerts_sent[0]["alert_level"] == "high"

    def test_notifier_nivel_medium_para_score_entre_6_e_8(self):
        self.bus.publish(Event("news.scored", {
            "source": "g1",
            "articles": [
                {"title": "Tecnologia avança", "url": "https://exemplo.com",
                 "score": 7.0, "matched_topics": ["tecnologia"]}
            ]
        }))

        assert self.notifier.alerts_sent[0]["alert_level"] == "medium"

    def test_notifier_get_alerts_retorna_lista(self):
        self.bus.publish(Event("news.scored", {
            "source": "g1",
            "articles": [
                {"title": "Concurso IBGE", "url": "https://exemplo.com",
                 "score": 8.5, "matched_topics": ["concurso"]}
            ]
        }))

        alerts = self.notifier.get_alerts()
        assert len(alerts) == 1
        assert alerts[0]["article"]["score"] == 8.5