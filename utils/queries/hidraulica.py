from utils.queries.base import executar_query

# A tabela de cisternas só tem cd_mun (recriada em 30/09/2026, sem nm_mun/
# sigla_uf): nome e UF vêm de carac_mun, como no PIB. Ela já tem 2026, mas o
# Doc e a legenda do gráfico vão "até 2025": o último parâmetro é o ano limite.
TECNOLOGIAS_ACESSO_AGUA = """
    SELECT
        t.ano,
        t.tot_cisternas,
        t.i_agua_total,
        t.ii_agua,
        t.escolares
    FROM hidr_cisternas.final_tecnologias_sociais_de_acesso_a_agua t
    JOIN carac_mun.caracteristicas_municipais c ON c.cd_mun::int = t.cd_mun::int
    WHERE LOWER(c.nm_mun) = LOWER(%s)
      AND c.sigla_uf = %s
      AND t.ano <= %s
    ORDER BY t.ano
"""

_DECADAS_SERIE_HISTORICA = (2010, 2020, 2025)

# i_agua = tecnologias de "1ª água" (abastecimento humano); ii_agua = "2ª água"
# (irrigação e dessedentação animal). tot_cisternas = i_agua_total + ii_agua +
# escolares em todos os municípios (conferido no beta em 29/09/2026): sem as
# escolares, a divisão por finalidade não fecha com o total em 801 municípios,
# e em 44 deles todas as tecnologias são escolares. Por isso elas entram no
# contexto como `escolares_qtd`/`escolares_per`.
_LABEL_PRIMEIRA_AGUA = "abastecimento humano (1ª água)"
_LABEL_SEGUNDA_AGUA = "irrigação e dessedentação de animais (2ª água)"


def _calcular_indicadores_finalidade(
    total_referencia: float | None,
    primeira_agua_qtd: float | None,
    segunda_agua_qtd: float | None,
    escolares_qtd: float | None = None,
) -> dict[str, object]:
    indicadores: dict[str, object] = {}
    if not total_referencia:
        return indicadores

    if primeira_agua_qtd is not None:
        indicadores["primeira_agua_qtd"] = primeira_agua_qtd
        indicadores["primeira_agua_per"] = round(
            primeira_agua_qtd / total_referencia * 100, 2
        )

    if segunda_agua_qtd is not None:
        indicadores["segunda_agua_qtd"] = segunda_agua_qtd
        indicadores["segunda_agua_per"] = round(
            segunda_agua_qtd / total_referencia * 100, 2
        )

    if escolares_qtd is not None:
        indicadores["escolares_qtd"] = escolares_qtd
        indicadores["escolares_per"] = round(
            escolares_qtd / total_referencia * 100, 2
        )

    # A predominância segue só entre 1ª e 2ª água: as escolares nunca superam
    # as duas num município que tem alguma delas (0 casos no beta, 29/09/2026).
    if primeira_agua_qtd is None or segunda_agua_qtd is None:
        return indicadores

    # Empate (ex.: Jijoca de Jericoacoara/CE, 10 e 10): nenhuma predomina, e o
    # Doc dizia "predominância ... 50%". sol_predom/sol_predom_per ficam como
    # estão porque a abertura do tema também depende de sol_predom_per > 0; o
    # Doc escolhe a frase da Síntese por empate_finalidade. Com 0 e 0 (só
    # escolares) não é empate: o Doc tem frase própria para esse caso.
    indicadores["empate_finalidade"] = int(
        primeira_agua_qtd == segunda_agua_qtd and primeira_agua_qtd > 0
    )

    if primeira_agua_qtd >= segunda_agua_qtd:
        indicadores["sol_predom"] = _LABEL_PRIMEIRA_AGUA
        indicadores["sol_predom_per"] = indicadores["primeira_agua_per"]
    else:
        indicadores["sol_predom"] = _LABEL_SEGUNDA_AGUA
        indicadores["sol_predom_per"] = indicadores["segunda_agua_per"]

    return indicadores


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
        indicadores["var_total_per"] = round(acrescimo_qtd / total_inicio * 100, 2)

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
        acrescimo_decada_concentrada / acrescimo_qtd * 100, 2
    )

    return indicadores


def buscar_tecnologias_acesso_agua(
    nome_municipio: str, sigla_uf: str
) -> dict[str, object] | None:
    linhas = executar_query(
        TECNOLOGIAS_ACESSO_AGUA,
        (nome_municipio, sigla_uf, _DECADAS_SERIE_HISTORICA[-1]),
        f"tecnologias sociais de acesso à água de '{nome_municipio} ({sigla_uf})'",
        buscar_todas=True,
    )
    if not linhas:
        return None

    serie = [
        {"ano": ano, "total": total}
        for ano, total, _i_agua_total, _ii_agua, _escolares in linhas
        if ano is not None and total is not None
    ]
    if not serie:
        return None

    por_ano = {item["ano"]: item["total"] for item in serie}
    dados: dict[str, object] = {"tecnologias_acesso_agua_serie": serie}
    dados.update(_calcular_indicadores_serie_historica(por_ano))

    ultimo_ano = max(por_ano)
    _, total_ultimo_ano, i_agua_total, ii_agua, escolares = next(
        linha for linha in linhas if linha[0] == ultimo_ano
    )
    dados.update(
        _calcular_indicadores_finalidade(
            total_ultimo_ano, i_agua_total, ii_agua, escolares
        )
    )
    # Ano real dos dados de 1ª/2ª água, que nem sempre é o mais recente da
    # série. A capa usava isso para rotular a fonte dos cards de acesso à
    # água; hoje ela lê `fonte_abastecimento_humano`/`fonte_irrigacao` direto
    # de vw_indicadores. Fica exposto no contexto como placeholder para os
    # Docs, que são editados fora do repositório.
    dados["ano_referencia_finalidade"] = ultimo_ano
    return dados
