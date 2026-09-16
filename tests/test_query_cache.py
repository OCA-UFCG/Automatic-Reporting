"""Cache de resultados em utils/queries/base.py — não deve tocar o banco.

`get_connection` é mockado; o cursor fake devolve um resultado canônico. Os testes
checam que a segunda chamada com a mesma (query, params) vem do cache (get_connection
não é chamado de novo), que params diferentes ou um resultado ``None`` furam o cache,
e que `limpar_cache_queries` esvazia tudo.
"""

from unittest.mock import MagicMock, patch

from utils.queries import base


def _fake_connection(fetchone=None, fetchall=None, description=None):
    """Monta uma conexão/cursor fake equivalente à psycopg2 real, sem rede."""
    cursor = MagicMock()
    cursor.fetchone.return_value = fetchone
    cursor.fetchall.return_value = fetchall
    cursor.description = description or [("nm_mun",), ("sigla_uf",)]
    cursor.__enter__.return_value = cursor
    cursor.__exit__.return_value = False

    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn


def test_segunda_chamada_mesma_query_params_usa_cache():
    conn = _fake_connection(fetchone=("Campina Grande", "PB"))

    with patch.object(base, "get_connection", return_value=conn) as mock_get_conn:
        primeira = base.executar_query("SELECT 1", ("Campina Grande", "PB"), "teste")
        segunda = base.executar_query("SELECT 1", ("Campina Grande", "PB"), "teste")

    assert primeira == ("Campina Grande", "PB")
    assert segunda == ("Campina Grande", "PB")
    mock_get_conn.assert_called_once()


def test_params_diferentes_nao_usa_cache():
    conn = _fake_connection(fetchone=("Campina Grande", "PB"))

    with patch.object(base, "get_connection", return_value=conn) as mock_get_conn:
        base.executar_query("SELECT 1", ("Campina Grande", "PB"), "teste")
        base.executar_query("SELECT 1", ("Recife", "PE"), "teste")

    assert mock_get_conn.call_count == 2


def test_resultado_none_nao_e_cacheado():
    conn = _fake_connection(fetchone=None)

    with patch.object(base, "get_connection", return_value=conn) as mock_get_conn:
        primeira = base.executar_query("SELECT 1", ("Sem Dados", "PB"), "teste")
        segunda = base.executar_query("SELECT 1", ("Sem Dados", "PB"), "teste")

    assert primeira is None
    assert segunda is None
    # Sem cache para None: as duas chamadas batem no banco de novo (evita
    # "congelar" um timeout/erro transitório).
    assert mock_get_conn.call_count == 2


def test_limpar_cache_queries_forca_reexecucao():
    conn = _fake_connection(fetchone=("Campina Grande", "PB"))

    with patch.object(base, "get_connection", return_value=conn) as mock_get_conn:
        base.executar_query("SELECT 1", ("Campina Grande", "PB"), "teste")
        base.limpar_cache_queries()
        base.executar_query("SELECT 1", ("Campina Grande", "PB"), "teste")

    assert mock_get_conn.call_count == 2


def test_buscar_todas_diferente_nao_compartilha_cache():
    # buscar_todas muda o formato do resultado (fetchone vs fetchall); precisa
    # fazer parte da chave, senão uma chamada "rouba" o cache da outra.
    conn = _fake_connection(fetchone=("linha_unica",), fetchall=[("linha_unica",)])

    with patch.object(base, "get_connection", return_value=conn) as mock_get_conn:
        base.executar_query("SELECT 1", ("PB",), "teste", buscar_todas=False)
        base.executar_query("SELECT 1", ("PB",), "teste", buscar_todas=True)

    assert mock_get_conn.call_count == 2


def test_executar_query_dict_usa_cache():
    conn = _fake_connection(
        fetchone=("Campina Grande", "PB"),
        description=[("nm_mun",), ("sigla_uf",)],
    )

    with patch.object(base, "get_connection", return_value=conn) as mock_get_conn:
        primeira = base.executar_query_dict("SELECT * FROM v", ("Campina Grande", "PB"), "teste")
        segunda = base.executar_query_dict("SELECT * FROM v", ("Campina Grande", "PB"), "teste")

    assert primeira == {"nm_mun": "Campina Grande", "sigla_uf": "PB"}
    assert segunda == primeira
    mock_get_conn.assert_called_once()
