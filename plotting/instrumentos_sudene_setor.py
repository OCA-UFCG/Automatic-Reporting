"""Gráfico de setor econômico do macrotema Instrumentos da Sudene (FNE, 2025).

Um card de barras agrupadas, que o Doc insere com o marcador `*grafico_setor`
acima da legenda "Quantidade de contratações e valor investido por tipo de setor
econômico". Em cada setor há duas barras: laranja para o número de contratações e
verde para o valor contratado.

A view `relatorios_auto.instrsudene_munic` entrega os números absolutos
(`<setor>_contrato` e `valor_<setor>_contrato`), com o valor em reais sem escala.
Recife/PE em 2025: comércio e serviços com 4.045 contratações e R$ 359.580.433,74.
"""

import pathlib

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
# do grupo de barras.
SETORES_ECONOMICOS = (
    ("agro", "Agroindústria"),
    ("comercio", "Comércio e\nServiços"),
    ("industria", "Indústria"),
    ("pecuaria", "Pecuária"),
    ("pessoaf", "Pessoa\nFísica"),
    ("turismo", "Turismo"),
)
# Cores medidas do design. São as mesmas das pizzas de porte
# (`plotting/instrumentos_sudene_porte.py`): laranja = contratações, verde = valor.
_COR_QUANTIDADE = "#DD7402"
_COR_VALOR = "#018F39"
_COR_TEXTO = "#514C50"
_LARGURA_BARRA = 0.32
# Distância do centro do grupo até o centro de cada barra. WARNING: com 0,21 os
# rótulos do pior caso ("999" e "R$ 999,99M") se sobrepunham e os de Recife/PE
# ("4k" e "R$ 359,58M") encostavam. O teste de folga mede isso.
_DESLOCAMENTO_BARRA = 0.24
# IMPORTANT: cada série é escalada pelo próprio máximo, como no design ("4k" e
# "R$ 359,58M" com a mesma altura). Por isso o card não tem eixo Y: as alturas
# laranja e verde não são comparáveis entre si, só dentro da mesma cor.
_FRACAO_ALTURA_MINIMA = 0.012
_FOLGA_TOPO = 1.22
# (divisor, sufixo, casas decimais), da menor faixa para a maior.
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
        raise ValueError(f"Todos os setores do FNE estão zerados em {chaves}; esperado ao menos um > 0.")

    return totais


def formatar_quantidade(valor: float) -> str:
    """Rótulo da barra laranja: 129 -> "129", 4045 -> "4k", 1530 -> "1,5k"."""
    divisor, sufixo, decimais = _faixa_do_rotulo(valor, _FAIXAS_QUANTIDADE)

    return f"{_sem_zero_decimal(formatar_numero_ptbr(valor / divisor, decimais=decimais))}{sufixo}"


def formatar_valor_reais(valor: float) -> str:
    """Rótulo da barra verde: 154528.6 -> "R$ 154,53k", 359580433.74 -> "R$ 359,58M"."""
    divisor, sufixo, decimais = _faixa_do_rotulo(valor, _FAIXAS_REAIS)

    return f"R$ {formatar_numero_ptbr(valor / divisor, decimais=decimais)}{sufixo}"


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
    return texto.removesuffix(",0")


def alturas_normalizadas(totais: list[float]) -> list[float]:
    """Altura de cada barra como fração do maior total da série.

    Valor > 0 nunca fica abaixo de `_FRACAO_ALTURA_MINIMA`: no design a
    Agroindústria de Recife (3 contratações contra 4.045) ainda aparece como um
    traço. Zero continua zero.
    """
    maior = max(totais)

    return [max(total / maior, _FRACAO_ALTURA_MINIMA) if total > 0 else 0.0 for total in totais]


def _desenhar_serie(ax, posicoes: list[float], totais: list[float], cor: str, formatar) -> None:
    alturas = alturas_normalizadas(totais)
    ax.bar(posicoes, alturas, width=_LARGURA_BARRA, color=cor, zorder=3)
    for posicao, altura, total in zip(posicoes, alturas, totais):
        ax.annotate(
            formatar(total), (posicao, altura), xytext=(0, 4), textcoords="offset points",
            ha="center", va="bottom", fontsize=FONTE_ROTULO_VALOR * 0.85 * ESCALA_FONTE,
            color=_COR_TEXTO, zorder=4,
        )


def _estilizar_eixos(ax) -> None:
    ax.set_xticks(range(len(SETORES_ECONOMICOS)))
    ax.set_xticklabels([rotulo for _, rotulo in SETORES_ECONOMICOS])
    ax.set_xlim(-0.6, len(SETORES_ECONOMICOS) - 0.4)
    ax.set_ylim(0, _FOLGA_TOPO)
    ax.set_yticks([])
    ax.tick_params(axis="x", length=0, pad=8, colors=_COR_TEXTO, labelsize=FONTE_TICK * ESCALA_FONTE)
    for lado in ("left", "right", "top"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(_COR_TEXTO)


def desenhar_barras_por_setor(quantidades: list[float], valores: list[float]):
    """Monta o card (sem salvar) e devolve a figura, para o teste medir os rótulos."""
    fig, ax = iniciar_card_grafico(
        (8, 3.8), "Quantidade de contratações e valor total investido por tipo de setor",
        margem_esquerda=0.04,
    )
    _reservar_espaco_rotulo_x(fig, ax, reserva_polegadas=0.45)
    centros = range(len(SETORES_ECONOMICOS))
    _desenhar_serie(ax, [c - _DESLOCAMENTO_BARRA for c in centros], quantidades, _COR_QUANTIDADE, formatar_quantidade)
    _desenhar_serie(ax, [c + _DESLOCAMENTO_BARRA for c in centros], valores, _COR_VALOR, formatar_valor_reais)
    _estilizar_eixos(ax)

    return fig


def gerar_grafico_setor(
    cidade: dict,
    OUTPUT_DIR: pathlib.Path,
    safe_city: str,
) -> str:
    quantidades = totais_por_setor(cidade, "{setor}_contrato")
    valores = totais_por_setor(cidade, "valor_{setor}_contrato")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_file = OUTPUT_DIR / f"grafico_setor_{safe_city}.png"
    reuso = reusar_grafico(chart_file)
    if reuso is not None:
        return reuso

    salvar_card_grafico(desenhar_barras_por_setor(quantidades, valores), chart_file)

    return chart_file.name
