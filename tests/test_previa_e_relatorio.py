"""A prévia do painel é o relatório, não uma renderização paralela.

O portal (`data-nordeste-frontend`, /reports) mostra ao usuário o PDF que sai de
`gerar_relatorio_handler`. Se a prévia do painel renderizasse por outro caminho,
ela responderia a uma pergunta diferente da que o editor está fazendo — e foi
exatamente assim que a prévia antiga passou a divergir sem ninguém notar.

Estes testes travam duas garantias:

1. a prévia passa pelo mesmo handler do relatório; e
2. ela nunca escreve por cima dos artefatos que o portal serve ao público.

Nenhum deles toca o banco nem gera PDF.
"""

import pytest

from services import admin
from utils.editorial.contrato import novo_contrato
from utils.external.editorial import carregar_texto_editorial, contrato_em_edicao


class RespostaFalsa:
    def __init__(self, html: str):
        self.body = html.encode("utf-8")


@pytest.fixture
def contrato():
    return novo_contrato("demografia")


def test_previa_chama_o_handler_do_relatorio(monkeypatch, contrato):
    chamadas = {}

    async def handler_falso(cidade, macrotema=None, **kwargs):
        chamadas.update({"cidade": cidade, "macrotema": macrotema, **kwargs})
        return RespostaFalsa("<p>Relatório de $pop_total_2022</p>")

    monkeypatch.setattr(
        "services.generation.gerar_relatorio_handler", handler_falso
    )
    monkeypatch.setattr(
        admin, "montar_contexto_de_previa", lambda slug, cidade: ({}, None)
    )

    import asyncio

    resultado = asyncio.run(
        admin.previa_handler("demografia", contrato, "Campina Grande (PB)")
    )

    assert chamadas["cidade"] == "Campina Grande (PB)"
    assert chamadas["macrotema"] == "demografia"
    assert resultado["html"] == "<p>Relatório de $pop_total_2022</p>"
    assert resultado["campos_nao_resolvidos"] == ["pop_total_2022"]


def test_previa_nao_sobrescreve_os_artefatos_de_producao(monkeypatch, contrato):
    """O portal entrega `output/relatorio_<tema>__<cidade>.pdf`. A prévia não pode tocá-lo."""
    chamadas = {}

    async def handler_falso(cidade, macrotema=None, **kwargs):
        chamadas.update(kwargs)
        return RespostaFalsa("<p>ok</p>")

    monkeypatch.setattr(
        "services.generation.gerar_relatorio_handler", handler_falso
    )
    monkeypatch.setattr(
        admin, "montar_contexto_de_previa", lambda slug, cidade: ({}, None)
    )

    import asyncio

    asyncio.run(admin.previa_handler("demografia", contrato, "X (PB)"))

    assert chamadas["prefixo_artefato"], "sem prefixo a prévia grava por cima do relatório publicado"


def test_previa_devolve_o_pdf_e_nao_so_o_html(monkeypatch, contrato):
    """A tela mostra o PDF, então o handler precisa gerá-lo e dizer onde ele está.

    Regressão: a prévia já rodou com `gerar_pdf=False`. O HTML sozinho não tem
    o cabeçalho com as logos (vive em `@media print`) nem quebra de página (é
    do `@page` do WeasyPrint), e não havia arquivo para o botão de baixar.
    """
    chamadas = {}

    async def handler_falso(cidade, macrotema=None, **kwargs):
        chamadas.update(kwargs)
        return RespostaFalsa("<p>ok</p>")

    monkeypatch.setattr("services.generation.gerar_relatorio_handler", handler_falso)
    monkeypatch.setattr(
        admin, "montar_contexto_de_previa", lambda slug, cidade: ({}, None)
    )

    import asyncio

    resultado = asyncio.run(
        admin.previa_handler("demografia", contrato, "Campina Grande (PB)")
    )

    assert chamadas.get("gerar_pdf") is not False
    assert resultado["arquivo_pdf"] == "relatorio_previa__demografia__campina_grande_pb_.pdf"
    assert resultado["pdf_url"].startswith(f"/output/{resultado['arquivo_pdf']}?")


def test_contrato_em_edicao_vence_a_fonte_configurada():
    """Mesmo com o macrotema servido pelo Doc, a prévia mostra o contrato em edição."""
    contrato = novo_contrato("demografia")
    contrato["corpo"]["blocos"] = [
        {
            "id": "b1",
            "tipo": "paragrafo",
            "regra": None,
            "conteudo": [{"t": "texto", "v": "Texto que só existe no rascunho."}],
        }
    ]

    import asyncio

    with contrato_em_edicao("demografia", contrato):
        texto = asyncio.run(
            carregar_texto_editorial("demografia", {"docs_url": None}, {})
        )

    assert "Texto que só existe no rascunho." in texto


def test_contrato_em_edicao_nao_vaza_para_outro_macrotema(monkeypatch):
    """Duas requisições simultâneas não podem se contaminar."""
    chamado = {}

    async def docs_falso(url):
        chamado["url"] = url
        return "prosa do doc"

    monkeypatch.setattr("utils.external.editorial.carregar_texto_do_docs", docs_falso)
    monkeypatch.setattr("utils.external.editorial.fonte_editorial", lambda slug: "docs")

    import asyncio

    with contrato_em_edicao("demografia", novo_contrato("demografia")):
        texto = asyncio.run(
            carregar_texto_editorial(
                "saude", {"docs_url": "http://exemplo", "docs_env": "X"}, {}
            )
        )

    assert texto == "prosa do doc"


def test_contrato_em_edicao_e_desfeito_ao_sair():
    contrato = novo_contrato("demografia")
    with contrato_em_edicao("demografia", contrato):
        pass

    from utils.external.editorial import _contrato_em_edicao

    assert _contrato_em_edicao.get() is None
