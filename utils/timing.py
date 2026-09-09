"""Medição de tempo por etapa do pipeline de geração de relatório.

Instrumentação temporária (branch de investigação): acumula o tempo de cada
etapa num dicionário e loga um resumo. Puramente aditivo — não altera nenhum
resultado do relatório.
"""

import time
from contextlib import contextmanager


@contextmanager
def medir(acumulador: dict[str, float], etapa: str):
    inicio = time.perf_counter()
    try:
        yield
    finally:
        acumulador[etapa] = acumulador.get(etapa, 0.0) + (time.perf_counter() - inicio)


def logar_medicoes(
    acumulador: dict[str, float], contexto: str, wall: float | None = None
) -> None:
    # print (não logging.info): sob uvicorn os logs INFO da aplicação são
    # engolidos por falta de handler no root. print garante visibilidade.
    medido = sum(acumulador.values())
    etapas = " ".join(
        f"{etapa}={seg:.3f}s" for etapa, seg in sorted(acumulador.items())
    )
    # "outros" = trabalho do handler não coberto por nenhum bracket (montagem de
    # HTML, extração de docs, etc.). wall = tempo de parede do handler inteiro.
    extra = ""
    if wall is not None:
        extra = f" wall={wall:.3f}s outros={max(wall - medido, 0.0):.3f}s"
    print(
        f"[MEDICAO_TEMPO] contexto={contexto} medido={medido:.3f}s {etapas}{extra}",
        flush=True,
    )
