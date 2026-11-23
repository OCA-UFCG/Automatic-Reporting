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


# INTENTIONAL: temas de área com Doc de texto fixo, sem `$area_*` (Rayane, 16/11/2026).
# Não há matview do tema e não vai haver: o contexto é só a linha da areaint_geral, que
# basta para a capa. O texto fala de uma área só (o de desenvolvimento social cita os
# 1.794 municípios do Nordeste), então o tema vale só para as áreas listadas; nas
# outras ele some do relatório, em vez de sair com os números de outra área.
AREAS_DO_TEMA_DE_TEXTO_FIXO: dict[str, tuple[str, ...]] = {
    "desenvolvimento-social": ("Nordeste",),
}


def buscar_contexto_area(slug: str, area: str) -> dict | None:
    """A linha da área na matview de área do tema, como contexto do relatório. None
    quando o tema não tem matview de área, a área não está nela ou o banco falhou
    (executar_query_dict engole o erro: o relatório degrada, não dá 500). Tema de
    texto fixo lê a areaint_geral, e só nas áreas de AREAS_DO_TEMA_DE_TEXTO_FIXO.

    Ex.: buscar_contexto_area("demografia", "Caatinga")["area_sujeito"] == "A Caatinga"
    """
    if slug in AREAS_DO_TEMA_DE_TEXTO_FIXO:
        return _contexto_do_tema_de_texto_fixo(slug, area)
    view = MATVIEW_AREA_POR_MACROTEMA.get(slug)
    if view is None:
        return None
    # `view` vem do dicionário acima, nunca do usuário; a área vai como parâmetro.
    return executar_query_dict(
        f"SELECT * FROM auto_relatorios_areaint.{view} WHERE area_nome = %s",
        (area,),
        f"contexto de área de {slug} para {area!r}",
    )


def _contexto_do_tema_de_texto_fixo(slug: str, area: str) -> dict | None:
    """A linha da área na areaint_geral, ou None fora das áreas do tema."""
    if area not in AREAS_DO_TEMA_DE_TEXTO_FIXO[slug]:
        return None
    return executar_query_dict(
        "SELECT * FROM auto_relatorios_areaint.areaint_geral WHERE area_nome = %s",
        (area,),
        f"contexto de área de {slug} (texto fixo) para {area!r}",
    )


def buscar_caracteristicas_area(area: str) -> dict | None:
    """A linha da área para a primeira página: a areaint_geral (area_cd, area_de, área
    territorial) com a de Demografia por cima, que traz a população
    (`demografia.$area_pop_total_2022` no Doc). None se a área não está em nenhuma
    das duas ou o banco falhou.

    Ex.: buscar_caracteristicas_area("Caatinga")["area_de"] == "da Caatinga"
    """
    geral = executar_query_dict(
        "SELECT * FROM auto_relatorios_areaint.areaint_geral WHERE area_nome = %s",
        (area,),
        f"características gerais da área {area!r}",
    )
    demografia = buscar_contexto_area("demografia", area)
    if geral is None and demografia is None:
        return None
    return {**(geral or {}), **(demografia or {})}
