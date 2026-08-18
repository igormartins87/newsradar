from unittest.mock import patch
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.security import validate_api_key

client = TestClient(app)


def auth_ok():
    """Mock que simula autenticação válida."""
    return "valid-key"


class TestAPI:

    def test_health_check(self):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_get_news_sem_api_key_retorna_403(self):
        response = client.get("/news/")
        assert response.status_code == 403

    def test_get_news_com_api_key_invalida_retorna_403(self):
        response = client.get(
            "/news/",
            headers={"X-API-Key": "chave-errada"}
        )
        assert response.status_code == 403

    @patch("src.api.routers.news.rss")
    def test_get_news_fonte_invalida_retorna_404(self, mock_rss):
        app.dependency_overrides[validate_api_key] = auth_ok
        response = client.get(
            "/news/fonte-inexistente",
            headers={"X-API-Key": "any-key"}
        )
        app.dependency_overrides.clear()
        assert response.status_code == 404