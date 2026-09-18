import time

import pytest

from services import cache


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
