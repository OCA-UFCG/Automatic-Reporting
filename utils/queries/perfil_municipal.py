from utils.queries.base import executar_query_dict

VIEW_POR_MACROTEMA = {
    "demografia": "vw_perfil_populacional_municipal",
    # Views pesadas materializadas (relatorios_auto.mv_perfil_*): a leitura da view
    # crua chega a >30s (economia) e é recalculada a cada relatório. A matview é um
    # snapshot rápido (~ms), atualizado por scripts/refresh_matviews.sh (cron diário
    # 04:00 UTC). Ver docs/matviews-perfil.md.
    "educacao": "mv_perfil_educacional_municipal",
    "saude": "mv_perfil_saude_municipal",
    "economia-renda": "mv_perfil_economia",
    "saneamento": "vw_perfil_infraestrutura_municipal",
    "hidraulica": "vw_seguranca_hidrica",
    "meio-ambiente": "ambiente",
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
    # com o sufixo "(UF)"; outras guardam só o nome (ex.: mv_perfil_saude_municipal
    # pra Recife). Compara sempre pelo nome sem o parêntese final dos dois lados —
    # só normalizar a coluna e comparar contra o `nome_municipio` já canonicalizado
    # como "Cidade (UF)" (generation.py) nunca casa quando a view não tem o
    # sufixo, e a cidade cai silenciosamente pro fallback de CSV mesmo com a
    # linha existindo na view (bug real: Recife (PE) em saúde).
    query = f"""
        SELECT * FROM relatorios_auto.{view}
        WHERE LOWER(regexp_replace(nm_mun, '\\s*\\([^)]*\\)\\s*$', '')) =
              LOWER(regexp_replace(%s, '\\s*\\([^)]*\\)\\s*$', ''))
          AND sigla_uf = %s
        LIMIT 1
    """
    contexto = f"perfil municipal ({view}) de '{nome_municipio} ({sigla_uf})'"

    return executar_query_dict(query, (nome_municipio, sigla_uf), contexto)
