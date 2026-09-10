"""Leitura do painel de indicadores municipais (`relatorios_auto.vw_indicadores`).

Essa view consolida, num registro por município, os indicadores que aparecem no
bloco "Panorama de indicadores" da capa de cada macrotema. Antes dela os cards
eram preenchidos com valores fixos no código (`utils/cover.py`), o que fazia o
relatório exibir score fictício ou "N/D".
"""

from utils.queries.base import executar_query_dict

# Colunas de identificação da view: não são indicadores e já chegam ao contexto
# pelas views de perfil. Removê-las evita sobrescrever o `nm_mun` canonicalizado
# em `services/generation.py` (a view guarda o nome sem o sufixo "(UF)").
COLUNAS_IDENTIFICACAO = ("nm_mun", "cd_mun", "estado", "sigla_uf")


def buscar_indicadores_municipio(nome_municipio: str, sigla_uf: str) -> dict | None:
    """Busca a linha de indicadores do município em `vw_indicadores`.

    Retorna um dict plano `{coluna: valor}` (sem as colunas de identificação) ou
    `None` quando falta a UF, o banco está fora do ar ou o município não está na
    view (ela cobre apenas os municípios da área de atuação da Sudene).
    """
    if not nome_municipio or not sigla_uf:
        return None

    # `statement_timeout` + município no WHERE: a view é uma agregação pesada
    # (dez CTEs sobre os schemas temáticos) e não pode ser varrida inteira.
    query = """
        SET LOCAL statement_timeout = '30s';
        SELECT *
        FROM relatorios_auto.vw_indicadores
        WHERE LOWER(regexp_replace(nm_mun, '\\s*\\([^)]*\\)\\s*$', '')) = LOWER(%s)
          AND sigla_uf = %s
        LIMIT 1
    """
    contexto = f"indicadores de '{nome_municipio} ({sigla_uf})'"

    linha = executar_query_dict(query, (nome_municipio, sigla_uf), contexto)
    if not linha:
        return None

    return {
        coluna: valor
        for coluna, valor in linha.items()
        if coluna not in COLUNAS_IDENTIFICACAO
    }
