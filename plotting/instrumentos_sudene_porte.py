"""Gráficos de porte da empresa do macrotema Instrumentos da Sudene (FNE, 2025).

Dois cards de pizza que o Doc põe lado a lado com o marcador
`*grafico_porte_contratacoes+grafico_porte_valor`, acima da legenda "Percentual de
contratação e de valor investido por porte da empresa".

A view `relatorios_auto.instrsudene_munic` já entrega o percentual de cada porte
(`contrato_<porte>` e `valor_<porte>`, somando ~100). Recife/PE em 2025:
micro 72,54% das contratações, pequeno 41,29% do valor.
"""

import math
import pathlib

from plotting import (
    ESCALA_FONTE,
    FONTE_ROTULO_VALOR,
    iniciar_card_grafico,
    reusar_grafico,
    salvar_card_grafico,
)
from plotting.saneamento import _formatar_percentual, _posicoes_dos_rotulos

# (sufixo da coluna na view, rótulo). Ordem crescente de porte: a pizza anda do
# menor para o maior e a cor escurece junto, porque porte é uma escala ordenada.
PORTES_EMPRESA = (
    ("mini", "Mini"),
    ("micro", "Micro"),
    ("pequeno", "Pequeno"),
    ("peq_medio", "Pequeno-Médio"),
    ("media1", "Médio I"),
    ("media2", "Médio II"),
    ("grande", "Grande"),
)
_CORES_CONTRATACOES = ("#FCD9A0", "#F9B95C", "#F39A2E", "#E07B12", "#B8600C", "#8C470A", "#5E3008")
_CORES_VALOR = ("#BDEBCB", "#86D7A0", "#50BF76", "#27A155", "#12823F", "#0A6331", "#054522")
_COR_GUIA = "#9A9A9A"
_COR_TEXTO = "#4A4A4A"
# IMPORTANT: no relatório os dois cards dividem a largura da página
# (`*grafico_porte_contratacoes+grafico_porte_valor`), então o PNG sai com menos
# da metade do tamanho de um gráfico sozinho. Card estreito e rótulo em duas
# linhas ("Pequeno-Médio" / "33,13%") fazem a fonte chegar legível ao PDF; com
# 6,4" e rótulo numa linha só, pizza e texto ficavam minúsculos.
_TAMANHO_CARD = (4.6, 3.4)
# Meia-largura/altura do eixo, em raios da pizza: cabe a coluna de rótulos de
# `_posicoes_dos_rotulos` (x = ±1,30) mais a palavra "Pequeno-Médio".
_LIMITE_EIXO_X = 2.8
_LIMITE_EIXO_Y = 1.5
# Começa às 9 horas, e não no topo: os portes pequenos (Mini no começo, Médio e
# Grande no fim) costumam ter fatias finas, que assim ficam na lateral esquerda,
# na altura da coluna de rótulos. Começando no topo, os rótulos delas desciam em
# pilha pela lateral e as linhas-guia cruzavam outras fatias (Recife/PE).
_ANGULO_INICIAL = 180.0
# Distância vertical entre rótulos de duas linhas, em raios (o padrão de
# `_posicoes_dos_rotulos` cabe uma linha só).
_ESPACO_ROTULO_DUAS_LINHAS = 0.5


def percentuais_por_porte(cidade: dict, prefixo: str) -> list[float]:
    """Percentual de cada porte em `PORTES_EMPRESA`, lido de `<prefixo><porte>`.

    Ex.: percentuais_por_porte(recife, "contrato_")[1] -> 72.54 (micro).
    """
    chaves = [f"{prefixo}{porte}" for porte, _ in PORTES_EMPRESA]
    faltando = [chave for chave in chaves if cidade.get(chave) is None]
    if faltando:
        raise ValueError(f"Percentuais por porte ausentes: {faltando}; esperado número em cada coluna.")

    percentuais = [float(cidade[chave]) for chave in chaves]
    if sum(percentuais) <= 0:
        raise ValueError(f"Percentuais por porte zerados em '{prefixo}*': {percentuais}.")

    return percentuais


def _desenhar_rotulo(ax, angulo: float, x: float, y: float, texto: str) -> None:
    # Mesma linha-guia com cotovelo da rosca de esgotamento (plotting/saneamento.py):
    # sai radialmente da borda da fatia e segue na horizontal até o texto.
    rad = math.radians(angulo)
    borda = (math.cos(rad), math.sin(rad))
    cotovelo = (1.08 * borda[0], 1.08 * borda[1])
    lado = 1 if x > 0 else -1
    ax.plot(
        [borda[0], cotovelo[0], x - lado * 0.04], [borda[1], cotovelo[1], y],
        color=_COR_GUIA, linewidth=0.8, solid_capstyle="round",
    )
    ax.text(
        x, y, texto, ha="left" if lado == 1 else "right", va="center", linespacing=1.1,
        fontsize=FONTE_ROTULO_VALOR * ESCALA_FONTE, color=_COR_TEXTO,
    )


def _desenhar_pizza_por_porte(
    titulo: str, percentuais: list[float], cores: tuple[str, ...], chart_file: pathlib.Path
) -> None:
    fig, ax = iniciar_card_grafico(_TAMANHO_CARD, titulo, margem_esquerda=0.03)
    # Fatia de 0% fica de fora do desenho e dos rótulos (`_posicoes_dos_rotulos`
    # só devolve fatias > 0): não há o que mostrar, e um "0%" solto confunde.
    ax.pie(
        percentuais, colors=cores, startangle=_ANGULO_INICIAL, counterclock=False,
        wedgeprops={"edgecolor": "white", "linewidth": 1.2},
    )
    for indice, (angulo, x, y) in _posicoes_dos_rotulos(
        percentuais, _ESPACO_ROTULO_DUAS_LINHAS, _ANGULO_INICIAL
    ).items():
        texto = f"{PORTES_EMPRESA[indice][1]}\n{_formatar_percentual(percentuais[indice])}"
        _desenhar_rotulo(ax, angulo, x, y, texto)

    ax.set_xlim(-_LIMITE_EIXO_X, _LIMITE_EIXO_X)
    ax.set_ylim(-_LIMITE_EIXO_Y, _LIMITE_EIXO_Y)
    ax.set_aspect("equal")
    salvar_card_grafico(fig, chart_file)


def _gerar_grafico_porte(
    cidade: dict, output_dir: pathlib.Path, safe_city: str, tipo: str
) -> str:
    prefixo, titulo, cores = _TIPOS_GRAFICO_PORTE[tipo]
    percentuais = percentuais_por_porte(cidade, prefixo)
    output_dir.mkdir(parents=True, exist_ok=True)
    chart_file = output_dir / f"grafico_porte_{tipo}_{safe_city}.png"
    reuso = reusar_grafico(chart_file)
    if reuso is not None:
        return reuso

    _desenhar_pizza_por_porte(titulo, percentuais, cores, chart_file)
    return chart_file.name


# tipo -> (prefixo da coluna na view, título do card, cores por porte).
_TIPOS_GRAFICO_PORTE = {
    "contratacoes": ("contrato_", "Total de contratações", _CORES_CONTRATACOES),
    "valor": ("valor_", "Valor total investido", _CORES_VALOR),
}


def gerar_grafico_porte_contratacoes(cidade: dict, OUTPUT_DIR: pathlib.Path, safe_city: str) -> str:
    return _gerar_grafico_porte(cidade, OUTPUT_DIR, safe_city, "contratacoes")


def gerar_grafico_porte_valor(cidade: dict, OUTPUT_DIR: pathlib.Path, safe_city: str) -> str:
    return _gerar_grafico_porte(cidade, OUTPUT_DIR, safe_city, "valor")
