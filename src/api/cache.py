import time
from typing import Any


class InMemoryCache:
    """
    Cache em memória com TTL (Time To Live).

    Armazena resultados de operações custosas por um
    período configurável, evitando chamadas repetidas
    ao RSS e ao ScorerService.

    Atributos:
        ttl: tempo em segundos que o cache é válido
        _store: dicionário interno com os dados e timestamp
    """

    def __init__(self, ttl: int = 1800) -> None:
        """
        Args:
            ttl: tempo de vida do cache em segundos (padrão 30 min)
        """
        self.ttl = ttl
        self._store: dict[str, dict] = {}

    def get(self, key: str) -> Any | None:
        """
        Busca um valor no cache.

        Args:
            key: chave do cache

        Returns:
            Valor armazenado ou None se expirado/inexistente
        """
        entry = self._store.get(key)
        if not entry:
            return None

        if time.time() - entry["timestamp"] > self.ttl:
            del self._store[key]
            print(f"[Cache] '{key}' expirado e removido.")
            return None

        print(f"[Cache] HIT — '{key}'")
        return entry["value"]

    def set(self, key: str, value: Any) -> None:
        """
        Armazena um valor no cache.

        Args:
            key: chave do cache
            value: valor a ser armazenado
        """
        self._store[key] = {
            "value": value,
            "timestamp": time.time(),
        }
        print(f"[Cache] SET — '{key}' armazenado por {self.ttl}s")

    def invalidate(self, key: str) -> None:
        """Remove uma entrada do cache manualmente."""
        if key in self._store:
            del self._store[key]
            print(f"[Cache] '{key}' invalidado.")

    def clear(self) -> None:
        """Limpa todo o cache."""
        self._store.clear()
        print("[Cache] Cache limpo.")

    def info(self) -> dict:
        """
        Retorna informações sobre o estado do cache.

        Returns:
            Dicionário com chaves ativas e TTL configurado
        """
        now = time.time()
        active = {
            k: round(self.ttl - (now - v["timestamp"]), 1)
            for k, v in self._store.items()
            if now - v["timestamp"] <= self.ttl
        }
        return {
            "ttl_configured": self.ttl,
            "active_keys": active,
            "total": len(active),
        }