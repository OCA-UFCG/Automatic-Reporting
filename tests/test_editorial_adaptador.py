import asyncio
import json

import pytest

from utils.editorial.contrato import novo_contrato
from utils.editorial.render import CHAVE_FONTE_PAINEL, FONTE_PAINEL
from utils.external import editorial
from utils.external.editorial import (
    ContratoIndisponivel,
    carregar_texto_editorial,
    fonte_editorial,
)


@pytest.fixture(autouse=True)
def _limpar_ambiente(monkeypatch):
    for nome in ("FONTE_EDITORIAL_EDUCACAO", "FONTE_EDITORIAL_DEMOGRAFIA"):
        monkeypatch.delenv(nome, raising=False)
    editorial._cache_contratos.clear()


def _contrato_em(tmp_path, slug, texto="Corpo do tema."):
    contrato = novo_contrato(slug)
    contrato["corpo"]["blocos"] = [
        {
            "id": "c1", "tipo": "paragrafo", "regra": None,
            "conteudo": [{"t": "texto", "v": texto}],
        }
    ]
    destino = tmp_path / f"{slug}.json"
    destino.write_text(json.dumps(contrato, ensure_ascii=False), encoding="utf-8")
    return destino


def test_padrao_e_docs():
    assert fonte_editorial("educacao") == "docs"


def test_variavel_por_macrotema_vence_a_global(monkeypatch):
    monkeypatch.setenv("FONTE_EDITORIAL_EDUCACAO", "painel")

    assert fonte_editorial("educacao") == "painel"
    assert fonte_editorial("demografia") == "docs"


def test_slug_com_hifen_vira_underscore_na_variavel(monkeypatch):
    monkeypatch.setenv("FONTE_EDITORIAL_ECONOMIA_RENDA", "painel")

    assert fonte_editorial("economia-renda") == "painel"


def test_valor_invalido_cai_para_docs(monkeypatch):
    """Errar a flag não pode derrubar o relatório: o caminho seguro é o atual."""
    monkeypatch.setenv("FONTE_EDITORIAL_EDUCACAO", "contentful")

    assert fonte_editorial("educacao") == "docs"


def test_caminho_docs_nao_toca_no_painel(monkeypatch):
    chamado = {}

    async def _falso_carregar(url):
        chamado["url"] = url
        return "descricao_tema = Veio do Doc.@@"

    monkeypatch.setattr(editorial, "carregar_texto_do_docs", _falso_carregar)
    contexto = {}

    texto = asyncio.run(
        carregar_texto_editorial(
            "educacao",
            {"docs_url": "https://docs.google.com/document/d/abc", "docs_env": "X"},
            contexto,
        )
    )

    assert "Veio do Doc." in texto
    assert CHAVE_FONTE_PAINEL not in contexto


def test_caminho_painel_renderiza_o_contrato_e_marca_o_contexto(monkeypatch, tmp_path):
    monkeypatch.setenv("FONTE_EDITORIAL_EDUCACAO", "painel")
    monkeypatch.setattr(editorial, "CONTRATOS_DIR", tmp_path)
    _contrato_em(tmp_path, "educacao")
    contexto = {}

    texto = asyncio.run(
        carregar_texto_editorial("educacao", {"docs_url": None, "docs_env": "X"}, contexto)
    )

    assert "descricao_tema = Corpo do tema." in texto
    assert contexto[CHAVE_FONTE_PAINEL] == FONTE_PAINEL


def test_painel_sem_contrato_publicado_avisa_como_gerar(monkeypatch, tmp_path):
    monkeypatch.setenv("FONTE_EDITORIAL_EDUCACAO", "painel")
    monkeypatch.setattr(editorial, "CONTRATOS_DIR", tmp_path)

    with pytest.raises(ContratoIndisponivel) as erro:
        asyncio.run(
            carregar_texto_editorial("educacao", {"docs_url": None, "docs_env": "X"}, {})
        )

    assert "importar_doc.py" in str(erro.value)


def test_contrato_republicado_invalida_o_cache(monkeypatch, tmp_path):
    """Publicar uma versão nova tem de surtir efeito sem reiniciar o processo."""
    monkeypatch.setenv("FONTE_EDITORIAL_EDUCACAO", "painel")
    monkeypatch.setattr(editorial, "CONTRATOS_DIR", tmp_path)
    destino = _contrato_em(tmp_path, "educacao", "Primeira versão.")

    primeiro = asyncio.run(
        carregar_texto_editorial("educacao", {"docs_url": None, "docs_env": "X"}, {})
    )

    contrato = json.loads(destino.read_text(encoding="utf-8"))
    contrato["corpo"]["blocos"][0]["conteudo"][0]["v"] = "Segunda versão."
    destino.write_text(json.dumps(contrato, ensure_ascii=False), encoding="utf-8")
    import os
    os.utime(destino, (0, 0))

    segundo = asyncio.run(
        carregar_texto_editorial("educacao", {"docs_url": None, "docs_env": "X"}, {})
    )

    assert "Primeira versão." in primeiro
    assert "Segunda versão." in segundo
