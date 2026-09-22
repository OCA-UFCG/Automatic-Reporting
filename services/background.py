"""Geração de relatório fora do event loop do worker.

O pipeline bloqueia (queries psycopg2 e matplotlib são síncronos inline), então
agendar com asyncio.create_task deixaria o worker cego para o próprio /relatorios
— o polling do portal pararia justamente enquanto os relatórios geram. Aqui a
geração roda numa thread com loop próprio; o loop do worker fica livre.

O semáforo de 1 é por processo e existe por correção, não por capacidade:
utils/render/renderer.py guarda o contador de figuras em global de módulo, então
dois relatórios no mesmo processo embaralham a numeração.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Awaitable, Callable

from services.cache import liberar_geracao

_UM_POR_PROCESSO = threading.Semaphore(1)


def agendar_geracao(fabrica: Callable[[], Awaitable[object]], safe_report: str) -> None:
    def alvo() -> None:
        with _UM_POR_PROCESSO:
            try:
                asyncio.run(fabrica())
            except Exception as err:  # noqa: BLE001 - nada acima pra tratar
                print(f"[background] geração de {safe_report} falhou: {err}")
            finally:
                liberar_geracao(safe_report)

    threading.Thread(target=alvo, name=f"geracao:{safe_report}", daemon=True).start()
