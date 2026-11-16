"""Fontes com nome escrito à mão, sem `tema.$campo` (Doc de área de Demografia,
16/11/2026). Antes, só "demografia.“$nm_painel1” = url" virava badge; a linha
"Perfil demográfico = url" saía como frase comum dentro da caixa cinza."""

from utils.render.renderer import texto_para_html

FONTES_COM_NOME_FIXO = """#!Fontes

Os dados deste relatório foram extraídos dos seguintes painéis de dados do Data Nordeste:

Perfil demográfico = https://datanordeste.sudene.gov.br/data-panel/populacao

#!Conteúdos relacionados

Narrativa de dados: O Nordeste é feminino = https://datanordeste.sudene.gov.br/data-stories/f7d447d1017f4bf58270abba6919a9eb
Boletim: Terceira idade = https://datanordeste.sudene.gov.br/boletim/22yf24FX8jtrU80GS0u8el
"""


def _caixa() -> str:
    return texto_para_html(FONTES_COM_NOME_FIXO, {}, namespace="demografia")


def test_painel_com_nome_fixo_vira_badge():
    assert (
        '<a class="fonte-badge" href="https://datanordeste.sudene.gov.br/data-panel/populacao">'
        "Perfil demográfico</a>"
    ) in _caixa()


def test_tipo_escrito_antes_do_nome_nao_se_repete_no_badge():
    caixa = _caixa()

    assert "<strong>Boletim:</strong> Terceira idade</a>" in caixa
    assert "<strong>Narrativa de dados:</strong> O Nordeste é feminino</a>" in caixa
    assert "Boletim: Boletim" not in caixa


def test_link_fora_do_data_nordeste_continua_texto():
    html = texto_para_html(
        "#!Fontes\n\nIBGE = https://www.ibge.gov.br/censo\n", {}, namespace="demografia"
    )

    assert "fonte-badge" not in html
