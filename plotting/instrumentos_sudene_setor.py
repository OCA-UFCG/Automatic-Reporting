"""Gráficos de setor econômico do macrotema Instrumentos da Sudene (FNE, 2025).

Dois cards de barras, um por figura do Doc:

- `*grafico_setor`, acima da legenda "Quantidade de contratações por tipo de
  setor econômico" (Figura v): barras laranja com o número de contratações.
- `*grafico_valor_total_tipo`, acima da legenda "Valor investido por tipo de
  setor econômico" (Figura w): barras verdes com o valor contratado.

LEGACY: até 12/11/2026 era um card só, com as duas séries agrupadas e sem eixo Y
(cada série escalada pelo próprio máximo). O design separou as séries e o Doc
ganhou o marcador `*grafico_valor_total_tipo`.

A view `relatorios_auto.instrsudene_munic` entrega os números absolutos
(`<setor>_contrato` e `valor_<setor>_contrato`), com o valor em reais sem escala.
Recife/PE em 2025: comércio e serviços com 4.045 contratações e R$ 359.580.433,74.
"""

import math
import pathlib
from collections.abc import Callable
from typing import NamedTuple

from matplotlib.ticker import FuncFormatter

from plotting import (
    ESCALA_FONTE,
    FONTE_ROTULO_VALOR,
    FONTE_TICK,
    iniciar_card_grafico,
    reusar_grafico,
    salvar_card_grafico,
)
from plotting.economia_renda import _reservar_espaco_rotulo_x
from utils.formatting import arredondar_meio_para_cima, formatar_numero_ptbr

# (sufixo da coluna na view, rótulo no eixo X). INTENTIONAL: ordem alfabética,
# como no design. A quebra de linha mantém os nomes longos dentro da largura
# do grupo de barras: com 8 setores cada grupo tem ~1 polegada, e
# "Agroindústria"/"Infraestrutura" inteiros invadiam o vizinho.
# IMPORTANT: os 8 setores de `instrsudene_fne.fne_indicadores` (a soma deles é
# `fne_qtd_total`). Até 13/11/2026 a view só expunha 6 — sem agricultura e
# infraestrutura, 2.003 municípios tinham barras somando menos que `contrato2025`.
# Setor novo na origem precisa entrar aqui e na view, senão as barras não fecham.
SETORES_ECONOMICOS = (
    ("agri", "Agri-\ncultura"),
    ("agro", "Agro-\nindústria"),
    ("comercio", "Comércio\ne Serviços"),
    ("industria", "Indústria"),
    ("infra", "Infra-\nestrutura"),
    ("pecuaria", "Pecuária"),
    ("pessoaf", "Pessoa\nFísica"),
    ("turismo", "Turismo"),
)
# IMPORTANT: iguais às legendas "Figura v" e "Figura w" do Doc, que saem logo
# abaixo de cada card; com textos diferentes os dois pareciam descrever gráficos
# distintos (revisão do PR). O design abrevia o do valor para "Valor total por
# tipo de setor". Se o Doc mudar a legenda, mude aqui também.
TITULO_CARD_QUANTIDADE = "Quantidade de contratações por tipo de setor econômico"
TITULO_CARD_VALOR = "Valor investido por tipo de setor econômico"
# Cores medidas do design. São as mesmas do gráfico de porte
# (`plotting/instrumentos_sudene_porte.py`): laranja = contratações, verde = valor.
_COR_QUANTIDADE = "#DD7402"
_COR_VALOR = "#018F39"
_COR_TEXTO = "#514C50"
_LARGURA_BARRA = 0.55
# Fração do topo do eixo abaixo da qual um valor > 0 não encolhe: no design a
# Agroindústria de Recife (R$ 154,53k contra R$ 359,58M) ainda aparece como um
# traço. Zero continua sem barra.
_FRACAO_ALTURA_MINIMA = 0.012
# Espaço acima da barra mais alta para o rótulo dela, em fração do maior valor.
_FOLGA_TOPO = 1.15
# Poucas marcas no eixo Y, como no design (três em Recife/PE): os rótulos acima
# das barras já dão o número exato.
_INTERVALOS_MAXIMOS = 3
# (divisor, sufixo, casas decimais), da menor faixa para a maior.
# INTENTIONAL: k/M/B como no design, não o mil/Mi/Bi dos outros cards do tema
# (`_UNIDADE_ABREVIADA` em `plotting/instrumentos_sudene.py`). Com mil/Mi os dois
# rótulos de um setor não cabem lado a lado: "4 mil" e "R$ 359,58 Mi" de Recife
# ficavam a 1 px, e o pior caso ("999,9 mil" + "R$ 999,99 Mi") soma 135 px num
# grupo de 115 px. Revisão do PR do gráfico de setor.
# Com as séries em cards separados (12/11/2026) o design manteve k/M/B.
_FAIXAS_QUANTIDADE = ((1, "", 0), (1e3, "k", 1), (1e6, "M", 1))
_FAIXAS_REAIS = ((1, "", 0), (1e3, "k", 2), (1e6, "M", 2), (1e9, "B", 2))


def totais_por_setor(cidade: dict, coluna: str) -> list[float]:
    """Total de cada setor de `SETORES_ECONOMICOS`, na coluna `coluna.format(setor=...)`.

    Ex.: totais_por_setor(recife, "{setor}_contrato")[1] -> 4045.0 (comércio).
    """
    chaves = [coluna.format(setor=setor) for setor, _ in SETORES_ECONOMICOS]
    faltando = [chave for chave in chaves if cidade.get(chave) is None]
    if faltando:
        raise ValueError(f"Colunas de setor do FNE ausentes: {faltando}; esperado um número em cada.")

    totais = [float(cidade[chave]) for chave in chaves]
    if not any(totais):
        raise ValueError(f"Colunas '{coluna}' zeradas em todos os setores: {totais}; esperado ao menos um > 0.")

    return totais


def formatar_quantidade(valor: float) -> str:
    """Rótulo da barra laranja: 129 -> "129", 4045 -> "4k", 1530 -> "1,5k"."""
    divisor, sufixo, decimais = _faixa_do_rotulo(valor, _FAIXAS_QUANTIDADE)

    return f"{_sem_zero_decimal(formatar_numero_ptbr(valor / divisor, decimais=decimais))}{sufixo}"


def formatar_valor_reais(valor: float) -> str:
    """Rótulo da barra verde: 154528.6 -> "R$ 154,53k", 359580433.74 -> "R$ 359,58M"."""
    divisor, sufixo, decimais = _faixa_do_rotulo(valor, _FAIXAS_REAIS)

    return f"R$ {_sem_zero_decimal(formatar_numero_ptbr(valor / divisor, decimais=decimais))}{sufixo}"


def _faixa_do_rotulo(valor: float, faixas: tuple) -> tuple[float, str, int]:
    """Primeira faixa em que `valor`, já arredondado, fica abaixo de 1000; senão a maior.

    WARNING: decidir pelo valor bruto põe o sufixo da faixa de baixo perto da
    fronteira: R$ 999.995 virava "R$ 1.000,00k" e 999.999 contratações "1.000k".
    Ex.: _faixa_do_rotulo(999995, _FAIXAS_REAIS) -> (1e6, "M", 2).
    """
    for divisor, sufixo, decimais in faixas[:-1]:
        if arredondar_meio_para_cima(valor / divisor, decimais) < 1000:
            return divisor, sufixo, decimais

    return faixas[-1]


def _sem_zero_decimal(texto: str) -> str:
    """Convenção dos cards: X,0 / X,00 sai inteiro ("4,0" -> "4", "302,00" -> "302"); "1,50" fica."""
    inteiro, virgula, decimais = texto.partition(",")
    if virgula and not decimais.strip("0"):
        return inteiro

    return texto


def marcas_do_eixo(maior: float) -> list[float]:
    """Marcas do eixo Y: zero e o menor passo 1-2-5 que chega a `maior` em até
    `_INTERVALOS_MAXIMOS` intervalos, como no design (R$ 0, R$ 200M, R$ 400M).
    Ex.: 359_580_433.74 -> [0, 2e8, 4e8]; 4045 -> [0, 2000, 4000, 6000]."""
    expoente = math.floor(math.log10(maior / _INTERVALOS_MAXIMOS))
    passo = next(
        base * 10**exp
        for exp in (expoente, expoente + 1)
        for base in (1, 2, 5)
        if math.ceil(maior / (base * 10**exp)) <= _INTERVALOS_MAXIMOS
    )

    return [float(passo * i) for i in range(math.ceil(maior / passo) + 1)]


def alturas_das_barras(totais: list[float], topo_do_eixo: float) -> list[float]:
    """Altura real de cada barra, com piso de `_FRACAO_ALTURA_MINIMA` do topo
    do eixo para valor > 0. Ex.: ([3, 0, 4045], 5000) -> [60.0, 0.0, 4045]."""
    piso = topo_do_eixo * _FRACAO_ALTURA_MINIMA

    return [max(total, piso) if total > 0 else 0.0 for total in totais]


class SerieSetor(NamedTuple):
    """O que muda de um card de setor para o outro."""

    coluna: str
    titulo: str
    cor: str
    formatar: Callable[[float], str]
    arquivo: str


# IMPORTANT: nomes de arquivo novos, não o `grafico_setor_<cidade>.png` do card
# antigo. `reusar_grafico` reaproveita o PNG pelo nome até o próximo refresh das
# matviews; com o nome antigo, a produção serviria o card de duas séries.
SERIES_SETOR = {
    "quantidade": SerieSetor(
        "{setor}_contrato", TITULO_CARD_QUANTIDADE, _COR_QUANTIDADE, formatar_quantidade, "grafico_setor_quantidade",
    ),
    "valor": SerieSetor(
        "valor_{setor}_contrato", TITULO_CARD_VALOR, _COR_VALOR, formatar_valor_reais, "grafico_setor_valor",
    ),
}


def _desenhar_barras(ax, totais: list[float], marcas: list[float], serie: SerieSetor) -> None:
    alturas = alturas_das_barras(totais, marcas[-1])
    posicoes = range(len(SETORES_ECONOMICOS))
    ax.bar(posicoes, alturas, width=_LARGURA_BARRA, color=serie.cor, zorder=3)
    for posicao, altura, total in zip(posicoes, alturas, totais):
        ax.annotate(
            serie.formatar(total), (posicao, altura), xytext=(0, 4), textcoords="offset points",
            ha="center", va="bottom", fontsize=FONTE_ROTULO_VALOR * 0.85 * ESCALA_FONTE,
            color=_COR_TEXTO, zorder=4,
        )


def _estilizar_eixos(ax, totais: list[float], marcas: list[float], serie: SerieSetor) -> None:
    ax.set_xticks(range(len(SETORES_ECONOMICOS)))
    ax.set_xticklabels([rotulo for _, rotulo in SETORES_ECONOMICOS])
    ax.set_xlim(-0.6, len(SETORES_ECONOMICOS) - 0.4)
    ax.set_ylim(0, max(marcas[-1], max(totais) * _FOLGA_TOPO))
    ax.set_yticks(marcas)
    # `float`: o matplotlib passa np.float64, que `formatar_numero_ptbr` não converte.
    ax.yaxis.set_major_formatter(FuncFormatter(lambda valor, _: serie.formatar(float(valor))))
    ax.tick_params(axis="both", length=0, colors=_COR_TEXTO, labelsize=FONTE_TICK * ESCALA_FONTE)
    ax.tick_params(axis="x", pad=8)
    for lado in ("left", "right", "top"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(_COR_TEXTO)


def desenhar_barras_por_setor(totais: list[float], serie: SerieSetor):
    """Monta o card (sem salvar) e devolve a figura, para o teste medir os rótulos."""
    fig, ax = iniciar_card_grafico((8, 3.8), serie.titulo, margem_esquerda=0.12)
    _reservar_espaco_rotulo_x(fig, ax, reserva_polegadas=0.45)
    marcas = marcas_do_eixo(max(totais))
    _desenhar_barras(ax, totais, marcas, serie)
    _estilizar_eixos(ax, totais, marcas, serie)

    return fig


def _gerar_grafico_por_setor(cidade: dict, output_dir: pathlib.Path, safe_city: str, tipo: str) -> str:
    serie = SERIES_SETOR[tipo]
    totais = totais_por_setor(cidade, serie.coluna)
    output_dir.mkdir(parents=True, exist_ok=True)
    chart_file = output_dir / f"{serie.arquivo}_{safe_city}.png"
    reuso = reusar_grafico(chart_file)
    if reuso is not None:
        return reuso

    salvar_card_grafico(desenhar_barras_por_setor(totais, serie), chart_file)

    return chart_file.name


def gerar_grafico_setor(cidade: dict, OUTPUT_DIR: pathlib.Path, safe_city: str) -> str:
    """Card da Figura v (`*grafico_setor`): contratações por setor."""
    return _gerar_grafico_por_setor(cidade, OUTPUT_DIR, safe_city, "quantidade")


def gerar_grafico_valor_total_tipo(cidade: dict, OUTPUT_DIR: pathlib.Path, safe_city: str) -> str:
    """Card da Figura w (`*grafico_valor_total_tipo`): valor investido por setor."""
    return _gerar_grafico_por_setor(cidade, OUTPUT_DIR, safe_city, "valor")
