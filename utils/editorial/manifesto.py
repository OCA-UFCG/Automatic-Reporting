"""O vocabulário que o painel pode usar, publicado pelo FastAPI.

O painel é burro de propósito: ele não sabe quais campos existem, quais gráficos
estão registrados nem quais operadores valem — pergunta ao ``GET /manifesto``.
Isso inverte a dependência que hoje custa caro. O commit `61b3aab` desfez o
rename de uma coluna porque o Google Doc usava a grafia antiga; com o manifesto,
renomear uma coluna passa a quebrar a **validação no painel**, e não o PDF.

A lista de campos vem do banco quando ele está acessível e, quando não está, do
que os contratos e os documentos em cache já usam. O painel precisa abrir mesmo
com o túnel do banco fora do ar — por isso cada lista carrega sua ``origem``.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from config import CONTRATOS_DIR
from utils.data.macrotemas import MACROTEMAS
from utils.editorial.contrato import SLOT_FONTES, SLOTS_MOLDURA, TIPOS_DE_BLOCO
from utils.editorial.regras import (
    ACOES_SEM_DADO,
    OPERADORES,
    OPERADORES_DE_PRESENCA,
    ROTULOS_OPERADORES,
)

logger = logging.getLogger(__name__)

_TIPO_SQL_PARA_TIPO_CAMPO = {
    "integer": "inteiro",
    "bigint": "inteiro",
    "smallint": "inteiro",
    "numeric": "decimal",
    "double precision": "decimal",
    "real": "decimal",
    "boolean": "booleano",
    "date": "data",
}

_PLACEHOLDER = re.compile(r"(?:[A-Za-z_][\w-]*\.)?\$([A-Za-z_][\w]*)")

# O rótulo de um campo é o nome cru da coluna, sem embelezamento. Quem opera o
# painel conversa direto com quem mantém as views: precisa citar `pri_nivel_per`,
# o identificador que a outra pessoa reconhece. "Pri nivel per" não existe em
# lugar nenhum do banco e obriga uma tradução mental de volta.


def _campos_do_banco(macrotema_slug: str) -> list[dict] | None:
    """Colunas da view de perfil do macrotema, lidas do catálogo do Postgres.

    Consulta ``information_schema``, nunca a view: as ``vw_perfil_*`` são
    agregações pesadas e listar colunas não pode custar um scan.
    """
    from utils.queries.base import executar_query
    from utils.queries.perfil_municipal import VIEW_POR_MACROTEMA

    view = VIEW_POR_MACROTEMA.get(macrotema_slug)
    if not view:
        return None

    linhas = executar_query(
        """
        SELECT column_name, data_type
          FROM information_schema.columns
         WHERE table_schema = 'relatorios_auto' AND table_name = %s
         ORDER BY ordinal_position
        """,
        (view,),
        f"colunas de relatorios_auto.{view}",
        buscar_todas=True,
    )
    if not linhas:
        return None

    return [
        {
            "campo": nome,
            "rotulo": nome,
            "tipo": _TIPO_SQL_PARA_TIPO_CAMPO.get(tipo_sql, "texto"),
            "origem": f"relatorios_auto.{view}",
        }
        for nome, tipo_sql in linhas
    ]


def _campos_em_uso(macrotema_slug: str) -> list[dict]:
    """Campos que o contrato e o Doc em cache já referenciam.

    É o fallback quando o banco não responde: incompleto por construção (só
    mostra o que já é usado), mas suficiente para o painel abrir e editar.
    """
    vistos: dict[str, dict] = {}

    contrato = CONTRATOS_DIR / f"{macrotema_slug}.json"
    if contrato.exists():
        for campo in _PLACEHOLDER.findall(contrato.read_text(encoding="utf-8")):
            vistos.setdefault(
                campo,
                {
                    "campo": campo,
                    "rotulo": campo,
                    "tipo": "desconhecido",
                    "origem": "contrato publicado",
                },
            )

    docs_url = MACROTEMAS[macrotema_slug]["docs_url"]
    if docs_url:
        try:
            from utils.external.docs import _cache_path, extrair_doc_id

            caminho = _cache_path(extrair_doc_id(docs_url))
            if caminho.exists():
                texto = json.loads(caminho.read_text(encoding="utf-8"))["texto"]
                for campo in _PLACEHOLDER.findall(texto):
                    vistos.setdefault(
                        campo,
                        {
                            "campo": campo,
                            "rotulo": campo,
                            "tipo": "desconhecido",
                            "origem": "Google Doc (cache)",
                        },
                    )
        except (ValueError, KeyError, OSError, json.JSONDecodeError):
            logger.debug("Sem cache de Doc utilizável para %s", macrotema_slug)

    return sorted(vistos.values(), key=lambda c: c["campo"])


def _campos_do_csv(macrotema_slug: str) -> list[dict] | None:
    """Colunas da planilha CSV do macrotema — o mesmo fallback do relatório.

    Quando o banco não responde, o relatório não fica sem dado: cai para o CSV
    (PR #91). A paleta de variáveis precisa seguir a mesma regra, senão o editor
    vê "lista parcial" e conclui que a ferramenta está quebrada, quando na
    verdade há uma fonte inteira disponível — e é justamente a fonte de onde os
    números do relatório vão sair naquele momento.

    Lê só o cabeçalho: `nrows=0` basta para ter os nomes das colunas.
    """
    from services.csv_loader import (
        carregar_csv,
        get_csv_config_for_macrotema,
        normalizar_colunas_macrotema,
    )
    from services.macrotemas import get_macrotema

    try:
        csv_url, csv_env = get_csv_config_for_macrotema(get_macrotema(macrotema_slug))
        from config import resolve_csv_source

        df = normalizar_colunas_macrotema(
            carregar_csv(resolve_csv_source(csv_url, csv_env)), macrotema_slug
        )
    except Exception:
        # O CSV é fallback de fallback: se ele também falhar, ainda resta a
        # lista do que o contrato já usa. Não vale derrubar o painel por isso.
        logger.debug("Sem CSV utilizável para %s", macrotema_slug, exc_info=True)
        return None

    colunas = [str(c) for c in df.columns if str(c).strip()]
    if not colunas:
        return None

    return [
        {
            "campo": nome,
            "rotulo": nome,
            "tipo": "desconhecido",
            "origem": "planilha CSV",
        }
        for nome in colunas
    ]


def campos_do_macrotema(macrotema_slug: str, usar_banco: bool = True) -> dict[str, Any]:
    if usar_banco:
        do_banco = _campos_do_banco(macrotema_slug)
        if do_banco:
            return {"origem": "banco", "completo": True, "campos": do_banco}

    # Mesma ordem de fontes do relatório: view, depois CSV.
    do_csv = _campos_do_csv(macrotema_slug)
    if do_csv:
        return {
            "origem": "csv",
            "completo": True,
            "aviso": (
                "Sem conexão com o banco do Data Nordeste: a lista vem da "
                "planilha CSV, a mesma fonte que o relatório usa nessa "
                "situação. Abra o túnel SSH para ver os campos da view."
            ),
            "campos": do_csv,
        }

    return {
        "origem": "cache",
        "completo": False,
        "aviso": (
            "Banco e planilha indisponíveis: a lista traz apenas os campos que "
            "o contrato e o documento em cache já usam."
        ),
        "campos": _campos_em_uso(macrotema_slug),
    }


def graficos_do_macrotema(macrotema_slug: str) -> list[dict]:
    """Gráficos registrados para o macrotema, com a legenda que os ancora hoje."""
    from services.generation import GRAFICOS_AUTO_MARCADOR

    return [
        {
            "nome": nome,
            "rotulo": nome,
            "legenda_esperada": legenda,
        }
        for nome, legenda in GRAFICOS_AUTO_MARCADOR.get(macrotema_slug, ())
    ]


def _contrato_publicado(macrotema_slug: str) -> dict | None:
    caminho = CONTRATOS_DIR / f"{macrotema_slug}.json"
    if not caminho.exists():
        return None
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return {
        "versao": dados.get("versao"),
        "publicado_em": dados.get("publicado_em"),
        "publicado_por": dados.get("publicado_por"),
    }


def montar_manifesto(usar_banco: bool = True) -> dict[str, Any]:
    """Payload do ``GET /manifesto``."""
    from utils.external.editorial import (
        alternavel_no_painel,
        fonte_do_ambiente,
        fonte_editorial,
        variavel_de_ambiente,
    )

    macrotemas = []
    campos: dict[str, Any] = {}
    graficos: dict[str, Any] = {}

    for slug, dados in MACROTEMAS.items():
        macrotemas.append(
            {
                "slug": slug,
                "nome": dados["nome"],
                "cor": dados["cor"],
                "icone": dados["icone"],
                "fonte_editorial": fonte_editorial(slug),
                # Quem manda é o ambiente; o painel só alterna dentro do que ele
                # libera. A tela precisa dos dois para explicar por que o botão
                # está desabilitado em vez de só desabilitá-lo.
                "fonte_do_ambiente": fonte_do_ambiente(slug),
                "pode_alternar_fonte": alternavel_no_painel(slug),
                "variavel_de_ambiente": variavel_de_ambiente(slug),
                "contrato": _contrato_publicado(slug),
            }
        )
        campos[slug] = campos_do_macrotema(slug, usar_banco=usar_banco)
        graficos[slug] = graficos_do_macrotema(slug)

    return {
        "versao_contrato": 1,
        "macrotemas": macrotemas,
        "campos": campos,
        "graficos": graficos,
        "tipos_de_bloco": list(TIPOS_DE_BLOCO),
        "slots_moldura": [*SLOTS_MOLDURA, SLOT_FONTES],
        "operadores": [
            {
                "op": op,
                "rotulo": ROTULOS_OPERADORES[op],
                "aridade": 0 if op in OPERADORES_DE_PRESENCA else (2 if op == "entre" else 1),
            }
            for op in OPERADORES
        ],
        "acoes_sem_dado": list(ACOES_SEM_DADO),
    }
