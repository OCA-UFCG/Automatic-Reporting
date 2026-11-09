from decimal import Decimal
from pathlib import Path

import pytest

from plotting.instrumentos_sudene_porte import (
    PORTES_EMPRESA,
    _cor_do_texto_sobre,
    _desenhar_pizza_por_porte,
    _texto_do_rotulo,
    faixas_angulares,
    gerar_grafico_porte_contratacoes,
    gerar_grafico_porte_valor,
    percentuais_por_porte,
    ponto_dentro_da_fatia,
)
from plotting.saneamento import _angulos_dos_meios
from services.generation import GRAFICOS_AUTO_MARCADOR, GRAFICOS_POR_TEMA


def _linha_da_view(contratos: dict[str, str], valores: dict[str, str]) -> dict:
    # Mesmo formato de `relatorios_auto.instrsudene_munic`: contrato_<porte> e
    # valor_<porte>, já em percentual.
    linha = {f"contrato_{porte}": Decimal(pct) for porte, pct in contratos.items()}
    linha.update({f"valor_{porte}": Decimal(pct) for porte, pct in valores.items()})
    return linha


# Recife/PE na view do Gamma em 04/11/2026: os números do exemplo do design.
RECIFE = _linha_da_view(
    {"mini": "1.64", "micro": "72.54", "pequeno": "18.18", "peq_medio": "4.15",
     "media1": "2.56", "media2": "0.58", "grande": "0.37"},
    {"mini": "0.52", "micro": "6.82", "pequeno": "41.29", "peq_medio": "33.13",
     "media1": "10.72", "media2": "3.64", "grande": "3.87"},
)
# Igaci/AL: três portes com 0% nos dois gráficos.
IGACI = _linha_da_view(
    {"mini": "69.88", "micro": "28.40", "pequeno": "1.15", "peq_medio": "0.58",
     "media1": "0", "media2": "0", "grande": "0"},
    {"mini": "68.97", "micro": "10.61", "pequeno": "10.63", "peq_medio": "9.79",
     "media1": "0", "media2": "0", "grande": "0"},
)


def test_percentuais_seguem_a_ordem_alfabetica_do_design():
    assert [rotulo for _, rotulo in PORTES_EMPRESA] == [
        "Grande", "Médio I", "Médio II", "Micro", "Mini", "Pequeno", "Pequeno-Médio",
    ]
    assert percentuais_por_porte(RECIFE, "contrato_") == [0.37, 2.56, 0.58, 72.54, 1.64, 18.18, 4.15]
    assert percentuais_por_porte(RECIFE, "valor_")[5] == 41.29


def test_porte_com_zero_nao_ganha_rotulo():
    # `_angulos_dos_meios` só devolve fatia > 0: Grande, Médio I e Médio II
    # (índices 0, 1 e 2) ficam fora do desenho em Igaci.
    rotulados = _angulos_dos_meios(percentuais_por_porte(IGACI, "contrato_"))

    assert sorted(rotulados) == [3, 4, 5, 6]


def test_faixas_angulares_seguem_a_pizza_a_partir_do_topo_no_sentido_horario():
    assert faixas_angulares([25, 0, 75]) == {0: (90, 0), 2: (0, -270)}


@pytest.mark.parametrize(
    ("x", "y", "esperado"),
    [
        (0.5, 0.5, True),     # meio da fatia de 90° a 0°
        (-0.5, 0.5, False),   # outra fatia
        (0.69, 0.69, False),  # dentro do ângulo, mas além do raio útil
        (0.6, 0.005, False),  # colado na borda de 0°, sem folga
    ],
)
def test_ponto_dentro_da_fatia(x, y, esperado):
    assert ponto_dentro_da_fatia(x, y, (90, 0)) is esperado


def test_rotulo_de_dentro_nunca_passa_da_borda_da_fatia(tmp_path: Path, monkeypatch):
    # Regressão: "Pequeno 18%" (Recife/PE) era posto dentro pelo percentual e
    # passava da borda da fatia. Todo texto que fica dentro tem de caber nela.
    import matplotlib.pyplot as plt

    from plotting import instrumentos_sudene_porte as porte

    capturados = []
    original = porte._texto_cabe_na_fatia

    def espiao(ax, texto, faixa):
        cabe = original(ax, texto, faixa)
        capturados.append((texto.get_text(), cabe))
        return cabe

    monkeypatch.setattr(porte, "_texto_cabe_na_fatia", espiao)
    monkeypatch.setattr(porte, "salvar_card_grafico", lambda fig, _: plt.close(fig))
    for prefixo, cores in (("contrato_", porte._CORES_CONTRATACOES), ("valor_", porte._CORES_VALOR)):
        _desenhar_pizza_por_porte("t", percentuais_por_porte(RECIFE, prefixo), cores, tmp_path / "x.png")

    aceitos = {texto.split("\n")[0] for texto, cabe in capturados if cabe}
    assert "Pequeno" in aceitos  # o de 41% do valor cabe
    assert "Micro" in aceitos    # o de 73% das contratações cabe
    assert ("Pequeno\n18%", True) not in capturados


def test_rotulo_tem_percentual_inteiro_e_quebra_no_hifen():
    assert _texto_do_rotulo(3, 72.54) == "Micro\n73%"
    assert _texto_do_rotulo(6, 33.13) == "Pequeno-\nMédio\n33%"
    assert _texto_do_rotulo(0, 0.37) == "Grande\n0%"


def test_texto_branco_so_em_fatia_escura():
    assert _cor_do_texto_sobre("#085F2D") == "#FFFFFF"
    assert _cor_do_texto_sobre("#FFD65A") != "#FFFFFF"


def test_coluna_ausente_vira_value_error_com_a_chave():
    linha = {**RECIFE, "valor_grande": None}

    with pytest.raises(ValueError, match="valor_grande"):
        percentuais_por_porte(linha, "valor_")


def test_todos_os_portes_zerados_vira_value_error():
    linha = {chave: Decimal(0) for chave in RECIFE}

    with pytest.raises(ValueError, match="zerados"):
        percentuais_por_porte(linha, "contrato_")


@pytest.mark.parametrize(
    ("gerar", "arquivo"),
    [
        (gerar_grafico_porte_contratacoes, "grafico_porte_contratacoes_recife_pe.png"),
        (gerar_grafico_porte_valor, "grafico_porte_valor_recife_pe.png"),
    ],
)
def test_gera_as_pizzas_de_recife(tmp_path: Path, gerar, arquivo):
    assert gerar(RECIFE, tmp_path, "recife_pe") == arquivo
    assert (tmp_path / arquivo).is_file()


def test_gera_pizza_com_portes_zerados(tmp_path: Path):
    assert gerar_grafico_porte_valor(IGACI, tmp_path, "igaci_al").endswith(".png")


def test_tema_registra_as_pizzas_pelos_marcadores_do_doc():
    nomes = [nome for nome, _, _ in GRAFICOS_POR_TEMA["instrumentos-sudene"]]

    # Presentes e adjacentes, sem prender à posição na tupla: o próximo gráfico
    # do tema não deve quebrar este teste (revisão do PR do gráfico de setor).
    assert nomes.index("grafico_porte_valor") == nomes.index("grafico_porte_contratacoes") + 1
    assert "instrumentos-sudene" not in GRAFICOS_AUTO_MARCADOR
