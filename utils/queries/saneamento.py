from utils.queries.base import executar_query_dict

# Categorias de esgotamento sanitário (Censo 2022), na ordem em que aparecem no
# gráfico de rosca do Doc. Cada coluna é a contagem de domicílios naquela
# categoria; `total` é o denominador (centro da rosca).
CATEGORIAS_ESGOTAMENTO = (
    ("esg_rede_geral_ou_pluvial", "rede_geral_ou_pluvial"),
    ("esg_fossa_septica_ou_fossa_filtro", "fossa_septica_ou_fossa_filtro"),
    ("esg_fossa_rudimentar_ou_buraco", "fossa_rudimentar_ou_buraco"),
    ("esg_vala", "vala"),
    ("esg_rio_lago_corrego_ou_mar", "rio_lago_corrego_ou_mar"),
    ("esg_outra_forma", "outra_forma"),
    ("esg_nao_tinham_banheiro", "nao_tinham_banheiro_e_ou_sanitario"),
)


def buscar_esgotamento_sanitario(nome_municipio: str, sigla_uf: str) -> dict | None:
    """Distribuição de domicílios por tipo de esgotamento sanitário (2022) para o
    gráfico de rosca. Fonte crua: `infra_esgotamento_sanitario.view_esgotamento_2022`
    (a view-perfil não traz as categorias detalhadas). Retorna dict achatado com
    `esg_total` + uma chave por categoria, ou None se a cidade não estiver na view."""
    colunas = ", ".join(coluna for _, coluna in CATEGORIAS_ESGOTAMENTO)
    query = f"""
        SELECT total AS esg_total, {colunas}
        FROM infra_esgotamento_sanitario.view_esgotamento_2022
        WHERE LOWER(regexp_replace(nm_mun, '\\s*\\([^)]*\\)\\s*$', '')) = LOWER(%s)
          AND sigla_uf = %s
        LIMIT 1
    """
    contexto = f"esgotamento sanitário 2022 de '{nome_municipio} ({sigla_uf})'"
    linha = executar_query_dict(query, (nome_municipio, sigla_uf), contexto)
    if not linha:
        return None
    return {chave: linha[coluna] for chave, coluna in
            (("esg_total", "esg_total"), *CATEGORIAS_ESGOTAMENTO)}
