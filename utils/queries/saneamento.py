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


def buscar_esgotamento_sanitario_estado(sigla_uf: str) -> dict | None:
    """A mesma distribuição de buscar_esgotamento_sanitario, somando os municípios
    do estado (relatório por estado, 12/11/2026). A est_infraestrutura não traz
    fossa séptica nem "sem banheiro"; nas categorias que ela tem, e no total, a soma
    desta view confere com ela. None se o banco falhar.

    Ex.: buscar_esgotamento_sanitario_estado("PB")["esg_fossa_septica_ou_fossa_filtro"] == 251638
    """
    somas = ", ".join(f"SUM({coluna}) AS {coluna}" for _, coluna in CATEGORIAS_ESGOTAMENTO)
    query = f"""
        SELECT SUM(total) AS esg_total, {somas}
        FROM infra_esgotamento_sanitario.view_esgotamento_2022
        WHERE sigla_uf = %s
    """
    linha = executar_query_dict(query, (sigla_uf,), f"esgotamento sanitário 2022 do estado '{sigla_uf}'")
    if not linha or linha.get("esg_total") is None:
        return None
    return {chave: linha[coluna] for chave, coluna in
            (("esg_total", "esg_total"), *CATEGORIAS_ESGOTAMENTO)}
