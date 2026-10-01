import pathlib
from decimal import ROUND_HALF_UP, Decimal

import numpy as np
from matplotlib.ticker import FuncFormatter, MaxNLocator

from plotting import (
    ESCALA_FONTE,
    iniciar_card_grafico,
    reusar_grafico,
    salvar_card_grafico,
)
from utils.formatting import formatar_numero_ptbr
from utils.queries.base import escalar_valor


def _reservar_espaco_rotulo_x(fig, ax, reserva_polegadas: float = 0.34) -> None:
    # Mesmo ajuste de plotting.saude: `iniciar_card_grafico` posiciona o
    # corpo do card sem folga para um `ax.set_xlabel` — o texto cai abaixo da
    # moldura e some do PNG. Encolhe o eixo reservando uma faixa fixa, em
    # polegadas, na base do card.
    altura_fig = fig.get_size_inches()[1]
    fracao = reserva_polegadas / altura_fig
    posicao = ax.get_position()
    ax.set_position(
        (posicao.x0, posicao.y0 + fracao, posicao.width, posicao.height - fracao)
    )


def gerar_grafico_faixa_etaria_e_sexo(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    faixas = cidade.get("faixas_etarias_sexo") or []
    if not faixas:
        raise ValueError("Dados por faixa etária e sexo não disponíveis.")

    labels = [str(item["faixa"]) for item in faixas]
    mulheres = np.array([float(item["mulheres"] or 0) for item in faixas])
    homens = np.array([float(item["homens"] or 0) for item in faixas])
    y = np.arange(len(labels))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_faixa_etaria_e_sexo_{safe_city}.png"
    reuso = reusar_grafico(chart_file)
    if reuso is not None:
        return reuso

    fig, ax = iniciar_card_grafico((8, 5.6), "População por faixa etária e sexo")
    # Reserva uma faixa abaixo do corpo do gráfico, dentro do card, para a
    # legenda (senão ela cai fora da área desenhada e some do PNG).
    posicao = ax.get_position()
    altura_legenda = posicao.height * 0.12
    ax.set_position(
        (posicao.x0, posicao.y0 + altura_legenda, posicao.width, posicao.height - altura_legenda)
    )
    ax.barh(y, -mulheres, height=0.86, color="#C92F67", label="Mulheres")
    ax.barh(y, homens, height=0.86, color="#8DB52B", label="Homens")

    limite = max(float(mulheres.max()), float(homens.max()), 1.0)
    margem_rotulo = limite * 0.035
    for indice, (valor_mulheres, valor_homens) in enumerate(zip(mulheres, homens)):
        rotulo_mulheres = f"{valor_mulheres:,.0f}".replace(",", ".")
        rotulo_homens = f"{valor_homens:,.0f}".replace(",", ".")
        ax.text(-valor_mulheres - margem_rotulo, indice, rotulo_mulheres,
                ha="right", va="center", fontsize=11*ESCALA_FONTE, color="#292829")
        ax.text(valor_homens + margem_rotulo, indice, rotulo_homens,
                ha="left", va="center", fontsize=11*ESCALA_FONTE, color="#292829")

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=11*ESCALA_FONTE)
    ax.axvline(0, color="#FFFFFF", linewidth=1.5)
    ax.set_xlim(-limite * 1.38, limite * 1.38)
    ax.set_xticks([])
    ax.tick_params(axis="y", length=0, pad=8)
    for borda in ax.spines.values():
        borda.set_visible(False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.05), ncol=2,
              frameon=False, fontsize=11*ESCALA_FONTE)
    salvar_card_grafico(fig, chart_file)
    return chart_file.name


_ROTULOS_COR_RACA = {
    "branca": "Branca",
    "preta": "Preta",
    "parda": "Parda",
    "amarela": "Amarela",
    "indigena": "Indígena",
}

_CORES_COR_RACA = {
    "branca": "#D97AAA",
    "preta": "#514C50",
    "parda": "#C9A227",
    "amarela": "#8DB52B",
    "indigena": "#2F9E8F",
}


def _percentuais_cor_raca(cidade: dict) -> list[tuple[str, float]]:
    """(cor, %) da maior pra menor, com o mesmo denominador e arredondamento do
    $cor_*_per do texto (view): população total do Censo 2022, que inclui quem
    não declarou cor ou raça, e ROUND do Postgres (meio pra cima). Com a soma das
    cinco raças, Águas Belas (PE) saía 56,44% de pardos no gráfico e 56,43% no
    texto (revisão editorial, 30/09/2026)."""
    racas = {
        cor: Decimal(str(cidade.get(f"pop_{cor}") or 0)) for cor in _ROTULOS_COR_RACA
    }
    if not sum(racas.values()):
        raise ValueError("Dados de composição por cor ou raça não disponíveis.")
    total = Decimal(str(cidade.get("pop_total_2022") or sum(racas.values())))

    itens = sorted(racas.items(), key=lambda item: item[1], reverse=True)
    return [
        (cor, float((valor * 100 / total).quantize(Decimal("0.01"), ROUND_HALF_UP)))
        for cor, valor in itens
    ]


# O renderer limita este card a 350px de largura (utils/render/renderer.py), e
# o PNG de 6,4" encolhe para ~76%: com os 11pt padrão, os rótulos saíam com ~8px
# no PDF e a revisão de Humberto de Campos (MA) leu "3,90%" como "3,00%"
# (01/10/2026). Fontes maiores compensam a redução.
_FONTE_COR_RACA = 15.0


def gerar_grafico_composicao_cor_raca(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    itens = _percentuais_cor_raca(cidade)
    labels = [_ROTULOS_COR_RACA[cor] for cor, _ in itens]
    percentuais = [percentual for _, percentual in itens]
    cores = [_CORES_COR_RACA[cor] for cor, _ in itens]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_composicao_cor_raca_{safe_city}.png"
    reuso = reusar_grafico(chart_file)
    if reuso is not None:
        return reuso

    fig, ax = iniciar_card_grafico((6.4, 4.3), "Composição por cor ou raça")

    # Maior percentual no topo, como na lista do card (barras horizontais).
    y = np.arange(len(labels))[::-1]
    ax.barh(y, percentuais, height=0.56, color=cores, zorder=3)

    limite = max(percentuais) * 1.3 if percentuais else 1
    ax.set_xlim(0, limite)
    ax.set_ylim(-0.7, len(labels) - 0.3)
    for pos_y, percentual in zip(y, percentuais):
        ax.text(
            percentual + limite * 0.02,
            pos_y,
            f"{percentual:.2f}%".replace(".", ","),
            ha="left",
            va="center",
            fontsize=_FONTE_COR_RACA*ESCALA_FONTE,
            fontweight=600,
            color="#292829",
        )

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=_FONTE_COR_RACA*ESCALA_FONTE, fontweight=600, color="#292829")
    ax.set_xticks([])
    ax.tick_params(axis="y", length=0, pad=10)
    for borda in ax.spines.values():
        borda.set_visible(False)
    salvar_card_grafico(fig, chart_file)
    return chart_file.name


_ANOS_VISAO_HISTORICA = (2000, 2010, 2022)
_SUFIXO_UNIDADE_POPULACAO = {"bilhões": "Bi", "milhões": "Mi", "mil": "mil", "": ""}
_DIVISOR_UNIDADE_POPULACAO = {"bilhões": 1e9, "milhões": 1e6, "mil": 1e3, "": 1}


def gerar_grafico_visao_historica_populacao(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    populacao_por_ano = {
        ano: cidade.get(f"pop_total_{ano}") for ano in _ANOS_VISAO_HISTORICA
    }
    if any(valor is None for valor in populacao_por_ano.values()):
        raise ValueError("Dados de visão histórica da população não disponíveis.")

    anos = [str(ano) for ano in _ANOS_VISAO_HISTORICA]
    valores = [float(populacao_por_ano[ano]) for ano in _ANOS_VISAO_HISTORICA]

    # A unidade é escolhida a partir do maior valor da série (municípios
    # pequenos ficam na casa do "mil", não de "Mi" — dividir tudo por milhão
    # fazia a barra inteira arredondar para "0 Mi").
    _, unidade = escalar_valor(max(valores))
    divisor = _DIVISOR_UNIDADE_POPULACAO[unidade]
    sufixo = _SUFIXO_UNIDADE_POPULACAO[unidade]
    decimais = 1 if divisor > 1 else 0
    valores_escalados = [valor / divisor for valor in valores]

    def _rotulo(valor_escalado: float) -> str:
        texto = formatar_numero_ptbr(valor_escalado, decimais=decimais)
        return f"{texto} {sufixo}".strip()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_visao_historica_populacao_{safe_city}.png"
    reuso = reusar_grafico(chart_file)
    if reuso is not None:
        return reuso

    fig, ax = iniciar_card_grafico(
        (8, 4.4), "Dinâmica populacional", margem_esquerda=0.20
    )
    _reservar_espaco_rotulo_x(fig, ax, reserva_polegadas=0.5)
    x = np.arange(len(anos))
    barras = ax.bar(x, valores_escalados, width=0.6, color="#D97AAA", zorder=3)
    limite = max(valores_escalados) * 1.26 if valores_escalados else 1
    ax.set_ylim(0, limite)

    for barra, valor_escalado in zip(barras, valores_escalados):
        ax.text(
            barra.get_x() + barra.get_width() / 2,
            valor_escalado + limite * 0.025,
            _rotulo(valor_escalado),
            ha="center",
            va="bottom",
            fontsize=11*ESCALA_FONTE,
            fontweight=600,
            color="#514C50",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(anos, fontsize=11*ESCALA_FONTE, fontweight=600)
    ax.set_xlabel("Ano", fontsize=12*ESCALA_FONTE, color="#514C50")
    ax.set_ylabel("População", fontsize=12*ESCALA_FONTE, color="#514C50")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda valor, _: _rotulo(valor)))
    ax.yaxis.set_major_locator(MaxNLocator(4))
    ax.tick_params(axis="both", length=0, colors="#514C50", labelsize=11*ESCALA_FONTE)
    ax.grid(axis="y", linestyle=(0, (1, 4)), linewidth=0.8, color="#D9D9D9", zorder=0)
    for lado in ("left", "right", "top"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color("#514C50")
    ax.margins(x=0.18)
    salvar_card_grafico(fig, chart_file)
    return chart_file.name
