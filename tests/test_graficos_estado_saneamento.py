"""Gráficos de Infraestrutura e Saneamento no relatório por estado (12/11/2026). A
rosca de esgotamento segue a flag uf_distrib_esgoto_2022_completa da matview, como
o Doc estadual. Nenhum teste toca o banco: a consulta ao painel é trocada por falsos."""

from decimal import Decimal
from pathlib import Path

import pytest

from services import graficos_estado_saneamento as saneamento_estado
from services.graficos_estado import gerar_graficos_do_estado
from services.graficos_estado_saneamento import (
    coleta_lixo_do_estado,
    complemento_de_saneamento,
    dinamica_esgoto_do_estado,
    esgotamento_do_estado,
)
from utils.queries import saneamento


def _linha_infraestrutura_paraiba(**overrides: object) -> dict:
    base = {
        "uf_estado": "Paraíba",
        "uf_sigla_uf": "PB",
        "uf_esgoto_rede_2000": Decimal("29.57"),
        "uf_esgoto_rede_2010": Decimal("39.94"),
        "uf_esgoto_rede_2022": Decimal("46.80"),
        "uf_coleta_2010": Decimal("77.67"),
        "uf_coleta_2022": Decimal("84.61"),
        "uf_distrib_esgoto_2022_completa": 0,
    }
    return {**base, **overrides}


# Soma da view do painel para a Paraíba (12/11/2026).
_ESGOTAMENTO_PARAIBA = {
    "esg_total": 1372108,
    "esg_rede_geral_ou_pluvial": 642104,
    "esg_fossa_septica_ou_fossa_filtro": 251638,
    "esg_fossa_rudimentar_ou_buraco": 385912,
    "esg_vala": 40460,
    "esg_rio_lago_corrego_ou_mar": 19340,
    "esg_outra_forma": 22142,
    "esg_nao_tinham_banheiro": 10512,
}


class ConsultaDeEsgotamentoFake:
    """Troca buscar_esgotamento_sanitario_estado: devolve a soma da Paraíba e guarda as siglas."""

    def __init__(self) -> None:
        self.siglas: list[str] = []

    def __call__(self, sigla_uf: str) -> dict:
        self.siglas.append(sigla_uf)
        return dict(_ESGOTAMENTO_PARAIBA)


def test_dinamica_e_coleta_tiram_so_o_prefixo_uf():
    linha = _linha_infraestrutura_paraiba()

    assert dinamica_esgoto_do_estado(linha) == {
        "esgoto_rede_2000": Decimal("29.57"),
        "esgoto_rede_2010": Decimal("39.94"),
        "esgoto_rede_2022": Decimal("46.80"),
    }
    assert coleta_lixo_do_estado(linha) == {"coleta_2010": Decimal("77.67"), "coleta_2022": Decimal("84.61")}


def test_com_distribuicao_incompleta_o_painel_nem_e_consultado(monkeypatch):
    consulta = ConsultaDeEsgotamentoFake()
    monkeypatch.setattr(saneamento_estado, "buscar_esgotamento_sanitario_estado", consulta)

    assert complemento_de_saneamento(_linha_infraestrutura_paraiba()) == {}
    assert consulta.siglas == []


def test_com_distribuicao_completa_o_painel_e_consultado_pela_sigla(monkeypatch):
    consulta = ConsultaDeEsgotamentoFake()
    monkeypatch.setattr(saneamento_estado, "buscar_esgotamento_sanitario_estado", consulta)

    dados = complemento_de_saneamento(_linha_infraestrutura_paraiba(uf_distrib_esgoto_2022_completa=1))

    assert consulta.siglas == ["PB"]
    assert dados["esg_fossa_septica_ou_fossa_filtro"] == 251638


def test_rosca_recusa_distribuicao_incompleta():
    with pytest.raises(ValueError, match="uf_distrib_esgoto_2022_completa=0"):
        esgotamento_do_estado(_linha_infraestrutura_paraiba())


def test_hoje_saem_so_os_dois_graficos_de_barras(tmp_path: Path):
    graficos = gerar_graficos_do_estado(
        "saneamento", _linha_infraestrutura_paraiba(), tmp_path, "estado_para_ba",
        complementos={"saneamento": lambda linha: {}},
    )

    assert list(graficos) == ["grafico_domicilio", "grafico_coleta_lixo"]


def test_com_a_flag_em_1_sai_tambem_a_rosca(tmp_path: Path):
    linha = _linha_infraestrutura_paraiba(uf_distrib_esgoto_2022_completa=1)

    graficos = gerar_graficos_do_estado(
        "saneamento", linha, tmp_path, "estado_para_ba",
        complementos={"saneamento": lambda linha: dict(_ESGOTAMENTO_PARAIBA)},
    )

    assert list(graficos) == ["grafico_domicilio", "grafico_domicilio_por_tipo_esgosto", "grafico_coleta_lixo"]
    assert all((tmp_path / arquivo).is_file() for arquivo in graficos.values())


def test_consulta_estadual_soma_as_7_categorias_pela_sigla(monkeypatch):
    recebidos: list[tuple] = []

    def consulta_fake(sql: str, parametros: tuple, contexto: str) -> dict:
        recebidos.append(parametros)
        return {"esg_total": 1372108, **{coluna: 1 for _, coluna in saneamento.CATEGORIAS_ESGOTAMENTO}}

    monkeypatch.setattr(saneamento, "executar_query_dict", consulta_fake)

    dados = saneamento.buscar_esgotamento_sanitario_estado("PB")

    assert recebidos == [("PB",)]
    assert set(dados) == set(_ESGOTAMENTO_PARAIBA)


def test_consulta_estadual_sem_linhas_devolve_none(monkeypatch):
    monkeypatch.setattr(saneamento, "executar_query_dict", lambda *args: {"esg_total": None})

    assert saneamento.buscar_esgotamento_sanitario_estado("XX") is None
