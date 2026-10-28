import json
import math
from datetime import UTC, date, datetime
from decimal import Decimal

import pandas as pd

from utils.json_tipado import codificar, decodificar


def _ida_e_volta(valor):
    return decodificar(json.loads(json.dumps(codificar(valor), ensure_ascii=False)))


def test_tipos_voltam_iguais():
    original = {
        "decimal": Decimal("1.50"),
        "data": date(2022, 8, 1),
        "momento": datetime(2026, 10, 28, 4, 10, tzinfo=UTC),
        "serie": [(2010, Decimal("3.2")), (2022, None)],
        "texto": "Alcântara (MA)",
        "inteiro": 7,
    }
    volta = _ida_e_volta(original)
    assert volta == original
    assert type(volta["decimal"]) is Decimal and str(volta["decimal"]) == "1.50"
    assert type(volta["momento"]) is datetime
    assert type(volta["serie"][0]) is tuple


def test_linha_do_csv_volta_igual():
    # Fallback do CSV: a linha vem de df.to_dict("records"), com NaN nas células vazias.
    linha = pd.DataFrame({"nm_mun": ["Arez (RN)"], "pop": [12_000], "taxa": [float("nan")]}).to_dict(
        "records"
    )[0]
    volta = _ida_e_volta(linha)
    assert volta["nm_mun"] == "Arez (RN)" and volta["pop"] == 12_000
    assert math.isnan(volta["taxa"])
