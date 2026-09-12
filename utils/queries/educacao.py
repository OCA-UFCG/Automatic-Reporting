from utils.queries.base import executar_query

# O perfil educacional não mora mais aqui: ele vem de
# `utils.queries.perfil_municipal.buscar_perfil_municipal`, o mesmo caminho dos
# outros sete macrotemas. A lista fixa de colunas que existia neste arquivo
# ficou três colunas atrás de `relatorios_auto.vw_perfil_educacional_municipal`
# e fazia `$tend_ens_sup` sair cru no relatório; com `SELECT *` na view, coluna
# nova chega sozinha ao contexto.

# O gráfico de taxas por cor/faixa etária consulta edu_analfabetismo.vw_analfabetismo_2022,
# uma fonte diferente de relatorios_auto.vw_perfil_educacional_municipal (usada pelo texto
# acima). É intencional por ora: essa view não tem o detalhamento por cor/faixa etária que
# o gráfico precisa. Se um dia isso mudar, reavaliar se dá para unificar as duas consultas.
FAIXAS_ETARIAS_EDUCACAO = [
    ("15_a_19", "15 a 19 anos"),
    ("20_a_29", "20 a 29 anos"),
    ("30_a_39", "30 a 39 anos"),
    ("40_a_49", "40 a 49 anos"),
    ("50_a_59", "50 a 59 anos"),
    ("mais60", "60 anos ou mais"),
]

CORES_EDUCACAO = {
    "Amarela": "amarela",
    "Branca": "branca",
    "Indígena": "indigena",
    "Parda": "parda",
    "Preta": "preta",
}

TAXAS_EDUCACAO_POR_COR_FAIXA = """
    SELECT
        cor_ou_raca,
        faixa_etaria,
        sexo,
        COALESCE(SUM(alfabetizadas), 0) as alfabetizadas,
        COALESCE(SUM(total), 0) as total
    FROM edu_analfabetismo.vw_analfabetismo_2022
    WHERE cd_mun = (
        SELECT cd_mun::int FROM carac_mun.caracteristicas_municipais
        WHERE LOWER(nm_mun) = LOWER(%s) AND UPPER(sigla_uf) = UPPER(%s)
    )
      AND faixa_etaria IN (
        '15 a 19 anos', '20 a 29 anos', '30 a 39 anos',
        '40 a 49 anos', '50 a 59 anos', '60 anos ou mais'
    )
      AND cor_ou_raca IN ('Amarela', 'Branca', 'Indígena', 'Parda', 'Preta')
    GROUP BY cor_ou_raca, faixa_etaria, sexo
"""


def buscar_taxas_educacao_cor_faixa_etaria(
    nome_municipio: str, sigla_uf: str
) -> dict[str, object] | None:
    linhas = executar_query(
        TAXAS_EDUCACAO_POR_COR_FAIXA,
        (nome_municipio, sigla_uf),
        f"taxas de educação por cor/faixa etária de '{nome_municipio} ({sigla_uf})'",
        buscar_todas=True,
    )
    if not linhas:
        return None

    dados_agregados: dict[tuple[str, str], dict[str, int]] = {}
    for cor_ou_raca, faixa_etaria, _sexo, alfabetizadas, total in linhas:
        key = (cor_ou_raca, faixa_etaria)
        if key not in dados_agregados:
            dados_agregados[key] = {"alfabetizadas": 0, "total": 0}
        dados_agregados[key]["alfabetizadas"] += alfabetizadas
        dados_agregados[key]["total"] += total

    dados: dict[str, object] = {}
    for (cor, faixa), vals in dados_agregados.items():
        sufixo_cor = CORES_EDUCACAO[cor]
        sufixo_faixa = next(s for s, f in FAIXAS_ETARIAS_EDUCACAO if f == faixa)
        chave = f"taxa_{sufixo_faixa}_{sufixo_cor}"
        if vals["total"] > 0:
            taxa_analfabetismo = (
                (vals["total"] - vals["alfabetizadas"]) / vals["total"]
            ) * 100
            dados[chave] = round(taxa_analfabetismo, 2)
        else:
            dados[chave] = 0.0

    return dados or None