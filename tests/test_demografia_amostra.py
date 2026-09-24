"""Revisão de demografia por amostra: Recife (PE), Cabedelo (PB), Pedra Preta (RN)
e Igarassu (PE).

As quatro cobrem os ramos que o Doc distingue: porte grande/médio/pequeno,
crescimento positivo e negativo, mais idosos ou mais crianças, indígenas com e
sem registro em 2010, quilombolas presentes ou não, população de rua zerada ou
não e 0, 1 ou vários Centros POP.

Os fixtures são snapshots (2026-09-24) — nada aqui toca o banco nem o Google Doc:
- `fixtures/demografia_amostra.json`: a linha do relatório já mesclada (view +
  buscar_*), como services/generation.py a monta;
- `fixtures/doc_demografia_descricao_tema.txt`: o `descricao_tema` do Doc.
Se o Doc mudar, atualize o snapshot junto com as frases esperadas.
"""

import json
import re
from decimal import Decimal
from pathlib import Path

import pytest

from plotting.demografia import (
    gerar_grafico_composicao_cor_raca,
    gerar_grafico_faixa_etaria_e_sexo,
    gerar_grafico_visao_historica_populacao,
)
from utils.queries import demografia
from utils.render.placeholders import (
    interpretar_blocos_condicionais,
    substituir_placeholders,
)

FIXTURES = Path(__file__).parent / "fixtures"
AMOSTRA = {
    cidade: contexto
    for cidade, contexto in json.loads(
        (FIXTURES / "demografia_amostra.json").read_text(encoding="utf-8")
    ).items()
    if not cidade.startswith("_")
}
DOC_DEMOGRAFIA = (FIXTURES / "doc_demografia_descricao_tema.txt").read_text(
    encoding="utf-8"
)
CIDADES = sorted(AMOSTRA)


def _renderizar(cidade: str) -> str:
    contexto = AMOSTRA[cidade]
    texto = interpretar_blocos_condicionais(DOC_DEMOGRAFIA, contexto)
    return substituir_placeholders(texto, contexto, "demografia")


@pytest.mark.parametrize("cidade", CIDADES)
def test_doc_nao_deixa_placeholder_literal(cidade):
    assert re.findall(r"\$[A-Za-z_]\w*", _renderizar(cidade)) == []


@pytest.mark.parametrize("cidade", CIDADES)
def test_doc_nao_deixa_condicionante_no_texto(cidade):
    assert "Para quando" not in _renderizar(cidade)


@pytest.mark.parametrize("cidade", CIDADES)
def test_cada_bloco_condicional_escolhe_um_unico_ramo(cidade):
    # Um ramo a mais duplica o parágrafo; um a menos some com ele.
    texto = _renderizar(cidade)
    assert texto.count("A distribuição por faixa etária permite") == 1
    assert texto.count("Entre 2010 e 2022") == 1
    assert texto.count("Outro grupo relevante para a caracterização") == 1
    assert texto.count("Centro de Referência Especializado") + texto.count(
        "Centros de Referência Especializado"
    ) == 1


@pytest.mark.parametrize(
    ("cidade", "trechos"),
    [
        (
            "Recife (PE)",
            (
                "sendo considerado um município de grande porte",
                "a população com 60 anos ou mais supera em aproximadamente 89.774",
                "apresentou uma redução de 3,17",
                "houve redução de aproximadamente 27,50%",
                "frente a 1.817 pessoas registradas em 2022",
                "contava com 4 Centros de Referência",
            ),
        ),
        (
            "Cabedelo (PB)",
            (
                "sendo considerado um município de médio porte",
                "a população de crianças de até 9 anos supera em aproximadamente 223",
                "apresentou um aumento de 14,80",
                "não foram identificados registros para Cabedelo",
                "contava com um Centro de Referência",
            ),
        ),
        (
            "Pedra Preta (RN)",
            (
                "sendo considerado um município de pequeno porte",
                "a população com 60 anos ou mais supera em aproximadamente 118",
                "apresentou uma redução de 5,75",
                "não foram encontrados registros de pessoas autodeclaradas indígenas e quilombolas",
                "Em 2022 e março de 2026, não havia pessoas registradas",
                "não contava com um Centro de Referência",
            ),
        ),
        (
            "Igarassu (PE)",
            (
                "sendo considerado um município de grande porte",
                "a população de crianças de até 9 anos supera em aproximadamente 1.352",
                "apresentou um aumento de 12,91",
                "houve aumento de aproximadamente 337,80%",
                "frente a 15 pessoas registradas em 2022",
                "não contava com um Centro de Referência",
            ),
        ),
    ],
)
def test_ramos_do_doc_por_cidade(cidade, trechos):
    texto = _renderizar(cidade)
    for trecho in trechos:
        assert trecho in texto


@pytest.mark.parametrize("cidade", CIDADES)
def test_faixa_etaria_citada_no_texto_e_a_do_grafico(cidade):
    # cat_etaria_maior/menor vêm do cálculo local; etaria_*_per vem da view. Os
    # dois precisam falar da mesma faixa que aparece na pirâmide (Figura 2).
    contexto = AMOSTRA[cidade]
    totais = {
        faixa["faixa"]: faixa["mulheres"] + faixa["homens"]
        for faixa in contexto["faixas_etarias_sexo"]
    }
    populacao = contexto["pop_total_2022"]
    assert sum(totais.values()) == populacao

    maior = max(totais, key=totais.get)
    menor = min(totais, key=totais.get)
    assert contexto["cat_etaria_maior"] == maior
    assert contexto["cat_etaria_menor"] == menor
    assert contexto["etaria_maior_per"] == pytest.approx(
        totais[maior] / populacao * 100, abs=0.01
    )
    assert contexto["etaria_menor_per"] == pytest.approx(
        totais[menor] / populacao * 100, abs=0.01
    )


@pytest.mark.parametrize("cidade", CIDADES)
def test_sexo_soma_a_populacao_total(cidade):
    contexto = AMOSTRA[cidade]
    assert contexto["pop_mulher"] + contexto["pop_homem"] == contexto["pop_total_2022"]
    assert contexto["pop_mulher_per"] + contexto["pop_homem_per"] == pytest.approx(100)


@pytest.mark.parametrize(
    "gerar_grafico",
    [
        gerar_grafico_faixa_etaria_e_sexo,
        gerar_grafico_composicao_cor_raca,
        gerar_grafico_visao_historica_populacao,
    ],
)
@pytest.mark.parametrize("cidade", CIDADES)
def test_graficos_da_amostra_sao_gerados(tmp_path: Path, cidade, gerar_grafico):
    # Pedra Preta cobre a ponta pequena: amarela e indígena zeradas no gráfico de
    # cor/raça e a escala "mil" na visão histórica.
    nome = gerar_grafico(AMOSTRA[cidade], tmp_path, "amostra")
    assert (tmp_path / nome).stat().st_size > 0


# --- Regressões dos bugs de código mapeados na revisão ---------------------------


def _linha_rua(ano: int, pessoas: int, familias_bf: int) -> tuple:
    # Colunas de POP_RUA_MUNICIPIO: ano, pessoas, crianças, pcd, idosos, centros
    # POP, famílias, famílias no Bolsa Família, pobreza, baixa renda, acima de ½ SM.
    return (ano, pessoas, 0, 0, 0, 0, familias_bf, familias_bf, 0, 0, 0)


@pytest.mark.parametrize(
    ("pessoas_2022", "pessoas_2026", "analise_pessoas", "analise_bf"),
    [
        (15, 27, "aumento", "aumentou"),  # Igarassu (PE)
        (21, 13, "redução", "diminuiu"),  # Cabedelo (PB)
        (0, 0, "estabilidade", "permaneceu igual"),  # Pedra Preta (RN)
    ],
)
def test_analise_da_populacao_de_rua_usa_os_rotulos_da_view(
    monkeypatch, pessoas_2022, pessoas_2026, analise_pessoas, analise_bf
):
    # Regressão: com ">=" um empate saía "aumento"/"aumentou" onde a view traz
    # "estabilidade"/"permaneceu igual", e o cálculo local sobrescreve a view na
    # mescla de generation.py.
    monkeypatch.setattr(
        demografia,
        "executar_query",
        lambda *args, **kwargs: [
            _linha_rua(2022, pessoas_2022, pessoas_2022),
            _linha_rua(2026, pessoas_2026, pessoas_2026),
        ],
    )
    dados = demografia.buscar_populacao_rua("Cidade", "UF")
    assert dados["var_pop_rua_analise"] == analise_pessoas
    assert dados["pop_rua_bolsaf_analise"] == analise_bf


def test_porte_local_usa_o_mesmo_termo_da_view(monkeypatch):
    # Regressão: o cálculo local dizia "baixo porte" e a view "pequeno porte";
    # no fallback de CSV (sem view) o relatório trocava o termo.
    respostas = iter([[(2022, 2441), (2010, 2590), (2000, 2847)], (Decimal("-0.61"),)])
    monkeypatch.setattr(
        demografia, "executar_query", lambda *args, **kwargs: next(respostas)
    )
    dados = demografia.buscar_populacao_demografia("Pedra Preta", "RN")
    assert dados["porte_mun"] == AMOSTRA["Pedra Preta (RN)"]["porte_mun"]
