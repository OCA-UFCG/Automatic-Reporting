"""`linhas_base_do_tema`: a linha da view quando existe, senão o CSV (fallback legado).
O harness do relatório congelado proíbe o CSV, então o fallback é coberto aqui."""

import pandas as pd
import pytest
from fastapi import HTTPException

from services import generation

_CSV = pd.DataFrame(
    {
        "nm_mun": ["Arez", "Arez", "Santa Luzia"],
        "sigla_uf": ["RN", "RN", "PB"],
        "saude.taxa": [1.5, 2.5, 3.0],
    }
)


@pytest.fixture
def csv_falso(monkeypatch):
    chamadas = []

    def carregar(fonte):
        chamadas.append(fonte)
        return _CSV

    monkeypatch.setattr(generation, "carregar_csv", carregar)
    monkeypatch.setattr(generation, "get_csv_config_for_macrotema", lambda _d: ("url", "ENV"))
    monkeypatch.setattr(generation, "resolve_csv_source", lambda url, _env: url)
    return chamadas


def test_linha_da_view_com_nome_canonico_sem_tocar_no_csv(csv_falso):
    perfil = {"nm_mun": "RECIFE", "sigla_uf": "PE", "taxa": 1}
    linhas = generation.linhas_base_do_tema("recife (PE)", "saude", {}, perfil)
    assert linhas == [{"nm_mun": "RECIFE (PE)", "sigla_uf": "PE", "taxa": 1}]
    assert perfil["nm_mun"] == "RECIFE"  # não muta a linha da view
    assert csv_falso == []


def test_sem_linha_na_view_cai_no_csv(csv_falso):
    linhas = generation.linhas_base_do_tema("Arez (RN)", "saude", {}, None)
    assert [linha["taxa"] for linha in linhas] == [1.5, 2.5]  # prefixo "saude." sai
    assert csv_falso == ["url"]


def test_cidade_fora_do_csv_e_404(csv_falso):
    with pytest.raises(HTTPException) as erro:
        generation.linhas_base_do_tema("Atlântida (PB)", "saude", {}, None)
    assert erro.value.status_code == 404
