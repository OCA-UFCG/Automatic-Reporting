from decimal import Decimal
from pathlib import Path

import pytest

from plotting.economia_renda import gerar_grafico_visao_mensal
from utils.queries import economia_caged
from utils.render.placeholders import (
    conferir_condicoes,
    interpretar_blocos_condicionais,
    substituir_placeholders,
)


def _linha_mv(**extra) -> dict:
    # Como a matview devolve: somas em numeric (Decimal), anos em texto, meses do
    # ano atual depois do trimestre de referência em NULL.
    linha = {
        "cd_mun": 2611101, "nm_mun": "Petrolina", "sigla_uf": "PE",
        "tri_atual1": "segundo", "ano_atual": "2026", "tri_anterior1": "primeiro",
        "ano_tri_anterior": "2026", "ano_anterior": "2025", "ultimo_mes_tri": "junho",
        "admissao_tri_atual": Decimal(15260), "desligamento_tri_atual": Decimal(13789),
        "saldo_tri_atual": Decimal(1471), "movimentacoes_tri_atual": Decimal(29049),
        "analise_saldo_tri_atual": "positivo",
        "saldo_tri_anterior": Decimal(2352), "analise_saldo_tri_anterior": "positivo",
        "saldo_tri_ano_anterior": Decimal(1847), "analise_saldo_tri_ano_anterior": "positivo",
        "saldo_acumulado_ano_atual": Decimal(3823), "saldo_acumulado_ano_anterior": Decimal(2049),
        "variacao_acumulado_per": Decimal("86.6"),
        "setores_saldo_lista": "serviços (+1.010), construção (+338) e agricultura (-53)",
    }
    for mes in range(1, 13):
        linha[f"saldo_mes{mes:02d}_ano_anterior"] = Decimal(mes * 10)
        linha[f"saldo_mes{mes:02d}_ano_atual"] = Decimal(mes * 20) if mes <= 6 else None
    linha.update(extra)
    return linha


def test_buscar_tira_identificacao_e_monta_serie_ate_o_fim_do_trimestre(monkeypatch):
    monkeypatch.setattr(economia_caged, "executar_query_dict", lambda *a, **k: _linha_mv())

    dados = economia_caged.buscar_caged_municipal("Petrolina (PE)", "PE")

    # nm_mun da matview não pode sobrescrever o "Cidade (UF)" canonicalizado.
    assert "nm_mun" not in dados and "cd_mun" not in dados and "sigla_uf" not in dados
    assert dados["saldo_tri_atual"] == 1471
    assert [mes for mes, _ant, _atual in dados["caged_serie_mensal"]] == [
        "jan", "fev", "mar", "abr", "mai", "jun",
    ]
    assert dados["caged_serie_mensal"][0] == ("jan", Decimal(10), Decimal(20))


def test_serie_mensal_nao_corta_em_mes_sem_movimentacao(monkeypatch):
    # Mês sem movimentação também é NULL na matview; a série vai até ultimo_mes_tri.
    linha = _linha_mv(saldo_mes02_ano_atual=None, saldo_mes01_ano_anterior=None)
    monkeypatch.setattr(economia_caged, "executar_query_dict", lambda *a, **k: linha)

    serie = economia_caged.buscar_caged_municipal("Petrolina", "PE")["caged_serie_mensal"]

    assert len(serie) == 6
    assert serie[0] == ("jan", 0, Decimal(20))
    assert serie[1] == ("fev", Decimal(20), 0)


def _consultas(principal: dict | None, detalhe: dict | None):
    """executar_query_dict falso: devolve a linha certa para cada matview."""
    def executar(query, _params, _contexto):
        return detalhe if "mv_caged_municipal_detalhe" in query else principal
    return executar


def test_ocupacoes_saem_com_titulo_oficial_da_cbo(monkeypatch):
    detalhe = {
        "nm_mun": "Petrolina", "cd_mun": 2611101, "sigla_uf": "PE",
        "escolaridade_maior_saldo": "ensino médio completo",
        "escolaridade_maior_saldo_postos": Decimal(900),
        # Como a base grava: sem acento e com marca de cadastro.
        "ocupacao_maior_saldo1": "alimentador de linha de producao",
        "ocupacao_maior_saldo1_cbo": "784205", "ocupacao_maior_saldo1_valor": Decimal(40),
        "ocupacao_maior_saldo2": "faxineiro (desativado em 2010)",
        "ocupacao_maior_saldo2_cbo": "514320", "ocupacao_maior_saldo2_valor": Decimal(30),
        # Código fora da lista oficial de 2002: fica o nome da base.
        "ocupacao_maior_saldo3": "massoterapeuta",
        "ocupacao_maior_saldo3_cbo": "322120", "ocupacao_maior_saldo3_valor": Decimal(5),
        "ocupacao_maior_saldo4": None, "ocupacao_maior_saldo4_cbo": None,
        "ocupacao_maior_saldo4_valor": Decimal(0),
    }
    monkeypatch.setattr(economia_caged, "executar_query_dict", _consultas(_linha_mv(), detalhe))

    dados = economia_caged.buscar_caged_municipal("Petrolina (PE)", "PE")

    assert dados["ocupacao_maior_saldo1"] == "alimentador de linha de produção"
    assert dados["ocupacao_maior_saldo2"] == "faxineiro"
    assert dados["ocupacao_maior_saldo3"] == "massoterapeuta"
    assert dados["ocupacao_maior_saldo4"] is None
    assert dados["escolaridade_maior_saldo"] == "ensino médio completo"
    assert dados["saldo_tri_atual"] == 1471  # a linha principal continua lá
    assert "nm_mun" not in dados


def test_sem_matview_de_detalhe_os_marcadores_principais_continuam(monkeypatch):
    monkeypatch.setattr(economia_caged, "executar_query_dict", _consultas(_linha_mv(), None))

    dados = economia_caged.buscar_caged_municipal("Petrolina (PE)", "PE")

    assert dados["saldo_tri_atual"] == 1471
    assert "ocupacao_maior_saldo1" not in dados


def test_buscar_sem_linha_ou_sem_uf_devolve_none(monkeypatch):
    monkeypatch.setattr(economia_caged, "executar_query_dict", lambda *a, **k: None)
    assert economia_caged.buscar_caged_municipal("Petrolina", "PE") is None
    assert economia_caged.buscar_caged_municipal("Petrolina", "") is None


def test_grafico_visao_mensal_gera_png(tmp_path: Path):
    cidade = {
        "ano_anterior": "2025", "ano_atual": "2026",
        "caged_serie_mensal": [("jan", 100, -50), ("fev", -20, 300)],
    }
    arquivo = gerar_grafico_visao_mensal(cidade, tmp_path, "petrolina_pe")
    assert arquivo == "grafico_visao_mensal_petrolina_pe.png"
    assert (tmp_path / arquivo).is_file()


def test_grafico_visao_mensal_exige_serie_com_algum_saldo():
    with pytest.raises(ValueError):
        gerar_grafico_visao_mensal({}, Path("/tmp"), "sem_dados")
    with pytest.raises(ValueError):
        gerar_grafico_visao_mensal(
            {"caged_serie_mensal": [("jan", 0, 0), ("fev", 0, 0)]}, Path("/tmp"), "zerado"
        )


# Trecho do Doc aprovado em 12/11/2026 (texto-caged.txt), reduzido às regras que
# escolhem a versão de cada parágrafo.
_DOC = """Para quando economia.$saldo_tri_atual for diferente de 0:
Saldo economia.$analise_saldo_tri_atual: economia.$saldo_tri_atual.

Para quando economia.$saldo_tri_atual for igual a 0 e economia.$movimentacoes_tri_atual for maior que 0:
Saldo nulo.

Para quando economia.$movimentacoes_tri_atual for igual a 0:
Sem movimentação.

Para quando economia.$saldo_acumulado_ano_anterior for maior ou igual a 30:
Variação de economia.$variacao_acumulado_per:1%.

Para quando economia.$saldo_acumulado_ano_anterior for menor que 30:
Ante economia.$saldo_acumulado_ano_anterior.

Para quando economia.$movimentacoes_tri_atual for maior ou igual a 30:
Setores: economia.$setores_saldo_lista.

Para quando economia.$movimentacoes_tri_atual for maior ou igual a 30 e economia.$escolaridade_maior_saldo_postos for maior que 0 e economia.$escolaridade_menor_saldo_postos for maior que 0:
Escolaridade: +economia.$escolaridade_maior_saldo_postos e -economia.$escolaridade_menor_saldo_postos.

Para quando economia.$movimentacoes_tri_atual for maior ou igual a 30 e economia.$escolaridade_maior_saldo_postos for maior que 0 e economia.$escolaridade_menor_saldo_postos for igual a 0:
Escolaridade só positiva.

Para quando economia.$movimentacoes_tri_atual for maior ou igual a 30 e economia.$ocupacao_maior_saldo4_valor for maior que 0:
Ocupações: economia.$ocupacao_maior_saldo1.

Para quando economia.$movimentacoes_tri_atual for menor que 30 e economia.$movimentacoes_tri_atual for maior que 0:
Poucas movimentações.
"""


def _render(**extra) -> str:
    contexto = _linha_mv(**extra)
    texto = interpretar_blocos_condicionais(_DOC, contexto)
    return substituir_placeholders(texto, contexto, "economia-renda")


def test_regras_do_doc_sao_reconhecidas():
    assert conferir_condicoes(_DOC) == []


def test_municipio_grande_com_saldo_positivo():
    saida = _render()
    assert "Saldo positivo: 1.471." in saida
    assert "Variação de 86,6%." in saida
    assert "Setores: serviços (+1.010)" in saida
    assert "Saldo nulo" not in saida and "Sem movimentação" not in saida
    assert "Ante" not in saida and "Poucas" not in saida


def test_acumulado_do_ano_anterior_negativo_nao_mostra_percentual():
    saida = _render(saldo_acumulado_ano_anterior=Decimal(-508), variacao_acumulado_per=None)
    assert "Ante -508." in saida
    assert "Variação" not in saida


def test_acumulado_do_ano_anterior_pequeno_nao_mostra_percentual():
    # Passagem (PB): de 1 para -5 virava "variação de -600,0%" (revisão 13/11).
    saida = _render(saldo_acumulado_ano_anterior=Decimal(1), variacao_acumulado_per=Decimal("-600.0"))
    assert "Ante 1." in saida
    assert "Variação" not in saida


def test_saldo_nulo_com_poucas_movimentacoes():
    saida = _render(saldo_tri_atual=Decimal(0), movimentacoes_tri_atual=Decimal(12),
                    analise_saldo_tri_atual="nulo")
    assert "Saldo nulo." in saida and "Poucas movimentações." in saida
    assert "Setores" not in saida and "Saldo positivo" not in saida


def test_sem_movimentacao_no_trimestre():
    saida = _render(saldo_tri_atual=Decimal(0), movimentacoes_tri_atual=Decimal(0),
                    analise_saldo_tri_atual="nulo")
    assert "Sem movimentação." in saida
    assert "Saldo nulo" not in saida and "Poucas" not in saida


def test_escolaridade_e_ocupacoes_escolhem_a_versao_certa():
    base = {"escolaridade_maior_saldo_postos": Decimal(900), "ocupacao_maior_saldo1": "faxineiro",
            "ocupacao_maior_saldo4_valor": Decimal(3)}
    saida = _render(**base, escolaridade_menor_saldo_postos=Decimal(12))
    assert "Escolaridade: +900 e -12." in saida and "Ocupações: faxineiro." in saida
    assert "só positiva" not in saida

    saida = _render(**base, escolaridade_menor_saldo_postos=Decimal(0))
    assert "Escolaridade só positiva." in saida and "Escolaridade: +" not in saida

    # Menos de 4 ocupações positivas: a frase das 4 ocupações não sai.
    saida = _render(**{**base, "ocupacao_maior_saldo4_valor": Decimal(0)},
                    escolaridade_menor_saldo_postos=Decimal(12))
    assert "Ocupações" not in saida


def test_titulos_cbo_tem_codigos_com_zero_a_esquerda():
    # A matview faz lpad(cd_cbo, 6, '0'): o CAGED grava 10105, a lista oficial 010105.
    assert economia_caged._titulos_cbo()["010105"] == "Oficial general da aeronáutica"


def test_titulos_cbo_sem_espaco_duplo():
    # A lista oficial grava "Cortador de calçados, a  máquina (...)" (dois espaços).
    titulos = economia_caged._titulos_cbo()
    assert not [t for t in titulos.values() if "  " in t]
    assert titulos["764105"].startswith("Cortador de calçados, a máquina")
