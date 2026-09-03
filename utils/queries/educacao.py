from utils.queries.base import executar_query

COLUNAS_PERFIL_EDUCACIONAL = [
    "nm_mun",
    "estado",
    "sigla_uf",
    "ano",
    "pri_nivel_classe",
    "pri_nivel_per",
    "pri_nivel_pop",
    "seg_nivel_classe",
    "seg_nivel_per",
    "seg_nivel_pop",
    "ter_nivel_classe",
    "ter_nivel_per",
    "ter_nivel_pop",
    "quar_nivel_classe",
    "quar_nivel_per",
    "quar_nivel_pop",
    "alfabetizado_per",
    "tend_sem_instr",
    "sem_instr_2000",
    "sem_instr_2022",
    "tend_nivel_sup",
    "fund_comp_per",
    "comp_fund_br",
    "sup_comp_per",
    "comp_sup_br",
    "sup_comp_mulher",
    "sup_comp_homem",
    "comp_alfab_pne",
    "analf_faixa_maior",
    "pri_cor_analf",
    "pri_cor_analf_per",
    "seg_cor_analf",
    "ter_cor_analf",
    "inter_cor_analf_per",
    "ult_cor_analf",
    "ult_cor_analf_per",
    "tend_sem_instr_per",
    "tend_nivel_sup_per",
    "comp_fund_br_per",
    "comp_sup_br_per",
    "comp_alfab_pne_per",
    "analf_faixa_menor",
    "sint_evolucao_per",
    "sint_evolucao",
]

PERFIL_EDUCACIONAL_MUNICIPIO = f"""
    SELECT {", ".join(COLUNAS_PERFIL_EDUCACIONAL)}
    FROM relatorios_auto.vw_perfil_educacional_municipal
    WHERE nm_mun = %s AND sigla_uf = %s
"""


def buscar_perfil_educacional_municipio(
    nome_municipio: str, sigla_uf: str
) -> dict[str, object] | None:
    linha = executar_query(
        PERFIL_EDUCACIONAL_MUNICIPIO,
        (f"{nome_municipio} ({sigla_uf})", sigla_uf),
        f"perfil educacional de '{nome_municipio} ({sigla_uf})'",
    )
    if linha is None:
        return None

    return dict(zip(COLUNAS_PERFIL_EDUCACIONAL, linha))

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
        WHERE nm_mun = %s AND sigla_uf = %s
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