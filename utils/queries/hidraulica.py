from utils.queries.base import executar_query

TECNOLOGIAS_ACESSO_AGUA = """
    SELECT
        ano,
        tot_cisternas
    FROM hidr_cisternas.final_tecnologias_sociais_de_acesso_a_agua
    WHERE LOWER(nm_mun) = LOWER(%s)
      AND sigla_uf = %s
    ORDER BY ano
"""


def buscar_tecnologias_acesso_agua(
    nome_municipio: str, sigla_uf: str
) -> dict[str, object] | None:
    linhas = executar_query(
        TECNOLOGIAS_ACESSO_AGUA,
        (nome_municipio, sigla_uf),
        f"tecnologias sociais de acesso à água de '{nome_municipio} ({sigla_uf})'",
        buscar_todas=True,
    )
    if not linhas:
        return None

    serie = [
        {"ano": ano, "total": total}
        for ano, total in linhas
        if ano is not None and total is not None
    ]
    return {"tecnologias_acesso_agua_serie": serie} if serie else None
