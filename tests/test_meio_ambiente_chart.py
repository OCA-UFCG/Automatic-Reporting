from pathlib import Path

import pytest

from plotting.meio_ambiente import gerar_grafico_aridez


def test_gera_grafico_de_aridez(tmp_path: Path):
    cidade = {
        "area_arida2021_per": 0.6,
        "area_semiarida2021_per": 49.4,
        "area_subumida2021_per": 14.7,
        "area_umida2021_per": 34.7,
    }

    arquivo = gerar_grafico_aridez(cidade, tmp_path, "cidade_teste")

    assert arquivo == "grafico_aridez_cidade_teste.png"
    assert (tmp_path / arquivo).is_file()


def test_grafico_ignora_categoria_sem_dado(tmp_path: Path):
    cidade = {
        "area_semiarida2021_per": 80.0,
        "area_umida2021_per": 20.0,
    }

    arquivo = gerar_grafico_aridez(cidade, tmp_path, "cidade_parcial")

    assert (tmp_path / arquivo).is_file()


def test_grafico_exige_dados(tmp_path: Path):
    with pytest.raises(ValueError, match="não disponíveis"):
        gerar_grafico_aridez({}, tmp_path, "sem_dados")


@pytest.mark.parametrize(
    "cidade",
    [
        {
            "area_arida2021_per": 0.6,
            "area_semiarida2021_per": 49.4,
            "area_subumida2021_per": 14.7,
            "area_umida2021_per": 34.7,
        },
        {"area_semiarida2021_per": 80.0, "area_umida2021_per": 20.0},
        {"area_semiarida2021_per": 100.0},
    ],
)
def test_legenda_fica_dentro_do_card(tmp_path: Path, monkeypatch, cidade: dict):
    """Os testes acima passariam com a legenda inteiramente fora da imagem:
    só checam que o PNG existe."""
    import plotting
    from plotting import meio_ambiente

    medido = {}
    salvar_original = meio_ambiente.salvar_card_grafico

    def espiao(fig, chart_file, dpi=180):
        fig.canvas.draw()
        caixa = (
            fig.axes[0]
            .get_legend()
            .get_window_extent()
            .transformed(fig.transFigure.inverted())
        )
        medido["y0"] = caixa.y0
        return salvar_original(fig, chart_file, dpi)

    monkeypatch.setattr(meio_ambiente, "salvar_card_grafico", espiao)
    gerar_grafico_aridez(cidade, tmp_path, "cidade_legenda")

    assert medido["y0"] >= plotting._CARD_MARGEM, (
        f"legenda ultrapassa a borda do card em {plotting._CARD_MARGEM - medido['y0']:.4f}"
    )
