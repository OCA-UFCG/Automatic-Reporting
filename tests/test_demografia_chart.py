from pathlib import Path

import pytest

from plotting.demografia import (
    gerar_grafico_composicao_cor_raca,
    gerar_grafico_faixa_etaria_e_sexo,
    gerar_grafico_visao_historica_populacao,
)


def _cidade_cor_raca():
    return {
        "pop_branca": 160000,
        "pop_preta": 80000,
        "pop_parda": 350000,
        "pop_amarela": 7700,
        "pop_indigena": 3200,
    }


def _cidade_faixa_etaria():
    return {
        "faixas_etarias_sexo": [
            {"faixa": "0-4", "mulheres": 1200, "homens": 1300},
            {"faixa": "5-9", "mulheres": 1400, "homens": 1500},
        ]
    }


def _cidade_visao_historica():
    # Campina Grande/PB (Censo 2000/2010/2022).
    return {
        "pop_total_2000": 355331,
        "pop_total_2010": 385213,
        "pop_total_2022": 405072,
    }


def test_gera_grafico_composicao_cor_raca(tmp_path: Path):
    arquivo = gerar_grafico_composicao_cor_raca(
        _cidade_cor_raca(), tmp_path, "campina_grande_pb"
    )

    assert arquivo == "grafico_composicao_cor_raca_campina_grande_pb.png"
    assert (tmp_path / arquivo).is_file()


def test_grafico_composicao_cor_raca_exige_dados(tmp_path: Path):
    with pytest.raises(ValueError, match="Dados de composição por cor ou raça"):
        gerar_grafico_composicao_cor_raca({}, tmp_path, "sem_dados")


def test_gera_grafico_faixa_etaria_e_sexo(tmp_path: Path):
    arquivo = gerar_grafico_faixa_etaria_e_sexo(
        _cidade_faixa_etaria(), tmp_path, "campina_grande_pb"
    )

    assert arquivo == "grafico_faixa_etaria_e_sexo_campina_grande_pb.png"
    assert (tmp_path / arquivo).is_file()


def test_grafico_faixa_etaria_e_sexo_exige_dados(tmp_path: Path):
    with pytest.raises(ValueError, match="Dados por faixa etária e sexo"):
        gerar_grafico_faixa_etaria_e_sexo({}, tmp_path, "sem_dados")


def test_gera_visao_historica_populacao(tmp_path: Path):
    arquivo = gerar_grafico_visao_historica_populacao(
        _cidade_visao_historica(), tmp_path, "campina_grande_pb"
    )

    assert arquivo == "grafico_visao_historica_populacao_campina_grande_pb.png"
    assert (tmp_path / arquivo).is_file()


def test_visao_historica_populacao_usa_titulo_e_legenda_do_eixo_y(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import plotting.demografia as demografia_module
    from plotting import salvar_card_grafico as salvar_card_grafico_original

    figuras_capturadas = []

    def _capturar_e_salvar(fig, chart_file, dpi=180):
        figuras_capturadas.append(fig)
        salvar_card_grafico_original(fig, chart_file, dpi=dpi)

    monkeypatch.setattr(demografia_module, "salvar_card_grafico", _capturar_e_salvar)

    gerar_grafico_visao_historica_populacao(
        _cidade_visao_historica(), tmp_path, "campina_grande_pb"
    )

    (fig,) = figuras_capturadas
    titulo = fig.texts[0].get_text()
    # Sem nm_mun/sigla_uf no contexto (fixture não traz), o título cai no
    # caso genérico, sem cidade anexada.
    assert titulo == "Dinâmica populacional."
    (ax,) = fig.axes
    assert ax.get_ylabel() == "População"


def test_visao_historica_populacao_titulo_inclui_cidade_quando_disponivel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import plotting.demografia as demografia_module
    from plotting import salvar_card_grafico as salvar_card_grafico_original

    figuras_capturadas = []

    def _capturar_e_salvar(fig, chart_file, dpi=180):
        figuras_capturadas.append(fig)
        salvar_card_grafico_original(fig, chart_file, dpi=dpi)

    monkeypatch.setattr(demografia_module, "salvar_card_grafico", _capturar_e_salvar)

    cidade = {**_cidade_visao_historica(), "nm_mun": "Campina Grande", "sigla_uf": "PB"}
    gerar_grafico_visao_historica_populacao(cidade, tmp_path, "campina_grande_pb")

    (fig,) = figuras_capturadas
    assert fig.texts[0].get_text() == "Dinâmica populacional de Campina Grande (PB)."


def test_visao_historica_populacao_titulo_nao_duplica_uf_quando_nm_mun_ja_canonico(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Em produção, nm_mun já chega como "Cidade (UF)" (canonicalização em
    # services/generation.py) e a linha ainda carrega "sigla_uf" à parte —
    # concatenar os dois duplicava a UF ("... (PB) (PB).").
    import plotting.demografia as demografia_module
    from plotting import salvar_card_grafico as salvar_card_grafico_original

    figuras_capturadas = []

    def _capturar_e_salvar(fig, chart_file, dpi=180):
        figuras_capturadas.append(fig)
        salvar_card_grafico_original(fig, chart_file, dpi=dpi)

    monkeypatch.setattr(demografia_module, "salvar_card_grafico", _capturar_e_salvar)

    cidade = {
        **_cidade_visao_historica(),
        "nm_mun": "Campina Grande (PB)",
        "sigla_uf": "PB",
    }
    gerar_grafico_visao_historica_populacao(cidade, tmp_path, "campina_grande_pb")

    (fig,) = figuras_capturadas
    assert fig.texts[0].get_text() == "Dinâmica populacional de Campina Grande (PB)."


def test_ylabel_nao_sai_cortado_para_municipio_de_porte_medio(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Regressão: cidades na faixa de Maceió/Teresina/João Pessoa (pop na
    # casa dos 900 mil) empurram o MaxNLocator para ticks de "1.200,0 mil" —
    # sem ajustar_margem_esquerda_para_rotulos, o "População" rotacionado
    # cai fora da moldura do card (x0 negativo em relação à borda).
    import plotting.demografia as demografia_module
    from plotting import _CARD_MARGEM
    from plotting import salvar_card_grafico as salvar_card_grafico_original

    bboxes_capturadas = []

    def _medir_e_salvar(fig, chart_file, dpi=180):
        # Mede o layout antes do savefig/close originais fecharem a figura —
        # depois disso o canvas deixa de ter um renderer utilizável.
        ax = fig.axes[0]
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        ylabel_bbox = ax.yaxis.get_label().get_window_extent(renderer=renderer)
        largura_fig_px = fig.get_size_inches()[0] * fig.dpi
        bboxes_capturadas.append((ylabel_bbox.x0, _CARD_MARGEM * largura_fig_px))
        salvar_card_grafico_original(fig, chart_file, dpi=dpi)

    monkeypatch.setattr(demografia_module, "salvar_card_grafico", _medir_e_salvar)

    cidade = {
        "pop_total_2000": 700_000,
        "pop_total_2010": 850_000,
        "pop_total_2022": 999_000,
    }

    gerar_grafico_visao_historica_populacao(cidade, tmp_path, "porte_medio")

    ylabel_x0, borda_card_px = bboxes_capturadas[0]
    assert ylabel_x0 >= borda_card_px


def test_grafico_usa_unidade_mil_para_municipios_pequenos(tmp_path: Path):
    # Canapi/AL: população na casa do milhar, não do milhão — dividir tudo
    # por 1_000_000 fazia toda barra arredondar para "0 Mi" (regressão).
    cidade = {
        "pop_total_2000": 7900,
        "pop_total_2010": 7600,
        "pop_total_2022": 6900,
    }

    arquivo = gerar_grafico_visao_historica_populacao(cidade, tmp_path, "canapi_al")

    assert (tmp_path / arquivo).is_file()


def test_grafico_visao_historica_populacao_exige_dados():
    with pytest.raises(ValueError, match="não disponíveis"):
        gerar_grafico_visao_historica_populacao({}, Path("/tmp"), "sem_dados")
