"""Gráficos do relatório por estado: as mesmas funções de `plotting/`, alimentadas
pela linha da matview estadual (`uf_*`) em vez da linha do município.

Pedido de 12/11/2026: o Doc estadual já traz os marcadores `*grafico_...` com os
mesmos nomes do municipal. Em vez de copiar as funções de desenho, cada gráfico tem
um adaptador que monta, a partir das colunas `uf_*`, o dicionário que a função
municipal já sabe ler. Assim o gráfico do estado tem a mesma cara do municipal.

Diferenças de dado, decididas em 12/11/2026:
  - pirâmide etária: as 12 faixas da matview (de 5 em 5 anos até 29, de 10 em 10
    depois), não as 9 do municipal. É com elas que a matview calcula a "maior
    concentração" citada no texto (D9 do registro de problemas);
  - dinâmica populacional: só 2010 e 2022, porque a matview não tem 2000.
"""

import logging
import pathlib
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass

from plotting.demografia import (
    gerar_grafico_composicao_cor_raca,
    gerar_grafico_faixa_etaria_e_sexo,
    gerar_grafico_visao_historica_populacao,
)

logger = logging.getLogger(__name__)

_PREFIXO_FAIXA = "uf_faixa_etaria_2022_"
_POSICOES_COR_RACA = ("pri", "seg", "ter", "quar", "quin")
_ANOS_CENSO_ESTADO = (2010, 2022)


def faixas_etarias_sexo_do_estado(linha: dict) -> list[dict[str, object]]:
    """As faixas da pirâmide, da mais nova à mais velha, no formato de
    `faixas_etarias_sexo` do municipal. O sufixo da coluna ("00_04", "80_mais")
    ordena as faixas; o rótulo vem da própria matview ("0 a 4 anos").

    Ex.: faixas_etarias_sexo_do_estado(linha)[0]["faixa"] == "0 a 4 anos"
    """
    sufixos = sorted(
        chave.removeprefix(_PREFIXO_FAIXA) for chave in linha if chave.startswith(_PREFIXO_FAIXA)
    )
    return [
        {
            "faixa": linha[f"{_PREFIXO_FAIXA}{sufixo}"],
            "mulheres": linha.get(f"uf_pop_faixa_mulher_2022_{sufixo}"),
            "homens": linha.get(f"uf_pop_faixa_homem_2022_{sufixo}"),
        }
        for sufixo in sufixos
    ]


def _sem_acento(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)

    return "".join(letra for letra in decomposto if not unicodedata.combining(letra))


def populacao_por_cor_raca_do_estado(linha: dict) -> dict[str, object]:
    """`pop_<cor>` e `pop_total_2022` como no municipal, a partir do ranking da
    matview (`uf_cor_raca_pri_class` + `uf_cor_pri_pop` … `uf_cor_quin_*`). A
    classe vem com acento ("indígena") e a chave municipal não tem ("pop_indigena").

    Ex.: populacao_por_cor_raca_do_estado(linha)["pop_parda"] == Decimal("2207880")
    """
    populacao: dict[str, object] = {"pop_total_2022": linha.get("uf_pop_total_2022")}
    for posicao in _POSICOES_COR_RACA:
        # A 1ª posição tem nome próprio na matview: uf_cor_raca_pri_class.
        coluna_classe = "uf_cor_raca_pri_class" if posicao == "pri" else f"uf_cor_{posicao}_class"
        classe = linha.get(coluna_classe)
        if not classe:
            continue
        populacao[f"pop_{_sem_acento(str(classe)).lower()}"] = linha.get(f"uf_cor_{posicao}_pop")

    return populacao


def populacao_historica_do_estado(linha: dict) -> dict[str, object]:
    """`pop_total_<ano>` como no municipal, para os anos que a matview tem.

    Ex.: populacao_historica_do_estado(linha) == {"pop_total_2010": …, "pop_total_2022": …}
    """
    return {f"pop_total_{ano}": linha.get(f"uf_pop_total_{ano}") for ano in _ANOS_CENSO_ESTADO}


def _grafico_faixa_etaria(linha: dict, output_dir: pathlib.Path, safe_estado: str) -> str:
    cidade = {"faixas_etarias_sexo": faixas_etarias_sexo_do_estado(linha)}

    return gerar_grafico_faixa_etaria_e_sexo(cidade, output_dir, safe_estado)


def _grafico_cor_raca(linha: dict, output_dir: pathlib.Path, safe_estado: str) -> str:
    return gerar_grafico_composicao_cor_raca(populacao_por_cor_raca_do_estado(linha), output_dir, safe_estado)


def _grafico_visao_historica(linha: dict, output_dir: pathlib.Path, safe_estado: str) -> str:
    return gerar_grafico_visao_historica_populacao(
        populacao_historica_do_estado(linha), output_dir, safe_estado, anos_censo=_ANOS_CENSO_ESTADO
    )


@dataclass(frozen=True)
class GraficoDoEstado:
    """Um gráfico estadual: o marcador `*<placeholder>` do Doc e a função que o gera."""

    placeholder: str
    gerar: Callable[[dict, pathlib.Path, str], str]


# Mesmos placeholders de GRAFICOS_POR_TEMA (services/generation.py): o Doc estadual
# usa os nomes do municipal. Tema fora daqui sai sem gráficos, como antes.
GRAFICOS_ESTADO_POR_TEMA: dict[str, tuple[GraficoDoEstado, ...]] = {
    "demografia": (
        GraficoDoEstado("grafico_faixa_etaria_e_sexo", _grafico_faixa_etaria),
        GraficoDoEstado("grafico_composicao_cor_raca", _grafico_cor_raca),
        GraficoDoEstado("grafico_visao_historica", _grafico_visao_historica),
    ),
}


def gerar_graficos_do_estado(
    slug: str, linha: dict, output_dir: pathlib.Path, safe_estado: str
) -> dict[str, str]:
    """{placeholder: arquivo PNG} dos gráficos do tema para o estado. Gráfico sem
    dado (a função levanta ValueError) fica de fora, com aviso no log, e some do
    relatório junto com a menção "(Figura X)", como no municipal.

    Ex.: gerar_graficos_do_estado("demografia", linha, OUTPUT_DIR, "estado_para_ba")
    """
    graficos: dict[str, str] = {}
    for grafico in GRAFICOS_ESTADO_POR_TEMA.get(slug, ()):
        try:
            graficos[grafico.placeholder] = grafico.gerar(linha, output_dir, safe_estado)
        except ValueError as err:
            logger.warning(
                "Não foi possível gerar o gráfico estadual '%s' para '%s': %s",
                grafico.placeholder, safe_estado, err,
            )

    return graficos
