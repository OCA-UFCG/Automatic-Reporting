from fastapi.testclient import TestClient

import main
from utils.queries import painel_pib

# (uf, ano, pib_total, populacao_implicita, vab_agro, vab_ind, vab_serv, vab_adm, impostos)
# vab_*/impostos já chegam em reais: a conversão de milhares é feita no SQL.
LINHAS_BANCO = [
    ("PB", 2022, 80_000_000_000.0, 4_000_000.0, 5e9, 15e9, 40e9, 12e9, 8e9),
    ("AL", 2022, 70_000_000_000.0, 3_500_000.0, 6e9, 10e9, 38e9, 9e9, 7e9),
    ("PB", 2023, 90_000_000_000.0, 4_050_000.0, None, None, None, None, None),
]


class ExecutarQueryFake:
    """Substitui executar_query: devolve linhas fixas e guarda a última chamada."""

    def __init__(self, linhas):
        self.linhas = linhas
        self.chamadas = []

    def __call__(self, query, params, contexto_erro, buscar_todas=False):
        self.chamadas.append((query, params, buscar_todas))
        return self.linhas


def test_buscar_pib_por_uf_mapeia_colunas(monkeypatch):
    fake = ExecutarQueryFake(LINHAS_BANCO)
    monkeypatch.setattr(painel_pib, "executar_query", fake)

    linhas = painel_pib.buscar_pib_por_uf()

    assert linhas[0]["uf"] == "PB"
    assert linhas[0]["populacao_implicita"] == 4_000_000.0
    assert fake.chamadas[0][2] is True


def test_buscar_pib_por_uf_devolve_none_quando_banco_falha(monkeypatch):
    monkeypatch.setattr(painel_pib, "executar_query", ExecutarQueryFake(None))

    assert painel_pib.buscar_pib_por_uf() is None


def test_montar_painel_pib_calcula_per_capita_e_listas(monkeypatch):
    monkeypatch.setattr(painel_pib, "executar_query", ExecutarQueryFake(LINHAS_BANCO))

    painel = painel_pib.montar_painel_pib(painel_pib.buscar_pib_por_uf())

    assert painel["anos"] == [2022, 2023]
    assert painel["ufs"] == ["AL", "PB"]
    primeiro = painel["registros"][0]
    assert primeiro["pib_per_capita"] == 20_000.0
    assert primeiro["vab"]["servicos"] == 40e9
    assert painel["registros"][2]["vab"]["agropecuaria"] is None


def test_montar_painel_pib_sem_populacao_nao_divide_por_zero():
    linha = dict(zip(painel_pib._COLUNAS, ("PB", 2022, 1e9, 0, *[None] * 5)))

    painel = painel_pib.montar_painel_pib([linha])

    assert painel["registros"][0]["pib_per_capita"] is None


def test_endpoint_painel_pib_responde_503_sem_banco(monkeypatch):
    monkeypatch.setattr(main, "buscar_pib_por_uf", lambda: None)

    resposta = TestClient(main.app).get("/paineis/pib")

    assert resposta.status_code == 503


def test_endpoint_painel_pib_devolve_json(monkeypatch):
    monkeypatch.setattr(main, "buscar_pib_por_uf", list)

    resposta = TestClient(main.app).get("/paineis/pib")

    assert resposta.status_code == 200
    assert resposta.json()["registros"] == []
