from scripts import startup_container


def test_roda_limpeza_e_invalidacao_uma_vez(monkeypatch):
    chamadas = []
    monkeypatch.setattr(startup_container, "limpar_tmp_orfaos", lambda: chamadas.append("tmp") or [])
    monkeypatch.setattr(startup_container, "invalidar_artefatos_em_disco", lambda: chamadas.append("cache"))

    startup_container.main()

    assert chamadas == ["tmp", "cache"]


def test_on_startup_fica_so_com_ssr_e_aviso_de_mv_indicadores():
    import main

    # Pina o conjunto inteiro, não só a ausência dos dois hooks removidos: um
    # regression que esvaziasse on_startup ou derrubasse start_ssr_server também
    # devia falhar aqui. `start_ssr_server` é alias de import
    # (`from utils.ssr import start_server as start_ssr_server`); o objeto função
    # carrega o __name__ original do módulo de origem, "start_server" — não o nome
    # do alias.
    nomes = {f.__name__ for f in main.app.router.on_startup}
    assert nomes == {"start_server", "_avisar_se_mv_indicadores_faltar"}
