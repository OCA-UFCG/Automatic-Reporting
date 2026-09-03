from pathlib import Path

import pytest

from plotting.economia_renda import _escolher_unidade, gerar_grafico_pib
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


@pytest.mark.parametrize("valor", [500, 25_000, 3_000_000, 12_945_093_200])
def test_escala_do_grafico_usa_a_mesma_unidade_do_texto(valor):
    """O gráfico não pode rotular em "bn"/"mi" enquanto o texto do relatório
    usa "bilhões"/"milhões" para o mesmo valor -- ambos devem vir da mesma
    fonte de escala (`_escalar_valor`)."""
    _, unidade_texto = _escalar_valor(valor)
    _, unidade_grafico = _escolher_unidade(valor)

    assert unidade_grafico == unidade_texto
