"""Cache em disco de relatórios prontos: frescor e limite de tamanho.

Frescor = "gerado depois da última mudança". A mudança é sinalizada por
output/.data_version, tocado pelo refresh noturno das materialized views (dado
novo) e pelo startup da app (código novo — ver invalidar_artefatos_em_disco).
Se o marcador não existe, nada foi invalidado ainda -> tudo é fresco.
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from stat import S_ISREG

from config import (
    GRAFICO_CACHE_MAX_BYTES,
    OUTPUT_DIR,
    REPORT_CACHE_MAX_BYTES,
    SENTINELA_TTL_S,
)
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


def _retrato(caminho: Path) -> os.stat_result | None:
    """stat() de um arquivo regular, ou None se ele sumiu entre o glob e esta
    chamada.

    TOCTOU: toda função aqui lista primeiro e lê depois, e entre as duas coisas
    o diretório é território compartilhado — o DELETE de /relatorios
    (main.py:181 é `def`, não `async def`, então o FastAPI o roda num threadpool
    realmente paralelo ao handler de geração) e outra geração concorrente apagam
    artefatos debaixo desta varredura.

    O retrato é tirado UMA vez e reusado pra ordenar, orçar e debitar. Reperguntar
    o mesmo stat a cada passo não só custa syscall: deixava o `total` e o
    `removidos` errados, porque cada pergunta podia ser respondida por um estado
    diferente do disco.

    TODO: services/handlers.py tem três pontos da mesma classe, todos anteriores
    a este PR e no caminho dos endpoints públicos — `entrada.stat()` (:58), o
    `exists()`-então-`stat()` do listar (:63-64) e o `exists()`-então-`unlink()`
    do apagar (:150-151). Ficaram de fora de propósito: são bug pré-existente no
    main, não regressão deste cache, e corrigi-los aqui faria o PR dizer que
    consertou algo que não introduziu. Branch própria, a partir do main.
    """
    try:
        st = caminho.stat()
    except FileNotFoundError:
        return None
    return st if S_ISREG(st.st_mode) else None


def _relatorios_por_idade() -> list[Path]:
    """PDFs de relatório, do mais antigo pro mais novo (mtime do PDF). O que sumiu
    entre o glob e o stat fica de fora da lista, em vez de entrar com um mtime
    sentinela e depois ser contabilizado como apagado por nós."""
    entradas: list[tuple[float, Path]] = []
    for pdf in OUTPUT_DIR.glob("relatorio_*.pdf"):
        st = _retrato(pdf)
        if st is not None:
            entradas.append((st.st_mtime, pdf))
    entradas.sort(key=lambda item: item[0])
    return [pdf for _, pdf in entradas]


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
        apagou_algo = False
        for art in _artefatos_unicos_do_relatorio(pdf.stem):
            st = _retrato(art)
            if st is None:
                continue
            # Debita sempre: o espaço sai do orçamento tendo sido esta eviction ou
            # outra request a liberá-lo. Creditar em `removidos`, só o que de fato
            # apagamos — senão a lista afirma uma remoção que não foi nossa.
            total -= st.st_size
            try:
                art.unlink()
            except FileNotFoundError:
                continue
            apagou_algo = True
        if apagou_algo:
            removidos.append(pdf.name)
    return removidos


def _sentinela(safe_report: str) -> Path:
    return OUTPUT_DIR / f"relatorio_{safe_report}.inflight"


def _viva(caminho: Path) -> bool:
    try:
        return (time.time() - caminho.stat().st_mtime) < SENTINELA_TTL_S
    except FileNotFoundError:
        return False


def adquirir_geracao(safe_report: str) -> bool:
    """True se esta chamada ganhou o direito de gerar `safe_report`.

    O registro é um arquivo em disco, e não um lock em memória, porque com
    `--workers N` quem precisa enxergar a geração em curso é outro processo.
    Uma sentinela mais velha que SENTINELA_TTL_S é de uma geração que morreu:
    ela é removida e o direito passa a quem chegou. Estourar o TTL com a geração
    ainda viva custa uma geração duplicada, nunca um artefato corrompido — as
    escritas são atômicas (services/pdf.py, generation.py).
    """
    sentinela = _sentinela(safe_report)
    for _ in range(3):
        try:
            # O conteúdo (pid de quem criou) é o que permite a liberar_geracao
            # discriminar depois "essa sentinela ainda é minha?" — ver docstring lá.
            fd = os.open(sentinela, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return True
        except FileExistsError:
            if _viva(sentinela):
                return False
            try:
                sentinela.unlink()
            except FileNotFoundError:
                pass
    return False


def liberar_geracao(safe_report: str) -> None:
    """Devolve o direito de gerar `safe_report` — mas só se a sentinela em disco
    ainda for a que este processo criou.

    Sem essa checagem de dono, um estouro de TTL vira cascata em vez do único
    duplicado que o design aceita: A demora mais que SENTINELA_TTL_S, B vê a
    sentinela como morta e reclama (a corrida aceita — 1 duplicata), mas quando A
    finalmente termina e chama liberar_geracao, ela apagaria a sentinela NOVA de
    B (unlink incondicional, sem checar dono). C chega, O_EXCL abre livre, e é uma
    terceira geração concorrente do mesmo relatório — e entre a apagada e a de C,
    geracoes_em_voo() subconta o trabalho de A, que ainda está rodando. Comparar o
    pid gravado no arquivo mantém a decisão inteiramente em disco (task 11 garante
    uma geração por processo, então pid basta pra discriminar).

    Idempotente: arquivo já ausente, ou pertencente a outro dono (reclamado
    enquanto este processo ainda segurava a referência antiga), não é erro —
    apenas não há nada para este processo liberar.
    """
    sentinela = _sentinela(safe_report)
    try:
        dono = sentinela.read_bytes()
    except FileNotFoundError:
        return
    if dono != str(os.getpid()).encode():
        return  # a sentinela atual é de outro dono; não é nossa para apagar
    try:
        sentinela.unlink()
    except FileNotFoundError:
        pass


def geracoes_em_voo() -> int:
    """Quantas gerações de fundo estão em curso agora, no container inteiro
    (a sentinela é visível entre workers). Usado para respeitar o teto
    MAX_GERACOES_EM_VOO."""
    return sum(1 for s in OUTPUT_DIR.glob("*.inflight") if _viva(s))


def limpar_tmp_orfaos() -> list[str]:
    """Apaga os .tmp e .inflight deixados por um render morto no meio. Roda no
    startup do container (scripts/startup_container.py, uma vez, antes de o
    uvicorn subir): nenhum .tmp ou .inflight pode estar em uso ainda.

    Os .tmp existem porque a escrita atômica passou a usar mkstemp (nome único por
    escritor, pra dois writers concorrentes não intercalarem bytes no mesmo
    arquivo). Com o nome fixo de antes, o render seguinte sobrescrevia o resíduo;
    com nome aleatório, ele fica — e não casa nenhum dos globs de eviction
    (`relatorio_*.pdf`, `grafico_*.png`), então era a única categoria de artefato
    sem teto de disco."""
    removidos: list[str] = []
    for padrao in ("*.tmp", "*.inflight"):
        for tmp in OUTPUT_DIR.glob(padrao):
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
    # (mtime, tamanho, caminho) num retrato só por arquivo — antes eram tres stats
    # independentes (ordenar, somar, subtrair), cada um podendo pegar o disco num
    # estado diferente.
    graficos: list[tuple[float, int, Path]] = []
    for png in OUTPUT_DIR.glob("grafico_*.png"):
        st = _retrato(png)
        if st is not None:
            graficos.append((st.st_mtime, st.st_size, png))
    graficos.sort(key=lambda item: item[0])

    total = sum(tamanho for _, tamanho, _ in graficos)
    removidos: list[str] = []
    for _, tamanho, png in graficos:
        if total <= GRAFICO_CACHE_MAX_BYTES:
            break
        total -= tamanho
        try:
            png.unlink()
        except FileNotFoundError:
            continue  # outra request chegou primeiro: o espaço conta, o crédito não
        removidos.append(png.name)
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
