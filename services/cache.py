"""Cache em disco de relatórios prontos: frescor e limite de tamanho.

Frescor = "gerado depois da última mudança". A mudança é sinalizada por
output/.data_version, tocado pelo refresh noturno das materialized views (dado
novo) e pelo startup da app (código novo — ver invalidar_artefatos_em_disco).
Se o marcador não existe, nada foi invalidado ainda -> tudo é fresco.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

from config import GRAFICO_CACHE_MAX_BYTES, OUTPUT_DIR, REPORT_CACHE_MAX_BYTES
from utils.queries.base import limpar_cache_queries

DATA_VERSION_FILE = OUTPUT_DIR / ".data_version"


def _data_version_mtime() -> float:
    try:
        return DATA_VERSION_FILE.stat().st_mtime
    except FileNotFoundError:
        return 0.0  # sem marcador = dado nunca invalidado


def artefato_fresco(caminho: Path, ttl_s: float | None = None) -> bool:
    """True se o arquivo existe e foi gerado depois da última mudança de dado.

    Com `ttl_s`, exige também que o arquivo tenha menos que esse tempo de vida.
    O marcador é invalidação por evento: precisa, mas só enxerga o que alguém
    lembrou de instrumentar (hoje, só o refresh das matviews). O TTL é
    invalidação por tempo: imprecisa, mas cobre toda entrada que o marcador não
    observa — o Doc editorial, os shapefiles, um PNG trocado à mão. Um é rede de
    segurança do outro, não substituto: as duas condições valem juntas.

    Sem `ttl_s` (default) só o marcador conta — é o caso dos gráficos, cujos
    dados vêm todos do banco e portanto já estão cobertos por ele.
    """
    try:
        mtime = caminho.stat().st_mtime
    except FileNotFoundError:
        return False
    if mtime <= _data_version_mtime():
        return False
    return ttl_s is None or (time.time() - mtime) < ttl_s


def invalidar_artefatos_em_disco() -> None:
    """Move a marca d'água para agora: tudo que está em disco passa a ser mais
    velho que ela e regenera sob demanda. Não apaga nada.

    Chamado no startup (main.py) porque o container só é recriado em deploy ou
    reboot, e código novo invalida artefato tanto quanto dado novo: o PNG de
    gráfico é função de (dados, código que desenha), e o marcador — tocado só
    pelo refresh noturno das matviews — enxerga apenas a primeira metade. Sem
    isto, um fix em plotting/ ficaria invisível atrás do reuso de
    plotting.reusar_grafico até o próximo refresh (PR #130).
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_VERSION_FILE.touch()


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


def limpar_tmp_orfaos() -> list[str]:
    """Apaga os .tmp deixados por um render morto no meio. Roda só no startup:
    nenhum .tmp está em uso antes de a app aceitar request.

    Existem porque a escrita atômica passou a usar mkstemp (nome único por
    escritor, pra dois writers concorrentes não intercalarem bytes no mesmo
    arquivo). Com o nome fixo de antes, o render seguinte sobrescrevia o resíduo;
    com nome aleatório, ele fica — e não casa nenhum dos globs de eviction
    (`relatorio_*.pdf`, `grafico_*.png`), então era a única categoria de artefato
    sem teto de disco."""
    removidos: list[str] = []
    for tmp in OUTPUT_DIR.glob("*.tmp"):
        try:
            tmp.unlink()
            removidos.append(tmp.name)
        except FileNotFoundError:
            pass
    return removidos


def evict_graficos_if_needed() -> list[str]:
    """Apaga gráficos mais antigos até o pool caber no teto. FIFO por mtime, igual
    ao evict_cache_if_needed acima (nunca toca mtime no acesso, mesmo motivo de
    frescor). Sem dono único (compartilhados por cidade), então não dá pra
    proteger um "protegido" específico como no eviction de relatório.

    ponytail: FIFO, não referência-contada. Os gráficos mais antigos tendem a
    pertencer aos relatórios mais antigos (já evictados antes deste). Um gráfico
    ainda referenciado por um relatório fresco pode, em tese, ser apagado aqui —
    mas o PDF já embute suas imagens (não é afetado) e o entregável principal é o
    PDF baixado, não o HTML servido depois; reconstituir o PNG sob demanda no
    próximo combo é aceitável. Sem contagem de referência por ora."""
    graficos = sorted(
        (p for p in OUTPUT_DIR.glob("grafico_*.png") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
    )
    total = 0
    for g in graficos:
        try:
            total += g.stat().st_size
        except FileNotFoundError:
            pass
    removidos: list[str] = []
    for g in graficos:
        if total <= GRAFICO_CACHE_MAX_BYTES:
            break
        try:
            total -= g.stat().st_size
            g.unlink()
        except FileNotFoundError:
            pass
        removidos.append(g.name)
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
