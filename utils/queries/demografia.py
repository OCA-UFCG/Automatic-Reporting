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

MEDIA_CRESCIMENTO_MESMO_PORTE = """
    WITH populacoes AS (
        SELECT cd_mun,
               SUM(populacao_total) FILTER (WHERE ano = 2010) AS pop_2010,
               SUM(populacao_total) FILTER (WHERE ano = 2022) AS pop_2022
        FROM dem_demografia.final_demografia
        WHERE ano IN (2010, 2022)
        GROUP BY cd_mun
    ), alvo AS (
        SELECT p.pop_2022
        FROM populacoes p
        JOIN carac_mun.caracteristicas_municipais c ON c.cd_mun = p.cd_mun::text
        WHERE c.nm_mun = %s AND c.sigla_uf = %s
    )
    SELECT AVG((p.pop_2022 - p.pop_2010) / NULLIF(p.pop_2010, 0) * 100.0)
    FROM populacoes p CROSS JOIN alvo a
    WHERE CASE
        WHEN a.pop_2022 <= 50000 THEN p.pop_2022 <= 50000
        WHEN a.pop_2022 <= 100000 THEN p.pop_2022 > 50000 AND p.pop_2022 <= 100000
        ELSE p.pop_2022 > 100000
    END
"""


def buscar_populacao_demografia(
    nome_municipio: str, sigla_uf: str, anos: tuple[int, ...] = (2022, 2010, 2000)
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

    dados: dict[str, object] = {
        f"pop_total_{ano}": pop_por_ano[ano] for ano in anos if ano in pop_por_ano
    }

    ano_mais_recente = 2022 if 2022 in anos else max(anos)
    ano_mais_antigo = 2010 if 2010 in anos else min(anos)
    if ano_mais_recente in pop_por_ano and ano_mais_antigo in pop_por_ano:
        pop_recente = pop_por_ano[ano_mais_recente]
        pop_antiga = pop_por_ano[ano_mais_antigo]
        if pop_antiga:
            dados["cres_pop"] = round(
                (pop_recente - pop_antiga) / pop_antiga * 100, 1
            )
            dados["porte_mun"] = (
                "baixo porte" if pop_recente <= 50000
                else "médio porte" if pop_recente <= 100000
                else "grande porte"
            )
            media_linha = executar_query(
                MEDIA_CRESCIMENTO_MESMO_PORTE,
                (nome_municipio, sigla_uf),
                f"média de crescimento por porte de '{nome_municipio} ({sigla_uf})'",
            )
            if media_linha and media_linha[0] is not None:
                media = round(float(media_linha[0]), 1)
                dados["media_porte"] = media
                dados["comparar_pop_porte"] = (
                    "superior à" if dados["cres_pop"] > media
                    else "inferior à" if dados["cres_pop"] < media
                    else "igual à"
                )

    return dados or None


DEMOGRAFIA_SEXO_FAIXA_ETARIA = """
    SELECT
        SUM(d.populacao_total) as pop_total,
        SUM(d.mulher) as pop_mulher,
        SUM(d.homem) as pop_homem,
        SUM(CASE WHEN d.classificador_idade BETWEEN 1 AND 2 THEN d.populacao_total ELSE 0 END) as pop_etaria_0_9,
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

DEMOGRAFIA_SEXO_POR_FAIXA = """
    SELECT
        CASE
            WHEN d.classificador_idade BETWEEN 1 AND 2 THEN '0 a 9 anos'
            WHEN d.classificador_idade BETWEEN 3 AND 4 THEN '10 a 19 anos'
            WHEN d.classificador_idade BETWEEN 5 AND 6 THEN '20 a 29 anos'
            WHEN d.classificador_idade = 7 THEN '30 a 39 anos'
            WHEN d.classificador_idade = 8 THEN '40 a 49 anos'
            WHEN d.classificador_idade = 9 THEN '50 a 59 anos'
            WHEN d.classificador_idade = 10 THEN '60 a 69 anos'
            WHEN d.classificador_idade = 11 THEN '70 a 79 anos'
            WHEN d.classificador_idade = 12 THEN '80+ anos'
        END AS faixa,
        SUM(d.mulher) AS mulheres,
        SUM(d.homem) AS homens,
        MIN(d.classificador_idade) AS ordem
    FROM carac_mun.caracteristicas_municipais c
    JOIN dem_demografia.final_demografia d
        ON c.cd_mun = d.cd_mun::text AND d.ano = 2022
    WHERE c.nm_mun = %s AND c.sigla_uf = %s
    GROUP BY faixa
    ORDER BY ordem
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
        pop_total, pop_mulher, pop_homem, pop_etaria_0_9,
        pop_etaria_0_14, pop_etaria_15_29, pop_etaria_30_59, pop_etaria_60_mais,
        pop_branca, pop_preta, pop_parda, pop_amarela, pop_indigena
    ) = linha

    dados: dict[str, object] = {
        "pop_mulher": pop_mulher,
        "pop_homem": pop_homem,
        "pop_etaria_0_9": pop_etaria_0_9,
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

    faixas = {
        "0_14": pop_etaria_0_14,
        "15_29": pop_etaria_15_29,
        "30_59": pop_etaria_30_59,
        "60_mais": pop_etaria_60_mais,
    }
    faixa_maior = max(faixas, key=faixas.get)
    dados["cat_etaria_maior"] = FAIXAS_ETARIAS_LABELS[faixa_maior]
    dados["etaria_maior"] = faixas[faixa_maior]

    faixa_menor = min(faixas, key=faixas.get)
    dados["cat_etaria_menor"] = FAIXAS_ETARIAS_LABELS[faixa_menor]
    dados["etaria_menor"] = faixas[faixa_menor]
    dados["pop_etaria_per_0_9"] = round(float(pop_etaria_0_9) / float(pop_total) * 100, 1)
    dados["pop_etaria_per_60_mais"] = round(float(pop_etaria_60_mais) / float(pop_total) * 100, 1)
    dados["dif_etaria_09_60"] = pop_etaria_60_mais - pop_etaria_0_9

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

    racas_ordenadas = sorted(racas.items(), key=lambda item: item[1], reverse=True)
    ordinais = ("pri", "seg", "ter", "quar")
    for ordinal, (cor, populacao) in zip(ordinais, racas_ordenadas):
        dados[f"cor_{ordinal}_class"] = cor
        dados[f"cor_{ordinal}_pop"] = populacao
        dados[f"cor_{ordinal}_per"] = round(float(populacao) / float(pop_total) * 100, 1)
    dados["cor_raca_pri_class"] = racas_ordenadas[0][0]

    linhas_faixa_sexo = executar_query(
        DEMOGRAFIA_SEXO_POR_FAIXA,
        (nome_municipio, sigla_uf),
        f"demografia por sexo/faixa etária de '{nome_municipio} ({sigla_uf})'",
        buscar_todas=True,
    ) or []
    dados["faixas_etarias_sexo"] = [
        {"faixa": faixa, "mulheres": mulheres, "homens": homens}
        for faixa, mulheres, homens, _ordem in linhas_faixa_sexo
        if faixa is not None
    ]

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

INDIGENA_COMPLEMENTAR_MUNICIPIO = """
    SELECT ano, faixa_etaria, COALESCE(SUM(pop_total_indigena), 0)
    FROM dem_demografia_indigena.vw_populacao_indigena_geral
    WHERE cd_mun = (
        SELECT cd_mun::int FROM carac_mun.caracteristicas_municipais
        WHERE nm_mun = %s AND sigla_uf = %s
    )
      AND ano IN (2010, 2022)
    GROUP BY ano, faixa_etaria
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

    faixas_por_ano = executar_query(
        INDIGENA_COMPLEMENTAR_MUNICIPIO,
        (nome_municipio, sigla_uf),
        f"população indígena complementar de '{nome_municipio} ({sigla_uf})'",
        buscar_todas=True,
    ) or []
    totais_por_ano: dict[int, object] = {}
    faixas_2022: list[tuple[str, object]] = []
    for ano, faixa, total in faixas_por_ano:
        totais_por_ano[ano] = totais_por_ano.get(ano, 0) + total
        if ano == 2022:
            faixas_2022.append((faixa, total))
    if 2010 in totais_por_ano:
        dados["pop_ind_2010"] = totais_por_ano[2010]
        if totais_por_ano[2010]:
            variacao = round(
                (float(pop_total_indigena) - float(totais_por_ano[2010]))
                / float(totais_por_ano[2010]) * 100,
                1,
            )
            dados["var_pop_ind_abs"] = abs(variacao)
            dados["var_pop_ind_analise"] = "aumento" if variacao >= 0 else "redução"
    if faixas_2022:
        faixas_2022.sort(key=lambda item: item[1], reverse=True)
        labels = {
            "faixa_0_9": "0 a 9", "faixa_10_19": "10 a 19",
            "faixa_20_29": "20 a 29", "faixa_30_39": "30 a 39",
            "faixa_40_49": "40 a 49", "faixa_50_59": "50 a 59",
            "faixa_60_69": "60 a 69", "faixa_70_79": "70 a 79",
            "faixa_80_mais": "80 ou mais",
        }
        for ordinal, (faixa, total) in zip(("pri", "seg"), faixas_2022):
            dados[f"cat_etaria_ind_{ordinal}"] = labels.get(faixa, faixa)
            dados[f"pop_etaria_ind_{ordinal}"] = total
    return {campo: valor for campo, valor in dados.items() if valor is not None}


QUILOMBOLA_MUNICIPIO = """
    SELECT
        COALESCE(populacao_total_quilombola, 0),
        COALESCE(porcentagem_populacao_quilombola, 0)
    FROM dem_demografia_quilombola.vw_demografia_quilombola_faixas_agrupadas
    WHERE cd_mun = (
        SELECT cd_mun::int FROM carac_mun.caracteristicas_municipais
        WHERE nm_mun = %s AND sigla_uf = %s
    )
      AND ano = 2022
    LIMIT 1
"""


def buscar_populacao_quilombola(
    nome_municipio: str, sigla_uf: str
) -> dict[str, object] | None:
    linha = executar_query(
        QUILOMBOLA_MUNICIPIO,
        (nome_municipio, sigla_uf),
        f"população quilombola de '{nome_municipio} ({sigla_uf})'",
    )
    if linha is None:
        return None
    pop_qui, pop_qui_per = linha
    return {"pop_qui": pop_qui, "pop_qui_per": pop_qui_per}


POP_RUA_MUNICIPIO = """
    SELECT
        ano,
        numero_pessoas_situacao_rua_cadunico,
        criancas_adolescentes_situacao_rua,
        pcd_em_situacao_de_rua,
        idosos_em_situacao_de_rua,
        num_centro_pop,
        total_familias_situacao_rua_cadunico,
        familias_situacao_rua_beneficiarias_bolsa_familia,
        qtd_pobreza_cadunico,
        qtd_baixa_renda_cadunico,
        qtd_acima_meio_salario_minimo_cadunico
    FROM dem_rua.vw_pop
    WHERE cd_mun = (
        SELECT cd_mun::int FROM carac_mun.caracteristicas_municipais
        WHERE nm_mun = %s AND sigla_uf = %s
    )
      AND ano IN (2022, 2026)
"""


def buscar_populacao_rua(
    nome_municipio: str, sigla_uf: str
) -> dict[str, object] | None:
    linhas = executar_query(
        POP_RUA_MUNICIPIO,
        (nome_municipio, sigla_uf),
        f"população em situação de rua de '{nome_municipio} ({sigla_uf})'",
        buscar_todas=True,
    )
    if not linhas:
        return None

    por_ano = {linha[0]: linha[1:] for linha in linhas}
    atual = por_ano.get(2026) or por_ano.get(2022)
    antigo = por_ano.get(2022)
    if atual is None:
        return None
    (pop_rua_total, criancas, pcd, idosos, centros_pop, familias_total,
     familias_bf, pobreza, baixa_renda, acima_meio) = atual
    dados = {
        "pop_rua_total": pop_rua_total, "pop_rua_2026": pop_rua_total,
        "pop_rua_criancas_adolescentes": criancas, "pop_rua_pcd": pcd,
        "pop_rua_idosos": idosos, "centros_pop": centros_pop,
        "familias_rua_total": familias_total, "familias_rua_bf": familias_bf,
        "pop_rua_bolsaf_2026": familias_bf, "pobreza_cadunico": pobreza,
        "baixa_renda_cadunico": baixa_renda,
        "acima_meio_sm_cadunico": acima_meio,
    }
    if familias_total:
        dados["pop_rua_pobreza_per"] = round(float(pobreza) / float(familias_total) * 100, 1)
        dados["pop_rua_br_per"] = round(float(baixa_renda) / float(familias_total) * 100, 1)
        dados["pop_rua_acima_br_per"] = round(float(acima_meio) / float(familias_total) * 100, 1)
    if antigo is not None:
        pop_2022, _, _, _, _, _, bf_2022, _, _, _ = antigo
        dados["pop_rua_2022"] = pop_2022
        dados["pop_rua_bolsaf_2022"] = bf_2022
        dados["var_pop_rua_abs"] = abs(pop_rua_total - pop_2022)
        dados["var_pop_rua_analise"] = "aumento" if pop_rua_total >= pop_2022 else "redução"
        dados["pop_rua_bolsaf_analise"] = "aumentou" if familias_bf >= bf_2022 else "diminuiu"
    return {campo: valor for campo, valor in dados.items() if valor is not None}
