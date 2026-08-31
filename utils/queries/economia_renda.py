from utils.queries.base import executar_query

INDICADORES_ECONOMIA = """
    SELECT
        MAX(p.pib_total) FILTER (WHERE p.ano = 2010) AS pib_2010,
        MAX(p.pib_total) FILTER (WHERE p.ano = 2023) AS pib_2023,
        MAX(p.pib_per_capita) FILTER (WHERE p.ano = 2023) AS pibcapita_2023,
        MAX(p.vab_agropecuaria) FILTER (WHERE p.ano = 2021) AS vab_agropecuaria,
        MAX(p.vab_industria) FILTER (WHERE p.ano = 2021) AS vab_industria,
        MAX(p.vab_servicos) FILTER (WHERE p.ano = 2021) AS vab_servicos,
        MAX(p.vab_adm_publica) FILTER (WHERE p.ano = 2021) AS vab_adm_publica,
        MAX(p.impostos_liquidos) FILTER (WHERE p.ano = 2021) AS imposto
    FROM eco_pib.pib_municipal p
    JOIN carac_mun.caracteristicas_municipais c ON c.cd_mun::int = p.cd_mun::int
    WHERE LOWER(c.nm_mun) = LOWER(%s)
      AND c.sigla_uf = %s
      AND p.ano IN (2010, 2021, 2023)
"""

_SETORES_VAB = {
    "vab_agropecuaria": "Agropecuária",
    "vab_industria": "Indústria",
    "vab_servicos": "Serviços",
    "vab_adm_publica": "Administração Pública",
}


def _escalar_valor(valor: object) -> tuple[object, object]:
    if valor is None:
        return None, None
    valor = float(valor)
    if valor >= 1_000_000_000:
        return valor / 1_000_000_000, "bilhões"
    if valor >= 1_000_000:
        return valor / 1_000_000, "milhões"
    if valor >= 1_000:
        return valor / 1_000, "mil"
    return valor, ""


def _variacao_pib(pib_2010: object, pib_2023: object) -> tuple[object, object]:
    if pib_2010 is None or pib_2023 is None:
        return None, None
    pib_2010, pib_2023 = float(pib_2010), float(pib_2023)
    variacao_nominal = pib_2023 - pib_2010
    variacao_percentual = (variacao_nominal / pib_2010 * 100) if pib_2010 else None
    return variacao_nominal, variacao_percentual


def _setor_maior_vab(linha: dict) -> tuple[object, object]:
    vabs = {
        nome: float(linha[coluna])
        for coluna, nome in _SETORES_VAB.items()
        if linha.get(coluna) is not None
    }
    if not vabs:
        return None, None
    setor, valor = max(vabs.items(), key=lambda item: item[1])
    return setor, valor


def buscar_indicadores_economia(nome_municipio: str, sigla_uf: str) -> dict[str, object] | None:
    linha = executar_query(
        INDICADORES_ECONOMIA,
        (nome_municipio, sigla_uf),
        f"indicadores de economia de '{nome_municipio} ({sigla_uf})'",
    )
    if not linha or all(valor is None for valor in linha):
        return None

    colunas = (
        "pib_2010",
        "pib_2023",
        "pibcapita_2023",
        "vab_agropecuaria",
        "vab_industria",
        "vab_servicos",
        "vab_adm_publica",
        "imposto",
    )
    dados = dict(zip(colunas, linha))

    analise1_pib, analise1_pib_per = _variacao_pib(dados["pib_2010"], dados["pib_2023"])
    setor2021_maior, setor2021 = _setor_maior_vab(dados)

    pib_2023, pib_unid_2023 = _escalar_valor(dados["pib_2023"])
    pibcapita_2023, pibcapita_unid_2023 = _escalar_valor(dados["pibcapita_2023"])
    imposto, imposto_unid = _escalar_valor(dados["imposto"])
    setor2021, setor2021_maior_unid = _escalar_valor(setor2021)

    return {
        "pib_2010": dados["pib_2010"],
        "pib_2023": pib_2023,
        "pib_unid_2023": pib_unid_2023,
        "pibcapita_2023": pibcapita_2023,
        "pibcapita_unid_2023": pibcapita_unid_2023,
        "analise1_pib": analise1_pib,
        "analise1_pib_per": analise1_pib_per,
        "setor2021_maior": setor2021_maior,
        "setor2021": setor2021,
        "setor2021_maior_unid": setor2021_maior_unid,
        "imposto": imposto,
        "imposto_unid": imposto_unid,
    }


PIB_EVOLUCAO = """
    SELECT
        p.ano,
        p.pib_total
    FROM eco_pib.pib_municipal p
    JOIN carac_mun.caracteristicas_municipais c ON c.cd_mun::int = p.cd_mun::int
    WHERE LOWER(c.nm_mun) = LOWER(%s)
      AND c.sigla_uf = %s
      AND p.ano BETWEEN 2010 AND 2023
    ORDER BY p.ano
"""


def buscar_pib_evolucao(nome_municipio: str, sigla_uf: str) -> dict[str, object] | None:
    linhas = executar_query(
        PIB_EVOLUCAO,
        (nome_municipio, sigla_uf),
        f"evolução do PIB de '{nome_municipio} ({sigla_uf})'",
        buscar_todas=True,
    )
    if not linhas:
        return None

    serie = [
        {"ano": ano, "pib_total": pib_total}
        for ano, pib_total in linhas
        if ano is not None and pib_total is not None
    ]
    return {"pib_serie": serie} if serie else None
