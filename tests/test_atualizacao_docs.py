"""Conferir antes de gravar (services/atualizacao_docs.py), 24/11/2026: o botão
"Atualizar relatórios" do Data Nordeste e o cron só gravam no cache o Doc que passou
na conferência rápida. Doc com regra problemática ou que falhou mantém a cópia
anterior. Sem rede: o download e a gravação entram por parâmetro."""

import asyncio
import fcntl

import pytest
from fastapi.testclient import TestClient

from services import atualizacao_docs
from services.atualizacao_docs import (
    AtualizacaoEmAndamento,
    ResultadoDoDoc,
    conferir_e_atualizar,
    problemas_do_doc,
    token_de_docs_valido,
)
from utils.external import docs

DOC_OK = "Para quando $populacao for maior que 1000, então:\nCidade grande."
# A forma real dos 4 Docs de área barrados em 24/11/2026: o "igual a municipios" depois
# de um "e" não é reconhecido e a regra nunca vale — o parágrafo some do relatório.
DOC_COM_REGRA_QUEBRADA = (
    "Para quando $base for diferente de sem dados e $base for igual a municipios, então:\n"
    "Parágrafo que sumiria."
)
DOC_COM_REGRA_NO_RESUMO = "resumo_tema = Para quando $x for maior que 1: alto. @@\nresto"


class GoogleDocsFake:
    """Faz o papel de baixar_doc: devolve o texto da URL ou levanta o erro dela."""

    def __init__(self, por_url: dict[str, str | Exception]):
        self.por_url = por_url

    async def baixar(self, url: str) -> str:
        resposta = self.por_url[url]
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


class CacheDeDocsFake:
    """Faz o papel de salvar_doc_no_cache, guardando o que foi gravado."""

    def __init__(self, falhar: bool = False):
        self.gravados: dict[str, str] = {}
        self.falhar = falhar

    def gravar(self, url: str, texto: str) -> None:
        if self.falhar:
            raise OSError("disco cheio")
        self.gravados[url] = texto


def _rodar(docs_por_url: dict[str, str | Exception], cache: CacheDeDocsFake, trava):
    google = GoogleDocsFake(docs_por_url)
    lista = [(f"doc-{url}", url) for url in docs_por_url]
    return asyncio.run(conferir_e_atualizar(lista, google.baixar, cache.gravar, trava))


def test_grava_so_os_docs_que_passaram(tmp_path):
    cache = CacheDeDocsFake()

    resultados = _rodar(
        {
            "ok": DOC_OK,
            "quebrado": DOC_COM_REGRA_QUEBRADA,
            "fora-do-ar": ValueError("Google Docs sem acesso público"),
        },
        cache,
        tmp_path / "trava",
    )

    assert cache.gravados == {"ok": DOC_OK}
    assert [r.estado for r in resultados] == ["atualizado", "com_problema", "falhou"]
    assert "comparação não reconhecida" in resultados[1].avisos[0]
    assert "sem acesso público" in resultados[2].avisos[0]


def test_regra_escrita_no_resumo_barra_o_doc():
    assert problemas_do_doc(DOC_COM_REGRA_NO_RESUMO) == [
        "Para quando $x for maior que 1:\n    → regra no resumo do tema: sai escrita no relatório"
    ]


def test_doc_sem_problema_nao_tem_aviso():
    assert problemas_do_doc(DOC_OK) == []


def test_falha_ao_gravar_nao_e_contada_como_atualizado(tmp_path):
    resultados = _rodar({"ok": DOC_OK}, CacheDeDocsFake(falhar=True), tmp_path / "trava")

    assert resultados == [
        ResultadoDoDoc("doc-ok", "falhou", ["gravação no cache: disco cheio"], len(DOC_OK))
    ]


def test_segunda_rodada_simultanea_e_recusada_sem_gravar(tmp_path):
    trava = tmp_path / "trava"
    cache = CacheDeDocsFake()
    with open(trava, "w") as outra_rodada:
        fcntl.flock(outra_rodada, fcntl.LOCK_EX)

        with pytest.raises(AtualizacaoEmAndamento):
            _rodar({"ok": DOC_OK}, cache, trava)

    assert cache.gravados == {}


@pytest.mark.parametrize(
    ("recebido", "esperado", "valido"),
    [
        ("segredo", "segredo", True),
        ("outro", "segredo", False),
        (None, "segredo", False),
        ("segredo", None, False),  # sem token no .env a rota fica desligada
        ("ção", "segredo", False),  # header fora do ASCII não pode levantar
    ],
)
def test_token_de_docs_valido(recebido, esperado, valido):
    assert token_de_docs_valido(recebido, esperado) is valido


def test_gravacao_no_cache_e_atomica_e_legivel(tmp_path, monkeypatch):
    monkeypatch.setattr(docs, "DOCS_CACHE_DIR", tmp_path)

    docs.salvar_doc_no_cache("https://docs.google.com/document/d/abc123/edit", "texto")

    assert docs._carregar_do_cache("abc123")["texto"] == "texto"
    assert [p.name for p in tmp_path.iterdir()] == ["abc123.json"]


# --- POST /docs/atualizar ---


@pytest.fixture
def cliente(monkeypatch):
    import main

    async def _atualizar(_docs):
        return [ResultadoDoDoc("demografia", "atualizado", [], 10)]

    monkeypatch.setattr(main, "conferir_e_atualizar", _atualizar)
    monkeypatch.setattr(main, "docs_configurados", lambda: [("demografia", "url")])
    return TestClient(main.app)


def test_rota_desligada_sem_token_configurado(cliente, monkeypatch):
    monkeypatch.delenv("DOCS_ATUALIZAR_TOKEN", raising=False)

    resposta = cliente.post("/docs/atualizar", headers={"X-Docs-Token": "qualquer"})

    assert resposta.status_code == 503


def test_rota_recusa_token_errado(cliente, monkeypatch):
    monkeypatch.setenv("DOCS_ATUALIZAR_TOKEN", "segredo")

    resposta = cliente.post("/docs/atualizar", headers={"X-Docs-Token": "errado"})

    assert resposta.status_code == 401


def test_rota_devolve_o_resultado_de_cada_doc(cliente, monkeypatch):
    monkeypatch.setenv("DOCS_ATUALIZAR_TOKEN", "segredo")

    resposta = cliente.post("/docs/atualizar", headers={"X-Docs-Token": "segredo"})

    assert resposta.status_code == 200
    assert resposta.json() == {
        "docs": [{"rotulo": "demografia", "estado": "atualizado", "avisos": [], "caracteres": 10}]
    }


def test_rota_responde_409_com_outra_rodada_em_andamento(cliente, monkeypatch):
    import main

    async def _ocupado(_docs):
        raise AtualizacaoEmAndamento("outra rodada")

    monkeypatch.setenv("DOCS_ATUALIZAR_TOKEN", "segredo")
    monkeypatch.setattr(main, "conferir_e_atualizar", _ocupado)

    resposta = cliente.post("/docs/atualizar", headers={"X-Docs-Token": "segredo"})

    assert resposta.status_code == 409


def test_trava_padrao_fica_na_pasta_de_saida():
    # O cron e os workers do uvicorn precisam enxergar o mesmo arquivo de trava.
    assert atualizacao_docs.TRAVA_DA_ATUALIZACAO.parent == atualizacao_docs.OUTPUT_DIR
