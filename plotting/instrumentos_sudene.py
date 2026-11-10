"""Gráficos do macrotema Instrumentos da Sudene (FNE).

A série vem achatada em `relatorios_auto.instrsudene_munic`: uma coluna por ano
(`contrato2021`…`contrato2025`, `valor_contrato2021`…`valor_contrato2025`), e
cada valor já escalado com a unidade numa coluna irmã (`valor_contrato2021unid`).
"""

import pathlib
from collections.abc import Callable

from matplotlib.ticker import FuncFormatter, MaxNLocator

from plotting import (
    ESCALA_FONTE,
    FONTE_ROTULO_VALOR,
    FONTE_TICK,
    iniciar_card_grafico,
    reusar_grafico,
    salvar_card_grafico,
)
from plotting.economia_renda import _reservar_espaco_rotulo_x
from utils.formatting import formatar_numero_ptbr
from utils.queries.base import escalar_valor

ANOS_SERIE_FNE = (2021, 2022, 2023, 2024, 2025)
_COR_QUANTIDADE = "#C0560F"
_COR_VALOR = "#13793B"
_COR_TEXTO = "#514C50"

# IMPORTANT: a unidade muda de ano para ano no mesmo município (Alcântara/MA:
# "mil" em 2021, "milhão" em 2023, "milhões" em 2024) e vem no singular e no
# plural. Plotar o número escalado cru misturaria escalas na mesma linha; tudo
# volta para reais antes de desenhar.
_MULTIPLICADOR_UNIDADE = {
    "reais": 1.0,
    "": 1.0,
    "mil": 1e3,
    "milhão": 1e6,
    "milhões": 1e6,
    "bilhão": 1e9,
    "bilhões": 1e9,
}
_UNIDADE_ABREVIADA = {"bilhões": "Bi", "milhões": "Mi", "mil": "mil", "": ""}
_DIVISOR_UNIDADE = {"bilhões": 1e9, "milhões": 1e6, "mil": 1e3, "": 1.0}
_UNIDADE_SINGULAR = {"bilhões": "bilhão", "milhões": "milhão"}


def quantidade_de_contratacoes_por_ano(cidade: dict) -> list[float]:
    """Número de contratações do FNE em cada ano de `ANOS_SERIE_FNE`.

    Ex.: Recife/PE -> [1015.0, 1317.0, 2223.0, 4274.0, 4341.0].
    """
    faltando = [ano for ano in ANOS_SERIE_FNE if cidade.get(f"contrato{ano}") is None]
    if faltando:
        raise ValueError(f"Contratações do FNE ausentes para os anos {faltando}.")

    return [float(cidade[f"contrato{ano}"]) for ano in ANOS_SERIE_FNE]


def valor_contratado_em_reais(valor: object, unidade: object) -> float:
    """Desfaz a escala da view: (785.66, "milhões") -> 785_660_000.0."""
    chave = str(unidade or "").strip().lower()
    if chave not in _MULTIPLICADOR_UNIDADE:
        raise ValueError(
            f"Unidade {unidade!r} do valor contratado não reconhecida; "
            f"esperado uma de {sorted(_MULTIPLICADOR_UNIDADE)}."
        )

    return float(valor) * _MULTIPLICADOR_UNIDADE[chave]


def valor_contratado_por_ano(cidade: dict) -> list[float]:
    """Valor contratado do FNE, em reais, em cada ano de `ANOS_SERIE_FNE`."""
    faltando = [ano for ano in ANOS_SERIE_FNE if cidade.get(f"valor_contrato{ano}") is None]
    if faltando:
        raise ValueError(f"Valor contratado do FNE ausente para os anos {faltando}.")

    return [
        valor_contratado_em_reais(cidade[f"valor_contrato{ano}"], cidade.get(f"valor_contrato{ano}unid"))
        for ano in ANOS_SERIE_FNE
    ]


# (deslocamento em pontos, alinhamento horizontal, alinhamento vertical).
_ANCORA_DO_ROTULO = {
    "acima": ((0, 9), "center", "bottom"),
    "abaixo": ((0, -11), "center", "top"),
    "acima_esquerda": ((-8, 6), "right", "bottom"),
    "acima_direita": ((8, 6), "left", "bottom"),
}


def posicao_do_rotulo(valores: list[float], indice: int) -> str:
    """Lado do ponto por onde a linha não passa, para o rótulo não ficar em cima
    dela. Ex.: Igaci/AL 2021 (9,8 Mi, subindo para 20,2 Mi) -> "acima_esquerda".

    WARNING: não volte ao rótulo centrado com fundo branco. O fundo escondia a
    linha que cruzava o texto, mas num trecho íngreme a linha parecia cortada
    (Igaci/AL e Arapiraca/AL, 04/11/2026).
    """
    valor = valores[indice]
    sobe_a_esquerda = indice > 0 and valores[indice - 1] > valor
    sobe_a_direita = indice < len(valores) - 1 and valores[indice + 1] > valor
    if sobe_a_esquerda and sobe_a_direita:
        # Vale: a linha sai para cima dos dois lados, então só embaixo está livre.
        return "abaixo"
    if sobe_a_direita:
        return "acima_esquerda"
    if sobe_a_esquerda:
        return "acima_direita"

    return "acima"


def _desenhar_serie_anual(
    titulo: str,
    valores: list[float],
    cor: str,
    formatar_eixo: Callable[[float], str],
    formatar_ponto: Callable[[float], str],
    chart_file: pathlib.Path,
    eixo_inteiro: bool = False,
) -> None:
    fig, ax = iniciar_card_grafico((8, 4.4), titulo, margem_esquerda=0.20)
    _reservar_espaco_rotulo_x(fig, ax, reserva_polegadas=0.3)
    ax.plot(ANOS_SERIE_FNE, valores, color=cor, linewidth=3, marker="o", markersize=9, zorder=3)
    topo = max(valores) * 1.18 or 1.0
    ax.set_ylim(0, topo)
    for indice, (ano, valor) in enumerate(zip(ANOS_SERIE_FNE, valores)):
        deslocamento, ha, va = _ANCORA_DO_ROTULO[posicao_do_rotulo(valores, indice)]
        ax.annotate(
            formatar_ponto(valor), (ano, valor), xytext=deslocamento, textcoords="offset points",
            ha=ha, va=va, fontsize=FONTE_ROTULO_VALOR * ESCALA_FONTE, color=_COR_TEXTO, zorder=4,
        )

    _estilizar_eixos(ax, formatar_eixo, eixo_inteiro)
    salvar_card_grafico(fig, chart_file)


def _estilizar_eixos(ax, formatar_eixo: Callable[[float], str], eixo_inteiro: bool) -> None:
    # O design mostra um ano vazio em cada ponta (2020 e 2026) para a linha não
    # encostar na borda do card.
    anos_do_eixo = range(ANOS_SERIE_FNE[0] - 1, ANOS_SERIE_FNE[-1] + 2)
    ax.set_xticks(list(anos_do_eixo))
    ax.set_xlim(anos_do_eixo[0] - 0.4, anos_do_eixo[-1] + 0.4)
    # Passos 1-2-5: as marcas caem em valores com no máximo uma casa decimal
    # ("R$ 1,5 milhão"), que o formatador consegue escrever sem arredondar
    # duas marcas para o mesmo texto.
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6, steps=[1, 2, 5, 10], integer=eixo_inteiro, min_n_ticks=3))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda valor, _: formatar_eixo(valor)))
    ax.tick_params(axis="both", length=0, colors=_COR_TEXTO, labelsize=FONTE_TICK * ESCALA_FONTE)
    # Sem esse afastamento o "0" do eixo Y fica na altura dos anos e encosta no
    # primeiro ano do eixo X ("2020").
    ax.tick_params(axis="x", pad=10)
    ax.tick_params(axis="y", pad=12)
    for lado in ("left", "right", "top"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(_COR_TEXTO)


def _formatar_contratacoes(valor: float) -> str:
    return formatar_numero_ptbr(valor)


def _formatadores_de_reais(maior_valor: float) -> tuple[Callable[[float], str], Callable[[float], str]]:
    # Unidade única para o card inteiro, escolhida pelo maior valor da série:
    # município pequeno fica em "mil", não em "0,1 milhões".
    _, unidade = escalar_valor(maior_valor)
    divisor = _DIVISOR_UNIDADE[unidade]
    decimais = 1 if divisor > 1 else 0

    def eixo(valor: float) -> str:
        if valor == 0:
            return "R$ 0"

        escalado = round(valor / divisor, 1)
        texto = formatar_numero_ptbr(escalado, decimais=0 if escalado.is_integer() else 1)
        nome_unidade = _UNIDADE_SINGULAR.get(unidade, unidade) if escalado < 2 else unidade

        return f"R$ {texto} {nome_unidade}".rstrip()

    def ponto(valor: float) -> str:
        return f"{formatar_numero_ptbr(valor / divisor, decimais=decimais)} {_UNIDADE_ABREVIADA[unidade]}".rstrip()

    return eixo, ponto


def gerar_grafico_quantidade_de_contratacoes(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    contratacoes = quantidade_de_contratacoes_por_ano(cidade)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_quantidade_de_contratacoes_{safe_city}.png"
    reuso = reusar_grafico(chart_file)
    if reuso is not None:
        return reuso

    _desenhar_serie_anual(
        "Quantidade de contratações", contratacoes, _COR_QUANTIDADE,
        _formatar_contratacoes, _formatar_contratacoes, chart_file, eixo_inteiro=True,
    )
    return chart_file.name


def gerar_grafico_valor_investido(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    valores = valor_contratado_por_ano(cidade)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_valor_investido_{safe_city}.png"
    reuso = reusar_grafico(chart_file)
    if reuso is not None:
        return reuso

    formatar_eixo, formatar_ponto = _formatadores_de_reais(max(valores))
    _desenhar_serie_anual(
        "Valor total investido", valores, _COR_VALOR, formatar_eixo, formatar_ponto, chart_file
    )
    return chart_file.name
