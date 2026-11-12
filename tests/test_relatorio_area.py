"""Relatório por área de interesse (12/11/2026): o mesmo handler do estado
(services/relatorio_estado.py, UNIDADES_DO_RELATORIO["area"]), com a matview de área
e o Doc de área do tema. Nenhum teste toca o banco, o Google ou o node do SSR."""

import asyncio
from pathlib import Path

import pytest
from fastapi import HTTPException

from services import cache, generation, laboratorio_snapshot, relatorio_estado
from utils.data.areas import AREAS_COM_RELATORIO, resolver_area
from utils.data.estados import ESTADOS_COM_RELATORIO
from utils.queries import area as consulta_area

DOC_DEMOGRAFIA_AREA = (
    "descricao_tema=“$area_sujeito tinha $area_pop_total_2022 habitantes em 2022.\n"
    "Para quando $area_pop_ne_per for maior que 100:\n"
    "Esse contingente é maior que a população do Nordeste.\n"
    "Texto sem condição.”@@\n"
    "#!Fontes\n"
    "Perfil demográfico = https://datanordeste.sudene.gov.br/data-panel/populacao\n"
)

LINHA_CAATINGA = {
    "area_cd": 1,
    "area_nome": "Caatinga",
    "area_sujeito": "A Caatinga",
    "area_pop_total_2022": 25949989,
    "area_pop_ne_per": 47.48,
}


class MatviewDeAreaFake:
    """A matview de área: só a Caatinga, e só em demografia."""

    def __init__(self) -> None:
        self.pedidos: list[tuple[str, str]] = []

    def buscar(self, slug: str, area: str) -> dict | None:
        self.pedidos.append((slug, area))
        if slug == "demografia" and area == "Caatinga":
            return dict(LINHA_CAATINGA)
        return None


class SsrFake:
    def __init__(self) -> None:
        self.props: dict | None = None

    async def render(self, props: dict) -> str:
        self.props = props
        return "<html>area</html>"


async def _pdf_fake(_html: str, destino: Path) -> bool:
    destino.write_bytes(b"%PDF-area")
    return True


async def _doc_fake(_url: str) -> str:
    return DOC_DEMOGRAFIA_AREA


@pytest.fixture
def ambiente_de_area(tmp_path, monkeypatch):
    monkeypatch.setattr(generation, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(cache, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(cache, "DATA_VERSION_FILE", tmp_path / ".data_version")
    monkeypatch.setattr(generation, "_gerar_pdf", _pdf_fake)
    matview, ssr = MatviewDeAreaFake(), SsrFake()
    docs_pedidos: list[tuple[str, str]] = []

    def docs_url_fake(slug: str, unidade: str) -> str | None:
        docs_pedidos.append((slug, unidade))
        return "https://docs.google.com/document/d/x/edit" if slug == "demografia" else None

    monkeypatch.setattr(relatorio_estado, "buscar_contexto_area", matview.buscar)
    monkeypatch.setattr(relatorio_estado, "render_react_ssr", ssr.render)
    monkeypatch.setattr(relatorio_estado, "carregar_texto_do_docs", _doc_fake)
    monkeypatch.setattr(relatorio_estado, "docs_url", docs_url_fake)
    return tmp_path, matview, ssr, docs_pedidos


def test_resolver_area_aceita_caixa_e_espacos_e_recusa_municipio_e_estado():
    assert resolver_area(" semiárido ") == "Semiárido"
    assert resolver_area("ÁREA DE ATUAÇÃO DA SUDENE") == "Área de atuação da Sudene"
    assert resolver_area("Campina Grande (PB)") is None
    assert resolver_area("Paraíba") is None


def test_lista_tem_as_quatro_areas_sem_colidir_com_estado():
    assert AREAS_COM_RELATORIO == ("Caatinga", "Área de atuação da Sudene", "Semiárido", "Nordeste")
    assert not {a.casefold() for a in AREAS_COM_RELATORIO} & {e.casefold() for e in ESTADOS_COM_RELATORIO}


def test_temalab_e_relatorio_leem_o_mesmo_mapa_de_matviews_de_area():
    assert laboratorio_snapshot.UNIDADES_POR_MATVIEW["area"]["matviews"] is consulta_area.MATVIEW_AREA_POR_MACROTEMA


def test_contexto_de_area_filtra_pela_area_na_matview_do_tema(monkeypatch):
    consultas: list[tuple[str, tuple]] = []

    def executar_fake(query: str, params: tuple, _contexto: str) -> dict:
        consultas.append((query, params))
        return {"area_nome": params[0]}

    monkeypatch.setattr(consulta_area, "executar_query_dict", executar_fake)

    assert consulta_area.buscar_contexto_area("hidraulica", "Semiárido") == {"area_nome": "Semiárido"}
    assert consultas == [
        ("SELECT * FROM auto_relatorios_areaint.areaint_seg_hidrica WHERE area_nome = %s", ("Semiárido",))
    ]


def test_tema_sem_matview_de_area_nao_consulta_o_banco(monkeypatch):
    def explode(*_a, **_k):
        raise AssertionError("consultou o banco para um tema sem matview de área")

    monkeypatch.setattr(consulta_area, "executar_query_dict", explode)

    assert consulta_area.buscar_contexto_area("desenvolvimento-social", "Caatinga") is None


def test_area_desconhecida_da_404(ambiente_de_area):
    with pytest.raises(HTTPException) as erro:
        asyncio.run(relatorio_estado.gerar_relatorio_unidade_handler("area", "Paraíba", "demografia"))
    assert erro.value.status_code == 404
    assert erro.value.detail == "Área de interesse 'Paraíba' não encontrada."


def test_relatorio_da_area_usa_doc_de_area_e_linha_da_matview(ambiente_de_area):
    pasta, matview, ssr, docs_pedidos = ambiente_de_area

    asyncio.run(relatorio_estado.gerar_relatorio_unidade_handler("area", "caatinga", "demografia,saude"))

    assert docs_pedidos == [("demografia", "area"), ("saude", "area")]
    assert matview.pedidos == [("demografia", "Caatinga")]
    cover = ssr.props["cover"]
    assert (cover["unidade"], cover["cidade_nome"], cover["uf"]) == ("area", "Caatinga", "")
    texto = " ".join(cover["macrotemas"][0]["descricao_html"])
    assert "A Caatinga tinha 25.949.989 habitantes" in texto
    # Condição falsa some, e a linha seguinte sem condição fica (regra do Doc estadual).
    assert "maior que a população do Nordeste" not in texto
    assert "Texto sem condição." in texto
    assert list(pasta.glob("relatorio_*caatinga*.pdf"))


def test_rotas_listam_areas_e_mandam_a_area_ao_handler_de_unidade(monkeypatch):
    import importlib

    from fastapi.testclient import TestClient

    import main

    main = importlib.reload(main)
    pedidos: list[tuple[str, str, str, bool]] = []

    async def handler_de_unidade_fake(unidade: str, nome: str, macrotema: str, aguardar: bool):
        pedidos.append((unidade, nome, macrotema, aguardar))
        return "<html>area</html>"

    monkeypatch.setattr(main, "gerar_relatorio_unidade_handler", handler_de_unidade_fake)
    cliente = TestClient(main.app)

    assert cliente.get("/areas").json() == list(AREAS_COM_RELATORIO)
    assert cliente.get("/relatorio/Semiárido?macrotema=saude&aguardar=nao").status_code == 200
    assert pedidos == [("area", "Semiárido", "saude", False)]


def test_indice_de_relatorios_devolve_o_nome_da_area(tmp_path, monkeypatch):
    from services import handlers

    (tmp_path / "relatorio_demografia__semi_rido.pdf").write_bytes(b"pdf")
    monkeypatch.setattr(handlers, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(handlers, "carregar_cidades", lambda: ["João Pessoa (PB)"])

    assert [r["cidade"] for r in handlers.listar_relatorios_handler()] == ["Semiárido"]


def test_card_do_panorama_de_area_tem_o_mesmo_icone_do_estado():
    from utils.cover import montar_indicadores_do_doc
    from utils.external.docs import CardDoPanorama

    def icone(campo: str) -> str:
        cards = montar_indicadores_do_doc([CardDoPanorama("Pop.", f"${campo}", "")], {campo: 10}, "demografia")
        return cards[0]["icone"]

    assert icone("area_pop_total_2022") == icone("uf_pop_total_2022") == "populacao_residente"
