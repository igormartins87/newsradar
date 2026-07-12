import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)
API_KEY = "newsradar-chave-secreta-2024"


class TestAPI:

    def test_health_check(self):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_get_news_sem_api_key_retorna_403(self):
        response = client.get("/news/")
        assert response.status_code == 403

    def test_get_news_com_api_key_invalida_retorna_403(self):
        response = client.get("/news/", headers={"X-API-Key": "chave-errada"})
        assert response.status_code == 403

    def test_get_news_fonte_invalida_retorna_404(self):
        response = client.get(
            "/news/fonte-inexistente",
            headers={"X-API-Key": API_KEY}
        )
        assert response.status_code == 404