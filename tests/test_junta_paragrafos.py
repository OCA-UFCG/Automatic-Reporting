"""Marcador "[junta com o próximo]" (utils/render/placeholders.py, _MARCADOR_JUNTA):
o próximo parágrafo que sair cola no marcado; sem versão marcada que tenha saído,
ele sai sozinho."""

from utils.render.placeholders import interpretar_blocos_condicionais

DOC = """Para quando $a for igual a 1:
Versão um. [junta com o próximo]

Para quando $a for igual a 2:
Versão dois. [junta com o próximo]

Comparação sem condição.

Para quando $b for maior que 0:
Detalhe opcional.

Fecho."""


def _paragrafos(contexto: dict) -> list[str]:
    return [p for p in interpretar_blocos_condicionais(DOC, contexto).splitlines() if p.strip()]


def test_cola_na_versao_que_saiu_e_nao_mostra_o_marcador():
    assert _paragrafos({"a": 2, "b": 0}) == ["Versão dois. Comparação sem condição.", "Fecho."]


def test_sem_versao_marcada_o_de_baixo_sai_sozinho():
    assert _paragrafos({"a": 3, "b": 0}) == ["Comparação sem condição.", "Fecho."]


def test_so_cola_no_proximo_paragrafo_que_sair_logo_depois():
    # "Detalhe opcional." não é marcado: o "Fecho." sai sozinho com ou sem ele.
    assert _paragrafos({"a": 1, "b": 1}) == [
        "Versão um. Comparação sem condição.",
        "Detalhe opcional.",
        "Fecho.",
    ]


def test_titulo_legenda_e_item_de_lista_nao_sao_colados():
    for de_baixo in ("Síntese", "Figura X – Saldo mensal.", "- Item da lista."):
        saida = interpretar_blocos_condicionais(f"Antes. [junta com o próximo]\n\n{de_baixo}", {})
        assert [p for p in saida.splitlines() if p.strip()] == ["Antes.", de_baixo]


def test_grafico_entre_os_dois_impede_a_colagem():
    doc = "Antes. [junta com o próximo]\n\n*grafico_x\n\nDepois."
    saida = interpretar_blocos_condicionais(doc, {})
    assert [p for p in saida.splitlines() if p.strip()] == ["Antes.", "*grafico_x", "Depois."]
