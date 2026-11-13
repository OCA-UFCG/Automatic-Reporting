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

Para quando economia.$saldo_acumulado_ano_anterior for maior que 0:
Variação de economia.$variacao_acumulado_per:1%.

Para quando economia.$saldo_acumulado_ano_anterior for menor ou igual a 0:
Ante economia.$saldo_acumulado_ano_anterior.

Para quando economia.$movimentacoes_tri_atual for maior ou igual a 30:
Setores: economia.$setores_saldo_lista.

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
