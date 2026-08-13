import json
import math

import pandas as pd

from utils.ssr import normalizar_para_json


def test_normalizar_para_json_converts_missing_and_non_finite_values_to_none():
    props = {
        "dados": [
            {
                "nan": float("nan"),
                "positivo": float("inf"),
                "negativo": float("-inf"),
                "pandas": pd.NA,
                "valido": 12.5,
            }
        ]
    }

    normalizado = normalizar_para_json(props)

    assert normalizado["dados"][0] == {
        "nan": None,
        "positivo": None,
        "negativo": None,
        "pandas": None,
        "valido": 12.5,
    }
    assert math.isfinite(normalizado["dados"][0]["valido"])
    json.dumps(normalizado, allow_nan=False)
