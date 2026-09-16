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
    assert dados["valor_balança1"] == -717.3
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
