import os
import time

from services import cache


def _output(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "OUTPUT_DIR", tmp_path)
    return tmp_path


def test_primeira_chamada_ganha_segunda_perde(tmp_path, monkeypatch):
    _output(tmp_path, monkeypatch)
    assert cache.adquirir_geracao("demografia__x") is True
    assert cache.adquirir_geracao("demografia__x") is False


def test_liberar_devolve_o_direito(tmp_path, monkeypatch):
    _output(tmp_path, monkeypatch)
    cache.adquirir_geracao("demografia__x")
    cache.liberar_geracao("demografia__x")
    assert cache.adquirir_geracao("demografia__x") is True


def test_liberar_duas_vezes_nao_explode(tmp_path, monkeypatch):
    _output(tmp_path, monkeypatch)
    cache.adquirir_geracao("demografia__x")
    cache.liberar_geracao("demografia__x")
    cache.liberar_geracao("demografia__x")


def test_sentinela_morta_e_retomada(tmp_path, monkeypatch):
    _output(tmp_path, monkeypatch)
    cache.adquirir_geracao("demografia__x")
    sentinela = tmp_path / "relatorio_demografia__x.inflight"
    velha = time.time() - (cache.SENTINELA_TTL_S + 1)
    os.utime(sentinela, (velha, velha))

    assert cache.adquirir_geracao("demografia__x") is True


def test_liberar_nao_apaga_sentinela_de_outro(tmp_path, monkeypatch):
    _output(tmp_path, monkeypatch)
    cache.adquirir_geracao("x")  # A adquire
    s = tmp_path / "relatorio_x.inflight"
    velha = time.time() - (cache.SENTINELA_TTL_S + 1)
    os.utime(s, (velha, velha))

    # Na vida real B é outro processo (outro pid do --workers). Aqui os dois
    # "processos" são o mesmo processo de teste, então o único jeito de fazer a
    # reclamação de B carregar um dono diferente de A é trocar, só durante a
    # chamada de B, o pid que o módulo enxerga — sem isso o teste não teria como
    # distinguir os dois donos e passaria por acidente.
    outro_pid = os.getpid() + 1  # capturado antes do patch, pra não recursar
    with monkeypatch.context() as m:
        m.setattr(cache.os, "getpid", lambda: outro_pid)
        assert cache.adquirir_geracao("x") is True  # B reclama, com "outro pid"

    cache.liberar_geracao("x")  # A, atrasado, tenta liberar o que já não é dele
    assert cache.geracoes_em_voo() == 1  # a sentinela de B continua de pé


def test_conta_so_as_sentinelas_vivas(tmp_path, monkeypatch):
    _output(tmp_path, monkeypatch)
    cache.adquirir_geracao("a__x")
    cache.adquirir_geracao("b__y")
    morta = tmp_path / "relatorio_c__z.inflight"
    morta.write_bytes(b"")
    velha = time.time() - (cache.SENTINELA_TTL_S + 1)
    os.utime(morta, (velha, velha))

    assert cache.geracoes_em_voo() == 2
