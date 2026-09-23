from utils.queries import saude


def _linha_perfil_saude(**overrides: object) -> tuple:
    base = {
        "dose_aplicada": None,
        "pop_alvo_vacina": None,
        "vacina_maior1": "Pneumo 10",
        "vacina_maior1_per": 88.79,
        "vacina_maior2": "Polio Injetável VIP, reforço",
        "vacina_maior2_per": 81.90,
        "vacina_menor1": "Varicela",
        "vacina_menor1_per": 50.86,
        "vacina_menor2": "Hepatite B em crianças com até 1 dia de vida",
        "vacina_menor2_per": 49.71,
        "vacina_menor3": "Influenza",
        "vacina_menor3_per": 36.25,
        "vacina_meta": "todas",
        "vacina_nao_meta": "nenhuma",
        "obitos": None,
        "nascidos": None,
        "mortalidade_2024": None,
        "mortalidade_2025": None,
        "var_mortalidade_per": None,
        "analise_mortalidade": None,
        "ano_menor_mortalidade": None,
        "media_porte_mortalidade": None,
        "analise_porte_mortalidade": None,
        "mortalidade_brasil": None,
        "analise_mortalidade_brasil": None,
        "estabelecimento_2010": None,
        "estabelecimento_2025": None,
        "analise_estabel_2010_2025": None,
        "var_estabel_2010_2025": None,
        "var_estabel_analise": None,
        "estabel_maior_1": None,
        "nome_estabel_maior_1": None,
        "estabel_maior_2": None,
        "nome_estabel_maior_2": None,
        "estabel_maior_3": None,
        "nome_estabel_maior_3": None,
        "estabel_maior_4": None,
        "nome_estabel_maior_4": None,
        "grupo_estabel_maior1": None,
        "n_estabel_maior1": None,
        "grupo_estabel_maior2": None,
        "n_estabel_maior2": None,
        "ubs_10mil": None,
        "bcg": 96.72,
        "dtp": 80.41,
        "febre_amarela": 68.79,
        "hepatite_a_infantil": 77.69,
        "hepatite_b_30dias": 101.92,
        "hepatite_b_1dia": 51.79,
        "hepatite_b_2dia": 63.84,
        "influenza": 51.09,
        "meningoc": 87.76,
        "meningoc_1reforco": 86.28,
        "penta": 84.30,
        "pneumo10": 94.38,
        "pneumo10_1reforco": 87.14,
        "vip": 82.88,
        "vip_1reforco": 80.28,
        "rotavirus": 87.82,
        "triplice_1dose": 88.57,
        "triplice_2dose": 67.12,
        "varicela": 71.14,
    }
    base.update(overrides)
    return tuple(base.values())


def test_perfil_saude_usa_as_19_colunas_de_vacina_na_serie(monkeypatch):
    monkeypatch.setattr(saude, "executar_query", lambda *a, **k: _linha_perfil_saude())

    dados = saude.buscar_perfil_saude_municipal("Açailândia", "MA")

    serie = dados["cobertura_vacinal_serie"]
    assert len(serie) == 19
    assert {"vacina": "Pneumo 10", "cobertura_vacinal": 94.38} in serie
    assert {"vacina": "Varicela", "cobertura_vacinal": 71.14} in serie
    # Os antigos destaques (vacina_maior/menor) não devem virar itens da série.
    nomes = {item["vacina"] for item in serie}
    assert "Polio Injetável VIP, reforço" not in nomes


def test_perfil_saude_remove_espaco_antes_da_virgula_em_vacina_nao_meta(monkeypatch):
    # Regressão: a view às vezes traz nomes de vacina com espaço sobrando
    # antes da vírgula que separa a lista ("Meningo C ,"), saindo cru no
    # texto do relatório.
    monkeypatch.setattr(
        saude,
        "executar_query",
        lambda *a, **k: _linha_perfil_saude(
            vacina_nao_meta="1° reforço de Meningo C , 1° reforço de Pneumo 10 , Varicela"
        ),
    )

    dados = saude.buscar_perfil_saude_municipal("Açailândia", "MA")

    assert dados["vacina_nao_meta"] == (
        "1° reforço de Meningo C, 1° reforço de Pneumo 10, Varicela"
    )


def test_perfil_saude_ignora_vacina_sem_valor(monkeypatch):
    monkeypatch.setattr(
        saude, "executar_query", lambda *a, **k: _linha_perfil_saude(varicela=None)
    )

    dados = saude.buscar_perfil_saude_municipal("Açailândia", "MA")

    serie = dados["cobertura_vacinal_serie"]
    assert len(serie) == 18
    assert all(item["vacina"] != "Varicela" for item in serie)
