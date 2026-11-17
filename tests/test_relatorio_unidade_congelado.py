"""Modo congelado do relatório de estado e de área (beta, 16/11/2026): com
RELATORIO_CONGELADO_DIR, texto, linha e gráficos vêm da pasta congelada, sem banco.
Nenhum teste toca o banco, o Google ou o node do SSR: um banco ou Doc chamado aqui falha."""

import asyncio
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

import config
from services import primeira_pagina_estado, relatorio_congelado, relatorio_estado
from utils.queries import area as consulta_area
from utils.queries import estado as consulta_estado
from utils.render.renderer import reset_figura_contador

TEXTO_DEMOGRAFIA_PB = (
    "Demografia\n"
    "Panorama de indicadores\n"
    "População residente\n"
    "3.974.687\n"
    "IBGE, Censo 2022 • pessoas\n"
    "\n"
    "descricao_tema = “A Paraíba (PB) tinha 3.974.687 habitantes em 2022 (Figura X).\n"
    "*grafico_visao_historica\n"
    "Figura X – Evolução da população da Paraíba (PB).”@@\n"
    "#!Fontes\n"
    "Perfil demográfico = https://datanordeste.sudene.gov.br/data-panel/populacao\n"
)


def _proibido(*_args, **_kwargs):
    raise AssertionError("o modo congelado não pode consultar o banco nem os Docs")


@pytest.fixture
def pasta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Pasta congelada com a demografia da Paraíba (texto, linha, um PNG), a linha geral
    das áreas e a est_caract_mun da Paraíba."""
    def gravar(caminho: str, conteudo: str | bytes) -> None:
        destino = tmp_path / caminho
        destino.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(conteudo, bytes):
            destino.write_bytes(conteudo)
        else:
            destino.write_text(conteudo, encoding="utf-8")

    gravar("textos/estado/demografia/paraiba.txt", TEXTO_DEMOGRAFIA_PB)
    gravar("congelado/estado/demografia/paraiba.json",
           json.dumps({"linha": {"uf_sigla_uf": "PB", "uf_pop": "3974687", "uf_area": "56467.243"}}))
    gravar("graficos/estado/demografia/paraiba/grafico_visao_historica.png", b"PNG")
    for area in ("nordeste", "caatinga"):
        gravar(f"congelado/area/geral/{area}.json", json.dumps({"linha": {"area_nome": area}}))
    gravar("congelado/estado/caract-mun/paraiba.json", json.dumps({"linha": {"estado": "Paraíba", "area": "56467.243"}}))

    monkeypatch.setattr(config, "RELATORIO_CONGELADO_DIR", str(tmp_path))
    monkeypatch.setattr(relatorio_estado, "OUTPUT_DIR", tmp_path / "output")
    for alvo, nome in [
        (relatorio_estado, "carregar_texto_do_docs"),
        (relatorio_estado, "gerar_graficos_do_estado"),
        (relatorio_estado, "gerar_graficos_da_area"),
        (consulta_estado, "buscar_contexto_estado"),
        (consulta_area, "buscar_contexto_area"),
        (primeira_pagina_estado, "buscar_caracteristicas_estado"),
    ]:
        monkeypatch.setattr(alvo, nome, _proibido)
    return tmp_path


def _tema(unidade: str, slug: str, nome: str):
    reset_figura_contador(com_mapa=False)  # como em _gerar: a numeração vive num ContextVar
    return asyncio.run(relatorio_estado.tema_da_unidade(unidade, slug, nome, datetime(2026, 11, 16, tzinfo=ZoneInfo("America/Fortaleza")), "r"))


def test_nome_de_arquivo():
    assert relatorio_congelado.nome_de_arquivo("Área de atuação da Sudene") == "area-de-atuacao-da-sudene"
    assert relatorio_congelado.nome_de_arquivo("Rio Grande do Norte") == "rio-grande-do-norte"


def test_tema_estatico_le_texto_linha_e_grafico_da_pasta(pasta: Path):
    tema = _tema("estado", "demografia", "Paraíba")

    assert tema is not None
    html = " ".join(tema.item["descricao_html"])
    assert "3.974.687 habitantes" in html
    assert "Figura 1" in html and "grafico_visao_historica_estado_para_ba.png" in html
    assert (pasta / "output" / "grafico_visao_historica_estado_para_ba.png").read_bytes() == b"PNG"
    assert [card["valor"] for card in tema.item["indicadores"]] == ["3.974.687"]
    # Números do congelamento voltam a ser número: placeholders formatam como com o banco.
    assert tema.contexto["uf_pop"] == 3974687 and tema.contexto["uf_area"] == Decimal("56467.243")


def test_tema_sem_arquivo_some(pasta: Path):
    assert _tema("estado", "saude", "Paraíba") is None
    assert _tema("estado", "demografia", "Ceará") is None


def test_ds_de_area_usa_o_doc_fixo_com_a_linha_geral_so_no_nordeste(pasta: Path, monkeypatch: pytest.MonkeyPatch):
    async def doc_fixo(_url: str) -> str:
        return "descricao_tema = “Texto fixo do Nordeste.”@@\n"

    monkeypatch.setattr(relatorio_estado, "docs_url", lambda slug, unidade: "https://doc-fixo")
    monkeypatch.setattr(relatorio_estado, "carregar_texto_do_docs", doc_fixo)

    tema = _tema("area", "desenvolvimento-social", "Nordeste")
    assert tema is not None and "Texto fixo do Nordeste." in " ".join(tema.item["descricao_html"])
    # A Caatinga tem linha geral, mas o Doc fixo fala só do Nordeste: o tema some.
    assert _tema("area", "desenvolvimento-social", "Caatinga") is None


def test_primeira_pagina_do_estado_le_a_linha_congelada(pasta: Path, monkeypatch: pytest.MonkeyPatch):
    async def doc(_url: str) -> str:
        return "apresentacao = “Área de geral.$area:2 km².” @@\n"

    monkeypatch.setattr(primeira_pagina_estado, "CARACTERISTICAS_ESTADO_DOCS_URL", "https://doc-1a-pagina")
    monkeypatch.setattr(primeira_pagina_estado, "carregar_texto_do_docs", doc)

    capa = asyncio.run(primeira_pagina_estado.primeira_pagina_do_estado("Paraíba", "r"))
    assert "56.467,24 km²" in capa["relatorio_geral"]


def test_texto_numerico_volta_a_decimal_e_inteiro_do_json_fica():
    linha = {"pop": "3974687", "area": "56467.243", "ano_area": 2025, "sigla": "PB", "cd": "PB-25"}
    tipada = {coluna: relatorio_congelado._tipar(valor) for coluna, valor in linha.items()}
    assert tipada == {"pop": Decimal(3974687), "area": Decimal("56467.243"), "ano_area": 2025,
                      "sigla": "PB", "cd": "PB-25"}


def test_linha_ilegivel_faz_o_tema_sumir_sem_500(pasta: Path):
    (pasta / "congelado/estado/demografia/paraiba.json").write_text("{quebrado", encoding="utf-8")
    assert _tema("estado", "demografia", "Paraíba") is None


def test_linha_sem_texto_vai_ao_doc_e_sem_doc_some(pasta: Path, monkeypatch: pytest.MonkeyPatch):
    (pasta / "textos/estado/demografia/paraiba.txt").unlink()
    monkeypatch.setattr(relatorio_estado, "docs_url", lambda slug, unidade: None)
    assert _tema("estado", "demografia", "Paraíba") is None


def test_texto_sem_linha_some(pasta: Path):
    (pasta / "congelado/estado/demografia/paraiba.json").unlink()
    assert _tema("estado", "demografia", "Paraíba") is None


def test_grafico_sem_png_some_com_a_mencao(pasta: Path):
    (pasta / "graficos/estado/demografia/paraiba/grafico_visao_historica.png").unlink()
    html = " ".join(_tema("estado", "demografia", "Paraíba").item["descricao_html"])
    assert "Figura" not in html and "3.974.687 habitantes em 2022." in html


PRIMEIRA_PAGINA_PB = (
    "Panorama de indicadores\n"
    "Área territorial\n"
    "56.467,243 km²\n"
    "IBGE (2025) • Extensão territorial\n"
    "População residente\n"
    "3.974.687\n"
    "Censo demográfico (IBGE, 2022) • Pessoas residentes\n"
    "\n"
    "apresentacao = “Este relatório apresenta um panorama geral da Paraíba (PB).” @@\n"
    "\n"
    "resumo_cidade = “A Paraíba (Figura X) tem João Pessoa como capital.” @@\n"
    "\n"
    "Figura X – Localização da Paraíba (PB).\n"
)


def _gerar_capturando(monkeypatch: pytest.MonkeyPatch, unidade: str, nome: str) -> dict:
    """Roda _gerar até o SSR e devolve as props que iriam para o React."""
    props: dict = {}

    async def ssr(p: dict) -> str:
        props.update(p)
        return "<html></html>"

    async def gravar(_html: str, _safe: str) -> str:
        return "ok"

    monkeypatch.setattr(relatorio_estado, "render_react_ssr", ssr)
    monkeypatch.setattr(relatorio_estado, "gravar_relatorio", gravar)
    asyncio.run(relatorio_estado._gerar(unidade, nome, ["demografia"], "r"))
    return props


def test_primeira_pagina_estatica_com_mapa_e_o_grafico_vira_figura_2(pasta: Path, monkeypatch: pytest.MonkeyPatch):
    (pasta / "textos/estado/primeira-pagina").mkdir(parents=True)
    (pasta / "textos/estado/primeira-pagina/paraiba.txt").write_text(PRIMEIRA_PAGINA_PB, encoding="utf-8")
    (pasta / "mapas/estado").mkdir(parents=True)
    (pasta / "mapas/estado/paraiba.png").write_bytes(b"MAPA")
    # O texto estático vence o Doc: o Doc não pode ser baixado.
    monkeypatch.setattr(primeira_pagina_estado, "carregar_texto_do_docs", _proibido)

    capa = _gerar_capturando(monkeypatch, "estado", "Paraíba")["cover"]

    assert [(m["valor"], m["sufixo"], m["icone"], m["fonte"]) for m in capa["metricas"]] == [
        ("56.467,243", "km²", "area", "IBGE (2025)"),
        ("3.974.687", "", "populacao", "Censo demográfico (IBGE, 2022)"),
    ]
    assert capa["relatorio_geral"] == "Este relatório apresenta um panorama geral da Paraíba (PB)."
    assert "A Paraíba (Figura 1) tem João Pessoa" in " ".join(capa["resumo_cidade_html"])
    assert "Figura 1 – Localização da Paraíba (PB)." in capa["mapa_principal"]
    assert 'src="/output/mapa_estado_para_ba.png"' in capa["mapa_principal"]
    assert (pasta / "output/mapa_estado_para_ba.png").read_bytes() == b"MAPA"
    # O mapa é a Figura 1: o gráfico do tema passa a ser a Figura 2.
    tema = " ".join(capa["macrotemas"][0]["descricao_html"])
    assert "Figura 2" in tema and "Figura 1" not in tema


def test_area_le_primeira_pagina_e_mapa_e_sem_mapa_a_mencao_sai(pasta: Path, monkeypatch: pytest.MonkeyPatch):
    for caminho, conteudo in [
        ("textos/area/demografia/caatinga.txt", TEXTO_DEMOGRAFIA_PB),
        ("congelado/area/demografia/caatinga.json", json.dumps({"linha": {"area_nome": "Caatinga"}})),
        ("textos/area/primeira-pagina/caatinga.txt",
         "resumo_cidade = “Na Caatinga (Figura X), a leitura territorial.” @@\n\nFigura X – Localização da Caatinga.\n"),
        ("mapas/area/caatinga.png", "MAPA"),
    ]:
        (pasta / caminho).parent.mkdir(parents=True, exist_ok=True)
        (pasta / caminho).write_text(conteudo, encoding="utf-8")

    capa = _gerar_capturando(monkeypatch, "area", "Caatinga")["cover"]
    assert "Na Caatinga (Figura 1), a leitura territorial." in " ".join(capa["resumo_cidade_html"])
    assert "Figura 1 – Localização da Caatinga." in capa["mapa_principal"]

    # Sem o PNG: sem mapa, e a menção ao mapa sai do texto.
    (pasta / "mapas/area/caatinga.png").unlink()
    capa = _gerar_capturando(monkeypatch, "area", "Caatinga")["cover"]
    assert capa["mapa_principal"] == ""
    assert "Na Caatinga, a leitura territorial." in " ".join(capa["resumo_cidade_html"])
