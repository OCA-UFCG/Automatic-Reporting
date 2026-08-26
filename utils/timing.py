import logging
import time

logger = logging.getLogger(__name__)


class StageTimer:
    """Mede o tempo decorrido entre marcas sucessivas de um pipeline sequencial.

    Cada chamada a ``mark`` registra quanto tempo passou desde a marca
    anterior (ou desde a criação do timer, na primeira chamada) e loga
    imediatamente, para que o tempo de cada etapa apareça mesmo se o
    pipeline falhar antes do fim.
    """

    def __init__(self, request_id: str):
        self.request_id = request_id
        self._inicio = time.perf_counter()
        self._ultima_marca = self._inicio
        self.marcas: list[tuple[str, float]] = []

    def mark(self, label: str) -> float:
        agora = time.perf_counter()
        duracao = agora - self._ultima_marca
        self._ultima_marca = agora
        self.marcas.append((label, duracao))
        logger.info("[timing][%s] %s: %.3fs", self.request_id, label, duracao)
        return duracao

    def resumo(self) -> str:
        total = time.perf_counter() - self._inicio
        detalhe = "; ".join(f"{label}={duracao:.3f}s" for label, duracao in self.marcas)
        return f"total={total:.3f}s | {detalhe}"
