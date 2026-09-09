from utils.queries.base import executar_query_dict

VIEW_POR_MACROTEMA = {
    "demografia": "vw_perfil_populacional_municipal",
    "educacao": "vw_perfil_educacional_municipal",
    "saude": "vw_perfil_saude_municipal",
    "economia-renda": "vw_perfil_economia",
    "saneamento": "vw_perfil_infraestrutura_municipal",
    "hidraulica": "vw_seguranca_hidrica",
    "meio-ambiente": "vw_perfil_ambiente_municipal",
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

    # Algumas views (ex.: vw_perfil_educacional_municipal) guardam nm_mun já
    # com o sufixo "(UF)"; outras guardam só o nome. Compara sempre pelo nome
    # sem o parêntese final, o que casa os dois formatos numa única query.
    query = f"""
        SELECT * FROM relatorios_auto.{view}
        WHERE LOWER(regexp_replace(nm_mun, '\\s*\\([^)]*\\)\\s*$', '')) = LOWER(%s)
          AND sigla_uf = %s
        LIMIT 1
    """
    contexto = f"perfil municipal ({view}) de '{nome_municipio} ({sigla_uf})'"

    return executar_query_dict(query, (nome_municipio, sigla_uf), contexto)
