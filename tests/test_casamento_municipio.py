"""A regra que casa o município com a linha da view tem uma fonte só
(`chave_municipio_sql`): o WHERE do relatório e o índice do snapshot usam a mesma
expressão, calculada no Postgres."""

from utils.queries import perfil_municipal

# SQL de buscar_perfil_municipal antes da extração (bug do Recife em saúde, sem "(UF)").
_SQL_ANTIGO = """
        SELECT * FROM relatorios_auto.mv_perfil_saude_municipal
        WHERE LOWER(regexp_replace(nm_mun, '\\s*\\([^)]*\\)\\s*$', '')) =
              LOWER(regexp_replace(%s, '\\s*\\([^)]*\\)\\s*$', ''))
          AND sigla_uf = %s
        LIMIT 1
    """


def test_sql_do_relatorio_nao_mudou(monkeypatch):
    executadas = []
    monkeypatch.setattr(
        perfil_municipal,
        "executar_query_dict",
        lambda query, params, _ctx: executadas.append((query, params)),
    )
    perfil_municipal.buscar_perfil_municipal("saude", "Recife (PE)", "PE")
    assert executadas == [(_SQL_ANTIGO, ("Recife (PE)", "PE"))]

