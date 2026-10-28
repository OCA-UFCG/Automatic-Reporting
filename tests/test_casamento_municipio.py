"""A regra que casa o município com a linha da view tem uma fonte só
(`chave_municipio_sql`): o WHERE do relatório e o índice do snapshot usam a mesma
expressão, calculada no Postgres."""

from utils.queries import perfil_municipal
from utils.queries.perfil_municipal import chave_municipio_sql

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


def test_snapshot_usa_a_mesma_expressao():
    from services import laboratorio_snapshot

    class _Cursor:
        def __init__(self):
            self.description = [("_chave_mun",), ("nm_mun",), ("sigla_uf",)]
            self.queries = []

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

        def execute(self, query, params=None):
            self.queries.append(query)

        def fetchall(self):
            return [("Recife", "recife")] if "unnest" in self.queries[-1] else []

    cursor = _Cursor()
    conn = type("C", (), {"cursor": lambda self: cursor})()
    laboratorio_snapshot.ler_view_do_tema(conn, "saude")
    chaves = laboratorio_snapshot.chaves_das_cidades(conn, ["Recife (PE)"])
    assert chaves == {"Recife (PE)": ("recife", "PE")}  # chave do índice: (nome, UF)
    assert chave_municipio_sql("nm_mun") in cursor.queries[0]
    assert chave_municipio_sql("nome") in cursor.queries[1]
