"""Precedência da fonte editorial: o ambiente manda, o painel alterna dentro.

A regra tem duas camadas de propósito. A variável de ambiente é a chave-mestra —
enquanto ela estiver em `docs`, nenhum clique na tela muda o que sai no PDF do
portal. Com ela em `painel`, o botão do painel decide macrotema a macrotema, sem
arrastar os outros sete junto.
"""

import json

import pytest
from fastapi import HTTPException

from services import admin
from utils.editorial import fontes
from utils.editorial.contrato import novo_contrato
from utils.editorial.repositorio import RepositorioDeContratos
from utils.external import editorial
from utils.external.editorial import alternavel_no_painel, fonte_editorial


@pytest.fixture(autouse=True)
def _registro_isolado(tmp_path, monkeypatch):
    """Cada teste com seu `_fontes.json`: o do repositório não pode interferir."""
    monkeypatch.setattr(fontes, "CONTRATOS_DIR", tmp_path)
    for nome in ("FONTE_EDITORIAL_EDUCACAO", "FONTE_EDITORIAL_DEMOGRAFIA"):
        monkeypatch.delenv(nome, raising=False)
    editorial._cache_contratos.clear()
    return tmp_path


def _publicar_contrato(repositorio, slug="educacao"):
    contrato = novo_contrato(slug)
    contrato["corpo"]["blocos"] = [
        {"id": "c1", "tipo": "paragrafo", "regra": None,
         "conteudo": [{"t": "texto", "v": "Corpo."}]}
    ]
    repositorio.publicar(slug, contrato, autor="teste", versao_esperada=None)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    repositorio = RepositorioDeContratos(tmp_path / "contratos")
    monkeypatch.setattr(admin, "repositorio", repositorio)
    return repositorio


# -- precedência ----------------------------------------------------------


def test_ambiente_em_docs_ignora_escolha_do_painel(monkeypatch):
    """A chave-mestra desligada tranca o tema, mesmo com escolha gravada."""
    monkeypatch.setenv("FONTE_EDITORIAL_EDUCACAO", "docs")
    fontes.registrar_escolha("educacao", "painel", "alguem")

    assert fonte_editorial("educacao") == "docs"
    assert alternavel_no_painel("educacao") is False


def test_ambiente_em_painel_sem_escolha_segue_painel(monkeypatch):
    """Comportamento de antes do botão: ligar a variável já bastava."""
    monkeypatch.setenv("FONTE_EDITORIAL_EDUCACAO", "painel")

    assert fonte_editorial("educacao") == "painel"
    assert alternavel_no_painel("educacao") is True


def test_ambiente_em_painel_respeita_volta_para_docs(monkeypatch):
    monkeypatch.setenv("FONTE_EDITORIAL_EDUCACAO", "painel")
    fontes.registrar_escolha("educacao", "docs", "alguem")

    assert fonte_editorial("educacao") == "docs"


def test_escolha_vale_so_para_o_macrotema_alternado(monkeypatch):
    # A global vem de config, lida na importação: aqui se troca o valor já lido.
    monkeypatch.setattr(editorial, "FONTE_EDITORIAL", "painel")
    fontes.registrar_escolha("educacao", "docs", "alguem")

    assert fonte_editorial("educacao") == "docs"
    assert fonte_editorial("demografia") == "painel"


def test_registro_corrompido_nao_derruba_a_leitura(monkeypatch, _registro_isolado):
    monkeypatch.setenv("FONTE_EDITORIAL_EDUCACAO", "painel")
    (_registro_isolado / fontes.NOME_DO_ARQUIVO).write_text("{isso não é json", encoding="utf-8")

    assert fonte_editorial("educacao") == "painel"


def test_registro_guarda_quem_alternou_e_quando(_registro_isolado):
    fontes.registrar_escolha("educacao", "painel", "marcelo")

    gravado = json.loads((_registro_isolado / fontes.NOME_DO_ARQUIVO).read_text(encoding="utf-8"))
    assert gravado["educacao"]["fonte"] == "painel"
    assert gravado["educacao"]["por"] == "marcelo"
    assert gravado["educacao"]["em"]


# -- handler do painel ----------------------------------------------------


def test_handler_recusa_quando_o_ambiente_trava(repo, monkeypatch):
    monkeypatch.setenv("FONTE_EDITORIAL_EDUCACAO", "docs")

    with pytest.raises(HTTPException) as erro:
        admin.alternar_fonte_handler("educacao", "painel", "marcelo")

    assert erro.value.status_code == 409
    # A mensagem precisa dizer o que falta: quem lê não tem acesso ao servidor.
    assert "FONTE_EDITORIAL_EDUCACAO=painel" in erro.value.detail
    assert fontes.escolha_do_painel("educacao") is None


def test_handler_recusa_painel_sem_contrato_publicado(repo, monkeypatch):
    monkeypatch.setenv("FONTE_EDITORIAL_EDUCACAO", "painel")

    with pytest.raises(HTTPException) as erro:
        admin.alternar_fonte_handler("educacao", "painel", "marcelo")

    assert erro.value.status_code == 409
    assert "contrato publicado" in erro.value.detail


def test_handler_alterna_com_contrato_publicado(repo, monkeypatch):
    monkeypatch.setenv("FONTE_EDITORIAL_EDUCACAO", "painel")
    _publicar_contrato(repo)

    resposta = admin.alternar_fonte_handler("educacao", "docs", "marcelo")

    assert resposta["fonte_editorial"] == "docs"
    assert resposta["registro"]["por"] == "marcelo"
    # Voltar para o painel não precisa de nada além do contrato que já existe.
    assert admin.alternar_fonte_handler("educacao", "painel", "marcelo")[
        "fonte_editorial"
    ] == "painel"


def test_handler_recusa_fonte_desconhecida(repo, monkeypatch):
    monkeypatch.setenv("FONTE_EDITORIAL_EDUCACAO", "painel")

    with pytest.raises(HTTPException) as erro:
        admin.alternar_fonte_handler("educacao", "contentful", "marcelo")

    assert erro.value.status_code == 400


def test_handler_recusa_macrotema_inexistente(repo, monkeypatch):
    monkeypatch.setattr(editorial, "FONTE_EDITORIAL", "painel")

    with pytest.raises(HTTPException) as erro:
        admin.alternar_fonte_handler("astrologia", "painel", "marcelo")

    assert erro.value.status_code == 404


def test_listagem_diz_se_o_tema_pode_ser_alternado(repo, monkeypatch):
    monkeypatch.setenv("FONTE_EDITORIAL_EDUCACAO", "painel")

    temas = {tema["slug"]: tema for tema in admin.listar_contratos_handler()}

    assert temas["educacao"]["pode_alternar_fonte"] is True
    assert temas["educacao"]["variavel_de_ambiente"] == "FONTE_EDITORIAL_EDUCACAO"
    assert temas["demografia"]["pode_alternar_fonte"] is False
