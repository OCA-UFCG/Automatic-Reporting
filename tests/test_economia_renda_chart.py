from pathlib import Path

import pytest

from plotting.economia_renda import (
    _atribuir_cores_por_ranking,
    _dispor_setores_por_valor,
    _escolher_unidade,
    gerar_grafico_balanca,
    gerar_grafico_fob,
    gerar_grafico_pib,
    gerar_grafico_vab,
)
from utils.queries.economia_renda import _escalar_valor


def test_gera_grafico_com_serie_do_banco(tmp_path: Path):
    cidade = {
        "pib_serie": [
            {"ano": 2010, "pib_total": 166512845},
            {"ano": 2020, "pib_total": 8299245300},
            {"ano": 2023, "pib_total": 12945093200},
        ]
    }

    arquivo = gerar_grafico_pib(cidade, tmp_path, "campina_grande_pb")

    assert arquivo == "grafico_pib_campina_grande_pb.png"
    assert (tmp_path / arquivo).is_file()


def test_grafico_exige_serie_anual():
    with pytest.raises(ValueError, match="Dados anuais"):
        gerar_grafico_pib({}, Path("/tmp"), "sem_dados")


def test_dispor_setores_por_valor_coloca_os_2_maiores_na_linha_de_cima():
    valores = {
        "servicos": 260_230_000.0,
        "industria": 101_700_000.0,
        "adm_publica": 493_420_000.0,
        "agropecuaria": 225_830_000.0,
    }

    linha1, linha2 = _dispor_setores_por_valor(valores)

    assert [chave for chave, _valor in linha1] == ["adm_publica", "servicos"]
    assert [chave for chave, _valor in linha2] == ["agropecuaria", "industria"]


def test_atribuir_cores_por_ranking_da_a_cor_mais_forte_ao_maior_valor():
    linha1 = [("adm_publica", 493_420_000.0), ("servicos", 260_230_000.0)]
    linha2 = [("agropecuaria", 225_830_000.0), ("industria", 101_700_000.0)]

    cores = _atribuir_cores_por_ranking(linha1, linha2)

    assert list(cores.keys()) == ["adm_publica", "servicos", "agropecuaria", "industria"]
    assert len(set(cores.values())) == 4


def test_gera_grafico_vab_com_os_4_setores_do_banco(tmp_path: Path):
    cidade = {
        "vab_setores_2021": {
            "agropecuaria": 101_700_000.0,
            "industria": 225_830_000.0,
            "servicos": 493_420_000.0,
            "adm_publica": 260_230_000.0,
        }
    }

    arquivo = gerar_grafico_vab(cidade, tmp_path, "recife_pe")

    assert arquivo == "grafico_vab_recife_pe.png"
    assert (tmp_path / arquivo).is_file()


def test_grafico_vab_exige_dados_de_setor():
    with pytest.raises(ValueError, match="VAB por setor"):
        gerar_grafico_vab({}, Path("/tmp"), "sem_dados")


def test_gera_grafico_vab_com_linha_fina_nao_estoura(tmp_path: Path):
    # Setores 3º/4º (linha de baixo) somados muito menores que os 2 primeiros:
    # a linha fica fina o bastante pra nome e valor colidirem verticalmente
    # (achado em revisão, texto sobreposto no card). Só cobre "não quebra";
    # a checagem de sobreposição em si é visual.
    cidade = {
        "vab_setores_2021": {
            "servicos": 1_000_000_000.0,
            "adm_publica": 900_000_000.0,
            "agropecuaria": 2_000_000.0,
            "industria": 1_000_000.0,
        }
    }

    arquivo = gerar_grafico_vab(cidade, tmp_path, "recife_pe_linha_fina")

    assert arquivo == "grafico_vab_recife_pe_linha_fina.png"
    assert (tmp_path / arquivo).is_file()


def test_gera_grafico_fob_com_paises_do_banco(tmp_path: Path):
    cidade = {
        "importacao_paises": [
            ("China", 780_940_000.0),
            ("Estados Unidos", 327_580_000.0),
            ("Canadá", 233_020_000.0),
        ]
    }

    arquivo = gerar_grafico_fob(cidade, tmp_path, "recife_pe")

    assert arquivo == "grafico_fob_recife_pe.png"
    assert (tmp_path / arquivo).is_file()


def test_grafico_fob_exige_paises_de_importacao():
    with pytest.raises(ValueError, match="países de importação"):
        gerar_grafico_fob({}, Path("/tmp"), "sem_dados")


def test_gera_grafico_balanca_com_fob_exportado_e_importado(tmp_path: Path):
    cidade = {
        "fob_exportado_ultimo": 6_300_000.0,
        "fob_importado_ultimo": 4_100_000.0,
        "balanca_mensal": [("Jan", 100_000.0), ("Fev", -50_000.0)],
    }

    arquivo = gerar_grafico_balanca(cidade, tmp_path, "recife_pe")

    assert arquivo == "grafico_balanca_recife_pe.png"
    assert (tmp_path / arquivo).is_file()


@pytest.mark.parametrize(
    "fob_exportado_ultimo,fob_importado_ultimo",
    [
        (0, 4_100_000.0),
        (6_300_000.0, 0),
        (None, 4_100_000.0),
        (6_300_000.0, None),
    ],
)
def test_grafico_balanca_exige_fob_exportado_e_importado_diferentes_de_zero(
    fob_exportado_ultimo, fob_importado_ultimo
):
    cidade = {
        "fob_exportado_ultimo": fob_exportado_ultimo,
        "fob_importado_ultimo": fob_importado_ultimo,
        "balanca_mensal": [("Jan", 100_000.0), ("Fev", -50_000.0)],
    }

    with pytest.raises(ValueError, match="fob_exportado_ultimo"):
        gerar_grafico_balanca(cidade, Path("/tmp"), "sem_dados")


@pytest.mark.parametrize("valor", [500, 25_000, 3_000_000, 12_945_093_200])
def test_escala_do_grafico_usa_a_mesma_unidade_do_texto(valor):
    """O gráfico não pode rotular em "bn"/"mi" enquanto o texto do relatório
    usa "bilhões"/"milhões" para o mesmo valor -- ambos devem vir da mesma
    fonte de escala (`_escalar_valor`)."""
    _, unidade_texto = _escalar_valor(valor)
    _, unidade_grafico = _escolher_unidade(valor)

    assert unidade_grafico == unidade_texto
