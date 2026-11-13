"""Emprego formal (Novo Caged) do relatório de Economia e Renda.

Lê `relatorios_auto.mv_caged_municipal` (db/2026-11-12-mv_caged_municipal.sql): uma
linha por município, já com os marcadores do Doc como colunas, calculados sobre o
último trimestre fechado nos dados. A agregação do microdado leva minutos, por isso
a matview (refresh noturno em scripts/refresh_matviews.sh) e nenhuma conta aqui.
Decisões e razões: Documentacao-OCA, HANDOFF-CAGED-ECONOMIA.md.
"""

from utils.queries.base import executar_query_dict

# Identificação já chega ao contexto pela view de perfil; sobrescrever o nm_mun
# canonicalizado em services/generation.py quebraria os joins seguintes.
_COLUNAS_IDENTIFICACAO = ("cd_mun", "nm_mun", "sigla_uf")

_MESES = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
_FIM_DO_TRIMESTRE = {"março": 3, "junho": 6, "setembro": 9, "dezembro": 12}


def _serie_mensal(linha: dict) -> list[tuple[str, object, object]]:
    """(mês, saldo no ano anterior, saldo no ano atual) de janeiro até o último mês
    do trimestre de referência — o recorte da Figura X3. O fim vem de
    `ultimo_mes_tri`, não do primeiro NULL: mês sem nenhuma movimentação também é
    NULL na matview (soma de nada) e cortava a série no meio (Milagres do Maranhão,
    sem movimentação em 2026, ficava sem gráfico). NULL dentro da série é saldo 0."""
    meses = _FIM_DO_TRIMESTRE.get(linha.get("ultimo_mes_tri"), 0)
    return [
        (
            mes,
            linha.get(f"saldo_mes{numero:02d}_ano_anterior") or 0,
            linha.get(f"saldo_mes{numero:02d}_ano_atual") or 0,
        )
        for numero, mes in enumerate(_MESES[:meses], start=1)
    ]


def buscar_caged_municipal(nome_municipio: str, sigla_uf: str) -> dict | None:
    """Marcadores CAGED do município (`economia.$saldo_tri_atual` etc.) mais
    `caged_serie_mensal` para o gráfico. None sem banco ou sem a linha."""
    if not nome_municipio or not sigla_uf:
        return None

    # Mesmo casamento de relatorios_auto.mv_perfil_* (utils/queries/perfil_municipal.py):
    # compara sem o "(UF)" final dos dois lados, porque o nome chega canonicalizado
    # como "Cidade (UF)" e a matview guarda só o nome.
    query = """
        SET LOCAL statement_timeout = '30s';
        SELECT *
        FROM relatorios_auto.mv_caged_municipal
        WHERE LOWER(regexp_replace(nm_mun, '\\s*\\([^)]*\\)\\s*$', '')) =
              LOWER(regexp_replace(%s, '\\s*\\([^)]*\\)\\s*$', ''))
          AND sigla_uf = %s
        LIMIT 1
    """
    linha = executar_query_dict(
        query, (nome_municipio, sigla_uf), f"CAGED de '{nome_municipio} ({sigla_uf})'"
    )
    if not linha:
        return None

    marcadores = {
        coluna: valor for coluna, valor in linha.items() if coluna not in _COLUNAS_IDENTIFICACAO
    }
    marcadores["caged_serie_mensal"] = _serie_mensal(linha)
    return marcadores
