from scripts import startup_container


def test_roda_limpeza_e_invalidacao_uma_vez(monkeypatch):
    chamadas = []
    monkeypatch.setattr(startup_container, "limpar_tmp_orfaos", lambda: chamadas.append("tmp") or [])
    monkeypatch.setattr(startup_container, "invalidar_artefatos_em_disco", lambda: chamadas.append("cache"))

    startup_container.main()

    assert chamadas == ["tmp", "cache"]


def test_app_nao_registra_mais_os_hooks_de_startup():
    import main

    nomes = {f.__name__ for f in main.app.router.on_startup}
    assert "_limpar_tmp_orfaos_do_startup" not in nomes
    assert "_invalidar_cache_do_startup" not in nomes
