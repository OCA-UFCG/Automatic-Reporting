from utils.queries import hidraulica


def test_buscar_tecnologias_acesso_agua_calcula_indicadores_historicos(monkeypatch):
    linhas = [
        (2010, 439, 439, 0, 0),
        (2020, 1841, 1500, 341, 0),
        (2025, 2038, 1600, 438, 0),
    ]

    monkeypatch.setattr(
        hidraulica, "executar_query", lambda *args, **kwargs: linhas
    )
    resultado = hidraulica.buscar_tecnologias_acesso_agua("Cidade X", "PB")

    assert resultado is not None
    assert resultado["tecnologias_acesso_agua_serie"] == [
        {"ano": 2010, "total": 439},
        {"ano": 2020, "total": 1841},
        {"ano": 2025, "total": 2038},
    ]
    assert resultado["total_2010"] == 439
    assert resultado["total_2020"] == 1841
    assert resultado["total_2025"] == 2038
    assert resultado["acrescimo_qtd"] == 1599
    assert resultado["var_total_per"] == round(1599 / 439 * 100, 2)
    # Segunda década (2020-2025) cresceu menos que a primeira (2010-2020)
    assert resultado["dec_concentracao"] == "2010 a 2020"
    assert resultado["dec_concentracao_per"] == round(1402 / 1599 * 100, 2)

    # Finalidade calculada com base no último ano disponível (2025)
    assert resultado["primeira_agua_qtd"] == 1600
    assert resultado["primeira_agua_per"] == round(1600 / 2038 * 100, 2)
    assert resultado["segunda_agua_qtd"] == 438
    assert resultado["segunda_agua_per"] == round(438 / 2038 * 100, 2)
    assert resultado["sol_predom"] == "abastecimento humano (1ª água)"
    assert resultado["sol_predom_per"] == resultado["primeira_agua_per"]


def test_buscar_tecnologias_acesso_agua_predominio_de_segunda_agua(monkeypatch):
    linhas = [(2025, 1000, 200, 800, 0)]

    monkeypatch.setattr(
        hidraulica, "executar_query", lambda *args, **kwargs: linhas
    )
    resultado = hidraulica.buscar_tecnologias_acesso_agua("Cidade X", "PB")

    assert resultado is not None
    assert resultado["sol_predom"] == "irrigação e dessedentação de animais (2ª água)"
    assert resultado["empate_finalidade"] == 0
    assert resultado["sol_predom_per"] == resultado["segunda_agua_per"] == 80.0


def test_buscar_tecnologias_acesso_agua_sem_ano_inicial_nao_calcula_variacao(monkeypatch):
    linhas = [(2020, 1841, 1500, 341, 0), (2025, 2038, 1600, 438, 0)]

    monkeypatch.setattr(
        hidraulica, "executar_query", lambda *args, **kwargs: linhas
    )
    resultado = hidraulica.buscar_tecnologias_acesso_agua("Cidade X", "PB")

    assert resultado is not None
    assert resultado["total_2020"] == 1841
    assert resultado["total_2025"] == 2038
    assert "total_2010" not in resultado
    assert "acrescimo_qtd" not in resultado
    assert "var_total_per" not in resultado


def test_buscar_tecnologias_acesso_agua_expoe_cisternas_escolares(monkeypatch):
    # Parari (PB), 2025: 394 = 389 (1ª água) + 0 (2ª água) + 5 escolares. Sem as
    # escolares no contexto, o texto dizia "Desse total, 389... e 0..." e a
    # conta não fechava.
    linhas = [(2025, 394, 389, 0, 5)]

    monkeypatch.setattr(
        hidraulica, "executar_query", lambda *args, **kwargs: linhas
    )
    resultado = hidraulica.buscar_tecnologias_acesso_agua("Parari", "PB")

    assert resultado is not None
    assert resultado["escolares_qtd"] == 5
    assert resultado["escolares_per"] == round(5 / 394 * 100, 2)
    assert (
        resultado["primeira_agua_qtd"]
        + resultado["segunda_agua_qtd"]
        + resultado["escolares_qtd"]
        == resultado["total_2025"]
    )
    assert resultado["sol_predom"] == "abastecimento humano (1ª água)"


def test_buscar_tecnologias_acesso_agua_so_escolares(monkeypatch):
    # Marajá do Sena (MA), 2025: as 12 tecnologias são escolares. O Doc escolhe
    # o parágrafo por primeira_agua_qtd = segunda_agua_qtd = 0.
    linhas = [(2025, 12, 0, 0, 12)]

    monkeypatch.setattr(
        hidraulica, "executar_query", lambda *args, **kwargs: linhas
    )
    resultado = hidraulica.buscar_tecnologias_acesso_agua("Marajá do Sena", "MA")

    assert resultado is not None
    assert resultado["escolares_qtd"] == 12
    assert resultado["escolares_per"] == 100.0
    assert resultado["primeira_agua_qtd"] == resultado["segunda_agua_qtd"] == 0


def test_buscar_tecnologias_acesso_agua_empate_nao_tem_predominancia(monkeypatch):
    # Jijoca de Jericoacoara (CE), 2025: 10 de 1ª água e 10 de 2ª. O Doc dizia
    # "com predominância ... 50%". sol_predom_per continua preenchido: a
    # abertura do tema depende dele; a Síntese escolhe a frase pelo empate.
    linhas = [(2025, 20, 10, 10, 0)]

    monkeypatch.setattr(
        hidraulica, "executar_query", lambda *args, **kwargs: linhas
    )
    resultado = hidraulica.buscar_tecnologias_acesso_agua("Jijoca de Jericoacoara", "CE")

    assert resultado is not None
    assert resultado["empate_finalidade"] == 1
    assert resultado["sol_predom_per"] == 50.0
    assert resultado["primeira_agua_per"] == resultado["segunda_agua_per"] == 50.0


def test_buscar_tecnologias_acesso_agua_so_escolares_nao_e_empate(monkeypatch):
    # 0 de 1ª e 0 de 2ª água (Marajá do Sena/MA) não é empate: o Doc tem frase
    # própria para quem só tem cisternas escolares.
    linhas = [(2025, 12, 0, 0, 12)]

    monkeypatch.setattr(
        hidraulica, "executar_query", lambda *args, **kwargs: linhas
    )
    resultado = hidraulica.buscar_tecnologias_acesso_agua("Marajá do Sena", "MA")

    assert resultado is not None
    assert resultado["empate_finalidade"] == 0
    assert resultado["sol_predom_per"] == 0


def test_buscar_tecnologias_acesso_agua_sem_dados_retorna_none(monkeypatch):
    monkeypatch.setattr(hidraulica, "executar_query", lambda *args, **kwargs: [])
    assert hidraulica.buscar_tecnologias_acesso_agua("Cidade X", "PB") is None


def test_consulta_casa_por_cd_mun_e_limita_ano(monkeypatch):
    # Em 30/09 a tabela de cisternas foi recriada só com cd_mun (sem nm_mun/
    # sigla_uf); o nome/UF vêm de carac_mun, como no PIB. A tabela passou a ter
    # 2026, mas o Doc e a legenda dizem "até 2025".
    capturado = {}

    def falso(sql, params, *args, **kwargs):
        capturado["sql"], capturado["params"] = sql, params
        return [(2025, 20, 10, 10, 0)]

    monkeypatch.setattr(hidraulica, "executar_query", falso)
    hidraulica.buscar_tecnologias_acesso_agua("Assú", "RN")

    sql = " ".join(capturado["sql"].split())
    assert "JOIN carac_mun.caracteristicas_municipais c ON c.cd_mun::int = t.cd_mun::int" in sql
    assert "LOWER(c.nm_mun) = LOWER(%s)" in sql and "c.sigla_uf = %s" in sql
    assert "t.nm_mun" not in sql and "t.sigla_uf" not in sql
    assert "t.ano <= %s" in sql
    assert capturado["params"] == ("Assú", "RN", 2025)
