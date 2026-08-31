from utils.queries.base import executar_query

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
