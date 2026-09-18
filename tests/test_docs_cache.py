import asyncio
import json

import pytest

from utils.external import docs

DOC_ID = "1AbCdEfGhIjK"
DOC_URL = f"https://docs.google.com/document/d/{DOC_ID}/edit"


@pytest.fixture
def cache_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(docs, "DOCS_CACHE_DIR", tmp_path)
    return tmp_path


def _proibir_rede(monkeypatch):
    """Envenena o caminho de rede: qualquer ida ao Google estoura o teste.
    É o que prova que a leitura foi do disco — asserção sobre o valor devolvido
    não distinguiria os dois caminhos."""

    async def _explode(*_a, **_k):
        raise AssertionError("foi na rede: deveria ter lido do cache em disco")

    monkeypatch.setattr(docs, "baixar_e_salvar_doc", _explode)


def test_le_do_disco_sem_tocar_na_rede(cache_tmp, monkeypatch):
    (cache_tmp / f"{DOC_ID}.json").write_text(
        json.dumps({"timestamp": 0, "texto": "PROSA EDITORIAL"}), encoding="utf-8"
    )
    _proibir_rede(monkeypatch)

    assert asyncio.run(docs.carregar_texto_do_docs(DOC_URL)) == "PROSA EDITORIAL"


def test_sem_cache_cai_pra_rede_uma_vez(cache_tmp, monkeypatch):
    # Deploy novo / Doc recém-configurado: degradar em lentidão, não em relatório
    # sem prosa (guarda do CLAUDE.md).
    chamadas = []

    async def _baixar(link):
        chamadas.append(link)
        return "BAIXADO"

    monkeypatch.setattr(docs, "baixar_e_salvar_doc", _baixar)

    assert asyncio.run(docs.carregar_texto_do_docs(DOC_URL)) == "BAIXADO"
    assert chamadas == [DOC_URL]


def test_texto_servido_e_identico_ao_gravado(cache_tmp):
    # Regressão: _carregar_do_cache limpava o texto de novo na leitura, e
    # limpar_texto_exportado_docs não é idempotente (come uma quebra de linha final
    # por aplicação). O texto servido variava conforme o número de idas ao cache.
    texto = "Titulo\n\nParagrafo final.\n"
    docs._salvar_no_cache(DOC_ID, texto)

    assert asyncio.run(docs.carregar_texto_do_docs(DOC_URL)) == texto


def test_cache_corrompido_cai_pra_rede(cache_tmp, monkeypatch):
    # JSON inválido não pode virar exceção no caminho do relatório.
    (cache_tmp / f"{DOC_ID}.json").write_text("{nao é json", encoding="utf-8")
    monkeypatch.setattr(docs, "baixar_e_salvar_doc", lambda _: _async("REBAIXADO"))

    assert asyncio.run(docs.carregar_texto_do_docs(DOC_URL)) == "REBAIXADO"


async def _async(valor):
    return valor
