"""Gráficos do relatório por estado (12/11/2026): os adaptadores montam, a partir da
linha `uf_*` da matview estadual, o dicionário que as funções de plotting/ leem.
Nenhum teste toca o banco: a linha é um recorte da Paraíba em est_demografia."""

from decimal import Decimal
from pathlib import Path

from plotting.demografia import _percentuais_cor_raca
from services.graficos_estado import (
    faixas_etarias_sexo_do_estado,
    gerar_graficos_do_estado,
    populacao_historica_do_estado,
    populacao_por_cor_raca_do_estado,
)
from services.relatorio_estado import nome_de_arquivo_da_unidade


def _linha_paraiba() -> dict:
    """Recorte de est_demografia para a Paraíba, com as faixas fora de ordem de
    propósito (o SELECT * não garante a ordem das colunas que importa aqui)."""
    return {
        "uf_estado": "Paraíba",
        "uf_pop_total_2010": Decimal(3766528),
        "uf_pop_total_2022": Decimal(3974687),
        "uf_faixa_etaria_2022_80_mais": "80 anos ou mais",
        "uf_pop_faixa_mulher_2022_80_mais": Decimal(64438),
        "uf_pop_faixa_homem_2022_80_mais": Decimal(40222),
        "uf_faixa_etaria_2022_00_04": "0 a 4 anos",
        "uf_pop_faixa_mulher_2022_00_04": Decimal(130135),
        "uf_pop_faixa_homem_2022_00_04": Decimal(134750),
        "uf_faixa_etaria_2022_30_39": "30 a 39 anos",
        "uf_pop_faixa_mulher_2022_30_39": Decimal(315854),
        "uf_pop_faixa_homem_2022_30_39": Decimal(293220),
        # Faixa da população indígena: não entra na pirâmide geral.
        "uf_faixa_etaria_ind_2022_00_09": "0 a 9 anos",
        "uf_pop_faixa_ind_2022_00_09": Decimal(5124),
        "uf_cor_raca_pri_class": "parda",
        "uf_cor_pri_pop": Decimal(2207880),
        "uf_cor_pri_per": Decimal("55.55"),
        "uf_cor_seg_class": "branca",
        "uf_cor_seg_pop": Decimal(1419778),
        "uf_cor_seg_per": Decimal("35.72"),
        "uf_cor_ter_class": "preta",
        "uf_cor_ter_pop": Decimal(316572),
        "uf_cor_ter_per": Decimal("7.96"),
        "uf_cor_quar_class": "indígena",
        "uf_cor_quar_pop": Decimal(25478),
        "uf_cor_quar_per": Decimal("0.64"),
        "uf_cor_quin_class": "amarela",
        "uf_cor_quin_pop": Decimal(4912),
        "uf_cor_quin_per": Decimal("0.12"),
    }


def test_faixas_saem_da_mais_nova_a_mais_velha_sem_a_faixa_indigena():
    faixas = faixas_etarias_sexo_do_estado(_linha_paraiba())

    assert [faixa["faixa"] for faixa in faixas] == ["0 a 4 anos", "30 a 39 anos", "80 anos ou mais"]
    assert faixas[0] == {"faixa": "0 a 4 anos", "mulheres": Decimal(130135), "homens": Decimal(134750)}


def test_cor_raca_tira_o_acento_da_classe_para_a_chave_municipal():
    populacao = populacao_por_cor_raca_do_estado(_linha_paraiba())

    assert populacao["pop_indigena"] == Decimal(25478)
    assert populacao["pop_total_2022"] == Decimal(3974687)


def test_percentuais_do_grafico_batem_com_os_do_texto():
    # O texto cita uf_cor_*_per da matview; a barra precisa mostrar o mesmo número.
    linha = _linha_paraiba()
    percentuais = dict(_percentuais_cor_raca(populacao_por_cor_raca_do_estado(linha)))

    assert percentuais == {
        "parda": 55.55,
        "branca": 35.72,
        "preta": 7.96,
        "indigena": 0.64,
        "amarela": 0.12,
    }


def test_visao_historica_do_estado_usa_so_2010_e_2022():
    assert populacao_historica_do_estado(_linha_paraiba()) == {
        "pop_total_2010": Decimal(3766528),
        "pop_total_2022": Decimal(3974687),
    }


def test_gera_os_tres_graficos_de_demografia(tmp_path: Path):
    graficos = gerar_graficos_do_estado("demografia", _linha_paraiba(), tmp_path, "estado_para_ba")

    assert graficos == {
        "grafico_faixa_etaria_e_sexo": "grafico_faixa_etaria_e_sexo_estado_para_ba.png",
        "grafico_composicao_cor_raca": "grafico_composicao_cor_raca_estado_para_ba.png",
        "grafico_visao_historica": "grafico_visao_historica_populacao_estado_para_ba.png",
    }
    assert all((tmp_path / arquivo).is_file() for arquivo in graficos.values())


def test_grafico_sem_dado_fica_de_fora_sem_derrubar_os_outros(tmp_path: Path):
    linha = _linha_paraiba()
    del linha["uf_pop_total_2010"]

    graficos = gerar_graficos_do_estado("demografia", linha, tmp_path, "estado_para_ba")

    assert "grafico_visao_historica" not in graficos
    assert "grafico_faixa_etaria_e_sexo" in graficos


def test_tema_sem_graficos_estaduais_devolve_vazio(tmp_path: Path):
    assert gerar_graficos_do_estado("educacao", _linha_paraiba(), tmp_path, "estado_para_ba") == {}


def test_arquivo_do_estado_nao_colide_com_o_do_municipio():
    assert nome_de_arquivo_da_unidade("estado", "Paraíba") == "estado_para_ba"
