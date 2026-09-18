"""Leitura do painel de indicadores municipais (`relatorios_auto.mv_indicadores`).

Essa materialized view (snapshot de `vw_indicadores`, ~14s de agregação
país-inteira) consolida, num registro por município, os indicadores que
aparecem no bloco "Panorama de indicadores" da capa de cada macrotema. Antes
dela os cards eram preenchidos com valores fixos no código (`utils/cover.py`),
o que fazia o relatório exibir score fictício ou "N/D".
"""

from utils.queries.base import executar_query_dict

# Colunas de identificação da view: não são indicadores e já chegam ao contexto
# pelas views de perfil. Removê-las evita sobrescrever o `nm_mun` canonicalizado
# em `services/generation.py` (a view guarda o nome sem o sufixo "(UF)").
COLUNAS_IDENTIFICACAO = ("nm_mun", "cd_mun", "estado", "sigla_uf")


def buscar_indicadores_municipio(nome_municipio: str, sigla_uf: str) -> dict | None:
    """Busca a linha de indicadores do município em `mv_indicadores`.

    Retorna um dict plano `{coluna: valor}` (sem as colunas de identificação) ou
    `None` quando falta a UF, o banco está fora do ar ou o município não está na
    view (ela cobre apenas os municípios da área de atuação da Sudene).
    """
    if not nome_municipio or not sigla_uf:
        return None

    # `statement_timeout` + município no WHERE: mantido por segurança mesmo
    # após materializar (db/2026-09-17-mv_indicadores.sql) — a mv reduz o scan
    # a ~15ms, mas a query original já tinha essa rede de segurança.
    query = """
        SET LOCAL statement_timeout = '30s';
        SELECT *
        FROM relatorios_auto.mv_indicadores
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
