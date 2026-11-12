"""Áreas de interesse que têm relatório próprio, ao lado dos municípios e estados.

Os nomes são exatamente os da coluna `area_nome` das matviews de área
(`auto_relatorios_areaint.areaint_*`, conferido no banco em 08/11/2026): é por ela que
utils/queries/area.py acha a linha da área. Na ordem de `area_cd`.
"""

# Quais áreas existem é decisão da equipe de dados. O TemaLab lê a lista do banco; aqui
# ela fica fixa, como a dos estados, para o portal achar a área mesmo com o banco fora
# (André, 12/11/2026). Uma área nova nas matviews entra também aqui.
AREAS_COM_RELATORIO: tuple[str, ...] = (
    "Caatinga",
    "Área de atuação da Sudene",
    "Semiárido",
    "Nordeste",
)

_AREA_POR_CHAVE = {area.casefold(): area for area in AREAS_COM_RELATORIO}


def resolver_area(nome: str) -> str | None:
    """Nome canônico da área, tolerante a caixa e espaços nas pontas; None quando o
    nome não é de uma área com relatório (um município ou um estado, por exemplo).

    Ex.: resolver_area(" semiárido ") == "Semiárido"; resolver_area("Paraíba") is None
    """
    return _AREA_POR_CHAVE.get(nome.strip().casefold())
