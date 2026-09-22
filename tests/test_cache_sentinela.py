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


def test_conta_so_as_sentinelas_vivas(tmp_path, monkeypatch):
    _output(tmp_path, monkeypatch)
    cache.adquirir_geracao("a__x")
    cache.adquirir_geracao("b__y")
    morta = tmp_path / "relatorio_c__z.inflight"
    morta.write_bytes(b"")
    velha = time.time() - (cache.SENTINELA_TTL_S + 1)
    os.utime(morta, (velha, velha))

    assert cache.geracoes_em_voo() == 2
