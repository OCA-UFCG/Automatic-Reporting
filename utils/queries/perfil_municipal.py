from utils.queries.base import executar_query_dict, executar_query_dicts

VIEW_POR_MACROTEMA = {
    "demografia": "vw_perfil_populacional_municipal",
    "educacao": "vw_perfil_educacional_municipal",
    "saude": "vw_perfil_saude_municipal",
    "economia-renda": "vw_perfil_economia",
    "saneamento": "vw_perfil_infraestrutura_municipal",
    "hidraulica": "vw_seguranca_hidrica",
    "meio-ambiente": "vw_perfil_ambiente_municipal",
}

# `SELECT *` e não uma lista de colunas: a view é o contrato. Educação tinha até
# então uma lista fixa de colunas escrita à mão (`COLUNAS_PERFIL_EDUCACIONAL`),
# que ficou três colunas atrás da view — `tend_ens_sup` existia no banco, não
# chegava ao contexto e saía como `$tend_ens_sup` cru no PDF. Com `*`, coluna
# nova na view aparece sozinha em todos os macrotemas.
#
# Algumas views (ex.: vw_perfil_educacional_municipal) guardam nm_mun já com o
# sufixo "(UF)"; outras guardam só o nome. Compara sempre pelo nome sem o
# parêntese final, o que casa os dois formatos numa única query.
_SELECT_POR_NOME = """
    SELECT * FROM relatorios_auto.{view}
    WHERE LOWER(regexp_replace(nm_mun, '\\s*\\([^)]*\\)\\s*$', '')) = LOWER(%s)
"""


def buscar_perfil_municipal(
    macrotema_slug: str, nome_municipio: str, sigla_uf: str = ""
) -> dict | None:
    """Busca a linha completa (fonte primária) de um macrotema na view
    `relatorios_auto.vw_perfil_*` correspondente. Retorna None se o macrotema
    não tiver view mapeada ou se a cidade não for encontrada.

    Sem `sigla_uf`, resolve pelo nome e levanta `ValueError` quando o nome
    existe em mais de uma UF — quem chama transforma isso num 400 pedindo a UF.
    """
    view = VIEW_POR_MACROTEMA.get(macrotema_slug)
    if not view:
        return None

    if sigla_uf:
        query = (
            _SELECT_POR_NOME.format(view=view)
            + "  AND UPPER(sigla_uf) = UPPER(%s)\n    LIMIT 1\n"
        )
        contexto = f"perfil municipal ({view}) de '{nome_municipio} ({sigla_uf})'"
        return executar_query_dict(query, (nome_municipio, sigla_uf), contexto)

    contexto = f"perfil municipal ({view}) de '{nome_municipio}'"
    linhas = executar_query_dicts(
        _SELECT_POR_NOME.format(view=view), (nome_municipio,), contexto
    )
    if not linhas:
        return None

    ufs_encontradas = sorted({str(linha.get("sigla_uf") or "") for linha in linhas})
    if len(ufs_encontradas) > 1:
        raise ValueError(
            f"Cidade ambígua: '{nome_municipio}' encontrada em "
            f"{', '.join(ufs_encontradas)}. Indique o estado, ex: "
            f"'{nome_municipio} ({ufs_encontradas[0]})'"
        )

    return linhas[0]
