from utils.queries.base import executar_query_dict

VIEW_POR_MACROTEMA = {
    "demografia": "vw_perfil_populacional_municipal",
    "educacao": "vw_perfil_educacional_municipal",
    "saude": "vw_perfil_saude_municipal",
    "economia-renda": "vw_perfil_economia_e_renda",
    "saneamento": "vw_perfil_infraestrutura_municipal",
    "hidraulica": "vw_seguranca_hidrica",
}


def buscar_perfil_municipal(
    macrotema_slug: str, nome_municipio: str, sigla_uf: str
) -> dict | None:
    """Busca a linha completa (fonte primária) de um macrotema na view
    `relatorios_auto.vw_perfil_*` correspondente. Retorna None se o macrotema
    não tiver view mapeada ou se a cidade não for encontrada."""
    view = VIEW_POR_MACROTEMA.get(macrotema_slug)
    if not view:
        return None

    query = f"""
        SELECT * FROM relatorios_auto.{view}
        WHERE LOWER(nm_mun) = LOWER(%s) AND sigla_uf = %s
        LIMIT 1
    """
    contexto = f"perfil municipal ({view}) de '{nome_municipio} ({sigla_uf})'"

    linha = executar_query_dict(query, (nome_municipio, sigla_uf), contexto)
    if linha:
        return linha

    # vw_perfil_educacional_municipal guarda nm_mun já com o sufixo "(UF)"
    # embutido (inconsistência da própria view); tenta essa variação antes
    # de considerar a cidade ausente do banco.
    nome_com_uf = f"{nome_municipio} ({sigla_uf})"
    return executar_query_dict(query, (nome_com_uf, sigla_uf), contexto)
