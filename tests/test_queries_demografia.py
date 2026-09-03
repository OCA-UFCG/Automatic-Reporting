from utils.queries import demografia


def test_buscar_populacao_rua_distinguishes_confirmed_zero_from_no_data(monkeypatch):
    linha_zero = (2026, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    monkeypatch.setattr(
        demografia, "executar_query", lambda *args, **kwargs: [linha_zero]
    )
    resultado = demografia.buscar_populacao_rua("Cidade X", "PB")
    assert resultado is not None
    assert resultado["pop_rua_total"] == 0

    monkeypatch.setattr(demografia, "executar_query", lambda *args, **kwargs: [])
    assert demografia.buscar_populacao_rua("Cidade X", "PB") is None


def test_buscar_populacao_rua_zero_familias_total_nao_gera_zero_division(monkeypatch):
    # pop_rua_2022 presente, pop_rua_2026 ausente, familias_total == 0
    linha_2022 = (2022, 10, 1, 1, 1, 1, 0, 0, 5, 3, 2)

    monkeypatch.setattr(
        demografia, "executar_query", lambda *args, **kwargs: [linha_2022]
    )
    resultado = demografia.buscar_populacao_rua("Cidade X", "PB")

    assert resultado is not None
    assert "pop_rua_2026" not in resultado
    assert resultado["pop_rua_pobreza_per"] == 0.0
    assert resultado["pop_rua_br_per"] == 0.0
    assert resultado["pop_rua_acima_br_per"] == 0.0
