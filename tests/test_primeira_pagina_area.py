"""Primeira página do relatório por área (23/11/2026): o Doc de
CARACTERISTICAS_AREA_DOCS_URL, escrito com os títulos "Apresentação" e "Características
Gerais", convertido para o formato marcado do estado e resolvido contra a linha da área.
Nenhum teste toca o banco, o Google ou o node do SSR."""

import asyncio

import pytest

from services import primeira_pagina_area, primeira_pagina_estado, relatorio_estado
from tests.test_relatorio_area import ambiente_de_area  # noqa: F401 (fixture)
from utils.queries import area as consulta_area

# O formato do Doc 1R7WVJJ… em 23/11/2026, encurtado.
DOC_PRIMEIRA_PAGINA_AREA = (
    "\ufeffApresentação \n"
    "Este relatório apresenta um panorama geral.$area_de, reunindo indicadores.\n"
    "Área territorial\n"
    "geral.$area_territorial_km2:2 km²\n"
    "\tPopulação residente\n"
    "demografia.$area_pop_total_2022\n"
    "\t\n"
    "\n"
    "Características Gerais\n"
    "Para quando geral.$area_cd for igual a 1, então:\n"
    "No bioma Caatinga (Figura 1), a leitura territorial aproxima a conservação.\n"
    "\n"
    "\n"
    "Para quando geral.$area_cd for igual a 4, então:\n"
    "A região Nordeste do Brasil é composta por nove estados (Figura 1).\n"
    # Duas frases, como no Doc: uma frase só seria colada no parágrafo de cima
    # (quebra "Shift+Enter", render_descricao_tema_html).
    "Nesse contexto, a análise regional permite compreender os desafios. Os indicadores orientam o planejamento.\n"
    "\n"
    "\n"
    "*Inserir figura\n"
    "Figura 1 – Localização geral.$area_de.\n"
)

LINHA_CAATINGA = {
    "area_cd": 1,
    "area_nome": "Caatinga",
    "area_de": "da Caatinga",
    "area_territorial_km2": 857823.6,
    "area_pop_total_2022": 25949989,
}
LINHA_NORDESTE = {**LINHA_CAATINGA, "area_cd": 4, "area_nome": "Nordeste", "area_de": "do Nordeste"}


def _montar(linha: dict) -> dict[str, object]:
    texto = primeira_pagina_area.marcar_blocos_da_primeira_pagina(DOC_PRIMEIRA_PAGINA_AREA)
    return primeira_pagina_estado.montar_primeira_pagina(texto, linha, "r", isolar_condicoes=False)


class CaracteristicasAreaFake:
    """A linha da área no banco: só a Caatinga."""

    def __init__(self) -> None:
        self.pedidos: list[str] = []

    def buscar(self, area: str) -> dict | None:
        self.pedidos.append(area)
        return dict(LINHA_CAATINGA) if area == "Caatinga" else None


class DocPrimeiraPaginaAreaFake:
    """O Google Docs: devolve o Doc da primeira página de área e anota as URLs pedidas."""

    def __init__(self) -> None:
        self.urls: list[str] = []

    async def carregar(self, url: str) -> str:
        self.urls.append(url)
        return DOC_PRIMEIRA_PAGINA_AREA


@pytest.fixture
def primeira_pagina_de_area_configurada(monkeypatch):
    tabela, doc = CaracteristicasAreaFake(), DocPrimeiraPaginaAreaFake()
    monkeypatch.setattr(primeira_pagina_area, "CARACTERISTICAS_AREA_DOCS_URL", "doc-primeira-pagina-area")
    monkeypatch.setattr(primeira_pagina_area, "buscar_caracteristicas_area", tabela.buscar)
    monkeypatch.setattr(primeira_pagina_area, "carregar_texto_do_docs", doc.carregar)
    return tabela, doc


def test_doc_com_titulos_vira_o_formato_marcado():
    texto = primeira_pagina_area.marcar_blocos_da_primeira_pagina(DOC_PRIMEIRA_PAGINA_AREA)

    assert texto.startswith("Panorama de indicadores\nÁrea territorial\ngeral.$area_territorial_km2:2 km²\n")
    assert "apresentacao = “Este relatório apresenta um panorama geral.$area_de, reunindo indicadores.” @@" in texto
    assert "resumo_cidade = “\nPara quando geral.$area_cd for igual a 1, então:" in texto
    assert "*Inserir figura" not in texto
    assert texto.endswith("” @@\n\nFigura X – Localização geral.$area_de.")


def test_doc_ja_marcado_passa_intacto():
    marcado = "apresentacao = “Texto.” @@\nApresentação\nCaracterísticas Gerais\n"

    assert primeira_pagina_area.marcar_blocos_da_primeira_pagina(marcado) == marcado


def test_doc_sem_os_titulos_passa_intacto():
    assert primeira_pagina_area.marcar_blocos_da_primeira_pagina("Texto solto.") == "Texto solto."


def test_cards_de_area_e_populacao_com_icone():
    capa = _montar(LINHA_CAATINGA)

    assert [(m["rotulo"], m["valor"], m["sufixo"], m["icone"]) for m in capa["metricas"]] == [
        ("Área territorial", "857.823,60", "km²", "area"),
        ("População residente", "25.949.989", "", "populacao"),
    ]


def test_apresentacao_resolve_o_nome_da_area():
    capa = _montar(LINHA_CAATINGA)

    assert capa["relatorio_geral"] == "Este relatório apresenta um panorama da Caatinga, reunindo indicadores."


def test_caracteristicas_mostram_so_a_area_e_sem_mencao_ao_mapa():
    html = " ".join(_montar(LINHA_CAATINGA)["resumo_cidade_html"])

    assert "No bioma Caatinga, a leitura territorial" in html
    assert "Nordeste" not in html
    # Sem mapa, "(Figura 1)" roubaria o número do primeiro gráfico do relatório.
    assert "Figura" not in html


def test_nordeste_leva_os_dois_paragrafos_e_as_outras_areas_nenhum():
    nordeste = " ".join(_montar(LINHA_NORDESTE)["resumo_cidade_html"])
    caatinga = " ".join(_montar(LINHA_CAATINGA)["resumo_cidade_html"])

    assert nordeste.count("<p ") == 2
    assert '<p class="theme-detail-text">Nesse contexto' in nordeste
    # Isolando a condição (como no estado), o 2º parágrafo sairia em todas as áreas.
    assert "Nesse contexto" not in caatinga


def test_sem_variavel_configurada_nao_consulta_nada(monkeypatch):
    def explode(*_a, **_k):
        raise AssertionError("consultou sem CARACTERISTICAS_AREA_DOCS_URL")

    monkeypatch.setattr(primeira_pagina_area, "CARACTERISTICAS_AREA_DOCS_URL", None)
    monkeypatch.setattr(primeira_pagina_area, "buscar_caracteristicas_area", explode)

    assert asyncio.run(primeira_pagina_area.primeira_pagina_da_area("Caatinga", "r")) == {}


def test_area_sem_linha_nao_baixa_o_doc(primeira_pagina_de_area_configurada):
    tabela, doc = primeira_pagina_de_area_configurada

    assert asyncio.run(primeira_pagina_area.primeira_pagina_da_area("Semiárido", "r")) == {}
    assert tabela.pedidos == ["Semiárido"]
    assert doc.urls == []


def test_caracteristicas_juntam_areaint_geral_e_demografia(monkeypatch):
    consultas: list[str] = []
    linhas = {
        "areaint_geral": {"area_cd": 1, "area_territorial_km2": 857823.6},
        "areaint_demografia": {"area_cd": 1, "area_pop_total_2022": 25949989},
    }

    def executar_fake(query: str, params: tuple, _contexto: str) -> dict:
        view = query.split(".")[1].split()[0]
        consultas.append(view)
        assert params == ("Caatinga",)
        return linhas[view]

    monkeypatch.setattr(consulta_area, "executar_query_dict", executar_fake)

    assert consulta_area.buscar_caracteristicas_area("Caatinga") == {
        "area_cd": 1,
        "area_territorial_km2": 857823.6,
        "area_pop_total_2022": 25949989,
    }
    assert consultas == ["areaint_geral", "areaint_demografia"]


def test_caracteristicas_sem_nenhuma_linha_devolvem_none(monkeypatch):
    monkeypatch.setattr(consulta_area, "executar_query_dict", lambda *_a: None)

    assert consulta_area.buscar_caracteristicas_area("Paraíba") is None


def test_relatorio_da_area_leva_a_primeira_pagina_para_a_capa(
    ambiente_de_area, primeira_pagina_de_area_configurada  # noqa: F811
):
    _, _, ssr, _ = ambiente_de_area

    asyncio.run(relatorio_estado.gerar_relatorio_unidade_handler("area", "Caatinga", "demografia"))

    capa = ssr.props["cover"]
    assert [m["rotulo"] for m in capa["metricas"]] == ["Área territorial", "População residente"]
    assert capa["relatorio_geral"].startswith("Este relatório apresenta um panorama da Caatinga")
    assert any("No bioma Caatinga" in parte for parte in capa["resumo_cidade_html"])
