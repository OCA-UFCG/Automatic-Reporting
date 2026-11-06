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
