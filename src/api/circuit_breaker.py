import time
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"       # funcionando normalmente
    OPEN = "open"           # bloqueado após falhas
    HALF_OPEN = "half_open" # testando se voltou


class CircuitBreaker:
    """
    Implementa o padrão Circuit Breaker para fontes RSS.

    Estados:
    - CLOSED: fonte funcionando, chamadas normais
    - OPEN: fonte falhou N vezes, chamadas bloqueadas
    - HALF_OPEN: testando se a fonte voltou

    Isso evita que uma fonte com problema
    trave ou degrade o sistema inteiro.
    """

    def __init__(
        self,
        source: str,
        failure_threshold: int = 3,
        recovery_timeout: int = 300,
    ) -> None:
        """
        Args:
            source: nome da fonte RSS
            failure_threshold: falhas consecutivas para abrir o circuit
            recovery_timeout: segundos até tentar novamente (padrão 5 min)
        """
        self.source = source
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.success_count = 0

    def call(self, func, *args, **kwargs):
        """
        Executa a função protegida pelo circuit breaker.

        Args:
            func: função a executar
            *args, **kwargs: argumentos da função

        Returns:
            Resultado da função ou [] se circuit aberto
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info(f"[CircuitBreaker] '{self.source}' → HALF_OPEN")
            else:
                logger.warning(f"[CircuitBreaker] '{self.source}' OPEN — ignorando chamada")
                return []

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            return []

    def _on_success(self) -> None:
        self.failure_count = 0
        self.success_count += 1
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info(f"[CircuitBreaker] '{self.source}' → CLOSED (recuperado)")

    def _on_failure(self, error: Exception) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        logger.error(f"[CircuitBreaker] '{self.source}' falhou ({self.failure_count}x): {error}")

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"[CircuitBreaker] '{self.source}' → OPEN "
                f"(recovery em {self.recovery_timeout}s)"
            )

    def _should_attempt_reset(self) -> bool:
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout

    def get_status(self) -> dict:
        """Retorna o status atual do circuit breaker."""
        return {
            "source": self.source,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure": self.last_failure_time,
        }