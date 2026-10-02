from decimal import Decimal

from utils.formatting import formatar_numero_ptbr
from utils.render.placeholders import _formatar_valor


def test_cinco_na_casa_seguinte_arredonda_para_cima_como_o_sql():
    assert formatar_numero_ptbr(1141.165, decimais=2) == "1.141,17"
    assert formatar_numero_ptbr(Decimal("1141.165"), decimais=2) == "1.141,17"
    assert formatar_numero_ptbr("1141.165", decimais=2) == "1.141,17"
    assert formatar_numero_ptbr(2.675, decimais=2) == "2,68"
    assert formatar_numero_ptbr(-2.675, decimais=2) == "-2,68"
    assert formatar_numero_ptbr(0.5) == "1"
    assert formatar_numero_ptbr(2.5) == "3"
    assert _formatar_valor(Decimal("1141.165"), 2) == "1.141,17"


def test_formato_ptbr_continua_igual():
    assert formatar_numero_ptbr(1234567) == "1.234.567"
    assert formatar_numero_ptbr(62.85, decimais=2) == "62,85"
    assert formatar_numero_ptbr("1.234,5", decimais=1) == "1.234,5"
    assert formatar_numero_ptbr("sem dado") == "sem dado"
    assert formatar_numero_ptbr(float("nan"), decimais=2) == "nan"
    assert formatar_numero_ptbr(1e30, decimais=2).startswith("1.000.000")
