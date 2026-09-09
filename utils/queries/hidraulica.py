from utils.queries.base import executar_query

TECNOLOGIAS_ACESSO_AGUA = """
    SELECT
        ano,
        tot_cisternas
    FROM hidr_cisternas.final_tecnologias_sociais_de_acesso_a_agua
    WHERE LOWER(nm_mun) = LOWER(%s)
      AND sigla_uf = %s
    ORDER BY ano
"""

_DECADAS_SERIE_HISTORICA = (2010, 2020, 2025)


def _calcular_indicadores_serie_historica(
    por_ano: dict[int, float],
) -> dict[str, object]:
    inicio, meio, fim = _DECADAS_SERIE_HISTORICA
    total_inicio, total_meio, total_fim = (
        por_ano.get(inicio),
        por_ano.get(meio),
        por_ano.get(fim),
    )

    indicadores: dict[str, object] = {}
    for ano in _DECADAS_SERIE_HISTORICA:
        if por_ano.get(ano) is not None:
            indicadores[f"total_{ano}"] = por_ano[ano]

    if total_inicio is None or total_fim is None:
        return indicadores

    acrescimo_qtd = total_fim - total_inicio
    indicadores["acrescimo_qtd"] = acrescimo_qtd
    if total_inicio:
        indicadores["var_total_per"] = round(acrescimo_qtd / total_inicio * 100, 1)

    if total_meio is None or not acrescimo_qtd:
        return indicadores

    acrescimo_primeira_decada = total_meio - total_inicio
    acrescimo_segunda_decada = total_fim - total_meio
    if acrescimo_segunda_decada >= acrescimo_primeira_decada:
        dec_concentracao = f"{meio} a {fim}"
        acrescimo_decada_concentrada = acrescimo_segunda_decada
    else:
        dec_concentracao = f"{inicio} a {meio}"
        acrescimo_decada_concentrada = acrescimo_primeira_decada

    indicadores["dec_concentracao"] = dec_concentracao
    indicadores["dec_concentracao_per"] = round(
        acrescimo_decada_concentrada / acrescimo_qtd * 100, 1
    )

    return indicadores


def buscar_tecnologias_acesso_agua(
    nome_municipio: str, sigla_uf: str
) -> dict[str, object] | None:
    linhas = executar_query(
        TECNOLOGIAS_ACESSO_AGUA,
        (nome_municipio, sigla_uf),
        f"tecnologias sociais de acesso à água de '{nome_municipio} ({sigla_uf})'",
        buscar_todas=True,
    )
    if not linhas:
        return None

    serie = [
        {"ano": ano, "total": total}
        for ano, total in linhas
        if ano is not None and total is not None
    ]
    if not serie:
        return None

    por_ano = {item["ano"]: item["total"] for item in serie}
    dados: dict[str, object] = {"tecnologias_acesso_agua_serie": serie}
    dados.update(_calcular_indicadores_serie_historica(por_ano))
    return dados
