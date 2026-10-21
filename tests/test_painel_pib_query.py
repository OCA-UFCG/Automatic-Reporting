import pytest
from fastapi.testclient import TestClient

import main
from utils.queries import painel_pib

# (ano, pib_total, populacao_implicita, vab_agro, vab_ind, vab_serv, vab_adm)
# vab_* já chegam em reais: a conversão de milhares é feita no SQL.
SERIE = [
    (2021, 80e9, 4_000_000.0, 5e9, 15e9, 40e9, 12e9),
    (2023, 90e9, 4_500_000.0, None, None, None, None),
]
# (ano, atividade_maior_vab, municipios, vab_setor_maior, pib_total)
ATIVIDADES = [(2021, "Demais serviços", 3, 20e9, 50e9)]
UFS = [("PB",), ("PE",)]
MUNICIPIOS = [(2504009, "Campina Grande")]


class VwPibFake:
    """Substitui executar_query: responde cada consulta do painel pelo SQL e
    guarda (sql, params) para checar o filtro montado."""

    def __init__(self, falhar: bool = False):
        self.falhar = falhar
        self.chamadas = []

    def __call__(self, query, params, contexto_erro, buscar_todas=False):
        self.chamadas.append((query, params))
        if self.falhar:
            return None
        if "atividade_maior_vab," in query:
            return ATIVIDADES
        if "DISTINCT sigla_uf" in query:
            return UFS
        if "DISTINCT btrim(cd_mun" in query:
            return MUNICIPIOS
        return SERIE


@pytest.fixture
def vw_pib(monkeypatch):
    fake = VwPibFake()
    monkeypatch.setattr(painel_pib, "executar_query", fake)
    return fake


def test_validar_recorte_usa_area_padrao():
    assert painel_pib.validar_recorte(None, None, None) == painel_pib.RecortePib()


@pytest.mark.parametrize(
    ("area", "uf", "municipio", "mensagem"),
    [
        ("ne; DROP TABLE x", None, None, "Área"),
        ("ne", "pb", None, "UF"),
        ("ne", "PB", "25a", "Município"),
    ],
)
def test_validar_recorte_recusa_valor_fora_do_formato(area, uf, municipio, mensagem):
    with pytest.raises(painel_pib.RecorteInvalido, match=mensagem):
        painel_pib.validar_recorte(area, uf, municipio)


def test_buscar_painel_pib_calcula_per_capita_e_separa_vab(vw_pib):
    painel = painel_pib.buscar_painel_pib(painel_pib.validar_recorte("ne", "PB", None))

    assert painel["serie"][0] == {"ano": 2021, "pib_total": 80e9, "pib_per_capita": 20_000.0}
    assert [vab["ano"] for vab in painel["vab"]] == [2021]
    assert painel["atividades"][0]["participacao_pib"] == pytest.approx(0.4)
    assert painel["opcoes"]["municipios"] == [{"codigo": 2504009, "nome": "Campina Grande"}]


def test_filtro_usa_coluna_da_area_e_parametros_para_uf_e_municipio(vw_pib):
    painel_pib.buscar_painel_pib(painel_pib.validar_recorte("semi_21", "PB", "2504009"))

    sql_serie, params_serie = vw_pib.chamadas[0]
    assert "semi_21 = 'Sim'" in sql_serie
    assert params_serie == ("PB", "2504009")
    sql_ufs, params_ufs = next(c for c in vw_pib.chamadas if "DISTINCT sigla_uf" in c[0])
    assert "sigla_uf = %s" not in sql_ufs
    assert params_ufs == ()


def test_sem_uf_nao_lista_municipios(vw_pib):
    painel = painel_pib.buscar_painel_pib(painel_pib.RecortePib())

    assert painel["opcoes"]["municipios"] == []
    assert not any("DISTINCT btrim(cd_mun" in sql for sql, _ in vw_pib.chamadas)


def test_buscar_painel_pib_devolve_none_quando_banco_falha(monkeypatch):
    monkeypatch.setattr(painel_pib, "executar_query", VwPibFake(falhar=True))

    assert painel_pib.buscar_painel_pib(painel_pib.RecortePib()) is None


def test_endpoint_painel_pib_responde_422_para_area_invalida():
    resposta = TestClient(main.app).get("/paineis/pib", params={"area": "x"})

    assert resposta.status_code == 422
    assert "Área" in resposta.json()["detail"]


def test_endpoint_painel_pib_responde_503_sem_banco(monkeypatch):
    monkeypatch.setattr(main, "buscar_painel_pib", lambda recorte: None)

    resposta = TestClient(main.app).get("/paineis/pib")

    assert resposta.status_code == 503


def test_endpoint_painel_pib_repassa_recorte(monkeypatch):
    recebidos = []
    monkeypatch.setattr(main, "buscar_painel_pib", lambda recorte: recebidos.append(recorte) or {})

    resposta = TestClient(main.app).get("/paineis/pib", params={"area": "ne", "uf": "PB"})

    assert resposta.status_code == 200
    assert recebidos == [painel_pib.RecortePib("ne", "PB", None)]
