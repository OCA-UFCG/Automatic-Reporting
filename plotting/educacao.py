import pathlib

import matplotlib.pyplot as plt
import numpy as np


def gerar_grafico_cor_faixa_etaria(
    cidade,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
):
    faixas_etarias = [
        ("15 a 19 anos", "15_a_19"),
        ("20 a 29 anos", "20_a_29"),
        ("30 a 39 anos", "30_a_39"),
        ("40 a 49 anos", "40_a_49"),
        ("50 a 59 anos", "50_a_59"),
        ("60 anos ou mais", "mais60"),
    ]

    cores = {
        "Amarela": "amarela",
        "Branca": "branca",
        "Indígena": "indigena",
        "Parda": "parda",
        "Preta": "preta",
    }

    dados = {}

    for nome_cor, sufixo_cor in cores.items():
        dados[nome_cor] = []

        for _, sufixo_idade in faixas_etarias:
            coluna = f"taxa_{sufixo_idade}_{sufixo_cor}"

            valor = cidade[coluna]

            if isinstance(valor, str):
                valor = valor.replace(",", ".")

            valor = float(valor)

            dados[nome_cor].append(valor)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    chart_file = (
        OUTPUT_DIR
        / f"grafico_cor_faixa_etaria_{safe_city}.png"
    )

    x = np.arange(len(faixas_etarias))

    largura = 0.15

    _fig, ax = plt.subplots(figsize=(8, 3.2))

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
        fontsize=8,
    )

    ax.set_ylim(0, 35)
    ax.set_yticks([0, 10, 20, 30])
    ax.set_yticklabels(
        ["0%", "10%", "20%", "30%"],
        fontsize=8,
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

    ax.tick_params(axis="both", length=0)

    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=5,
        frameon=False,
        fontsize=8,
    )

    plt.tight_layout()

    plt.savefig(
        chart_file,
        dpi=150,
        bbox_inches="tight",
    )

    plt.close()

    return chart_file.name