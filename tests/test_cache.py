import os
import time

import pytest

from services import cache, handlers


@pytest.fixture
def output_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(cache, "DATA_VERSION_FILE", tmp_path / ".data_version")
    return tmp_path


def test_sem_marcador_arquivo_existente_eh_fresco(output_tmp):
    pdf = output_tmp / "relatorio_demografia__x.pdf"
    pdf.write_bytes(b"pdf")
    assert cache.artefato_fresco(pdf) is True


def test_arquivo_inexistente_nao_eh_fresco(output_tmp):
    assert cache.artefato_fresco(output_tmp / "nao_existe.pdf") is False


def test_arquivo_mais_velho_que_marcador_eh_stale(output_tmp):
    pdf = output_tmp / "relatorio_demografia__x.pdf"
    pdf.write_bytes(b"pdf")
    time.sleep(0.01)
    (output_tmp / ".data_version").write_bytes(b"")  # marcador mais novo
    assert cache.artefato_fresco(pdf) is False


def test_arquivo_mais_novo_que_marcador_eh_fresco(output_tmp):
    (output_tmp / ".data_version").write_bytes(b"")
    time.sleep(0.01)
    pdf = output_tmp / "relatorio_demografia__x.pdf"
    pdf.write_bytes(b"pdf")
    assert cache.artefato_fresco(pdf) is True


def test_eviction_remove_mais_antigos_ate_caber(output_tmp, monkeypatch):
    # _artefatos_do_relatorio (services/handlers.py) resolve seus caminhos a
    # partir do próprio OUTPUT_DIR do módulo handlers (import feito na carga
    # do módulo) — precisa apontar pro tmp_path também, senão ele enumera
    # artefatos no output/ real do projeto em vez dos arquivos de teste.
    monkeypatch.setattr(handlers, "OUTPUT_DIR", output_tmp)
    monkeypatch.setattr(cache, "REPORT_CACHE_MAX_BYTES", 2500)
    # cria 3 relatórios de ~1KB cada, com mtime crescente
    nomes = ["a", "b", "c"]
    for i, n in enumerate(nomes):
        p = output_tmp / f"relatorio_demografia__{n}.pdf"
        p.write_bytes(b"x" * 1000)
        (output_tmp / f"relatorio_demografia__{n}.html").write_bytes(b"x" * 100)
        os.utime(p, (1000 + i, 1000 + i))  # a mais velho, c mais novo

    removidos = cache.evict_cache_if_needed()

    # ~3300 bytes > 2500: precisa apagar o mais antigo (a)
    assert "relatorio_demografia__a.pdf" in removidos
    assert not (output_tmp / "relatorio_demografia__a.pdf").exists()
    assert (output_tmp / "relatorio_demografia__c.pdf").exists()


def test_eviction_nunca_remove_protegido(output_tmp, monkeypatch):
    monkeypatch.setattr(handlers, "OUTPUT_DIR", output_tmp)
    monkeypatch.setattr(cache, "REPORT_CACHE_MAX_BYTES", 500)
    p = output_tmp / "relatorio_demografia__novo.pdf"
    p.write_bytes(b"x" * 1000)
    os.utime(p, (1000, 1000))  # mais velho, mas protegido
    removidos = cache.evict_cache_if_needed(protegido="demografia__novo")
    assert removidos == []
    assert p.exists()
