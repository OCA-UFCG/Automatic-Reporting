"""Cache em disco de relatórios prontos: frescor e limite de tamanho.

Frescor = "gerado depois da última mudança de dado". A mudança é sinalizada
por output/.data_version, tocado pelo refresh noturno das materialized views.
Se o marcador não existe, nada foi invalidado ainda -> tudo é fresco.
"""

from __future__ import annotations

import threading
from pathlib import Path

from config import OUTPUT_DIR, REPORT_CACHE_MAX_BYTES
from utils.queries.base import limpar_cache_queries

DATA_VERSION_FILE = OUTPUT_DIR / ".data_version"


def _data_version_mtime() -> float:
    try:
        return DATA_VERSION_FILE.stat().st_mtime
    except FileNotFoundError:
        return 0.0  # sem marcador = dado nunca invalidado


def artefato_fresco(caminho: Path) -> bool:
    """True se o arquivo existe e foi gerado depois da última mudança de dado."""
    try:
        return caminho.stat().st_mtime > _data_version_mtime()
    except FileNotFoundError:
        return False


def _relatorios_por_idade() -> list[Path]:
    """PDFs de relatório, do mais antigo pro mais novo (mtime do PDF)."""
    pdfs = [
        p for p in OUTPUT_DIR.glob("relatorio_*.pdf") if p.is_file()
    ]
    return sorted(pdfs, key=lambda p: p.stat().st_mtime)


def _artefatos_unicos_do_relatorio(nome_base: str) -> list[Path]:
    """Artefatos EXCLUSIVOS de um safe_report: o pdf, o html e o mapa da região.
    Os gráficos (grafico_*_<cidade>.png) NÃO entram: desde a D6 eles são chaveados
    por cidade e compartilhados entre todos os combos daquela cidade — apagá-los na
    eviction corromperia o HTML de outros relatórios frescos que os reusam. Eles
    formam um pool separado, retido pra reuso, fora deste teto de disco.
    (Distinto de handlers._artefatos_do_relatorio, que ainda varre os gráficos por
    cidade porque o DELETE manual apaga o relatório inteiro de propósito.)"""
    sufixo = nome_base.replace("relatorio_", "", 1)
    return [
        OUTPUT_DIR / f"{nome_base}.pdf",
        OUTPUT_DIR / f"{nome_base}.html",
        OUTPUT_DIR / f"mapa_regiao_{sufixo}.png",
    ]


def _tamanho_cache(pdfs: list[Path]) -> int:
    total = 0
    for pdf in pdfs:
        for art in _artefatos_unicos_do_relatorio(pdf.stem):
            try:
                total += art.stat().st_size
            except FileNotFoundError:
                pass
    return total


def evict_cache_if_needed(protegido: str | None = None) -> list[str]:
    """Apaga relatórios mais antigos até o cache caber no teto. FIFO por mtime
    (nunca toca mtime no acesso, pra não colidir com o frescor). Seguro: o que
    for evictado só regenera sob demanda."""
    pdfs = _relatorios_por_idade()
    total = _tamanho_cache(pdfs)
    removidos: list[str] = []
    for pdf in pdfs:
        if total <= REPORT_CACHE_MAX_BYTES:
            break
        if protegido and pdf.stem == f"relatorio_{protegido}":
            continue
        for art in _artefatos_unicos_do_relatorio(pdf.stem):
            try:
                total -= art.stat().st_size
                art.unlink()
            except FileNotFoundError:
                pass
        removidos.append(pdf.name)
    return removidos


# Query cache in-process (utils/queries/base.py) tem TTL de 6h: sem isto, um relatório
# regenerado logo após o refresh das materialized views serviria número pré-refresh
# por até 6h. _ultimo_data_version guarda o mtime já visto; lock porque o handler roda
# concorrente entre requests.
_ultimo_data_version: float = 0.0
_dv_lock = threading.Lock()


def invalidar_query_cache_se_dados_mudaram() -> bool:
    """Se o .data_version avançou desde a última checagem, esvazia o cache de query
    in-process. Retorna True se limpou, False se não havia mudança."""
    global _ultimo_data_version
    atual = _data_version_mtime()
    with _dv_lock:
        if atual > _ultimo_data_version:
            _ultimo_data_version = atual
            limpar_cache_queries()
            return True
    return False
