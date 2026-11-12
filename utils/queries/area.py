"""Contexto de área de interesse de um tema: a linha da área na matview de área do tema."""

from utils.queries.base import executar_query_dict

# Matview de área de cada tema (schema auto_relatorios_areaint, da equipe de dados). As
# colunas são as municipais com o prefixo `area_`, e as 6 primeiras vêm da areaint_geral
# (area_nome, area_sujeito "A Caatinga", area_em, area_de…). Desenvolvimento social e
# Instrumentos Sudene não têm. O TemaLab (services/laboratorio_snapshot.py) lê este
# mesmo mapa: os dois nunca leem matviews diferentes.
MATVIEW_AREA_POR_MACROTEMA = {
    "demografia": "areaint_demografia",
    "educacao": "areaint_educacao",
    "saude": "areaint_saude",
    "economia-renda": "areaint_economia",
    "hidraulica": "areaint_seg_hidrica",
    "meio-ambiente": "areaint_ambiente",
    "saneamento": "areaint_infraestrutura",
}


def buscar_contexto_area(slug: str, area: str) -> dict | None:
    """A linha da área na matview de área do tema, como contexto do relatório. None
    quando o tema não tem matview de área, a área não está nela ou o banco falhou
    (executar_query_dict engole o erro: o relatório degrada, não dá 500).

    Ex.: buscar_contexto_area("demografia", "Caatinga")["area_sujeito"] == "A Caatinga"
    """
    view = MATVIEW_AREA_POR_MACROTEMA.get(slug)
    if view is None:
        return None
    # `view` vem do dicionário acima, nunca do usuário; a área vai como parâmetro.
    return executar_query_dict(
        f"SELECT * FROM auto_relatorios_areaint.{view} WHERE area_nome = %s",
        (area,),
        f"contexto de área de {slug} para {area!r}",
    )
