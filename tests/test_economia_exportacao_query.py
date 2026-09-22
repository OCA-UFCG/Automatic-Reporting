import logging

from utils.queries import economia_exportacao


def test_buscar_comercio_exterior_economia_repassa_fob_exportado_ultimo(monkeypatch):
    # A matview já traz a coluna com o nome final que o Doc usa
    # (fob_exportado_ultimo/_unid); o código não deve depender de um alias
    # "fob_exportado" que não existe na view.
    linha_perfil = {
        "fob_exportado_ultimo": 6.3,
        "fob_exportado_ultimo_unid": "milhões",
        "kg_exportado": 918.2,
        "kg_exportado_unid": "mil",
    }
    monkeypatch.setattr(
        economia_exportacao,
        "buscar_perfil_municipal",
        lambda *args, **kwargs: linha_perfil,
    )

    dados = economia_exportacao.buscar_comercio_exterior_economia("Campina Grande", "PB")

    assert dados["fob_exportado_ultimo"] == 6.3
    assert dados["fob_exportado_ultimo_unid"] == "milhões"
    assert dados["kg_exportado"] == 918.2


def test_buscar_comercio_exterior_economia_retorna_none_sem_perfil(monkeypatch):
    monkeypatch.setattr(
        economia_exportacao, "buscar_perfil_municipal", lambda *args, **kwargs: None
    )

    assert economia_exportacao.buscar_comercio_exterior_economia("Sem Dados", "PB") is None


def test_buscar_comercio_exterior_economia_aplica_aliases_balanca_e_paises(monkeypatch):
    linha_perfil = {
        "analise_balanca1": "déficit",
        "analise_balanca2": "negativo",
        "valor_balanca1": -717.3,
        "valor_balanca1unid": "mil",
        "valor_balanca6meses": -30.6,
        "valor_balanca6mesesunid": "milhões",
        "valor_balanca_jan": -6203881.0,
        "valor_balanca_jun": -7305491.0,
        "pais_exportacao1": "Filipinas",
        "valor_pais_exportacao1": 824.3,
        "valor_pais_exportacaounid1": "mil",
        "pais_exportacao2": "Austrália",
        "valor_pais_exportacao2": 819.3,
        "valor_pais_exportacaounid2": "mil",
    }
    monkeypatch.setattr(
        economia_exportacao,
        "buscar_perfil_municipal",
        lambda *args, **kwargs: linha_perfil,
    )

    dados = economia_exportacao.buscar_comercio_exterior_economia("Campina Grande", "PB")

    # doc usa "balança" com cedilha
    assert dados["analise_balança1"] == "déficit"
    # doc usa "balanca"/"balanca2" (bare) na síntese
    assert dados["balanca"] == "déficit"
    assert dados["balanca2"] == "negativo"
    # doc usa "exportacao1/2" (sem "pais_") nessa seção
    assert dados["exportacao1"] == "Filipinas"
    assert dados["exportacao2"] == "Austrália"
    assert dados["exportacao_paises"] == [
        ("Filipinas", 824_300.0),
        ("Austrália", 819_300.0),
    ]
    assert dados["balanca_mensal"] == [
        ("Jan", -6203881.0),
        ("Jun", -7305491.0),
    ]


def test_municipio_sem_comercio_exterior_devolve_lista_vazia(monkeypatch):
    # Batalha/AL: unidade '' e nome/valor NULL porque o município não
    # comercia. A chave existe mesmo vazia, como `importacao_paises`.
    linha_perfil = {
        "valor_pais_exportacaounid1": "",
        "valor_pais_exportacaounid2": "",
        "valor_pais_exportacaounid3": "",
        "valor_pais_exportacaounid4": "",
    }
    monkeypatch.setattr(
        economia_exportacao, "buscar_perfil_municipal", lambda *a, **k: linha_perfil
    )

    dados = economia_exportacao.buscar_comercio_exterior_economia("Batalha", "AL")

    assert dados["exportacao_paises"] == []
    assert "exportacao1" not in dados


def test_pais_sem_valor_nao_entra_pela_metade_no_contexto(monkeypatch):
    # Publicar só o nome deixaria "$valor_pais_exportacao1" literal no PDF.
    linha_perfil = {
        "pais_exportacao1": "Filipinas",
        "valor_pais_exportacao1": 824.3,
        "valor_pais_exportacaounid1": "mil",
        "pais_exportacao2": "Austrália",  # sem valor_pais_exportacao2
        "valor_pais_exportacaounid2": "mil",
    }
    monkeypatch.setattr(
        economia_exportacao, "buscar_perfil_municipal", lambda *a, **k: linha_perfil
    )

    dados = economia_exportacao.buscar_comercio_exterior_economia("Campina Grande", "PB")

    assert dados["exportacao1"] == "Filipinas"
    assert "pais_exportacao2" not in dados
    assert "exportacao2" not in dados
    assert dados["exportacao_paises"] == [("Filipinas", 824_300.0)]


def test_unidade_desconhecida_nao_multiplica_e_avisa(monkeypatch, caplog):
    # Fora do mapa: mantém o valor cru e avisa, em vez de encolher 1.000x.
    linha_perfil = {
        "pais_exportacao1": "Filipinas",
        "valor_pais_exportacao1": 824.3,
        "valor_pais_exportacaounid1": "milhoes",  # sem cedilha: não é o do mapa
    }
    monkeypatch.setattr(
        economia_exportacao, "buscar_perfil_municipal", lambda *a, **k: linha_perfil
    )

    with caplog.at_level(logging.WARNING):
        dados = economia_exportacao.buscar_comercio_exterior_economia("X", "PB")

    assert dados["exportacao_paises"] == [("Filipinas", 824.3)]
    assert "milhoes" in caplog.text


def test_unidade_vazia_nao_gera_aviso(monkeypatch, caplog):
    # '' é o normal sem comércio; avisar seria ruído em toda cidade pequena.
    linha_perfil = {
        "pais_exportacao1": "Filipinas",
        "valor_pais_exportacao1": 824.3,
        "valor_pais_exportacaounid1": "",
    }
    monkeypatch.setattr(
        economia_exportacao, "buscar_perfil_municipal", lambda *a, **k: linha_perfil
    )

    with caplog.at_level(logging.WARNING):
        economia_exportacao.buscar_comercio_exterior_economia("X", "PB")

    assert caplog.text == ""


def test_saldo_do_mes_vem_de_junho_e_nao_do_ultimo_mes(monkeypatch):
    """A frase do Doc rotula o saldo como "no mês de junho": o par
    analise_balanca1/valor_balanca1 da view (último mês fechado) contradizia o
    card e a Figura, ambos de junho."""
    linha_perfil = {
        "analise_balanca1": "superávit",
        "valor_balanca1": 1.76,
        "valor_balanca1unid": "milhão",
        "valor_balanca_jun": -4961467.0,
    }
    monkeypatch.setattr(
        economia_exportacao, "buscar_perfil_municipal", lambda *a, **k: linha_perfil
    )

    dados = economia_exportacao.buscar_comercio_exterior_economia("Igarassu", "PE")

    # módulo: a palavra já carrega o sinal ("déficit de US$ 4,96 milhões")
    assert dados["analise_balanca1"] == "déficit"
    assert round(dados["valor_balanca1"], 2) == 4.96
    assert dados["valor_balanca1unid"] == "milhões"
    assert dados["analise_balança1"] == "déficit"
    assert dados["valor_balança1unid"] == "milhões"
    assert dados["balanca"] == "déficit"


def test_saldo_do_mes_preserva_o_da_view_sem_coluna_de_junho(monkeypatch):
    linha_perfil = {
        "analise_balanca1": "superávit",
        "valor_balanca1": 1.76,
        "valor_balanca1unid": "milhão",
    }
    monkeypatch.setattr(
        economia_exportacao, "buscar_perfil_municipal", lambda *a, **k: linha_perfil
    )

    dados = economia_exportacao.buscar_comercio_exterior_economia("Igarassu", "PE")

    assert dados["analise_balança1"] == "superávit"
    assert dados["valor_balança1"] == 1.76
