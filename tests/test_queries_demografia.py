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
