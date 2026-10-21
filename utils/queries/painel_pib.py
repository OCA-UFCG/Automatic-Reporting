"""Dados agregados por UF/ano para a versão mobile do painel de PIB do portal.

Diferente dos `buscar_*` dos relatórios (um município por vez, achatados em
placeholders), aqui a saída é a série inteira por UF, consumida como JSON pelo
`data-nordeste-frontend` em `/data-panel/[id]` no celular.
"""

from utils.queries.base import executar_query

# DISTINCT em caracteristicas_municipais: a tabela pode repetir cd_mun (as views
# de db/ agregam com max() pelo mesmo motivo), e um JOIN direto contaria o PIB do
# município duas vezes na soma da UF.
#
# `vab_*` e `impostos_liquidos` vêm em milhares de reais (ver `_em_reais` em
# economia_renda.py); `pib_total` e `pib_per_capita` já vêm em reais. A conversão
# acontece aqui para o JSON sair com uma unidade só.
#
# A população é implícita (pib_total / pib_per_capita, a mesma estimativa que o
# IBGE usou no per capita do município); somá-la dá o per capita da UF sem
# depender de outra tabela de população.
PIB_POR_UF_ANO = """
    SELECT
        c.sigla_uf,
        p.ano,
        SUM(p.pib_total) AS pib_total,
        SUM(p.pib_total / NULLIF(p.pib_per_capita, 0)) AS populacao_implicita,
        SUM(p.vab_agropecuaria) * 1000 AS vab_agropecuaria,
        SUM(p.vab_industria) * 1000 AS vab_industria,
        SUM(p.vab_servicos) * 1000 AS vab_servicos,
        SUM(p.vab_adm_publica) * 1000 AS vab_adm_publica,
        SUM(p.impostos_liquidos) * 1000 AS impostos_liquidos
    FROM eco_pib.pib_municipal p
    JOIN (
        SELECT DISTINCT cd_mun::int AS cd_mun, sigla_uf
        FROM carac_mun.caracteristicas_municipais
    ) c ON c.cd_mun = p.cd_mun::int
    WHERE p.ano IS NOT NULL AND c.sigla_uf IS NOT NULL
    GROUP BY c.sigla_uf, p.ano
    ORDER BY c.sigla_uf, p.ano
"""

_COLUNAS = (
    "uf",
    "ano",
    "pib_total",
    "populacao_implicita",
    "vab_agropecuaria",
    "vab_industria",
    "vab_servicos",
    "vab_adm_publica",
    "impostos_liquidos",
)

FONTE_PIB = "IBGE — Produto Interno Bruto dos Municípios"


def _numero(valor: object) -> float | None:
    return None if valor is None else float(valor)


def _per_capita(pib_total: float | None, populacao: float | None) -> float | None:
    if pib_total is None or not populacao:
        return None
    return pib_total / populacao


def _registro_painel(linha: dict) -> dict:
    pib_total = _numero(linha["pib_total"])
    return {
        "uf": linha["uf"],
        "ano": int(linha["ano"]),
        "pib_total": pib_total,
        "pib_per_capita": _per_capita(pib_total, _numero(linha["populacao_implicita"])),
        "vab": {
            "agropecuaria": _numero(linha["vab_agropecuaria"]),
            "industria": _numero(linha["vab_industria"]),
            "servicos": _numero(linha["vab_servicos"]),
            "adm_publica": _numero(linha["vab_adm_publica"]),
        },
        "impostos_liquidos": _numero(linha["impostos_liquidos"]),
    }


def buscar_pib_por_uf() -> list[dict] | None:
    """Série anual de PIB agregada por UF, ou None se o banco não respondeu.

    Exemplo: `buscar_pib_por_uf()[0]["uf"] == "AL"`.
    """
    linhas = executar_query(PIB_POR_UF_ANO, (), "PIB agregado por UF", buscar_todas=True)
    if linhas is None:
        return None
    return [dict(zip(_COLUNAS, linha)) for linha in linhas]


def montar_painel_pib(linhas: list[dict]) -> dict:
    """Monta o JSON do painel mobile: anos/UFs disponíveis e um registro por UF/ano.

    Exemplo: `montar_painel_pib(buscar_pib_por_uf())["anos"][-1] == 2023`.
    """
    registros = [_registro_painel(linha) for linha in linhas]
    return {
        "fonte": FONTE_PIB,
        "unidade": "R$",
        "anos": sorted({registro["ano"] for registro in registros}),
        "ufs": sorted({registro["uf"] for registro in registros}),
        "registros": registros,
    }
