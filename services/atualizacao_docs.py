"""Confere e atualiza os Docs editoriais no cache em disco (output/docs_cache/).

O relatório lê a prosa do disco, não do Google (utils/external/docs.py). Este módulo
baixa cada Doc, confere e só grava o que passou. Doc com problema ou que falhou no
download mantém a cópia anterior: o relatório sai com a prosa de ontem, mas não com
um parágrafo sumido ou uma regra escrita no meio do texto.

INTENTIONAL: a mesma regra vale para o cron (scripts/atualizar_docs.py) e para o
botão "Atualizar relatórios" do Data Nordeste (POST /docs/atualizar), decidido em
24/11/2026. Se só o botão conferisse, o cron gravaria o Doc com problema de
madrugada e desfaria a proteção. Até então o cron gravava tudo e só avisava no log.

A conferência é a rápida (milissegundos por Doc, só olha o texto do Doc):
- conferir_condicoes: regra "Para quando ...:" que o gerador lê diferente do escrito;
- condicoes_no_resumo: regra escrita no resumo do tema, que sai crua no relatório.
A conferência completa, município a município, continua no Laboratório de Temas.
"""

import asyncio
import fcntl
import hmac
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from config import (
    CARACTERISTICAS_AREA_DOCS_URL,
    CARACTERISTICAS_DOCS_URL,
    CARACTERISTICAS_ESTADO_DOCS_URL,
    OUTPUT_DIR,
)
from services.macrotemas import docs_url
from utils.data.macrotemas import MACROTEMAS
from utils.external.docs import baixar_doc, extrair_resumo_tema, salvar_doc_no_cache
from utils.queries.area import AREAS_DO_TEMA_DE_TEXTO_FIXO, MATVIEW_AREA_POR_MACROTEMA
from utils.queries.estado import MATVIEW_ESTADUAL_POR_MACROTEMA
from utils.render.placeholders import condicoes_no_resumo, conferir_condicoes

# Um arquivo, e não um lock em memória: o gamma roda 3 workers do uvicorn, e o cron
# roda em outro processo. Só serializa quem grava; a leitura do relatório não espera.
TRAVA_DA_ATUALIZACAO = OUTPUT_DIR / ".atualizar_docs.lock"

EstadoDoDoc = Literal["atualizado", "com_problema", "falhou"]
Baixador = Callable[[str], Awaitable[str]]
Gravador = Callable[[str, str], None]


@dataclass(frozen=True)
class ResultadoDoDoc:
    """O que aconteceu com um Doc numa rodada. `avisos` explica o "com_problema" e o
    "falhou"; vai inteiro para a tela do botão e para o log do cron."""

    rotulo: str
    estado: EstadoDoDoc
    avisos: list[str] = field(default_factory=list)
    caracteres: int = 0


class AtualizacaoEmAndamento(RuntimeError):
    """Outra rodada (botão ou cron) está gravando o cache agora."""


def docs_configurados() -> list[tuple[str, str]]:
    """(rótulo, url) de todo Doc que o relatório pode pedir. Macrotema sem
    docs_url no .env é pulado — é o mesmo tratamento de services/generation.py,
    que apenas loga e segue."""
    docs = [
        (slug, dados["docs_url"])
        for slug, dados in MACROTEMAS.items()
        if dados["docs_url"]
    ]
    # Os Docs estaduais (relatório por estado, 05/11/2026). Sem eles aqui, o primeiro
    # relatório de um estado baixava o Doc e ele ficava congelado no cache para sempre.
    docs.extend(
        (f"{slug} (estado)", url)
        for slug in MATVIEW_ESTADUAL_POR_MACROTEMA
        if (url := docs_url(slug, "estado"))
    )
    # Os Docs de área (Nordeste, Caatinga…), 16/11/2026: sem eles aqui, o Doc de área
    # ficava congelado no cache e a correção das Fontes no Google não aparecia. Os
    # temas de texto fixo não têm matview de área, mas têm Doc de área.
    docs.extend(
        (f"{slug} (área)", url)
        for slug in (*MATVIEW_AREA_POR_MACROTEMA, *AREAS_DO_TEMA_DE_TEXTO_FIXO)
        if (url := docs_url(slug, "area"))
    )
    if CARACTERISTICAS_DOCS_URL:
        docs.append(("caracteristicas", CARACTERISTICAS_DOCS_URL))
    if CARACTERISTICAS_ESTADO_DOCS_URL:
        docs.append(("caracteristicas (estado)", CARACTERISTICAS_ESTADO_DOCS_URL))
    if CARACTERISTICAS_AREA_DOCS_URL:
        docs.append(("caracteristicas (área)", CARACTERISTICAS_AREA_DOCS_URL))
    return docs


def problemas_do_doc(texto: str) -> list[str]:
    """Avisos da conferência rápida de um Doc já baixado; lista vazia = pode gravar.

    Ex.: problemas_do_doc(await baixar_doc(url)) == []
    """
    resumo, _ = extrair_resumo_tema(texto)
    no_resumo = [
        f"{regra}\n    → regra no resumo do tema: sai escrita no relatório"
        for regra in condicoes_no_resumo(resumo)
    ]
    return conferir_condicoes(texto) + no_resumo


def token_de_docs_valido(recebido: str | None, esperado: str | None) -> bool:
    """Confere o token do POST /docs/atualizar. Sem token configurado, a rota fica
    desligada (False sempre). compare_digest em bytes: tempo constante, e não levanta
    com caractere fora do ASCII no header.

    Ex.: token_de_docs_valido(request.headers.get("x-docs-token"), DOCS_ATUALIZAR_TOKEN)
    """
    if not recebido or not esperado:
        return False
    return hmac.compare_digest(recebido.encode(), esperado.encode())


@contextmanager
def _uma_rodada_por_vez(trava: Path) -> Iterator[None]:
    trava.parent.mkdir(parents=True, exist_ok=True)
    with open(trava, "w") as arquivo:
        try:
            fcntl.flock(arquivo, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as err:
            raise AtualizacaoEmAndamento(
                f"Outra atualização dos Docs está em andamento (trava {trava}); "
                "espere alguns segundos e tente de novo."
            ) from err
        yield  # o flock sai junto com o close do arquivo


def _conferir_e_gravar(
    rotulo: str, url: str, baixado: str | BaseException, gravar: Gravador
) -> ResultadoDoDoc:
    if isinstance(baixado, BaseException):
        return ResultadoDoDoc(rotulo, "falhou", [f"download: {baixado}"])
    avisos = problemas_do_doc(baixado)
    if avisos:
        return ResultadoDoDoc(rotulo, "com_problema", avisos, len(baixado))
    try:
        gravar(url, baixado)
    except OSError as err:
        return ResultadoDoDoc(rotulo, "falhou", [f"gravação no cache: {err}"], len(baixado))
    return ResultadoDoDoc(rotulo, "atualizado", [], len(baixado))


async def conferir_e_atualizar(
    docs: list[tuple[str, str]],
    baixar: Baixador = baixar_doc,
    gravar: Gravador = salvar_doc_no_cache,
    trava: Path = TRAVA_DA_ATUALIZACAO,
) -> list[ResultadoDoDoc]:
    """Baixa todos os Docs, confere cada um e grava só os que passaram. Grava o
    mesmo texto que foi conferido: rebaixar depois abriria espaço para uma edição
    no meio do caminho entrar sem conferência.

    Ex.: resultados = await conferir_e_atualizar(docs_configurados())
    """
    with _uma_rodada_por_vez(trava):
        # Em paralelo: são ~28 esperas de rede independentes. Sequencial mede ~15,7s
        # para 9 Docs, com gather ~1,1s. return_exceptions pra um Doc quebrado não
        # abortar os outros — cada um tem seu próprio cache e seu próprio dono.
        baixados = await asyncio.gather(
            *(baixar(url) for _, url in docs), return_exceptions=True
        )
        return [
            _conferir_e_gravar(rotulo, url, baixado, gravar)
            for (rotulo, url), baixado in zip(docs, baixados, strict=True)
        ]
