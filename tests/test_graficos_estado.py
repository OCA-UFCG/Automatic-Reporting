"""Gráficos do relatório por estado (12/11/2026): os adaptadores montam, a partir da
linha `uf_*` da matview estadual, o dicionário que as funções de plotting/ leem.
Nenhum teste toca o banco: as linhas são recortes da Paraíba nas matviews estaduais."""

from decimal import Decimal
from pathlib import Path

import pytest

from plotting.demografia import _percentuais_cor_raca
from services.graficos_estado import (
    aridez_do_estado,
    cobertura_vacinal_serie_do_estado,
    estabelecimentos_serie_do_estado,
    faixas_etarias_sexo_do_estado,
    gerar_graficos_do_estado,
    mortalidade_infantil_serie_do_estado,
    niveis_de_instrucao_do_estado,
    populacao_historica_do_estado,
    populacao_por_cor_raca_do_estado,
    publico_etario_do_estado,
    taxas_de_analfabetismo_do_estado,
    tecnologias_acesso_agua_do_estado,
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
    assert gerar_graficos_do_estado("cultura", _linha_paraiba(), tmp_path, "estado_para_ba") == {}


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


def _linha_saude_paraiba() -> dict:
    """Recorte de est_saude para a Paraíba, com os dois nomes de coluna errados da
    matview (hebatite, penumo) e sem os dados que vêm do painel."""
    return {
        "uf_estado": "Paraíba",
        "uf_sigla_uf": "PB",
        "uf_mortalidade_2025": Decimal("12.32"),
        "uf_mortalidade_2010": Decimal("14.43"),
        "uf_mortalidade_2020": Decimal("12.68"),
        # Comparações, não anos: não entram na série.
        "uf_mortalidade_nordeste": Decimal("13.11"),
        "uf_mortalidade_brasil": Decimal("12.15"),
        "uf_estabelecimento_2010": Decimal(4318),
        "uf_estabelecimento_2025": Decimal(9020),
        "uf_bcg": Decimal("106.85"),
        "uf_bcg_meta": Decimal(90),
        "uf_hebatite_b_30dias": Decimal("107.90"),
        "uf_hebatite_b_30dias_meta": Decimal(95),
        "uf_penumo10": Decimal("89.74"),
        "uf_penumo10_meta": Decimal(95),
        "uf_hepatite_b_1dia": Decimal("66.43"),
        "uf_hepatite_b_1dia_meta": None,
    }


class ComplementoDoPainelFake:
    """Troca a consulta às tabelas do painel: devolve a soma da Paraíba e guarda a
    sigla da linha que recebeu."""

    def __init__(self) -> None:
        self.siglas: list[str] = []

    def __call__(self, linha: dict) -> dict:
        self.siglas.append(linha["uf_sigla_uf"])
        faixas = ("ao_nascer", "menor_1_ano", "1_ano", "multifaixa")
        publico = dict(zip(faixas, (197504, 296256, 395008, 943786)))
        doses = dict(zip(faixas, (180497, 249193, 333419, 525207)))
        return {
            **{f"publico_etario_{faixa}": valor for faixa, valor in publico.items()},
            **{f"dose_etario_{faixa}": valor for faixa, valor in doses.items()},
            "estabelecimentos_saude_serie": [
                {"ano": 2010, "total_estabelecimentos": 4318},
                {"ano": 2020, "total_estabelecimentos": 6616},
                {"ano": 2025, "total_estabelecimentos": 9020},
            ],
        }


def test_mortalidade_do_estado_le_so_as_colunas_de_ano_em_ordem():
    serie = mortalidade_infantil_serie_do_estado(_linha_saude_paraiba())["mortalidade_infantil_serie"]

    assert [ponto["ano"] for ponto in serie] == [2010, 2020, 2025]


def test_cobertura_le_as_colunas_com_erro_de_digitacao_da_matview():
    serie = cobertura_vacinal_serie_do_estado(_linha_saude_paraiba())["cobertura_vacinal_serie"]
    por_vacina = {item["vacina"]: item for item in serie}

    assert por_vacina["Hepatite B (até 30 dias)"]["cobertura_vacinal"] == Decimal("107.90")
    assert por_vacina["Pneumo 10"]["meta"] == Decimal(95)
    assert por_vacina["Hepatite B (até 1 dia de vida)"]["meta"] is None


def test_cobertura_prefere_o_nome_certo_quando_a_matview_for_corrigida():
    linha = {**_linha_saude_paraiba(), "uf_pneumo10": Decimal("90.00"), "uf_pneumo10_meta": Decimal(95)}

    serie = cobertura_vacinal_serie_do_estado(linha)["cobertura_vacinal_serie"]

    assert {item["vacina"]: item["cobertura_vacinal"] for item in serie}["Pneumo 10"] == Decimal("90.00")


def test_estabelecimentos_sem_o_painel_usam_os_anos_da_matview():
    serie = estabelecimentos_serie_do_estado(_linha_saude_paraiba())["estabelecimentos_saude_serie"]

    assert [ponto["ano"] for ponto in serie] == [2010, 2025]


def test_publico_etario_sem_o_painel_recusa_o_grafico():
    with pytest.raises(ValueError, match="publico_etario_ao_nascer"):
        publico_etario_do_estado(_linha_saude_paraiba())


def test_gera_os_quatro_graficos_de_saude_com_o_painel(tmp_path: Path):
    painel = ComplementoDoPainelFake()

    graficos = gerar_graficos_do_estado(
        "saude", _linha_saude_paraiba(), tmp_path, "estado_para_ba", complementos={"saude": painel}
    )

    assert painel.siglas == ["PB"]
    assert list(graficos) == [
        "grafico_publico_etario",
        "grafico_cobertura_vacinal",
        "grafico_taxa_mortalidade",
        "grafico_de_estabelecimento",
    ]
    assert all((tmp_path / arquivo).is_file() for arquivo in graficos.values())


def test_saude_sem_o_painel_perde_so_o_publico_etario(tmp_path: Path):
    graficos = gerar_graficos_do_estado(
        "saude", _linha_saude_paraiba(), tmp_path, "estado_para_ba", complementos={"saude": lambda linha: {}}
    )

    assert "grafico_publico_etario" not in graficos
    assert len(graficos) == 3


def _linha_hidraulica_paraiba() -> dict:
    return {
        "uf_estado": "Paraíba",
        "uf_sigla_uf": "PB",
        "uf_total_2025": Decimal(123556),
        "uf_total_2010": Decimal(48456),
        "uf_total_2020": Decimal(114220),
        # Texto, não ano: não entra na série.
        "uf_total_tecnologia_txt": "tecnologias sociais de acesso à água",
    }


def test_tecnologias_usam_os_tres_anos_da_matview_em_ordem():
    dados = tecnologias_acesso_agua_do_estado(_linha_hidraulica_paraiba())

    assert [ponto["ano"] for ponto in dados["tecnologias_acesso_agua_serie"]] == [2010, 2020, 2025]
    assert dados["total_2025"] == Decimal(123556)


def test_gera_o_grafico_de_seguranca_hidrica(tmp_path: Path):
    graficos = gerar_graficos_do_estado("hidraulica", _linha_hidraulica_paraiba(), tmp_path, "estado_para_ba")

    assert graficos == {"grafico_tecnologias_acesso_agua": "grafico_tecnologias_acesso_agua_estado_para_ba.png"}


def test_tecnologias_com_total_2025_zero_ficam_de_fora(tmp_path: Path):
    # Mesma regra do municipal: o Doc descreve o caso em prosa e o gráfico some.
    linha = {**_linha_hidraulica_paraiba(), "uf_total_2025": 0}

    assert gerar_graficos_do_estado("hidraulica", linha, tmp_path, "estado_para_ba") == {}


def test_aridez_do_estado_tira_o_prefixo_e_ignora_o_resto():
    linha = {
        "uf_estado": "Paraíba",
        "uf_aridez_1991_valida": 1,
        "uf_area_semiarida2021_per": Decimal("83.62"),
        "uf_asd_per_2021": Decimal("90.00"),
    }

    assert aridez_do_estado(linha) == {"aridez_1991_valida": 1, "area_semiarida2021_per": Decimal("83.62")}


def test_meio_ambiente_usa_o_marcador_proprio_do_doc_estadual(tmp_path: Path):
    linha = {
        "uf_sigla_uf": "PB",
        "uf_aridez_1991_valida": 1,
        "uf_aridez_2021_valida": 1,
        "uf_area_semiarida1991_per": Decimal("60.35"),
        "uf_area_semiarida2021_per": Decimal("83.62"),
    }

    graficos = gerar_graficos_do_estado("meio-ambiente", linha, tmp_path, "estado_para_ba")

    assert graficos == {"grafico_aridez_estadual": "grafico_aridez_comparada_estado_para_ba.png"}
