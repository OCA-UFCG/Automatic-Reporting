"""Gráficos do relatório por estado (12/11/2026): os adaptadores montam, a partir da
linha `uf_*` da matview estadual, o dicionário que as funções de plotting/ leem.
Nenhum teste toca o banco: as linhas são recortes da Paraíba em est_demografia e
est_educacao."""

from decimal import Decimal
from pathlib import Path

from plotting.demografia import _percentuais_cor_raca
from services.graficos_estado import (
    faixas_etarias_sexo_do_estado,
    gerar_graficos_do_estado,
    niveis_de_instrucao_do_estado,
    populacao_historica_do_estado,
    populacao_por_cor_raca_do_estado,
    taxas_de_analfabetismo_do_estado,
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
    assert gerar_graficos_do_estado("saude", _linha_paraiba(), tmp_path, "estado_para_ba") == {}


def test_arquivo_do_estado_nao_colide_com_o_do_municipio():
    assert nome_de_arquivo_da_unidade("estado", "Paraíba") == "estado_para_ba"


_FAIXAS_DE_ANALFABETISMO = (
    "15 a 19 anos", "20 a 29 anos", "30 a 39 anos", "40 a 49 anos", "50 a 59 anos", "60 anos ou mais",
)


def _linha_educacao_paraiba() -> dict:
    """Recorte de est_educacao para a Paraíba. As taxas por faixa são as reais da
    cor preta; as outras cores repetem esses valores, só para o gráfico ter barras."""
    taxas_preta = ("3.24", "4.06", "8.68", "21.64", "33.14", "50.21")
    linha: dict = {
        "uf_estado": "Paraíba",
        "uf_pri_nivel_classe": "ensino fundamental incompleto ou sem instrução",
        "uf_pri_nivel_per": Decimal("47.49"),
        "uf_pri_nivel_pop": Decimal(1211253),
        "uf_seg_nivel_classe": "ensino médio completo",
        "uf_seg_nivel_per": Decimal("26.31"),
        "uf_seg_nivel_pop": Decimal(671120),
        "uf_ter_nivel_classe": "ensino superior completo",
        "uf_ter_nivel_per": Decimal("14.51"),
        "uf_ter_nivel_pop": Decimal(370167),
        "uf_quar_nivel_classe": "ensino fundamental completo",
        "uf_quar_nivel_per": Decimal("11.68"),
        "uf_quar_nivel_pop": Decimal(297895),
        # A matview reserva 8 posições; as duas últimas vêm vazias.
        "uf_analf_faixa_etaria_2022_fx7": None,
        "uf_analf_taxa_2022_preta_fx7": None,
    }
    for posicao, (faixa, taxa) in enumerate(zip(_FAIXAS_DE_ANALFABETISMO, taxas_preta), start=1):
        linha[f"uf_analf_faixa_etaria_2022_fx{posicao}"] = faixa
        for cor in ("branca", "preta", "amarela", "parda", "indigena"):
            linha[f"uf_analf_taxa_2022_{cor}_fx{posicao}"] = Decimal(taxa)

    return linha


def test_niveis_de_instrucao_tiram_so_o_prefixo_uf():
    niveis = niveis_de_instrucao_do_estado(_linha_educacao_paraiba())

    assert niveis["pri_nivel_classe"] == "ensino fundamental incompleto ou sem instrução"
    assert niveis["quar_nivel_pop"] == Decimal(297895)
    assert "uf_estado" not in niveis and "estado" not in niveis


def test_taxas_de_analfabetismo_casam_a_faixa_pelo_rotulo():
    linha = _linha_educacao_paraiba()
    # fx1 e fx6 trocadas: o rótulo manda, não a posição.
    for cor in ("branca", "preta", "amarela", "parda", "indigena"):
        linha[f"uf_analf_taxa_2022_{cor}_fx1"], linha[f"uf_analf_taxa_2022_{cor}_fx6"] = (
            linha[f"uf_analf_taxa_2022_{cor}_fx6"], linha[f"uf_analf_taxa_2022_{cor}_fx1"],
        )
    linha["uf_analf_faixa_etaria_2022_fx1"] = "60 anos ou mais"
    linha["uf_analf_faixa_etaria_2022_fx6"] = "15 a 19 anos"

    taxas = taxas_de_analfabetismo_do_estado(linha)

    assert taxas["taxa_mais60_preta"] == Decimal("50.21")
    assert taxas["taxa_15_a_19_preta"] == Decimal("3.24")
    assert len(taxas) == 30


def test_gera_os_dois_graficos_de_educacao(tmp_path: Path):
    graficos = gerar_graficos_do_estado("educacao", _linha_educacao_paraiba(), tmp_path, "estado_para_ba")

    assert graficos == {
        "grafico_cor_faixa_etaria": "grafico_cor_faixa_etaria_estado_para_ba.png",
        "grafico_nivel_instrucao": "grafico_nivel_instrucao_estado_para_ba.png",
    }
    assert all((tmp_path / arquivo).is_file() for arquivo in graficos.values())


def test_faixa_de_analfabetismo_faltando_tira_so_esse_grafico(tmp_path: Path):
    linha = _linha_educacao_paraiba()
    linha["uf_analf_faixa_etaria_2022_fx6"] = None

    graficos = gerar_graficos_do_estado("educacao", linha, tmp_path, "estado_para_ba")

    assert list(graficos) == ["grafico_nivel_instrucao"]
