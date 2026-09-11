import pathlib

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter, MaxNLocator

from plotting import ESCALA_FONTE
from utils.formatting import formatar_numero_ptbr
from utils.queries.base import escalar_valor


def _salvar_figura_com_fundo_branco(
    fig, ax, chart_file: pathlib.Path, pad: float | None = None
) -> None:
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    plt.tight_layout() if pad is None else plt.tight_layout(pad=pad)
    plt.savefig(chart_file, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


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

    fig, ax = plt.subplots(figsize=(8, 5.2))
    ax.barh(y, -mulheres, height=0.86, color="#C92F67", label="Mulheres")
    ax.barh(y, homens, height=0.86, color="#8DB52B", label="Homens")

    limite = max(float(mulheres.max()), float(homens.max()), 1.0)
    margem_rotulo = limite * 0.035
    for indice, (valor_mulheres, valor_homens) in enumerate(zip(mulheres, homens)):
        rotulo_mulheres = f"{valor_mulheres:,.0f}".replace(",", ".")
        rotulo_homens = f"{valor_homens:,.0f}".replace(",", ".")
        ax.text(-valor_mulheres - margem_rotulo, indice, rotulo_mulheres,
                ha="right", va="center", fontsize=9*ESCALA_FONTE, color="#292829")
        ax.text(valor_homens + margem_rotulo, indice, rotulo_homens,
                ha="left", va="center", fontsize=9*ESCALA_FONTE, color="#292829")

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9*ESCALA_FONTE)
    ax.axvline(0, color="#FFFFFF", linewidth=1.5)
    ax.set_xlim(-limite * 1.38, limite * 1.38)
    ax.set_xticks([])
    ax.tick_params(axis="y", length=0, pad=8)
    for borda in ax.spines.values():
        borda.set_visible(False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.06), ncol=2,
              frameon=False, fontsize=9*ESCALA_FONTE)
    _salvar_figura_com_fundo_branco(fig, ax, chart_file)
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


def gerar_grafico_composicao_cor_raca(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    racas = {
        cor: float(cidade.get(f"pop_{cor}") or 0) for cor in _ROTULOS_COR_RACA
    }
    total = sum(racas.values())
    if not total:
        raise ValueError("Dados de composição por cor ou raça não disponíveis.")

    itens = sorted(racas.items(), key=lambda item: item[1], reverse=True)
    labels = [_ROTULOS_COR_RACA[cor] for cor, _ in itens]
    percentuais = [valor / total * 100 for _, valor in itens]
    cores = [_CORES_COR_RACA[cor] for cor, _ in itens]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_composicao_cor_raca_{safe_city}.png"

    fig, ax = plt.subplots(figsize=(6.1, 4.05))
    x = np.arange(len(labels))
    barras = ax.bar(x, percentuais, width=0.6, color=cores, zorder=3)
    limite = max(percentuais) * 1.26 if percentuais else 1
    ax.set_ylim(0, limite)

    for barra, percentual in zip(barras, percentuais):
        ax.text(
            barra.get_x() + barra.get_width() / 2,
            percentual + limite * 0.025,
            f"{percentual:.1f}%".replace(".", ","),
            ha="center",
            va="bottom",
            fontsize=10*ESCALA_FONTE,
            fontweight=600,
            color="#514C50",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10*ESCALA_FONTE, fontweight=600)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda valor, _: f"{valor:.0f}%"))
    ax.yaxis.set_major_locator(MaxNLocator(4))
    ax.grid(axis="y", linestyle=(0, (1, 4)), linewidth=0.8, color="#D9D9D9", zorder=0)
    ax.tick_params(axis="both", length=0, colors="#514C50", labelsize=9*ESCALA_FONTE)
    for lado in ("left", "right", "bottom"):
        ax.spines[lado].set_visible(False)
    ax.spines["top"].set_color("#ECECEC")
    ax.spines["top"].set_linewidth(7)
    ax.margins(x=0.18)
    _salvar_figura_com_fundo_branco(fig, ax, chart_file, pad=1.2)
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

    fig, ax = plt.subplots(figsize=(6.1, 4.05))
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
            fontsize=10*ESCALA_FONTE,
            fontweight=600,
            color="#514C50",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(anos, fontsize=10*ESCALA_FONTE, fontweight=600)
    ax.set_xlabel("Ano", fontsize=9*ESCALA_FONTE, color="#514C50")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda valor, _: _rotulo(valor)))
    ax.yaxis.set_major_locator(MaxNLocator(4))
    ax.grid(axis="y", linestyle=(0, (1, 4)), linewidth=0.8, color="#D9D9D9", zorder=0)
    ax.tick_params(axis="both", length=0, colors="#514C50", labelsize=9*ESCALA_FONTE)
    for lado in ("left", "right", "bottom"):
        ax.spines[lado].set_visible(False)
    ax.spines["top"].set_color("#ECECEC")
    ax.spines["top"].set_linewidth(7)
    ax.margins(x=0.18)
    _salvar_figura_com_fundo_branco(fig, ax, chart_file, pad=1.2)
    return chart_file.name
