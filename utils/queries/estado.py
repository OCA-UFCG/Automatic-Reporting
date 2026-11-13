"""Contexto estadual de um tema: a linha do estado na matview estadual do tema."""

from utils.queries.base import executar_query_dict

# Matview estadual de cada tema (schema auto_relatorios_est, da equipe de dados). As
# colunas são as municipais com o prefixo `uf_`, e as 6 primeiras vêm da est_geral
# (uf_estado, uf_sujeito "A Paraíba", uf_em, uf_de…). Instrumentos Sudene não tem.
# Mora aqui, e não em services/laboratorio_snapshot.py, desde que o relatório por
# estado também a lê (05/11/2026).
MATVIEW_ESTADUAL_POR_MACROTEMA = {
    "demografia": "est_demografia",
    "educacao": "est_educacao",
    "saude": "est_saude",
    "economia-renda": "est_economia",
    "hidraulica": "est_seg_hidrica",
    "desenvolvimento-social": "est_desen_social",
    "meio-ambiente": "est_ambiente",
    "saneamento": "est_infraestrutura",
}


def buscar_contexto_estado(slug: str, estado: str) -> dict | None:
    """A linha do estado na matview estadual do tema, como contexto do relatório.
    None quando o tema não tem matview estadual, o estado não está nela ou o banco
    falhou (executar_query_dict engole o erro: o relatório degrada, não dá 500).

    Ex.: buscar_contexto_estado("demografia", "Paraíba")["uf_sujeito"] == "A Paraíba"
    """
    view = MATVIEW_ESTADUAL_POR_MACROTEMA.get(slug)
    if view is None:
        return None
    # `view` vem do dicionário acima, nunca do usuário; o estado vai como parâmetro.
    return executar_query_dict(
        f"SELECT * FROM auto_relatorios_est.{view} WHERE uf_estado = %s",
        (estado,),
        f"contexto estadual de {slug} para {estado!r}",
    )


def buscar_caracteristicas_estado(estado: str) -> dict | None:
    """A linha do estado em est_caract_mun: área, população, sigla e as formas do nome
    (`uf_de`) que o Doc da primeira página usa com o prefixo `geral.`. As colunas não
    têm o prefixo `uf_` das matviews de tema. None se o estado não está lá ou o banco
    falhou (executar_query_dict engole o erro, como em buscar_contexto_estado).

    Ex.: buscar_caracteristicas_estado("Paraíba")["sigla_uf"] == "PB"
    """
    return executar_query_dict(
        "SELECT * FROM auto_relatorios_est.est_caract_mun WHERE estado = %s",
        (estado,),
        f"características gerais de {estado!r}",
    )
