"""Regra inversa (só Saúde): o gráfico só sai se o texto renderizado o cita.

A legenda "Figura Z - ..." casa com a menção "(Figura Z)" pela letra. Quando a
condição editorial escolhe um parágrafo sem a menção (ex.: mortalidade zerada em
toda a série, Felipe Guerra/RN), o marcador e a legenda saem junto.
"""

from utils.render.renderer import (
    remover_graficos_sem_mencao,
    render_descricao_tema_html,
    reset_figura_contador,
)

COM_MENCAO = """\
Texto da mortalidade (Figura Z).

*grafico_taxa_mortalidade

Figura Z - Histórico da taxa de mortalidade infantil.

Depois.
"""

SEM_MENCAO = """\
Texto da mortalidade sem citar nada.

*grafico_taxa_mortalidade

Figura Z - Histórico da taxa de mortalidade infantil.

Depois.
"""


def test_mantem_marcador_e_legenda_quando_ha_mencao():
    assert remover_graficos_sem_mencao(COM_MENCAO) == COM_MENCAO


def test_remove_marcador_e_legenda_quando_nao_ha_mencao():
    saida = remover_graficos_sem_mencao(SEM_MENCAO)

    assert "grafico_taxa_mortalidade" not in saida
    assert "Figura Z" not in saida
    assert "Texto da mortalidade sem citar nada." in saida
    assert "Depois." in saida


def test_mencao_depois_do_grafico_tambem_conta():
    texto = (
        "*grafico_x\n\nFigura Y - Legenda.\n\nComo mostra a Figura Y, algo.\n"
    )

    assert remover_graficos_sem_mencao(texto) == texto


def test_mencao_de_outra_letra_nao_segura_o_grafico():
    texto = "Cita (Figura X).\n\n*grafico_z\n\nFigura Z - Legenda.\n"

    saida = remover_graficos_sem_mencao(texto)

    assert "grafico_z" not in saida
    assert "Figura Z" not in saida
    assert "(Figura X)" in saida


def test_avalia_cada_grafico_por_si():
    texto = (
        "Cita (Figura X).\n\n"
        "*grafico_a\n\nFigura X - Primeira.\n\n"
        "*grafico_b\n\nFigura Y - Segunda.\n"
    )

    saida = remover_graficos_sem_mencao(texto)

    assert "*grafico_a" in saida and "Figura X - Primeira." in saida
    assert "grafico_b" not in saida and "Figura Y" not in saida


def test_legenda_nao_conta_como_mencao_de_si_mesma():
    texto = "*grafico_a\n\nFigura Z - Legenda.\n"

    assert "grafico_a" not in remover_graficos_sem_mencao(texto)


def test_marcador_sem_legenda_e_mantido():
    texto = "Texto.\n\n*grafico_a\n\nOutro texto.\n"

    assert remover_graficos_sem_mencao(texto) == texto


def test_marcador_composto_e_avaliado_pela_legenda():
    texto = "Cita (Figura X).\n\n*grafico_a+grafico_b\n\nFigura X - Legenda.\n"

    assert remover_graficos_sem_mencao(texto) == texto


def _html(texto: str, namespace: str, graficos: dict) -> str:
    reset_figura_contador()
    return "".join(
        render_descricao_tema_html(
            texto, {}, namespace=namespace, graficos_por_placeholder=graficos
        )
    )


def test_saude_sem_mencao_nao_renderiza_grafico_nem_legenda():
    html = _html(SEM_MENCAO, "saude", {"grafico_taxa_mortalidade": "x.png"})

    assert "x.png" not in html
    assert "figure-caption" not in html


def test_saude_com_mencao_renderiza_grafico_e_legenda_casadas():
    html = _html(COM_MENCAO, "saude", {"grafico_taxa_mortalidade": "x.png"})

    assert "x.png" in html
    assert "Figura 2 –" in html
    assert "(Figura 2)" in html


def test_outros_macrotemas_continuam_exibindo_grafico_sem_mencao():
    html = _html(SEM_MENCAO, "demografia", {"grafico_taxa_mortalidade": "x.png"})

    assert "x.png" in html
    assert "figure-caption" in html
