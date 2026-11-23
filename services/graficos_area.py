"""Gráficos do relatório por área de interesse.

Pedido de 23/11/2026: a área gera os gráficos na hora, do banco, como o município e o
estado. As colunas das `areaint_*` são as das `est_*` com `area_` no lugar de `uf_`, e
os Docs de área usam os mesmos marcadores do estado. Por isso a área troca o prefixo
e usa os adaptadores do estado (services/graficos_estado.py), com dois complementos
próprios:
  - Saúde: público-alvo por faixa e estabelecimentos somados pelas colunas de
    pertencimento das tabelas do painel (buscar_saude_do_painel_da_area);
  - Saneamento: a rosca sai das quantidades da própria areaint_infraestrutura, que
    tem as 7 categorias (somam o total), sem consultar o painel.

Desenvolvimento Social não tem matview de área: o único gráfico é o do Nordeste, de
valores fixos, como o texto do Doc.

O beta mostra PNGs congelados de 16/11 (services/relatorio_congelado.py), feitos com
esta mesma troca de prefixo; lá o ponto de 2000 saiu do gráfico da rede porque o texto
estático não cita 2000. Aqui ele fica: o Doc de área da editoria cita 2000.
"""

import logging
import pathlib
from collections.abc import Callable

from plotting.desenvolvimento_social import gerar_grafico_idhm_e_componentes
from services.graficos_estado import ComplementoDoPainel, gerar_graficos_do_estado
from utils.queries.saude import buscar_saude_do_painel_da_area

logger = logging.getLogger(__name__)

# INTENTIONAL: valores fixos, como o texto do Doc de área de desenvolvimento social
# (Rayane, 16/11/2026: o texto não tem placeholder, e o gráfico tem que dizer o mesmo
# que ele). Vêm da planilha "Fig 1.xlsx" da equipe e conferem com as medianas de
# des_idhm.idhm (nordeste = 'Sim', 1.794 municípios por ano) no gamma em 16/11/2026.
# Se o IDHM for atualizado, mudam aqui e no Doc juntos.
_ANOS_DO_IDHM = ("1991", "2000", "2010")
_MEDIANAS_DO_IDHM_NO_NORDESTE = {
    "IDHM": (0.291, 0.420, 0.588),
    "Longevidade": (0.556, 0.648, 0.7575),
    "Renda": (0.417, 0.477, 0.559),
    "Educação": (0.108, 0.238, 0.4825),
}

GeradorDeGraficoDaArea = Callable[[pathlib.Path, str], str]


def _grafico_idhm_do_nordeste(output_dir: pathlib.Path, safe_area: str) -> str:
    return gerar_grafico_idhm_e_componentes(
        _ANOS_DO_IDHM, _MEDIANAS_DO_IDHM_NO_NORDESTE, output_dir, safe_area
    )


# Gráficos de valores fixos. {(tema, área): {marcador do Doc: gerador}}. O marcador é
# o `*grafico_…` do Doc, sem o asterisco.
GRAFICOS_DA_AREA: dict[tuple[str, str], dict[str, GeradorDeGraficoDaArea]] = {
    ("desenvolvimento-social", "Nordeste"): {"grafico_idhm_componentes": _grafico_idhm_do_nordeste},
}

# Temas sem matview de área: não passam pelos adaptadores do estado.
_TEMAS_SO_DE_VALORES_FIXOS = ("desenvolvimento-social",)

# (categoria da rosca do municipal, coluna da areaint_infraestrutura já com `uf_`).
_CATEGORIAS_DA_ROSCA = (
    ("esg_rede_geral_ou_pluvial", "uf_esgoto_rede_geral_pluvial_2022qtd"),
    ("esg_fossa_septica_ou_fossa_filtro", "uf_esgoto_fossa_septica_2022qtd"),
    ("esg_fossa_rudimentar_ou_buraco", "uf_esgoto_fossa_rudimentar_2022qtd"),
    ("esg_vala", "uf_esgoto_vala_2022qtd"),
    ("esg_rio_lago_corrego_ou_mar", "uf_esgoto_corpo_hidrico_2022qtd"),
    ("esg_outra_forma", "uf_esgoto_outra_forma_2022qtd"),
    ("esg_nao_tinham_banheiro", "uf_sem_banheiro_2022qtd"),
)


def com_prefixo_do_estado(linha: dict) -> dict:
    """A linha da matview de área com `area_` trocado por `uf_`, que é o que os
    adaptadores do estado leem.

    Ex.: com_prefixo_do_estado({"area_pib_2023": 1, "area_nome": "Caatinga"})
         == {"uf_pib_2023": 1, "uf_nome": "Caatinga"}
    """
    return {("uf_" + k.removeprefix("area_") if k.startswith("area_") else k): v for k, v in linha.items()}


def rosca_de_esgoto_da_area(linha: dict) -> dict[str, object]:
    """`esg_total` e as 7 categorias do municipal, das colunas de quantidade da
    matview. A flag `uf_distrib_esgoto_2022_completa` da própria matview decide se a
    rosca sai (services/graficos_estado_saneamento.py).

    Ex.: rosca_de_esgoto_da_area(linha)["esg_fossa_septica_ou_fossa_filtro"] == linha["uf_esgoto_fossa_septica_2022qtd"]
    """
    return {"esg_total": linha.get("uf_domicilios_total_2022"),
            **{chave: linha.get(coluna) for chave, coluna in _CATEGORIAS_DA_ROSCA}}


def _saude_do_painel(linha: dict) -> dict[str, object]:
    return buscar_saude_do_painel_da_area(str(linha.get("uf_nome") or ""))


COMPLEMENTOS_DA_AREA: dict[str, ComplementoDoPainel] = {
    "saude": _saude_do_painel,
    "saneamento": rosca_de_esgoto_da_area,
}


def gerar_graficos_da_area(
    slug: str,
    area: str,
    linha: dict,
    output_dir: pathlib.Path,
    safe_area: str,
    complementos: dict[str, ComplementoDoPainel] = COMPLEMENTOS_DA_AREA,
) -> dict[str, str]:
    """{marcador: arquivo PNG} dos gráficos do tema na área. Gráfico que falha
    (ValueError) fica de fora com aviso, e some do relatório junto com a menção
    "(Figura X)", como no estado. `complementos` é a costura dos testes para as
    consultas ao painel.

    Ex.: gerar_graficos_da_area("desenvolvimento-social", "Nordeste", {}, OUTPUT_DIR, "area_nordeste")
         == {"grafico_idhm_componentes": "grafico_idhm_componentes_area_nordeste.png"}
    """
    graficos: dict[str, str] = {}
    for marcador, gerar in GRAFICOS_DA_AREA.get((slug, area), {}).items():
        try:
            graficos[marcador] = gerar(output_dir, safe_area)
        except ValueError as err:
            logger.warning("Não foi possível gerar o gráfico de área '%s' para '%s': %s", marcador, area, err)
    if slug not in _TEMAS_SO_DE_VALORES_FIXOS:
        graficos.update(
            gerar_graficos_do_estado(slug, com_prefixo_do_estado(linha), output_dir, safe_area, complementos)
        )

    return graficos
