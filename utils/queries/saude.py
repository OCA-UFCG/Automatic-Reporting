from utils.queries.base import executar_query

PUBLICO_ETARIO_VACINAS = """
    SELECT
        -- Público-alvo por faixa etária
        COALESCE(SUM(CASE WHEN i.categoria = 'Ao nascer' THEN i.populacao ELSE 0 END), 0) as publico_etario_ao_nascer,
        COALESCE(SUM(CASE WHEN i.categoria = 'Menores de 1 ano de idade' THEN i.populacao ELSE 0 END), 0) as publico_etario_menor_1_ano,
        COALESCE(SUM(CASE WHEN i.categoria = '1 ano de idade' THEN i.populacao ELSE 0 END), 0) as publico_etario_1_ano,
        COALESCE(SUM(CASE WHEN i.categoria = 'Multifaixa etária' THEN i.populacao ELSE 0 END), 0) as publico_etario_multifaixa,
        -- Doses aplicadas por faixa etária
        COALESCE(SUM(CASE WHEN i.categoria = 'Ao nascer' THEN i.doses_aplicadas ELSE 0 END), 0) as dose_etario_ao_nascer,
        COALESCE(SUM(CASE WHEN i.categoria = 'Menores de 1 ano de idade' THEN i.doses_aplicadas ELSE 0 END), 0) as dose_etario_menor_1_ano,
        COALESCE(SUM(CASE WHEN i.categoria = '1 ano de idade' THEN i.doses_aplicadas ELSE 0 END), 0) as dose_etario_1_ano,
        COALESCE(SUM(CASE WHEN i.categoria = 'Multifaixa etária' THEN i.doses_aplicadas ELSE 0 END), 0) as dose_etario_multifaixa
    FROM sau_imunizacao.vw_imunizacao_anual_2024 i
    JOIN carac_mun.caracteristicas_municipais c
        ON i.cd_mun = c.cd_mun::int
    WHERE c.nm_mun = %s
      AND c.sigla_uf = %s
"""


COBERTURA_VACINAL = """
    SELECT
        i.vacina,
        i.cobertura_vacinal
    FROM sau_imunizacao.vw_imunizacao_anual_2024 i
    JOIN carac_mun.caracteristicas_municipais c
        ON i.cd_mun = c.cd_mun::int
    WHERE c.nm_mun = %s
      AND c.sigla_uf = %s
      AND i.cobertura_vacinal IS NOT NULL
    ORDER BY i.cobertura_vacinal DESC
"""


def buscar_cobertura_vacinal(
    nome_municipio: str, sigla_uf: str
) -> dict[str, object] | None:
    linhas = executar_query(
        COBERTURA_VACINAL,
        (nome_municipio, sigla_uf),
        f"cobertura vacinal de '{nome_municipio} ({sigla_uf})'",
        buscar_todas=True,
    )
    if not linhas:
        return None

    serie = [
        {"vacina": vacina, "cobertura_vacinal": cobertura_vacinal}
        for vacina, cobertura_vacinal in linhas
        if vacina is not None and cobertura_vacinal is not None
    ]
    return {"cobertura_vacinal_serie": serie} if serie else None


MORTALIDADE_INFANTIL_SERIE = """
    SELECT
        m.ano,
        ROUND((m.obitos_infantis::numeric / NULLIF(m.nascidos, 0)) * 1000, 2) AS taxa_mortalidade
    FROM sau_mortalidade.vw_mortalidade m
    JOIN carac_mun.caracteristicas_municipais c
        ON m.cd_mun = c.cd_mun::int
    WHERE c.nm_mun = %s
      AND c.sigla_uf = %s
    ORDER BY m.ano
"""


def buscar_mortalidade_infantil_serie(
    nome_municipio: str, sigla_uf: str
) -> dict[str, object] | None:
    linhas = executar_query(
        MORTALIDADE_INFANTIL_SERIE,
        (nome_municipio, sigla_uf),
        f"série histórica de mortalidade infantil de '{nome_municipio} ({sigla_uf})'",
        buscar_todas=True,
    )
    if not linhas:
        return None

    serie = [
        {"ano": ano, "taxa_mortalidade": taxa_mortalidade}
        for ano, taxa_mortalidade in linhas
        if ano is not None and taxa_mortalidade is not None
    ]
    return {"mortalidade_infantil_serie": serie} if serie else None


ESTABELECIMENTOS_SAUDE_SERIE = """
    SELECT
        e.ano,
        SUM(e.total) AS total_estabelecimentos
    FROM sau_estabelecimento_de_saude.estabelecimento_saude e
    JOIN carac_mun.caracteristicas_municipais c
        ON e.cd_mun = c.cd_mun::int
    WHERE c.nm_mun = %s
      AND c.sigla_uf = %s
    GROUP BY e.ano
    ORDER BY e.ano
"""


def buscar_estabelecimentos_saude_serie(
    nome_municipio: str, sigla_uf: str
) -> dict[str, object] | None:
    linhas = executar_query(
        ESTABELECIMENTOS_SAUDE_SERIE,
        (nome_municipio, sigla_uf),
        f"série histórica de estabelecimentos de saúde de '{nome_municipio} ({sigla_uf})'",
        buscar_todas=True,
    )
    if not linhas:
        return None

    serie = [
        {"ano": ano, "total_estabelecimentos": total}
        for ano, total in linhas
        if ano is not None and total is not None
    ]
    return {"estabelecimentos_saude_serie": serie} if serie else None


PERFIL_SAUDE_MUNICIPAL = """
    SELECT
        dose_aplicada,
        pop_alvo_vacina,
        vacina_maior1,
        vacina_maior1_per,
        vacina_maior2,
        vacina_maior2_per,
        vacina_menor1,
        vacina_menor1_per,
        vacina_menor2,
        vacina_menor2_per,
        vacina_menor3,
        vacina_menor3_per,
        vacina_meta,
        vacina_nao_meta,
        obitos,
        nascidos,
        mortalidade_2024,
        mortalidade_2025,
        var_mortalidade_per,
        analise_mortalidade,
        ano_menor_mortalidade,
        media_porte_mortalidade,
        analise_porte_mortalidade,
        mortalidade_brasil,
        analise_mortalidade_brasil,
        estabelecimento_2010,
        estabelecimento_2025,
        analise_estabel_2010_2025,
        var_estabel_2010_2025,
        var_estabel_analise,
        estabel_maior_1,
        nome_estabel_maior_1,
        estabel_maior_2,
        nome_estabel_maior_2,
        estabel_maior_3,
        nome_estabel_maior_3,
        estabel_maior_4,
        nome_estabel_maior_4,
        grupo_estabel_maior1,
        n_estabel_maior1,
        grupo_estabel_maior2,
        n_estabel_maior2,
        ubs_10mil
    FROM relatorios_auto.vw_perfil_saude_municipal
    WHERE nm_mun = %s
      AND sigla_uf = %s
"""


def _analise_variacao(variacao_per) -> str | None:
    if variacao_per is None:
        return None
    try:
        valor = float(variacao_per)
    except (TypeError, ValueError):
        return None
    if valor > 0:
        return "aumento"
    if valor < 0:
        return "redução"
    return "estabilidade"


def buscar_perfil_saude_municipal(
    nome_municipio: str, sigla_uf: str
) -> dict[str, object] | None:
    linha = executar_query(
        PERFIL_SAUDE_MUNICIPAL,
        (nome_municipio, sigla_uf),
        f"perfil de saúde de '{nome_municipio} ({sigla_uf})'",
    )
    if linha is None:
        return None

    (
        dose_aplicada,
        pop_alvo_vacina,
        vacina_maior1,
        vacina_maior1_per,
        vacina_maior2,
        vacina_maior2_per,
        vacina_menor1,
        vacina_menor1_per,
        vacina_menor2,
        vacina_menor2_per,
        vacina_menor3,
        vacina_menor3_per,
        vacina_meta,
        vacina_nao_meta,
        obitos,
        nascidos,
        mortalidade_2024,
        mortalidade_2025,
        var_mortalidade_per,
        analise_mortalidade,
        ano_menor_mortalidade,
        media_porte_mortalidade,
        analise_porte_mortalidade,
        mortalidade_brasil,
        analise_mortalidade_brasil,
        estabelecimento_2010,
        estabelecimento_2025,
        analise_estabel_2010_2025,
        var_estabel_2010_2025,
        var_estabel_analise,
        estabel_maior_1,
        nome_estabel_maior_1,
        estabel_maior_2,
        nome_estabel_maior_2,
        estabel_maior_3,
        nome_estabel_maior_3,
        estabel_maior_4,
        nome_estabel_maior_4,
        grupo_estabel_maior1,
        n_estabel_maior1,
        grupo_estabel_maior2,
        n_estabel_maior2,
        ubs_10mil,
    ) = linha

    dados = {
        "dose_aplicada": dose_aplicada,
        "pop_alvo_vacina": pop_alvo_vacina,
        "vacina_maior1": vacina_maior1,
        "vacina_maior1_per": vacina_maior1_per,
        "vacina_maior2": vacina_maior2,
        "vacina_maior2_per": vacina_maior2_per,
        "vacina_menor1": vacina_menor1,
        "vacina_menor1_per": vacina_menor1_per,
        "vacina_menor2": vacina_menor2,
        "vacina_menor2_per": vacina_menor2_per,
        "vacina_menor3": vacina_menor3,
        "vacina_menor3_per": vacina_menor3_per,
        "vacina_meta": vacina_meta,
        "vacina_nao_meta": vacina_nao_meta,
        "obitos": obitos,
        "nascidos": nascidos,
        "mortalidade_2024": mortalidade_2024,
        "mortalidade_2025": mortalidade_2025,
        "var_mortalidade_per": var_mortalidade_per,
        "analise_mortalidade_2024_2025": _analise_variacao(var_mortalidade_per),
        "analise_mortalidade": analise_mortalidade,
        "ano_menor_mortalidade": (
            str(ano_menor_mortalidade) if ano_menor_mortalidade is not None else None
        ),
        "media_porte_mortalidade": media_porte_mortalidade,
        "analise_porte_mortalidade": analise_porte_mortalidade,
        "mortalidade_nacional": mortalidade_brasil,
        "analise_nacional_mortalidade": analise_mortalidade_brasil,
        "estabelecimento_2010": estabelecimento_2010,
        "estabelecimento_2025": estabelecimento_2025,
        "analise_estabel_2010_2025": analise_estabel_2010_2025,
        "var_estabel_2010_2025": var_estabel_2010_2025,
        "var_estabel_analise": var_estabel_analise,
        "estabel_maior_1": estabel_maior_1,
        "nome_estabel_maior_1": nome_estabel_maior_1,
        "estabel_maior_2": estabel_maior_2,
        "nome_estabel_maior_2": nome_estabel_maior_2,
        "estabel_maior_3": estabel_maior_3,
        "nome_estabel_maior_3": nome_estabel_maior_3,
        "estabel_maior_4": estabel_maior_4,
        "nome_estabel_maior_4": nome_estabel_maior_4,
        "grupo_estabel_maior1": grupo_estabel_maior1,
        "n_estabelec_maior1": n_estabel_maior1,
        "grupo_estabel_maior2": grupo_estabel_maior2,
        "n_estabelec_maior2": n_estabel_maior2,
        "ubs_10mil": ubs_10mil,
    }
    return {campo: valor for campo, valor in dados.items() if valor is not None}


def buscar_publico_etario_vacinas(
    nome_municipio: str, sigla_uf: str
) -> dict[str, object] | None:
    linha = executar_query(
        PUBLICO_ETARIO_VACINAS,
        (nome_municipio, sigla_uf),
        f"público-etário de vacinas de '{nome_municipio} ({sigla_uf})'",
    )
    if linha is None:
        return None

    (
        publico_etario_ao_nascer,
        publico_etario_menor_1_ano,
        publico_etario_1_ano,
        publico_etario_multifaixa,
        dose_etario_ao_nascer,
        dose_etario_menor_1_ano,
        dose_etario_1_ano,
        dose_etario_multifaixa,
    ) = linha

    dados = {
        "publico_etario_ao_nascer": publico_etario_ao_nascer,
        "publico_etario_menor_1_ano": publico_etario_menor_1_ano,
        "publico_etario_1_ano": publico_etario_1_ano,
        "publico_etario_multifaixa": publico_etario_multifaixa,
        "dose_etario_ao_nascer": dose_etario_ao_nascer,
        "dose_etario_menor_1_ano": dose_etario_menor_1_ano,
        "dose_etario_1_ano": dose_etario_1_ano,
        "dose_etario_multifaixa": dose_etario_multifaixa,
    }
    return {campo: valor for campo, valor in dados.items() if valor is not None}