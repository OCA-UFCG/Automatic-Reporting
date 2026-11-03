"""Rede de segurança da extração de gerar_relatorio_handler: dados do banco e Docs
congelados (tests/fixtures/relatorio_congelado/) alimentam o handler de verdade, e as
props entregues ao SSR têm que ser byte a byte as gravadas em esperado/.

Quando a mudança de saída é proposital: ATUALIZAR_RELATORIO_CONGELADO=1 regrava o
esperado (e revise o diff). Para trocar dados/Docs, scripts/gravar_relatorio_congelado.py.
"""

import json
import os
import re

import pytest

from tests.relatorio_congelado import (
    CASOS,
    FIXTURES,
    buscar_do_replay,
    carregar_dados_gravados,
    carregar_doc_do_replay,
    instalar_ambiente,
    props_do_relatorio,
)


def _props(cidade, macrotema, monkeypatch, tmp_path) -> str:
    capturadas = instalar_ambiente(
        monkeypatch.setattr,
        tmp_path,
        buscar_do_replay(carregar_dados_gravados()),
        carregar_doc_do_replay(),
    )
    return props_do_relatorio(cidade, macrotema, capturadas)


@pytest.mark.parametrize("caso, cidade, macrotema", CASOS)
def test_relatorio_congelado_igual_ao_esperado(caso, cidade, macrotema, monkeypatch, tmp_path):
    props = _props(cidade, macrotema, monkeypatch, tmp_path)
    esperado = FIXTURES / "esperado" / f"{caso}.json"
    if os.environ.get("ATUALIZAR_RELATORIO_CONGELADO"):
        esperado.write_text(props, encoding="utf-8")
    assert props == esperado.read_text(encoding="utf-8")


def test_relatorio_congelado_nao_esta_vazio(monkeypatch, tmp_path):
    # Marcos que só aparecem se dados e Docs passaram de verdade pelo pipeline; sem eles
    # um esperado gravado vazio passaria para sempre.
    alcantara = json.loads(_props("Alcântara (MA)", "demografia", monkeypatch, tmp_path))
    assert alcantara["dados"][0]["pop_qui"] == 15608
    assert alcantara["dados"][0]["pop_rua_2026"] == 1
    assert len(alcantara["cover"]["macrotemas"]) == 1
    assert alcantara["cover"]["macrotemas"][0]["descricao_html"]

    todos = json.loads(_props("Campina Grande (PB)", "todos", monkeypatch, tmp_path))
    assert len(todos["cover"]["macrotemas"]) == 8

    recife = json.loads(_props("Recife (PE)", "saude", monkeypatch, tmp_path))
    assert "figure-caption" in "".join(recife["cover"]["macrotemas"][0]["descricao_html"])


@pytest.mark.parametrize("caso, cidade, macrotema", CASOS)
def test_texto_final_do_tema_igual_ao_relatorio(caso, cidade, macrotema, monkeypatch, tmp_path):
    # O laboratório mostra texto_final_do_tema; ele tem que ser o texto do HTML que o
    # relatório entrega, tema a tema, com o mesmo Doc e o mesmo contexto.
    from services import generation
    from utils.render.renderer import html_para_texto, texto_final_do_tema

    chamadas = []
    original = generation.render_descricao_tema_html

    def gravar(descricao, contexto, namespace="demografia", **kwargs):
        html = original(descricao, contexto, namespace=namespace, **kwargs)
        chamadas.append((descricao, dict(contexto), namespace, html))
        return html

    monkeypatch.setattr(generation, "render_descricao_tema_html", gravar)
    _props(cidade, macrotema, monkeypatch, tmp_path)

    temas = [c for c in chamadas if c[2] != "caract_mun"]
    assert temas
    for i, (descricao, contexto, namespace, html) in enumerate(temas):
        esperado = [t for t in map(html_para_texto, html) if t]
        obtido = texto_final_do_tema(descricao, contexto, namespace)
        if macrotema == "todos" and i > 0:
            # Num relatório de vários temas a numeração das figuras continua do tema
            # anterior; o laboratório numera o tema sozinho, como um relatório dele só.
            esperado = [re.sub(r"Figura \d+", "Figura N", t) for t in esperado]
            obtido = [re.sub(r"Figura \d+", "Figura N", t) for t in obtido]
        assert obtido == esperado, namespace
