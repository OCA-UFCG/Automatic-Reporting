import itertools
import math
from decimal import Decimal
from pathlib import Path

import matplotlib.pyplot as plt
import pytest

from plotting import saneamento
from plotting.saneamento import (
    _ANOS_DINAMICA_ESGOTO,
    _ESPACO_ENTRE_ROTULOS,
    _FONTE_TOTAL_MINIMA,
    _Y_MAXIMO_ROTULO,
    _angulos_dos_meios,
    _fonte_total_ajustada_ao_buraco,
    _pontos_por_ano,
    _posicoes_dos_rotulos,
    _quebrar_rotulo_longo,
    gerar_grafico_coleta_lixo,
    gerar_grafico_dinamica_esgoto,
    gerar_grafico_esgotamento_sanitario,
)


def test_gera_rosca_de_esgotamento(tmp_path: Path):
    # Campina Grande/PB (Censo 2022), a cidade da imagem do Doc.
    cidade = {
        "esg_total": 147149,
        "esg_rede_geral_ou_pluvial": 127454,
        "esg_fossa_septica_ou_fossa_filtro": 7799,
        "esg_fossa_rudimentar_ou_buraco": 6327,
        "esg_vala": 2060,
        "esg_rio_lago_corrego_ou_mar": 1913,
        "esg_outra_forma": 442,
        "esg_nao_tinham_banheiro": 1154,
    }

    arquivo = gerar_grafico_esgotamento_sanitario(cidade, tmp_path, "campina_grande_pb")

    assert arquivo == "grafico_esgotamento_sanitario_campina_grande_pb.png"
    assert (tmp_path / arquivo).is_file()


def test_fonte_total_encolhe_para_texto_longo():
    # Mesmo eixo/aspecto do buraco da rosca em `gerar_grafico_esgotamento_sanitario`:
    # a medição de largura depende do aspecto já estar "equal" (ver comentário
    # em `gerar_grafico_esgotamento_sanitario`), senão o teste passaria mesmo
    # com a medição feita na escala px/unidade errada.
    fig, ax = plt.subplots(figsize=(10, 5.4))
    ax.set_xlim(-1.55, 1.55)
    ax.set_ylim(-1.55, 1.55)
    ax.set_aspect("equal")

    fonte_curta = _fonte_total_ajustada_ao_buraco(fig, ax, "147 mil", 22.0)
    fonte_longa = _fonte_total_ajustada_ao_buraco(fig, ax, "5.470.000 mil", 22.0)

    assert fonte_curta == 22.0
    assert fonte_longa < fonte_curta
    assert fonte_longa >= _FONTE_TOTAL_MINIMA
    plt.close(fig)


def test_grafico_exige_dados(tmp_path: Path):
    with pytest.raises(ValueError, match="não disponíveis"):
        gerar_grafico_esgotamento_sanitario({"esg_total": 0}, tmp_path, "sem_dados")


def test_gera_dinamica_esgoto(tmp_path: Path):
    # Campina Grande/PB: 2000 vem como string (fonte antiga da view), 2010 e
    # 2022 como Decimal — mistura real que o parser precisa suportar.
    cidade = {
        "esgoto_rede_2000": "68.4",
        "esgoto_rede_2010": Decimal("79.4"),
        "esgoto_rede_2022": Decimal("86.6"),
    }

    arquivo = gerar_grafico_dinamica_esgoto(cidade, tmp_path, "campina_grande_pb")

    assert arquivo == "grafico_dinamica_esgoto_campina_grande_pb.png"
    assert (tmp_path / arquivo).is_file()


def test_dinamica_esgoto_mantem_ano_com_zero(tmp_path: Path):
    # 0% é cobertura real, não falta de dado: 469 dos 2.074 municípios da view
    # têm 0% em 2000. O ano precisa virar barra zerada, não sumir do gráfico.
    cidade = {
        "esgoto_rede_2000": "0",
        "esgoto_rede_2010": Decimal("12.5"),
        "esgoto_rede_2022": Decimal("30.0"),
    }

    assert _pontos_por_ano(cidade, _ANOS_DINAMICA_ESGOTO) == [
        ("2000", 0.0),
        ("2010", 12.5),
        ("2022", 30.0),
    ]
    arquivo = gerar_grafico_dinamica_esgoto(cidade, tmp_path, "com_zero")
    assert (tmp_path / arquivo).is_file()


def test_dinamica_esgoto_omite_ano_sem_dado(tmp_path: Path):
    # "sem dados" é o texto que a view guarda em alguns municípios; junto com
    # None, é o único caso que deve sair do gráfico.
    cidade = {
        "esgoto_rede_2000": "sem dados",
        "esgoto_rede_2010": None,
        "esgoto_rede_2022": Decimal("30.0"),
    }

    assert _pontos_por_ano(cidade, _ANOS_DINAMICA_ESGOTO) == [("2022", 30.0)]


def test_grafico_dinamica_esgoto_exige_dados(tmp_path: Path):
    cidade = {
        "esgoto_rede_2000": None,
        "esgoto_rede_2010": "sem dados",
        "esgoto_rede_2022": None,
    }
    with pytest.raises(ValueError, match="não disponíveis"):
        gerar_grafico_dinamica_esgoto(cidade, tmp_path, "sem_dados")


def test_gera_coleta_lixo(tmp_path: Path):
    # Campina Grande/PB.
    cidade = {
        "coleta_2010": Decimal("94.8"),
        "coleta_2022": Decimal("97.5"),
    }

    arquivo = gerar_grafico_coleta_lixo(cidade, tmp_path, "campina_grande_pb")

    assert arquivo == "grafico_coleta_lixo_campina_grande_pb.png"
    assert (tmp_path / arquivo).is_file()


def test_grafico_coleta_lixo_exige_dados(tmp_path: Path):
    cidade = {
        "coleta_2010": None,
        "coleta_2022": "sem dados",
    }
    with pytest.raises(ValueError, match="não disponíveis"):
        gerar_grafico_coleta_lixo(cidade, tmp_path, "sem_dados")


def test_quebra_rotulo_longo_da_legenda():
    # O rótulo mais longo de _CATEGORIAS vaza a faixa da legenda se não
    # quebrar; o corte é por comprimento, então continua valendo se o texto
    # do Doc mudar ou entrar categoria nova.
    assert _quebrar_rotulo_longo("Não tinham banheiro e/ou sanitário") == (
        "Não tinham banheiro e/ou\nsanitário"
    )
    assert _quebrar_rotulo_longo("Vala") == "Vala"
    assert "\n" not in _quebrar_rotulo_longo("Fossa séptica ou fossa filtro")


# Percentuais do exemplo da revisão de Segurança Hídrica: com o piso de 16°
# por fatia que existia antes, 0,22% e 0,02% eram desenhados do mesmo tamanho
# e 67,30% ocupava só metade da rosca.
_EXEMPLO_REVISAO = [67.30, 22.48, 8.23, 0.39, 1.37, 0.22, 0.02]


def test_fatias_sao_desenhadas_na_proporcao_real(tmp_path: Path, monkeypatch):
    figuras = []
    monkeypatch.setattr(
        saneamento, "salvar_card_grafico", lambda fig, _arquivo: figuras.append(fig)
    )
    cidade = dict(zip((chave for chave, _, _ in saneamento._CATEGORIAS), _EXEMPLO_REVISAO))
    cidade["esg_total"] = 100

    gerar_grafico_esgotamento_sanitario(cidade, tmp_path, "proporcao_real")

    fatias = [p for p in figuras[0].axes[0].patches if hasattr(p, "theta1")]
    graus = [(f.theta2 - f.theta1) % 360 for f in fatias]
    # `ax.pie` normaliza pela soma (os percentuais do exemplo, arredondados,
    # somam 100,01).
    soma = sum(_EXEMPLO_REVISAO)
    for grau, percentual in zip(graus, _EXEMPLO_REVISAO):
        assert grau == pytest.approx(360.0 * percentual / soma, abs=1e-6)
    plt.close(figuras[0])


def test_meio_da_fatia_segue_a_geometria_do_pie():
    # Começa no topo (90°) e anda no sentido horário.
    meios = _angulos_dos_meios([50, 0, 50])

    assert meios == {0: 0.0, 2: -180.0}


def test_categoria_zerada_nao_ganha_rotulo():
    assert 1 not in _posicoes_dos_rotulos([100, 0, 50])


def test_sem_rotulo_quando_nao_ha_total():
    assert _posicoes_dos_rotulos([0, 0, 0]) == {}


@pytest.mark.parametrize(
    "valores",
    [
        _EXEMPLO_REVISAO,
        [123, 10, 1397, 54, 59, 27, 6],  # Belém/AL
        [127454, 7799, 6327, 2060, 1913, 442, 1154],  # Campina Grande/PB
        [1, 1, 1, 1, 1, 1, 9994],  # seis fatias mínimas coladas
    ],
)
def test_rotulos_nao_se_sobrepoem_nem_cruzam(valores):
    posicoes = _posicoes_dos_rotulos(valores)
    meios = _angulos_dos_meios(valores)

    assert set(posicoes) == {i for i, valor in enumerate(valores) if valor > 0}
    for lado in (1, -1):
        coluna = sorted(
            (i for i, (_, x, _) in posicoes.items() if x * lado > 0),
            key=lambda i: -posicoes[i][2],
        )
        alturas = [posicoes[i][2] for i in coluna]
        assert all(abs(y) <= _Y_MAXIMO_ROTULO + 1e-9 for y in alturas)
        for cima, baixo in itertools.pairwise(alturas):
            assert cima - baixo >= _ESPACO_ENTRE_ROTULOS - 1e-9
        # Ordem dos rótulos = ordem vertical das fatias: linhas-guia não se cruzam.
        assert coluna == sorted(coluna, key=lambda i: -math.sin(math.radians(meios[i])))
