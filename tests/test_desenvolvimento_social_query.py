from utils.queries.desenvolvimento_social import _categoria_variacao


def test_categoria_variacao_returns_the_word_with_its_article():
    assert _categoria_variacao(0.161) == "um aumento"
    assert _categoria_variacao(-0.05) == "uma diminuição"
    assert _categoria_variacao(0) == "uma estabilidade"


def test_categoria_variacao_handles_missing_or_invalid_values():
    assert _categoria_variacao(None) is None
    assert _categoria_variacao("n/a") is None
