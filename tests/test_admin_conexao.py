"""O painel precisa poder reconferir a conexão sem recarregar a página.

Regressão de um problema concreto: o painel lê o `/manifesto` uma vez, quando a
aba abre. Com o túnel SSH fora do ar naquele instante, a lista de variáveis vem
da planilha CSV — e continua vindo de lá mesmo depois que o túnel sobe, porque
nada reconsulta. A tela dizia "sem conexão" enquanto o backend já enxergava o
banco, e recarregar a página custaria o rascunho não publicado.

Nenhum destes testes toca o banco de verdade.
"""

import psycopg2
import pytest

from services import admin


class ConexaoFalsa:
    def __init__(self, versao="PostgreSQL 18.3 (Ubuntu), compiled by gcc"):
        self.versao = versao
        self.fechada = False

    def cursor(self):
        conexao = self

        class Cursor:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def execute(self, *_):
                pass

            def fetchone(self):
                return (conexao.versao,)

        return Cursor()

    def close(self):
        self.fechada = True


@pytest.fixture
def sem_banco(monkeypatch):
    def recusar():
        raise psycopg2.OperationalError(
            'connection to server at "localhost" (127.0.0.1), port 5433 failed: '
            "Connection refused\n\tIs the server running on that host?"
        )

    monkeypatch.setattr("utils.database.get_connection", recusar)


def test_sem_conexao_reporta_desligado_e_a_causa(sem_banco):
    estado = admin.conexao_handler()

    assert estado["conectado"] is False
    assert "Connection refused" in estado["detalhe"]
    # Só a primeira linha do erro do psycopg2: o resto é ruído para quem opera.
    assert "\n" not in estado["detalhe"]


def test_sem_conexao_entrega_o_comando_do_tunel_com_a_porta_real(sem_banco, monkeypatch):
    """O comando mostrado na tela não pode divergir do que a aplicação procura."""
    monkeypatch.setattr("config.DB_PORT", "6000")

    estado = admin.conexao_handler()

    assert "-L 6000:127.0.0.1:5432" in estado["comando_tunel"]
    assert "ubuntu@10.5.8.5" in estado["comando_tunel"]


def test_com_conexao_reporta_a_versao_e_fecha_a_conexao(monkeypatch):
    conexao = ConexaoFalsa()
    monkeypatch.setattr("utils.database.get_connection", lambda: conexao)

    estado = admin.conexao_handler()

    assert estado["conectado"] is True
    assert estado["detalhe"] == "PostgreSQL 18.3 (Ubuntu)"
    assert conexao.fechada, "a sonda não pode vazar conexão a cada clique no botão"


def test_a_conexao_e_fechada_mesmo_se_a_consulta_falhar(monkeypatch):
    conexao = ConexaoFalsa()

    def cursor_que_falha():
        raise psycopg2.ProgrammingError("boom")

    conexao.cursor = cursor_que_falha
    monkeypatch.setattr("utils.database.get_connection", lambda: conexao)

    with pytest.raises(psycopg2.ProgrammingError):
        admin.conexao_handler()

    assert conexao.fechada


def test_a_rota_exige_autenticacao():
    """O estado do banco e o host não são informação pública."""
    import main

    rota = next(r for r in main.app.routes if getattr(r, "path", "") == "/admin/conexao")
    assert rota.dependant.dependencies, "a rota precisa da dependência de editor autenticado"
