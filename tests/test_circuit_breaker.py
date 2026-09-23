import time
from src.api.circuit_breaker import CircuitBreaker, CircuitState


class TestCircuitBreaker:

    def setup_method(self):
        self.cb = CircuitBreaker(
            source="test-source",
            failure_threshold=3,
            recovery_timeout=1,  # 1 segundo para testes
        )

    # ── Estado inicial ───────────────────────────────────────────────────

    def test_estado_inicial_fechado(self):
        assert self.cb.state == CircuitState.CLOSED
        assert self.cb.failure_count == 0
        assert self.cb.success_count == 0

    # ── Sucesso ──────────────────────────────────────────────────────────

    def test_call_sucesso_retorna_resultado(self):
        result = self.cb.call(lambda: [1, 2, 3])
        assert result == [1, 2, 3]

    def test_call_sucesso_incrementa_contador(self):
        self.cb.call(lambda: [])
        assert self.cb.success_count == 1

    def test_call_sucesso_mantem_circuit_fechado(self):
        self.cb.call(lambda: [])
        assert self.cb.state == CircuitState.CLOSED

    # ── Falha ────────────────────────────────────────────────────────────

    def test_call_falha_retorna_lista_vazia(self):
        def falha():
            raise Exception("Erro de rede")
        result = self.cb.call(falha)
        assert result == []

    def test_call_falha_incrementa_contador(self):
        def falha():
            raise Exception("Erro")
        self.cb.call(falha)
        assert self.cb.failure_count == 1

    def test_circuit_abre_apos_threshold(self):
        def falha():
            raise Exception("Erro")
        for _ in range(3):
            self.cb.call(falha)
        assert self.cb.state == CircuitState.OPEN

    def test_circuit_aberto_retorna_lista_vazia(self):
        def falha():
            raise Exception("Erro")
        for _ in range(3):
            self.cb.call(falha)

        chamou = []
        def nao_deve_chamar():
            chamou.append(True)
            return [1, 2, 3]

        result = self.cb.call(nao_deve_chamar)
        assert result == []
        assert len(chamou) == 0

    # ── Recuperação ──────────────────────────────────────────────────────

    def test_circuit_vai_para_half_open_apos_timeout(self):
        def falha():
            raise Exception("Erro")
        for _ in range(3):
            self.cb.call(falha)

        assert self.cb.state == CircuitState.OPEN
        time.sleep(1.1)

        self.cb.call(lambda: [])
        assert self.cb.state == CircuitState.CLOSED

    def test_circuit_fecha_apos_sucesso_em_half_open(self):
        def falha():
            raise Exception("Erro")
        for _ in range(3):
            self.cb.call(falha)

        time.sleep(1.1)
        self.cb.call(lambda: ["noticia"])
        assert self.cb.state == CircuitState.CLOSED
        assert self.cb.failure_count == 0

    # ── Status ───────────────────────────────────────────────────────────

    def test_get_status_retorna_campos_corretos(self):
        status = self.cb.get_status()
        assert "source" in status
        assert "state" in status
        assert "failure_count" in status
        assert "success_count" in status
        assert status["source"] == "test-source"
        assert status["state"] == "closed"