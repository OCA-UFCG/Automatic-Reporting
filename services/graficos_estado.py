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

Educação (12/11/2026) não tem diferença de dado: as 6 faixas de analfabetismo e os
4 níveis de instrução são os do municipal, nos 9 estados; só muda o nome da coluna.
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
from plotting.educacao import (
    gerar_grafico_cor_faixa_etaria,
    gerar_grafico_nivel_instrucao,
)

logger = logging.getLogger(__name__)

_PREFIXO_FAIXA = "uf_faixa_etaria_2022_"
_POSICOES_COR_RACA = ("pri", "seg", "ter", "quar", "quin")
_ANOS_CENSO_ESTADO = (2010, 2022)
_NIVEIS_INSTRUCAO = ("pri_nivel", "seg_nivel", "ter_nivel", "quar_nivel")
# Rótulo da faixa na matview -> sufixo da coluna municipal `taxa_<faixa>_<cor>`.
_SUFIXO_POR_FAIXA_DE_ANALFABETISMO = {
    "15 a 19 anos": "15_a_19",
    "20 a 29 anos": "20_a_29",
    "30 a 39 anos": "30_a_39",
    "40 a 49 anos": "40_a_49",
    "50 a 59 anos": "50_a_59",
    "60 anos ou mais": "mais60",
}
_CORES_DO_ANALFABETISMO = ("branca", "preta", "amarela", "parda", "indigena")
# A matview reserva 8 posições de faixa (fx1…fx8); hoje fx7 e fx8 vêm vazias.
_POSICOES_DE_FAIXA_DE_ANALFABETISMO = range(1, 9)


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


def niveis_de_instrucao_do_estado(linha: dict) -> dict[str, object]:
    """`<posição>_nivel_classe/per/pop` como no municipal: a matview só põe `uf_` na
    frente. Coluna que falta fica de fora, e a função municipal recusa o gráfico
    com a lista das ausentes.

    Ex.: niveis_de_instrucao_do_estado(linha)["pri_nivel_per"] == Decimal("47.49")
    """
    colunas = (f"{nivel}_{campo}" for nivel in _NIVEIS_INSTRUCAO for campo in ("classe", "per", "pop"))

    return {coluna: linha[f"uf_{coluna}"] for coluna in colunas if f"uf_{coluna}" in linha}


def taxas_de_analfabetismo_do_estado(linha: dict) -> dict[str, object]:
    """`taxa_<faixa>_<cor>` como no municipal. A matview numera as faixas (fx1…fx8)
    e dá o rótulo em `uf_analf_faixa_etaria_2022_fxN`; o casamento é pelo rótulo, e
    não pela posição, para uma faixa a mais ou fora de ordem não trocar as barras.
    Posição vazia ou rótulo desconhecido fica de fora; se faltar uma das 6 faixas,
    a função municipal recusa o gráfico.

    Ex.: taxas_de_analfabetismo_do_estado(linha)["taxa_mais60_preta"] == Decimal("50.21")
    """
    taxas: dict[str, object] = {}
    for posicao in _POSICOES_DE_FAIXA_DE_ANALFABETISMO:
        rotulo = linha.get(f"uf_analf_faixa_etaria_2022_fx{posicao}")
        sufixo = _SUFIXO_POR_FAIXA_DE_ANALFABETISMO.get(rotulo)
        if sufixo is None:
            continue
        for cor in _CORES_DO_ANALFABETISMO:
            taxas[f"taxa_{sufixo}_{cor}"] = linha.get(f"uf_analf_taxa_2022_{cor}_fx{posicao}")

    return taxas


def _grafico_faixa_etaria(linha: dict, output_dir: pathlib.Path, safe_estado: str) -> str:
    cidade = {"faixas_etarias_sexo": faixas_etarias_sexo_do_estado(linha)}

    return gerar_grafico_faixa_etaria_e_sexo(cidade, output_dir, safe_estado)


def _grafico_cor_raca(linha: dict, output_dir: pathlib.Path, safe_estado: str) -> str:
    return gerar_grafico_composicao_cor_raca(populacao_por_cor_raca_do_estado(linha), output_dir, safe_estado)


def _grafico_visao_historica(linha: dict, output_dir: pathlib.Path, safe_estado: str) -> str:
    return gerar_grafico_visao_historica_populacao(
        populacao_historica_do_estado(linha), output_dir, safe_estado, anos_censo=_ANOS_CENSO_ESTADO
    )


def _grafico_nivel_instrucao(linha: dict, output_dir: pathlib.Path, safe_estado: str) -> str:
    return gerar_grafico_nivel_instrucao(niveis_de_instrucao_do_estado(linha), output_dir, safe_estado)


def _grafico_analfabetismo(linha: dict, output_dir: pathlib.Path, safe_estado: str) -> str:
    return gerar_grafico_cor_faixa_etaria(taxas_de_analfabetismo_do_estado(linha), output_dir, safe_estado)


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
    "educacao": (
        GraficoDoEstado("grafico_cor_faixa_etaria", _grafico_analfabetismo),
        GraficoDoEstado("grafico_nivel_instrucao", _grafico_nivel_instrucao),
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
