from utils.queries.base import escalar_valor as _escalar_valor
from utils.queries.base import executar_query

DADOS_PIB_MUNICIPAL = """
    SELECT
        p.ano,
        p.pib_total,
        p.pib_per_capita,
        p.vab_agropecuaria,
        p.vab_industria,
        p.vab_servicos,
        p.vab_adm_publica,
        p.impostos_liquidos,
        p.atividade_maior_vab,
        p.vab_setor_maior
    FROM eco_pib.pib_municipal p
    JOIN carac_mun.caracteristicas_municipais c ON c.cd_mun::int = p.cd_mun::int
    WHERE LOWER(c.nm_mun) = LOWER(%s)
      AND c.sigla_uf = %s
      AND p.ano BETWEEN 2010 AND 2023
    ORDER BY p.ano
"""

_SETORES_VAB = {
    "vab_agropecuaria": "Agropecuária",
    "vab_industria": "Indústria",
    "vab_servicos": "Serviços",
    "vab_adm_publica": "Administração Pública",
}

_COLUNAS_LINHA_PIB = (
    "ano",
    "pib_total",
    "pib_per_capita",
    "vab_agropecuaria",
    "vab_industria",
    "vab_servicos",
    "vab_adm_publica",
    "impostos_liquidos",
    "atividade_maior_vab",
    "vab_setor_maior",
)


def _variacao_pib(pib_2010: object, pib_2023: object) -> tuple[object, object]:
    if pib_2010 is None or pib_2023 is None:
        return None, None
    pib_2010, pib_2023 = float(pib_2010), float(pib_2023)
    variacao_nominal = pib_2023 - pib_2010
    variacao_percentual = (variacao_nominal / pib_2010 * 100) if pib_2010 else None
    return variacao_nominal, variacao_percentual


def _setores_maiores_vab(linha: dict, top: int = 3) -> list[tuple[str, float]]:
    vabs = {
        nome: float(linha[coluna])
        for coluna, nome in _SETORES_VAB.items()
        if linha.get(coluna) is not None
    }
    return sorted(vabs.items(), key=lambda item: item[1], reverse=True)[:top]


def buscar_linhas_pib_municipal(nome_municipio: str, sigla_uf: str) -> list[dict]:
    """Busca, em uma única consulta, todas as linhas anuais de PIB do município.

    Alimenta tanto a série completa (gráfico) quanto os indicadores pontuais
    (2010/2021/2023), evitando duas consultas redundantes à mesma tabela.
    """
    linhas = executar_query(
        DADOS_PIB_MUNICIPAL,
        (nome_municipio, sigla_uf),
        f"dados de PIB de '{nome_municipio} ({sigla_uf})'",
        buscar_todas=True,
    )
    if not linhas:
        return []
    return [dict(zip(_COLUNAS_LINHA_PIB, linha)) for linha in linhas]


def processar_pib_evolucao(linhas: list[dict]) -> dict[str, object] | None:
    serie = [
        {"ano": linha["ano"], "pib_total": linha["pib_total"]}
        for linha in linhas
        if linha.get("ano") is not None and linha.get("pib_total") is not None
    ]
    return {"pib_serie": serie} if serie else None


def processar_indicadores_economia(linhas: list[dict]) -> dict[str, object] | None:
    if not linhas:
        return None

    por_ano = {linha["ano"]: linha for linha in linhas}
    linha_2010 = por_ano.get(2010, {})
    linha_2021 = por_ano.get(2021, {})
    linha_2023 = por_ano.get(2023, {})

    dados = {
        "pib_2010": linha_2010.get("pib_total"),
        "pib_2023": linha_2023.get("pib_total"),
        "pibcapita_2023": linha_2023.get("pib_per_capita"),
        "vab_agropecuaria": linha_2021.get("vab_agropecuaria"),
        "vab_industria": linha_2021.get("vab_industria"),
        "vab_servicos": linha_2021.get("vab_servicos"),
        "vab_adm_publica": linha_2021.get("vab_adm_publica"),
        "imposto": linha_2021.get("impostos_liquidos"),
    }
    if all(valor is None for valor in dados.values()):
        return None

    analise1_pib, analise1_pib_per = _variacao_pib(dados["pib_2010"], dados["pib_2023"])
    setores2021 = _setores_maiores_vab(dados)

    pib_2010, pib_unid_2010 = _escalar_valor(dados["pib_2010"])
    pib_2023, pib_unid_2023 = _escalar_valor(dados["pib_2023"])
    pibcapita_2023, pibcapita_unid_2023 = _escalar_valor(dados["pibcapita_2023"])
    imposto, imposto_unid = _escalar_valor(dados["imposto"])
    analise1_pib, analise1_pib_unid = _escalar_valor(analise1_pib)

    resultado = {
        "pib_2010": pib_2010,
        "pib_unid_2010": pib_unid_2010,
        "pib_2023": pib_2023,
        "pib_unid_2023": pib_unid_2023,
        "pibcapita_2023": pibcapita_2023,
        "pibcapita_unid_2023": pibcapita_unid_2023,
        "analise1_pib": analise1_pib,
        "analise1_pib_unid": analise1_pib_unid,
        "analise1_pib_per": analise1_pib_per,
        "imposto": imposto,
        "imposto_unid": imposto_unid,
    }
    # setor2021_maior{1,2,3}: os 3 setores de maior VAB em 2021, com nome,
    # valor escalado e unidade de escala de cada um.
    for posicao, (nome_setor, valor_vab) in enumerate(setores2021, start=1):
        valor_escalado, unidade = _escalar_valor(valor_vab)
        resultado[f"setor2021_maior{posicao}"] = nome_setor
        resultado[f"setor2021_valor{posicao}"] = valor_escalado
        resultado[f"setor2021_unid{posicao}"] = unidade

    # Atividade econômica (CNAE) de maior VAB em 2021, mais granular que os 4
    # setores agregados acima; participação = VAB da atividade / PIB total.
    atividade_maior_vab = linha_2021.get("atividade_maior_vab")
    vab_setor_maior = linha_2021.get("vab_setor_maior")
    pib_total_2021 = linha_2021.get("pib_total")
    if atividade_maior_vab is not None and vab_setor_maior is not None and pib_total_2021:
        resultado["ativ_participacao_pib"] = atividade_maior_vab
        resultado["ativ_participacao_pibper"] = (
            float(vab_setor_maior) / float(pib_total_2021) * 100
        )

    return resultado
