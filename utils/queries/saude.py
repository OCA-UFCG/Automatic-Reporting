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