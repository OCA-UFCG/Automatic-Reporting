"""Gráficos do relatório por área (services/graficos_area.py). Os PNGs vão para
tmp_path; nada toca o banco."""

from pathlib import Path

from services import graficos_area
from services.relatorio_estado import graficos_da_unidade


def test_nordeste_tem_o_grafico_do_idhm_em_desenvolvimento_social(tmp_path: Path):
    graficos = graficos_area.gerar_graficos_da_area("desenvolvimento-social", "Nordeste", tmp_path, "area_nordeste")

    assert graficos == {"grafico_idhm_componentes": "grafico_idhm_componentes_area_nordeste.png"}
    assert (tmp_path / graficos["grafico_idhm_componentes"]).is_file()


def test_outra_area_ou_outro_tema_nao_tem_grafico(tmp_path: Path):
    assert graficos_area.gerar_graficos_da_area("desenvolvimento-social", "Caatinga", tmp_path, "x") == {}
    assert graficos_area.gerar_graficos_da_area("demografia", "Nordeste", tmp_path, "x") == {}


def test_grafico_que_falha_fica_de_fora(tmp_path: Path, monkeypatch):
    def falha(_output_dir: Path, _safe: str) -> str:
        raise ValueError("sem dado")

    monkeypatch.setitem(graficos_area.GRAFICOS_DA_AREA, ("saude", "Semiárido"), {"grafico_x": falha})

    assert graficos_area.gerar_graficos_da_area("saude", "Semiárido", tmp_path, "x") == {}


def test_valores_fixos_conferem_com_o_texto_do_doc():
    # Os números que o Doc cita no texto e nos cards (16/11/2026).
    medianas = graficos_area._MEDIANAS_DO_IDHM_NO_NORDESTE
    assert medianas["IDHM"] == (0.291, 0.420, 0.588)
    assert (medianas["Educação"][0], medianas["Educação"][-1]) == (0.108, 0.4825)
    assert (medianas["Longevidade"][-1], medianas["Renda"][-1]) == (0.7575, 0.559)


def test_handler_usa_os_graficos_da_area_com_o_sufixo_da_unidade(tmp_path: Path, monkeypatch):
    from services import relatorio_estado

    monkeypatch.setattr(relatorio_estado, "OUTPUT_DIR", tmp_path)

    graficos = graficos_da_unidade("area", "desenvolvimento-social", "Nordeste", {})

    assert graficos == {"grafico_idhm_componentes": "grafico_idhm_componentes_area_nordeste.png"}
