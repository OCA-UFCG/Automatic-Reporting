"""Dados do painel de PIB do portal para um recorte (área, UF, município).

Diferente dos `buscar_*` dos relatórios (um município, achatado em placeholders),
aqui a saída é a série inteira do recorte, consumida como JSON pelo
`data-nordeste-frontend` em `/data-panel/pib` no celular. Espelha o painel do
Power BI: filtros Ano/Área/Estado/Município, PIB e per capita, evolução anual,
VAB por setor e atividade com maior VAB.
"""

import re
from dataclasses import dataclass

from utils.queries.base import executar_query

# IMPORTANT: a área vira nome de coluna no SQL, então só entra por esta whitelist
# — nunca interpolar o valor recebido na URL. Cada coluna da vw_pib marca
# 'Sim'/'Não' se o município pertence à área.
AREAS = {
    "aas_21": "Área de atuação da SUDENE",
    "ne": "Nordeste",
    "semi_21": "Semiárido",
    "caat_24": "Caatinga",
}
AREA_PADRAO = "aas_21"

FONTE_PIB = "IBGE — Produto Interno Bruto dos Municípios"

_UF_VALIDA = re.compile(r"^[A-Z]{2}$")


class RecorteInvalido(ValueError):
    """Parâmetro de filtro fora do formato esperado (vira 422 na API)."""


@dataclass(frozen=True)
class RecortePib:
    area: str = AREA_PADRAO
    uf: str | None = None
    municipio: int | None = None


def validar_recorte(area: str | None, uf: str | None, municipio: str | None) -> RecortePib:
    """Valida os filtros da URL. Exemplo: `validar_recorte("ne", "PB", None)`."""
    area = area or AREA_PADRAO
    if area not in AREAS:
        raise RecorteInvalido(f'Área "{area}" inválida; esperado uma de {", ".join(AREAS)}.')
    if uf and not _UF_VALIDA.match(uf):
        raise RecorteInvalido(f'UF "{uf}" inválida; esperado sigla com 2 letras maiúsculas.')
    if municipio and not municipio.isdigit():
        raise RecorteInvalido(f'Município "{municipio}" inválido; esperado código IBGE numérico.')
    return RecortePib(area, uf or None, int(municipio) if municipio else None)


def _filtro_sql(recorte: RecortePib, com_uf: bool = True, com_municipio: bool = True) -> tuple[str, tuple]:
    condicoes, params = [f"{recorte.area} = 'Sim'"], []
    if com_uf and recorte.uf:
        condicoes.append("sigla_uf = %s")
        params.append(recorte.uf)
    if com_municipio and recorte.municipio:
        # cd_mun é texto na view (com espaços em alguns registros, por isso o
        # btrim, como em db/2026-09-30-vw_indicadores.sql).
        condicoes.append("btrim(cd_mun::text) = %s")
        params.append(str(recorte.municipio))
    return " AND ".join(condicoes), tuple(params)


# `vab_*`, `impostos_liquidos` e `vab_setor_maior` vêm em milhares de reais (ver
# `_em_reais` em economia_renda.py); `pib_total` já vem em reais. A conversão é
# feita aqui para o JSON sair numa unidade só. A população é implícita
# (pib_total / pib_per_capita, a estimativa que o IBGE usou no per capita do
# município); somá-la dá o per capita do recorte sem outra tabela.
# `ano` é texto na view, daí o cast.
_SERIE = """
    SELECT
        ano::int AS ano,
        SUM(pib_total),
        SUM(pib_total / NULLIF(pib_per_capita, 0)),
        SUM(vab_agropecuaria) * 1000,
        SUM(vab_industria) * 1000,
        SUM(vab_servicos) * 1000,
        SUM(vab_adm_publica) * 1000
    FROM eco_pib.vw_pib
    WHERE {filtro}
    GROUP BY ano::int
    ORDER BY ano::int
"""

_ATIVIDADES = """
    SELECT
        ano::int AS ano,
        atividade_maior_vab,
        COUNT(*),
        SUM(vab_setor_maior) * 1000,
        SUM(pib_total)
    FROM eco_pib.vw_pib
    WHERE {filtro} AND atividade_maior_vab IS NOT NULL
    GROUP BY ano::int, atividade_maior_vab
    ORDER BY ano::int, COUNT(*) DESC
"""

_UFS = "SELECT DISTINCT sigla_uf FROM eco_pib.vw_pib WHERE {filtro} ORDER BY sigla_uf"

_MUNICIPIOS = """
    SELECT DISTINCT btrim(cd_mun::text)::int, nm_mun FROM eco_pib.vw_pib
    WHERE {filtro} ORDER BY nm_mun
"""


def _consultar(sql: str, recorte: RecortePib, contexto: str, **escopo: bool) -> list | None:
    filtro, params = _filtro_sql(recorte, **escopo)
    return executar_query(sql.format(filtro=filtro), params, contexto, buscar_todas=True)


def _numero(valor: object) -> float | None:
    return None if valor is None else float(valor)


def _ponto_serie(linha: tuple) -> dict:
    ano, pib_total, populacao = linha[:3]
    pib_total, populacao = _numero(pib_total), _numero(populacao)
    return {
        "ano": ano,
        "pib_total": pib_total,
        "pib_per_capita": pib_total / populacao if pib_total and populacao else None,
    }


def _vab_ano(linha: tuple) -> dict | None:
    agro, industria, servicos, adm = (_numero(valor) for valor in linha[3:7])
    if all(valor is None for valor in (agro, industria, servicos, adm)):
        return None
    return {
        "ano": linha[0],
        "agropecuaria": agro,
        "industria": industria,
        "servicos": servicos,
        "adm_publica": adm,
    }


def _atividade(linha: tuple) -> dict:
    ano, atividade, municipios, vab, pib_total = linha
    vab, pib_total = _numero(vab), _numero(pib_total)
    return {
        "ano": ano,
        "atividade": atividade,
        "municipios": municipios,
        "vab": vab,
        "participacao_pib": vab / pib_total if vab is not None and pib_total else None,
    }


def _opcoes(recorte: RecortePib) -> dict | None:
    ufs = _consultar(_UFS, recorte, "UFs do painel de PIB", com_uf=False, com_municipio=False)
    municipios = (
        _consultar(_MUNICIPIOS, recorte, "municípios do painel de PIB", com_municipio=False)
        if recorte.uf
        else []
    )
    if ufs is None or municipios is None:
        return None
    return {
        "areas": [{"id": area, "nome": nome} for area, nome in AREAS.items()],
        "ufs": [linha[0] for linha in ufs],
        "municipios": [{"codigo": codigo, "nome": nome} for codigo, nome in municipios],
    }


def buscar_painel_pib(recorte: RecortePib) -> dict | None:
    """JSON do painel para o recorte, ou None se o banco não respondeu.

    Exemplo: `buscar_painel_pib(validar_recorte("ne", "PB", None))["serie"][-1]["ano"]`.
    """
    serie = _consultar(_SERIE, recorte, "série do painel de PIB")
    atividades = _consultar(_ATIVIDADES, recorte, "atividades do painel de PIB")
    opcoes = _opcoes(recorte)
    if serie is None or atividades is None or opcoes is None:
        return None
    return {
        "fonte": FONTE_PIB,
        "recorte": {"area": recorte.area, "uf": recorte.uf, "municipio": recorte.municipio},
        "opcoes": opcoes,
        "serie": [_ponto_serie(linha) for linha in serie],
        "vab": [vab for vab in map(_vab_ano, serie) if vab],
        "atividades": [_atividade(linha) for linha in atividades],
    }
