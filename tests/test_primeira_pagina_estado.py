"""Primeira página do relatório por estado (13/11/2026): o Doc de
CARACTERISTICAS_ESTADO_DOCS_URL resolvido contra a linha do estado em est_caract_mun.
Nenhum teste toca o banco, o Google ou o node do SSR."""

import asyncio

import pytest

from services import primeira_pagina_estado, relatorio_estado
from tests.test_relatorio_estado import ambiente_estadual  # noqa: F401 (fixture)
from utils.queries import estado as consulta_estado

DOC_PRIMEIRA_PAGINA = (
    "Panorama de indicadores\n"
    "Área territorial\n"
    "geral.$area:3 km²\n"
    "\tPopulação residente\n"
    "geral.$pop_total_2022\n"
    "\n"
    "apresentacao = “Este relatório apresenta um panorama geral.$uf_de (geral.$sigla_uf).” @@\n"
    "\n"
    "resumo_cidade = “\n"
    "Para quando geral.$cd_uf for igual a 27, então:\n"
    "Alagoas (Figura X) tem Maceió como capital.\n"
    "Para quando geral.$cd_uf for igual a 25, então:\n"
    "A Paraíba (Figura X) tem João Pessoa como capital.\n"
    "” @@\n"
    "\n"
    "*Inserir figura\n"
    "Figura X – Localização geral.$uf_de (geral.$sigla_uf).\n"
)

CARACTERISTICAS_PARAIBA = {
    "cd_uf": 25,
    "estado": "Paraíba",
    "sigla_uf": "PB",
    "uf_de": "da Paraíba",
    "area": 56467.243,
    "pop_total_2022": 3974687,
}


class CaracteristicasEstadoFake:
    """A tabela est_caract_mun: só a Paraíba."""

    def __init__(self) -> None:
        self.pedidos: list[str] = []

    def buscar(self, estado: str) -> dict | None:
        self.pedidos.append(estado)
        return dict(CARACTERISTICAS_PARAIBA) if estado == "Paraíba" else None


class DocPrimeiraPaginaFake:
    """O Google Docs: devolve o Doc da primeira página e anota as URLs pedidas."""

    def __init__(self) -> None:
        self.urls: list[str] = []

    async def carregar(self, url: str) -> str:
        self.urls.append(url)
        return DOC_PRIMEIRA_PAGINA


@pytest.fixture
def primeira_pagina_configurada(monkeypatch):
    tabela, doc = CaracteristicasEstadoFake(), DocPrimeiraPaginaFake()
    monkeypatch.setattr(primeira_pagina_estado, "CARACTERISTICAS_ESTADO_DOCS_URL", "doc-primeira-pagina")
    monkeypatch.setattr(primeira_pagina_estado, "buscar_caracteristicas_estado", tabela.buscar)
    monkeypatch.setattr(primeira_pagina_estado, "carregar_texto_do_docs", doc.carregar)
    return tabela, doc


def test_cards_do_doc_viram_metricas_da_capa_com_unidade_separada():
    capa = primeira_pagina_estado.montar_primeira_pagina(DOC_PRIMEIRA_PAGINA, CARACTERISTICAS_PARAIBA, "r")

    assert capa["metricas"] == [
        {"rotulo": "Área territorial", "valor": "56.467,243", "sufixo": "km²",
         "fonte": "", "caption": "", "icone": "area"},
        {"rotulo": "População residente", "valor": "3.974.687", "sufixo": "",
         "fonte": "", "caption": "", "icone": "populacao"},
    ]


def test_apresentacao_resolve_os_campos_geral():
    capa = primeira_pagina_estado.montar_primeira_pagina(DOC_PRIMEIRA_PAGINA, CARACTERISTICAS_PARAIBA, "r")

    assert capa["relatorio_geral"] == "Este relatório apresenta um panorama da Paraíba (PB)."
    assert len(capa["relatorio_geral_html"]) == 1


def test_caracteristicas_gerais_mostram_so_o_estado_e_sem_mencao_ao_mapa():
    capa = primeira_pagina_estado.montar_primeira_pagina(DOC_PRIMEIRA_PAGINA, CARACTERISTICAS_PARAIBA, "r")

    html = " ".join(capa["resumo_cidade_html"])
    assert "A Paraíba tem João Pessoa como capital." in html
    assert "Alagoas" not in html
    # Sem mapa, a menção roubaria o número do primeiro gráfico do relatório.
    assert "Figura" not in html


def test_doc_sem_blocos_nao_mexe_na_capa():
    assert primeira_pagina_estado.montar_primeira_pagina("Texto solto.", CARACTERISTICAS_PARAIBA, "r") == {}


def test_sem_variavel_configurada_nao_consulta_nada(monkeypatch):
    def explode(*_a, **_k):
        raise AssertionError("consultou sem CARACTERISTICAS_ESTADO_DOCS_URL")

    monkeypatch.setattr(primeira_pagina_estado, "CARACTERISTICAS_ESTADO_DOCS_URL", None)
    monkeypatch.setattr(primeira_pagina_estado, "buscar_caracteristicas_estado", explode)

    assert asyncio.run(primeira_pagina_estado.primeira_pagina_do_estado("Paraíba", "r")) == {}


def test_estado_fora_da_tabela_nao_baixa_o_doc(primeira_pagina_configurada):
    tabela, doc = primeira_pagina_configurada

    assert asyncio.run(primeira_pagina_estado.primeira_pagina_do_estado("Bahia", "r")) == {}
    assert tabela.pedidos == ["Bahia"]
    assert doc.urls == []


def test_caracteristicas_filtram_pelo_nome_do_estado(monkeypatch):
    consultas: list[tuple[str, tuple]] = []

    def executar_fake(query: str, params: tuple, _contexto: str) -> dict:
        consultas.append((query, params))
        return {"estado": params[0]}

    monkeypatch.setattr(consulta_estado, "executar_query_dict", executar_fake)

    assert consulta_estado.buscar_caracteristicas_estado("Bahia") == {"estado": "Bahia"}
    assert consultas == [
        ("SELECT * FROM auto_relatorios_est.est_caract_mun WHERE estado = %s", ("Bahia",))
    ]


def test_relatorio_do_estado_leva_a_primeira_pagina_para_a_capa(
    ambiente_estadual, primeira_pagina_configurada  # noqa: F811
):
    _, _, ssr = ambiente_estadual

    asyncio.run(relatorio_estado.gerar_relatorio_estado_handler("Paraíba", "demografia"))

    capa = ssr.props["cover"]
    assert [m["rotulo"] for m in capa["metricas"]] == ["Área territorial", "População residente"]
    assert capa["relatorio_geral"].startswith("Este relatório apresenta um panorama da Paraíba")
    assert any("João Pessoa" in parte for parte in capa["resumo_cidade_html"])
