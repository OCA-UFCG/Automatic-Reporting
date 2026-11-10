"""Relatório por estado (05/11/2026): a busca do portal acha os 9 estados do NE e o
/relatorio/{nome} gera o relatório com a matview estadual e o Doc estadual do tema.
Nenhum teste toca o banco, o Google ou o node do SSR: as costuras são as funções que
services/relatorio_estado.py importa."""

import asyncio
import importlib
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from services import cache, generation, handlers, relatorio_estado
from utils.data.estados import ESTADOS_COM_RELATORIO, resolver_estado
from utils.queries import estado as consulta_estado

DOC_DEMOGRAFIA_ESTADUAL = (
    "descricao_tema=“$uf_sujeito tinha $uf_pop_total_2022 habitantes em 2022.”@@\n"
)

LINHA_PARAIBA = {
    "uf_cd_uf": 25,
    "uf_estado": "Paraíba",
    "uf_sigla_uf": "PB",
    "uf_sujeito": "A Paraíba",
    "uf_pop_total_2022": 3974495,
}


class MatviewEstadualFake:
    """A matview estadual: só a Paraíba, e só em demografia."""

    def __init__(self) -> None:
        self.pedidos: list[tuple[str, str]] = []

    def buscar(self, slug: str, estado: str) -> dict | None:
        self.pedidos.append((slug, estado))
        if slug == "demografia" and estado == "Paraíba":
            return dict(LINHA_PARAIBA)
        return None


class SsrFake:
    """O node do SSR: guarda as props e devolve um HTML fixo."""

    def __init__(self) -> None:
        self.props: dict | None = None

    async def render(self, props: dict) -> str:
        self.props = props
        return "<html>estado</html>"


async def _pdf_fake(_html: str, destino: Path) -> bool:
    destino.write_bytes(b"%PDF-estado")
    return True


async def _doc_fake(_url: str) -> str:
    return DOC_DEMOGRAFIA_ESTADUAL


@pytest.fixture
def ambiente_estadual(tmp_path, monkeypatch):
    monkeypatch.setattr(generation, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(cache, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(cache, "DATA_VERSION_FILE", tmp_path / ".data_version")
    monkeypatch.setattr(generation, "_gerar_pdf", _pdf_fake)
    matview, ssr = MatviewEstadualFake(), SsrFake()
    monkeypatch.setattr(relatorio_estado, "buscar_contexto_estado", matview.buscar)
    monkeypatch.setattr(relatorio_estado, "render_react_ssr", ssr.render)
    monkeypatch.setattr(relatorio_estado, "carregar_texto_do_docs", _doc_fake)
    # Só demografia tem Doc estadual, como no Drive em 05/11/2026.
    monkeypatch.setattr(
        relatorio_estado,
        "docs_url",
        lambda slug, _unidade: "https://docs.google.com/document/d/x/edit" if slug == "demografia" else None,
    )
    return tmp_path, matview, ssr


def test_resolver_estado_aceita_caixa_e_espacos_e_recusa_municipio():
    assert resolver_estado(" paraíba ") == "Paraíba"
    assert resolver_estado("RIO GRANDE DO NORTE") == "Rio Grande do Norte"
    assert resolver_estado("Recife (PE)") is None
    assert resolver_estado("Minas Gerais") is None  # fora até a matview ter MG


def test_lista_tem_os_nove_estados_do_nordeste():
    assert len(ESTADOS_COM_RELATORIO) == 9
    assert len(set(ESTADOS_COM_RELATORIO)) == 9


def test_contexto_estadual_filtra_pelo_estado_na_matview_do_tema(monkeypatch):
    consultas: list[tuple[str, tuple]] = []

    def executar_fake(query: str, params: tuple, _contexto: str) -> dict:
        consultas.append((query, params))
        return {"uf_estado": params[0]}

    monkeypatch.setattr(consulta_estado, "executar_query_dict", executar_fake)

    assert consulta_estado.buscar_contexto_estado("hidraulica", "Bahia") == {"uf_estado": "Bahia"}
    assert consultas == [
        ("SELECT * FROM auto_relatorios_est.est_seg_hidrica WHERE uf_estado = %s", ("Bahia",))
    ]


def test_tema_sem_matview_estadual_nao_consulta_o_banco(monkeypatch):
    def explode(*_a, **_k):
        raise AssertionError("consultou o banco para um tema sem matview estadual")

    monkeypatch.setattr(consulta_estado, "executar_query_dict", explode)

    assert consulta_estado.buscar_contexto_estado("instrumentos-sudene", "Bahia") is None


def test_estado_desconhecido_da_404(ambiente_estadual):
    with pytest.raises(HTTPException) as erro:
        asyncio.run(relatorio_estado.gerar_relatorio_estado_handler("Recife (PE)", "demografia"))
    assert erro.value.status_code == 404
    assert "Recife (PE)" in erro.value.detail


def test_relatorio_do_estado_resolve_o_doc_com_a_linha_da_matview(ambiente_estadual):
    pasta, matview, ssr = ambiente_estadual

    resposta = asyncio.run(
        relatorio_estado.gerar_relatorio_estado_handler("paraíba", "demografia,saude")
    )

    assert resposta.body.decode("utf-8") == "<html>estado</html>"
    assert (pasta / "relatorio_demografia_saude__para_ba.pdf").exists()
    assert (pasta / "relatorio_demografia_saude__para_ba.html").exists()
    # Saúde não tem Doc estadual: pula antes de ir ao banco.
    assert matview.pedidos == [("demografia", "Paraíba")]
    capa = ssr.props["cover"]
    assert (capa["unidade"], capa["cidade_nome"], capa["uf"]) == ("estado", "Paraíba", "PB")
    assert capa["metricas"] == []
    assert [tema["slug"] for tema in capa["macrotemas"]] == ["demografia"]
    descricao = capa["macrotemas"][0]["descricao"]
    assert descricao.startswith("A Paraíba tinha 3")
    assert "$" not in descricao  # nenhum placeholder ficou cru


def test_sem_nenhum_tema_da_503_e_nao_grava_relatorio_vazio(ambiente_estadual):
    pasta, _, ssr = ambiente_estadual

    with pytest.raises(HTTPException) as erro:
        asyncio.run(relatorio_estado.gerar_relatorio_estado_handler("Bahia", "saude"))

    assert erro.value.status_code == 503
    assert "Bahia" in erro.value.detail
    assert ssr.props is None
    assert not list(pasta.glob("relatorio_*"))


def test_indice_de_relatorios_devolve_o_nome_do_estado(tmp_path, monkeypatch):
    (tmp_path / "relatorio_demografia__para_ba.pdf").write_bytes(b"pdf")
    monkeypatch.setattr(handlers, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(handlers, "carregar_cidades", lambda: ["João Pessoa (PB)"])

    relatorios = handlers.listar_relatorios_handler()

    assert [r["cidade"] for r in relatorios] == ["Paraíba"]


def test_rotas_listam_estados_e_mandam_o_estado_ao_handler_estadual(monkeypatch):
    import main

    main = importlib.reload(main)
    pedidos: list[tuple[str, str, bool]] = []

    async def handler_estadual_fake(nome: str, macrotema: str, aguardar: bool):
        pedidos.append((nome, macrotema, aguardar))
        return "<html>estado</html>"

    monkeypatch.setattr(main, "gerar_relatorio_estado_handler", handler_estadual_fake)
    cliente = TestClient(main.app)

    assert cliente.get("/estados").json() == list(ESTADOS_COM_RELATORIO)
    assert cliente.get("/relatorio/Paraíba?macrotema=saude&aguardar=nao").status_code == 200
    assert pedidos == [("Paraíba", "saude", False)]
