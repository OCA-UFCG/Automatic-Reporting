"""Testes do painel: autenticação, concorrência otimista e histórico.

Testam os handlers direto, como o resto da suíte faz — subir o app inteiro
levantaria o servidor SSR em node, que não tem nada a ver com o que se verifica
aqui.
"""

import time

import pytest
from fastapi import HTTPException

from services import admin
from utils.editorial.contrato import novo_contrato
from utils.editorial.repositorio import ConflitoDeVersao, RepositorioDeContratos


@pytest.fixture
def repo(tmp_path, monkeypatch):
    repositorio = RepositorioDeContratos(tmp_path)
    monkeypatch.setattr(admin, "repositorio", repositorio)
    return repositorio


@pytest.fixture
def painel_configurado(monkeypatch):
    monkeypatch.setattr(admin, "PAINEL_SENHA", "abre-te-sesamo")
    monkeypatch.setattr(admin, "PAINEL_SEGREDO", "segredo-de-teste")


def _contrato(slug="educacao", texto="Corpo."):
    contrato = novo_contrato(slug)
    contrato["corpo"]["blocos"] = [
        {
            "id": "c1", "tipo": "paragrafo", "regra": None,
            "conteudo": [{"t": "texto", "v": texto}],
        }
    ]
    return contrato


# -- autenticação ---------------------------------------------------------


def test_sem_senha_configurada_o_painel_nao_abre(monkeypatch):
    """Falha fechada: o que se edita no painel sai publicado em relatório."""
    monkeypatch.setattr(admin, "PAINEL_SENHA", None)

    with pytest.raises(HTTPException) as erro:
        admin.login_handler("Marcelo", "qualquer")

    assert erro.value.status_code == 503
    assert "PAINEL_SENHA" in erro.value.detail


def test_senha_errada_e_recusada(painel_configurado):
    with pytest.raises(HTTPException) as erro:
        admin.login_handler("Marcelo", "chute")

    assert erro.value.status_code == 401


def test_login_devolve_token_que_identifica_o_editor(painel_configurado):
    sessao = admin.login_handler("Marcelo", "abre-te-sesamo")

    assert admin.verificar_token(sessao["token"]) == "Marcelo"
    assert admin.verificar_token(f"Bearer {sessao['token']}") == "Marcelo"


def test_login_exige_nome(painel_configurado):
    """O nome não autoriza nada — serve para o `publicado_por`."""
    with pytest.raises(HTTPException) as erro:
        admin.login_handler("   ", "abre-te-sesamo")

    assert erro.value.status_code == 400


def test_token_adulterado_e_recusado(painel_configurado):
    token = admin.login_handler("Marcelo", "abre-te-sesamo")["token"]
    corpo, _, assinatura = token.partition(".")

    with pytest.raises(HTTPException):
        admin.verificar_token(f"{corpo}x.{assinatura}")
    with pytest.raises(HTTPException):
        admin.verificar_token(f"{corpo}.{'0' * len(assinatura)}")


def test_token_expirado_e_recusado(painel_configurado, monkeypatch):
    monkeypatch.setattr(admin, "VALIDADE_DO_TOKEN_EM_SEGUNDOS", -1)
    token = admin.emitir_token("Marcelo")

    with pytest.raises(HTTPException) as erro:
        admin.verificar_token(token)

    assert "expirada" in erro.value.detail.casefold()


def test_trocar_a_senha_derruba_as_sessoes_quando_nao_ha_segredo_fixo(monkeypatch):
    monkeypatch.setattr(admin, "PAINEL_SEGREDO", None)
    monkeypatch.setattr(admin, "PAINEL_SENHA", "senha-antiga")
    token = admin.emitir_token("Marcelo")

    monkeypatch.setattr(admin, "PAINEL_SENHA", "senha-nova")
    with pytest.raises(HTTPException):
        admin.verificar_token(token)


def test_sem_token_a_resposta_e_401(painel_configurado):
    with pytest.raises(HTTPException) as erro:
        admin.verificar_token(None)

    assert erro.value.status_code == 401


# -- contratos ------------------------------------------------------------


def test_tema_sem_contrato_abre_num_contrato_vazio_e_valido(repo):
    resposta = admin.ler_contrato_handler("educacao")

    assert resposta["novo"] is True
    assert resposta["contrato"]["macrotema"] == "educacao"


def test_macrotema_desconhecido_e_404(repo):
    with pytest.raises(HTTPException) as erro:
        admin.ler_contrato_handler("astrologia")

    assert erro.value.status_code == 404


def test_publicar_grava_versao_autor_e_data(repo):
    publicado = admin.publicar_contrato_handler("educacao", _contrato(), None, "Marcelo")

    assert publicado["versao"] == 1
    assert publicado["publicado_por"] == "Marcelo"
    assert publicado["publicado_em"]
    assert repo.ler("educacao")["corpo"]["blocos"][0]["conteudo"][0]["v"] == "Corpo."


def test_contrato_de_outro_macrotema_e_recusado(repo):
    with pytest.raises(HTTPException) as erro:
        admin.publicar_contrato_handler("saude", _contrato("educacao"), None, "Marcelo")

    assert erro.value.status_code == 400


def test_contrato_invalido_nao_e_publicado(repo):
    invalido = _contrato()
    invalido["corpo"]["blocos"][0]["tipo"] = "carrossel"

    with pytest.raises(HTTPException) as erro:
        admin.publicar_contrato_handler("educacao", invalido, None, "Marcelo")

    assert erro.value.status_code == 422
    assert repo.ler("educacao") is None


# -- concorrência ---------------------------------------------------------


def test_duas_edicoes_a_partir_da_mesma_versao_conflitam(repo):
    """Sem lock e sem edição ao vivo: quem chega depois é recusado e vê o que
    mudou, em vez de sobrescrever o trabalho do outro em silêncio."""
    admin.publicar_contrato_handler("educacao", _contrato(), None, "Rayane")

    admin.publicar_contrato_handler("educacao", _contrato(texto="A"), 1, "Rayane")

    with pytest.raises(HTTPException) as erro:
        admin.publicar_contrato_handler("educacao", _contrato(texto="B"), 1, "André")

    assert erro.value.status_code == 409
    assert erro.value.detail["versao_atual"] == 2
    assert erro.value.detail["publicado_por"] == "Rayane"
    assert repo.ler("educacao")["corpo"]["blocos"][0]["conteudo"][0]["v"] == "A"


def test_publicar_sem_informar_a_versao_nao_confere_nada(repo):
    """Usado só na criação; o painel sempre manda a versão que leu."""
    admin.publicar_contrato_handler("educacao", _contrato(), None, "Marcelo")
    publicado = admin.publicar_contrato_handler("educacao", _contrato(), None, "Marcelo")

    assert publicado["versao"] == 2


# -- histórico ------------------------------------------------------------


def test_publicar_arquiva_a_versao_anterior(repo):
    admin.publicar_contrato_handler("educacao", _contrato(texto="v1"), None, "Marcelo")
    admin.publicar_contrato_handler("educacao", _contrato(texto="v2"), 1, "Rayane")
    admin.publicar_contrato_handler("educacao", _contrato(texto="v3"), 2, "André")

    historico = admin.historico_handler("educacao")

    assert [h["versao"] for h in historico] == [2, 1]
    assert repo.ler_versao("educacao", 1)["corpo"]["blocos"][0]["conteudo"][0]["v"] == "v1"
    assert repo.ler_versao("educacao", 3)["corpo"]["blocos"][0]["conteudo"][0]["v"] == "v3"


def test_versao_inexistente_e_404(repo):
    admin.publicar_contrato_handler("educacao", _contrato(), None, "Marcelo")

    with pytest.raises(HTTPException) as erro:
        admin.ler_versao_handler("educacao", 99)

    assert erro.value.status_code == 404


# -- repositório ----------------------------------------------------------


def test_slug_com_travessia_de_caminho_e_recusado(tmp_path):
    """O slug vem da URL e vira nome de arquivo."""
    repositorio = RepositorioDeContratos(tmp_path)

    for slug in ("../../etc/passwd", "educacao/../..", "Educação"):
        with pytest.raises(ValueError):
            repositorio.caminho(slug)


def test_conflito_traz_o_que_a_pessoa_precisa_para_decidir():
    erro = ConflitoDeVersao(3, 5, "Raína")

    assert "versão 5" in str(erro)
    assert "Raína" in str(erro)


def test_listagem_traz_os_oito_temas_com_estado_do_contrato(repo):
    admin.publicar_contrato_handler("educacao", _contrato(), None, "Marcelo")

    temas = admin.listar_contratos_handler()
    por_slug = {t["slug"]: t for t in temas}

    assert por_slug["educacao"]["contrato"]["versao"] == 1
    assert por_slug["saude"]["contrato"] is None
    assert por_slug["educacao"]["fonte_editorial"] in ("docs", "painel")
    assert por_slug["educacao"]["cor"].startswith("#")


def test_validar_devolve_todos_os_erros_sem_publicar(repo):
    invalido = _contrato()
    invalido["corpo"]["blocos"][0]["id"] = ""

    resposta = admin.validar_handler(invalido)

    assert resposta["valido"] is False
    assert resposta["erros"]
    assert repo.ler("educacao") is None


def test_token_leva_o_nome_e_o_prazo(painel_configurado):
    antes = time.time()
    token = admin.emitir_token("Raína")

    assert admin.verificar_token(token) == "Raína"
    assert time.time() - antes < 5


# -- rota da tela ---------------------------------------------------------


def test_painel_sem_barra_redireciona_para_a_tela(monkeypatch, tmp_path):
    """Um Mount em "/painel" só casa "/painel/...", e o mount do frontend em "/"
    engole o endereço sem barra antes que o Starlette redirecione sozinho."""
    import main

    monkeypatch.setattr(main, "ADMIN_DIST_DIR", tmp_path)
    resposta = main.painel_raiz()

    assert resposta.status_code in (302, 307)
    assert resposta.headers["location"] == "/painel/"


def test_painel_sem_build_explica_o_que_fazer(monkeypatch, tmp_path):
    """404 seco manda a pessoa procurar o erro no lugar errado."""
    import main

    monkeypatch.setattr(main, "ADMIN_DIST_DIR", tmp_path / "inexistente")

    with pytest.raises(HTTPException) as erro:
        main.painel_raiz()

    assert erro.value.status_code == 503
    assert "npm run build -w admin" in erro.value.detail
