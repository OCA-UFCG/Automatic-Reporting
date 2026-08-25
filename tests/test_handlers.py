from pathlib import Path

from services import handlers


def test_listar_relatorio_preserva_nome_e_uf_da_cidade(
    tmp_path: Path, monkeypatch
):
    arquivo = tmp_path / "relatorio_saude__campina_grande_pb_.pdf"
    arquivo.write_bytes(b"pdf")

    monkeypatch.setattr(handlers, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(
        handlers, "carregar_cidades", lambda: ["Campina Grande (PB)"]
    )

    relatorios = handlers.listar_relatorios_handler()

    assert len(relatorios) == 1
    assert relatorios[0]["cidade"] == "Campina Grande (PB)"
    assert relatorios[0]["macrotema"] == "Saúde"
