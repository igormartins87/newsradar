import time
from src.api.cache import InMemoryCache


class TestInMemoryCache:

    def setup_method(self):
        self.cache = InMemoryCache(ttl=2)  # 2 segundos para testes

    def test_cache_retorna_none_quando_vazio(self):
        assert self.cache.get("chave_inexistente") is None

    def test_cache_armazena_e_recupera_valor(self):
        self.cache.set("noticias", [{"title": "Teste"}])
        result = self.cache.get("noticias")
        assert result == [{"title": "Teste"}]

    def test_cache_expira_apos_ttl(self):
        self.cache.set("noticias", [{"title": "Teste"}])
        time.sleep(3)  # espera expirar
        assert self.cache.get("noticias") is None

    def test_cache_invalidate_remove_chave(self):
        self.cache.set("noticias", [{"title": "Teste"}])
        self.cache.invalidate("noticias")
        assert self.cache.get("noticias") is None

    def test_cache_clear_limpa_tudo(self):
        self.cache.set("a", [1])
        self.cache.set("b", [2])
        self.cache.clear()
        assert self.cache.get("a") is None
        assert self.cache.get("b") is None

    def test_cache_info_retorna_chaves_ativas(self):
        self.cache.set("noticias", [{"title": "Teste"}])
        info = self.cache.info()
        assert info["total"] == 1
        assert "noticias" in info["active_keys"]