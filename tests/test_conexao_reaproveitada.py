import psycopg2
import pytest

from utils.queries import base


class _Cursor:
    def __init__(self, conn):
        self.conn = conn
        self.description = [("valor",)]

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False

    def execute(self, query, params):
        self.conn.executadas.append(params)
        if self.conn.falhar_proxima:
            self.conn.falhar_proxima = False
            raise psycopg2.errors.QueryCanceled("canceling statement due to statement timeout")
        self._linha = (params[0],)

    def fetchone(self):
        return self._linha

    def fetchall(self):
        return [self._linha]


class _Conexao:
    def __init__(self):
        self.autocommit = False
        self.closed = 0
        self.executadas: list = []
        self.falhar_proxima = False

    def cursor(self):
        return _Cursor(self)

    def close(self):
        self.closed = 1


@pytest.fixture
def conexoes(monkeypatch):
    abertas: list[_Conexao] = []

    def conectar():
        abertas.append(_Conexao())
        return abertas[-1]

    monkeypatch.setattr(base, "get_connection", conectar)
    base.limpar_cache_queries()
    yield abertas
    base.limpar_cache_queries()


def test_executar_query_sem_contexto_abre_e_fecha(conexoes):
    assert base.executar_query("q", ("a",), "teste") == ("a",)
    assert base.executar_query_dict("q", ("b",), "teste") == {"valor": "b"}
    assert len(conexoes) == 2
    assert all(c.closed for c in conexoes)


def test_conexao_reaproveitada_usa_uma_conexao(conexoes):
    with base.conexao_reaproveitada():
        base.executar_query("q", ("a",), "teste")
        base.executar_query("q", ("b",), "teste", buscar_todas=True)
        base.executar_query_dict("q", ("c",), "teste")
        assert not conexoes[0].closed
    assert len(conexoes) == 1
    assert conexoes[0].executadas == [("a",), ("b",), ("c",)]
    assert conexoes[0].closed


def test_conexao_reaproveitada_liga_autocommit(conexoes):
    with base.conexao_reaproveitada():
        pass
    assert conexoes[0].autocommit is True


def test_conexao_reaproveitada_sobrevive_a_erro(conexoes):
    with base.conexao_reaproveitada() as conn:
        conn.falhar_proxima = True
        assert base.executar_query("q", ("a",), "teste") is None  # fail-soft continua
        assert base.executar_query("q", ("b",), "teste") == ("b",)
    assert len(conexoes) == 1


def test_conexao_reaproveitada_reabre_se_cair(conexoes):
    with base.conexao_reaproveitada() as conn:
        conn.closed = 2  # o psycopg2 marca assim quando o servidor derruba a conexão
        assert base.executar_query("q", ("a",), "teste") == ("a",)
    assert len(conexoes) == 2
    assert conexoes[1].autocommit is True and conexoes[1].closed


def test_fora_do_contexto_volta_ao_normal(conexoes):
    with base.conexao_reaproveitada():
        pass
    base.executar_query("q", ("a",), "teste")
    assert len(conexoes) == 2 and conexoes[1].closed
