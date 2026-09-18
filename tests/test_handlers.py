from pathlib import Path

from services import cache, handlers


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


def test_delete_nao_apaga_graficos_compartilhados_da_cidade(
    tmp_path: Path, monkeypatch
):
    # D6: grafico_*.png é chaveado por cidade e reusado entre combos. Apagar um
    # relatório não pode levar junto os gráficos, ou o gate segue servindo o HTML
    # (ainda fresco) dos outros relatórios da cidade com <img> quebrada.
    monkeypatch.setattr(handlers, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(cache, "OUTPUT_DIR", tmp_path)

    alvo = tmp_path / "relatorio_demografia__recife_pe_.pdf"
    alvo.write_bytes(b"pdf")
    (tmp_path / "relatorio_demografia__recife_pe_.html").write_bytes(b"html")
    vizinho = tmp_path / "relatorio_todos__recife_pe_.pdf"
    vizinho.write_bytes(b"pdf")
    grafico = tmp_path / "grafico_pib_recife_pe_.png"
    grafico.write_bytes(b"png")

    resultado = handlers.apagar_relatorio_handler(alvo.name)

    assert not alvo.exists()
    assert grafico.exists()  # pool compartilhado sobrevive
    assert vizinho.exists()
    assert all("grafico" not in nome for nome in resultado["removidos"])
