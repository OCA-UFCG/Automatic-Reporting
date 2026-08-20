from utils.queries.base import executar_query

POPULACAO_MUNICIPIO_POR_ANO = """
    SELECT d.ano, COALESCE(SUM(d.populacao_total), 0) as pop_total
    FROM carac_mun.caracteristicas_municipais c
    JOIN dem_demografia.final_demografia d
        ON c.cd_mun = d.cd_mun::text
    WHERE c.nm_mun = %s
      AND c.sigla_uf = %s
      AND d.ano = ANY(%s)
    GROUP BY d.ano
"""


def buscar_populacao_demografia(
    nome_municipio: str, sigla_uf: str, anos: tuple[int, ...] = (2022, 2010)
) -> dict[str, object] | None:
    linhas = executar_query(
        POPULACAO_MUNICIPIO_POR_ANO,
        (nome_municipio, sigla_uf, list(anos)),
        f"população por ano de '{nome_municipio} ({sigla_uf})'",
        buscar_todas=True,
    )
    if not linhas:
        return None

    pop_por_ano = {ano: pop_total for ano, pop_total in linhas}

    # Números crus: a formatação pt-BR acontece na hora de montar o texto
    # (utils/render/placeholders.py), não aqui.
    dados: dict[str, object] = {
        f"pop_total_{ano}": pop_por_ano[ano] for ano in anos if ano in pop_por_ano
    }

    ano_mais_recente, ano_mais_antigo = max(anos), min(anos)
    if ano_mais_recente in pop_por_ano and ano_mais_antigo in pop_por_ano:
        pop_recente = pop_por_ano[ano_mais_recente]
        pop_antiga = pop_por_ano[ano_mais_antigo]
        if pop_antiga:
            dados["cres_pop"] = round(
                (pop_recente - pop_antiga) / pop_antiga * 100, 1
            )

    return dados or None


DEMOGRAFIA_SEXO_FAIXA_ETARIA = """
    SELECT
        SUM(d.populacao_total) as pop_total,
        SUM(d.mulher) as pop_mulher,
        SUM(d.homem) as pop_homem,
        SUM(CASE WHEN d.classificador_idade BETWEEN 1 AND 3 THEN d.populacao_total ELSE 0 END) as pop_etaria_0_14,
        SUM(CASE WHEN d.classificador_idade BETWEEN 4 AND 6 THEN d.populacao_total ELSE 0 END) as pop_etaria_15_29,
        SUM(CASE WHEN d.classificador_idade BETWEEN 7 AND 9 THEN d.populacao_total ELSE 0 END) as pop_etaria_30_59,
        SUM(CASE WHEN d.classificador_idade >= 10 THEN d.populacao_total ELSE 0 END) as pop_etaria_60_mais,
        SUM(d.branca) as pop_branca,
        SUM(d.preta) as pop_preta,
        SUM(d.parda) as pop_parda,
        SUM(d.amarela) as pop_amarela,
        SUM(d.indigena) as pop_indigena
    FROM carac_mun.caracteristicas_municipais c
    JOIN dem_demografia.final_demografia d
        ON c.cd_mun = d.cd_mun::text
        AND d.ano = 2022
    WHERE c.nm_mun = %s
      AND c.sigla_uf = %s
"""


FAIXAS_ETARIAS_LABELS = {
    "0_14": "0 a 14",
    "15_29": "15 a 29",
    "30_59": "30 a 59",
    "60_mais": "60 ou mais",
}


def buscar_demografia_sexo_faixa_etaria(
    nome_municipio: str, sigla_uf: str
) -> dict[str, object] | None:
    linha = executar_query(
        DEMOGRAFIA_SEXO_FAIXA_ETARIA,
        (nome_municipio, sigla_uf),
        f"demografia sexo/faixa etária de '{nome_municipio} ({sigla_uf})'",
    )
    if linha is None:
        return None

    (
        _pop_total, pop_mulher, pop_homem,
        pop_etaria_0_14, pop_etaria_15_29, pop_etaria_30_59, pop_etaria_60_mais,
        pop_branca, pop_preta, pop_parda, pop_amarela, pop_indigena
    ) = linha

    # Números crus (não formatados) de propósito: "pop_mulher_per",
    # "pop_homem_per" etc. são resolvidos automaticamente pelo motor de
    # placeholders (utils/render/placeholders.py) como percentual sobre
    # "pop_total" — não precisam de código aqui. A formatação pt-BR também
    # acontece só na hora de montar o texto, não na query. "pop_total" não
    # entra no dict retornado de propósito: já vem de
    # buscar_caracteristicas_municipio/buscar_populacao_demografia.
    dados: dict[str, object] = {
        "pop_mulher": pop_mulher,
        "pop_homem": pop_homem,
        "pop_etaria_0_14": pop_etaria_0_14,
        "pop_etaria_15_29": pop_etaria_15_29,
        "pop_etaria_30_59": pop_etaria_30_59,
        "pop_etaria_60_mais": pop_etaria_60_mais,
        "pop_branca": pop_branca,
        "pop_preta": pop_preta,
        "pop_parda": pop_parda,
        "pop_amarela": pop_amarela,
        "pop_indigena": pop_indigena,
    }

    # Determina a faixa etária predominante
    faixas = {
        "0_14": pop_etaria_0_14,
        "15_29": pop_etaria_15_29,
        "30_59": pop_etaria_30_59,
        "60_mais": pop_etaria_60_mais,
    }
    faixa_maior = max(faixas, key=faixas.get)
    dados["cat_etaria_maior"] = FAIXAS_ETARIAS_LABELS[faixa_maior]
    # Nome cru para o percentual genérico ($etaria_maior_per) resolver contra
    # "pop_total".
    dados["etaria_maior"] = faixas[faixa_maior]

    # Determina a raça/cor predominante
    racas = {
        "branca": pop_branca,
        "preta": pop_preta,
        "parda": pop_parda,
        "amarela": pop_amarela,
        "indigena": pop_indigena,
    }
    raca_maior = max(racas, key=racas.get)
    dados["cor_maior"] = raca_maior
    dados["raca_maior"] = raca_maior

    return {campo: valor for campo, valor in dados.items() if valor is not None}


INDIGENA_MUNICIPIO = """
    SELECT
        COALESCE(SUM(pop_total_indigena), 0) as pop_total_indigena,
        COALESCE(SUM(homem_indigena), 0) as homem_indigena,
        COALESCE(SUM(mulher_indigena), 0) as mulher_indigena,
        COALESCE(SUM(dentro_territorio_indigena), 0) as dentro_territorio_indigena,
        COALESCE(SUM(fora_territorio_indigena), 0) as fora_territorio_indigena
    FROM dem_demografia_indigena.vw_populacao_indigena_geral_2022
    WHERE cd_mun = (
        SELECT cd_mun::int FROM carac_mun.caracteristicas_municipais
        WHERE nm_mun = %s AND sigla_uf = %s
    )
"""


def buscar_populacao_indigena(
    nome_municipio: str, sigla_uf: str
) -> dict[str, object] | None:
    linha = executar_query(
        INDIGENA_MUNICIPIO,
        (nome_municipio, sigla_uf),
        f"população indígena de '{nome_municipio} ({sigla_uf})'",
    )
    if linha is None:
        return None

    pop_total_indigena, homem_indigena, mulher_indigena, dentro_territorio, fora_territorio = linha

    if pop_total_indigena == 0:
        return None

    dados = {
        "pop_total_indigena": pop_total_indigena,
        "homem_indigena": homem_indigena,
        "mulher_indigena": mulher_indigena,
        "dentro_territorio_indigena": dentro_territorio,
        "fora_territorio_indigena": fora_territorio,
    }
    return {campo: valor for campo, valor in dados.items() if valor is not None}


POP_RUA_MUNICIPIO = """
    SELECT
        numero_pessoas_situacao_rua_cadunico as pop_rua_total,
        criancas_adolescentes_situacao_rua as pop_rua_criancas_adolescentes,
        pcd_em_situacao_de_rua as pop_rua_pcd,
        idosos_em_situacao_de_rua as pop_rua_idosos,
        num_centro_pop as centros_pop,
        total_familias_situacao_rua_cadunico as familias_rua_total,
        familias_situacao_rua_beneficiarias_bolsa_familia as familias_rua_bf,
        qtd_pobreza_cadunico as pobreza_cadunico,
        qtd_baixa_renda_cadunico as baixa_renda_cadunico,
        qtd_acima_meio_salario_minimo_cadunico as acima_meio_sm_cadunico
    FROM dem_rua.vw_pop_2022
    WHERE cd_mun = (
        SELECT cd_mun::int FROM carac_mun.caracteristicas_municipais
        WHERE nm_mun = %s AND sigla_uf = %s
    )
"""


def buscar_populacao_rua(
    nome_municipio: str, sigla_uf: str
) -> dict[str, object] | None:
    linha = executar_query(
        POP_RUA_MUNICIPIO,
        (nome_municipio, sigla_uf),
        f"população em situação de rua de '{nome_municipio} ({sigla_uf})'",
    )
    if linha is None:
        return None

    (
        pop_rua_total, pop_rua_criancas_adolescentes, pop_rua_pcd, pop_rua_idosos,
        centros_pop, familias_rua_total, familias_rua_bf,
        pobreza_cadunico, baixa_renda_cadunico, acima_meio_sm_cadunico
    ) = linha

    if pop_rua_total == 0:
        return None

    dados = {
        "pop_rua_total": pop_rua_total,
        "pop_rua_criancas_adolescentes": pop_rua_criancas_adolescentes,
        "pop_rua_pcd": pop_rua_pcd,
        "pop_rua_idosos": pop_rua_idosos,
        "centros_pop": centros_pop,
        "familias_rua_total": familias_rua_total,
        "familias_rua_bf": familias_rua_bf,
        "pobreza_cadunico": pobreza_cadunico,
        "baixa_renda_cadunico": baixa_renda_cadunico,
        "acima_meio_sm_cadunico": acima_meio_sm_cadunico,
    }
    return {campo: valor for campo, valor in dados.items() if valor is not None}
