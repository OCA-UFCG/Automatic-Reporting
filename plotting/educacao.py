import pathlib

import numpy as np

from plotting import ESCALA_FONTE, iniciar_card_grafico, salvar_card_grafico
from utils.formatting import coerce_para_float as _coerce_para_float
from utils.formatting import formatar_numero_ptbr

# (prefixo da coluna na view, cor) — ordem espelha a escala de instrução
# (pri = fundamental incompleto ... quar = superior completo) e as cores do Doc.
_NIVEIS_INSTRUCAO = (
    ("pri_nivel", "#8B4A2B"),
    ("seg_nivel", "#1D7A9C"),
    ("ter_nivel", "#E8871E"),
    ("quar_nivel", "#7ECBE0"),
)


def gerar_grafico_nivel_instrucao(
    cidade,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
):
    colunas_necessarias = [
        f"{prefixo}_{sufixo}"
        for prefixo, _cor in _NIVEIS_INSTRUCAO
        for sufixo in ("classe", "per", "pop")
    ]
    colunas_faltantes = [
        coluna for coluna in colunas_necessarias if coluna not in cidade
    ]
    if colunas_faltantes:
        raise ValueError(
            "Colunas necessárias ausentes para gerar o gráfico de nível de "
            "instrução: " + ", ".join(sorted(colunas_faltantes))
        )

    rotulos = [cidade[f"{prefixo}_classe"] for prefixo, _cor in _NIVEIS_INSTRUCAO]
    populacoes = [
        _coerce_para_float(cidade[f"{prefixo}_pop"]) for prefixo, _cor in _NIVEIS_INSTRUCAO
    ]
    percentuais = [
        _coerce_para_float(cidade[f"{prefixo}_per"]) for prefixo, _cor in _NIVEIS_INSTRUCAO
    ]
    cores = [cor for _prefixo, cor in _NIVEIS_INSTRUCAO]

    if not any(populacoes):
        raise ValueError(
            "Dados de distribuição da população por nível de instrução não "
            "disponíveis."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_nivel_instrucao_{safe_city}.png"

    fig, ax = iniciar_card_grafico(
        (10, 9.2),
        "Distribuição da população por nível de instrução",
        margem_esquerda=0.06,
        margem_direita=0.06,
    )
    # A rosca ocupa só a metade central do card: rótulos externos com linha
    # de chamada (acima/abaixo) e a legenda embaixo precisam da folga nas
    # bordas, senão vazam da moldura. `figsize` bem mais alto que largo (e não
    # só a fração `folga_base`) é o que garante essa folga: com fonte de
    # tamanho fixo em pontos, uma figura mais alta faz a legenda ocupar uma
    # fatia menor da altura total, sem estourar por baixo do card.
    posicao = ax.get_position()
    folga_lateral = posicao.width * 0.22
    folga_topo = posicao.height * 0.06
    folga_base = posicao.height * 0.3
    ax.set_position(
        (
            posicao.x0 + folga_lateral,
            posicao.y0 + folga_base,
            posicao.width - 2 * folga_lateral,
            posicao.height - folga_topo - folga_base,
        )
    )

    wedges, _textos = ax.pie(
        populacoes,
        colors=cores,
        startangle=90,
        counterclock=False,
        wedgeprops={"width": 0.42, "edgecolor": "white", "linewidth": 1.5},
    )

    # Rótulos externos com linha de chamada — mesma técnica do exemplo
    # "labeling a pie" do matplotlib: a linha sai da borda da fatia (no
    # ângulo médio dela) até o texto, posicionado fora da rosca.
    propriedades_seta = {
        "arrowstyle": "-",
        "color": "#8A8F98",
        "linewidth": 1,
    }
    for wedge, populacao, percentual in zip(wedges, populacoes, percentuais):
        angulo_medio = (wedge.theta1 + wedge.theta2) / 2
        y = np.sin(np.deg2rad(angulo_medio))
        x = np.cos(np.deg2rad(angulo_medio))
        alinhamento_horizontal = "left" if x >= 0 else "right"
        propriedades_seta["connectionstyle"] = f"angle,angleA=0,angleB={angulo_medio}"

        texto = (
            f"{formatar_numero_ptbr(populacao)} "
            f"({formatar_numero_ptbr(percentual, decimais=2)}%)"
        )
        ax.annotate(
            texto,
            xy=(x * 0.79, y * 0.79),
            xytext=(1.3 * x, 1.3 * y),
            ha=alinhamento_horizontal,
            va="center",
            fontsize=11.5 * ESCALA_FONTE,
            color="#4A4A4A",
            arrowprops=dict(propriedades_seta),
        )

    ax.legend(
        wedges,
        rotulos,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.14),
        bbox_transform=fig.transFigure,
        ncol=2,
        frameon=False,
        fontsize=11 * ESCALA_FONTE,
        handlelength=1.0,
        labelspacing=0.6,
        columnspacing=1.6,
    )
    ax.set_aspect("equal")

    salvar_card_grafico(fig, chart_file)

    return chart_file.name


def gerar_grafico_cor_faixa_etaria(
    cidade,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
):
    # Rótulo em duas linhas em vez de rotacionado: texto rotacionado fica
    # ilegível quando a imagem é reduzida pra caber na largura da página.
    faixas_etarias = [
        ("15 a 19\nanos", "15_a_19"),
        ("20 a 29\nanos", "20_a_29"),
        ("30 a 39\nanos", "30_a_39"),
        ("40 a 49\nanos", "40_a_49"),
        ("50 a 59\nanos", "50_a_59"),
        ("60 anos\nou mais", "mais60"),
    ]

    cores = {
        "Amarela": "amarela",
        "Branca": "branca",
        "Indígena": "indigena",
        "Parda": "parda",
        "Preta": "preta",
    }

    colunas_necessarias = [
        f"taxa_{sufixo_idade}_{sufixo_cor}"
        for sufixo_cor in cores.values()
        for _, sufixo_idade in faixas_etarias
    ]

    colunas_faltantes = [
        coluna for coluna in colunas_necessarias if coluna not in cidade
    ]
    if colunas_faltantes:
        raise ValueError(
            "Colunas necessárias ausentes para gerar o gráfico de educação: "
            + ", ".join(sorted(colunas_faltantes))
        )

    dados = {}

    for nome_cor, sufixo_cor in cores.items():
        dados[nome_cor] = []

        for _, sufixo_idade in faixas_etarias:
            coluna = f"taxa_{sufixo_idade}_{sufixo_cor}"

            valor = _coerce_para_float(cidade[coluna])

            dados[nome_cor].append(valor)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    chart_file = (
        OUTPUT_DIR
        / f"grafico_cor_faixa_etaria_{safe_city}.png"
    )

    x = np.arange(len(faixas_etarias))

    largura = 0.15

    fig, ax = iniciar_card_grafico(
        (12, 8.4),
        "Taxa de analfabetismo por cor/raça e faixa etária",
        tamanho_titulo=17,
    )
    # Mesmo ajuste de demografia.gerar_grafico_faixa_etaria_e_sexo: a legenda
    # fica abaixo do eixo (bbox_to_anchor negativo) e sairia cortada pra fora
    # do card, então encolhemos o `ax` pra sobrar uma faixa pra ela dentro.
    # A faixa reservada cobre as duas linhas do rótulo do eixo X + a legenda.
    posicao = ax.get_position()
    altura_legenda = posicao.height * 0.3
    # Margem extra no topo: sem ela a grade de 120% fica colada na barra
    # cinza do cabeçalho do card.
    margem_superior = posicao.height * 0.06
    ax.set_position(
        (
            posicao.x0,
            posicao.y0 + altura_legenda,
            posicao.width,
            posicao.height - altura_legenda - margem_superior,
        )
    )

    cores_grafico = {
        "Amarela": "#E88BC0",
        "Branca": "#F3B5D1",
        "Indígena": "#A92E5A",
        "Parda": "#F4A11A",
        "Preta": "#C6530D",
    }

    for i, (nome_cor, valores) in enumerate(dados.items()):
        deslocamento = (i - 2) * largura

        ax.bar(
            x + deslocamento,
            valores,
            width=largura,
            label=nome_cor,
            color=cores_grafico[nome_cor],
        )

    ax.set_xticks(x)
    ax.set_xticklabels(
        [nome for nome, _ in faixas_etarias],
        fontsize=15*ESCALA_FONTE,
        ha="center",
    )

    valor_maximo = max(
        max(valores) for valores in dados.values()
    )

    # Poucos ticks (no máx. ~6), como no Figma: passo de 10 deixava até 12-13
    # rótulos de "0%" a "120%" espremidos um em cima do outro. Sobe o passo
    # (10 -> 20 -> 25 -> 50 -> 100) até caber nesse teto.
    for passo in (10, 20, 25, 50, 100):
        limite_superior = max(passo, int(np.ceil(valor_maximo * 1.1 / passo)) * passo)
        if limite_superior / passo <= 6:
            break
    ticks_y = list(range(0, limite_superior + 1, passo))

    ax.set_ylim(0, limite_superior)
    ax.set_yticks(ticks_y)
    ax.set_yticklabels(
        [f"{tick}%" for tick in ticks_y],
        fontsize=15*ESCALA_FONTE,
    )

    ax.grid(
        axis="y",
        linestyle="--",
        linewidth=0.5,
        alpha=0.25,
    )

    ax.set_axisbelow(True)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)

    ax.tick_params(axis="x", length=0)
    # Pad explícito (não o default do matplotlib, que fica imperceptível com
    # a fonte grande deste gráfico): afasta "0%", "10%" etc. do eixo/barras.
    ax.tick_params(axis="y", length=0, pad=12)

    # `bbox_transform=fig.transFigure` em vez do default (`ax.transAxes`):
    # a legenda centraliza na largura do card inteiro, não só do `ax` (que é
    # mais estreito, com margem dos dois lados) — senão, com 5 itens numa
    # única linha, "Preta" (último item) estoura a borda direita do card.
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, 0.152),
        bbox_transform=fig.transFigure,
        ncol=5,
        frameon=False,
        fontsize=15*ESCALA_FONTE,
        markerscale=1.3,
        columnspacing=2.2,
        handletextpad=0.6,
    )

    salvar_card_grafico(fig, chart_file)

    return chart_file.name