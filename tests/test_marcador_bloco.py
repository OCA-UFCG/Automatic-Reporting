"""Marcadores "[bloco: nome]" e "[fimbloco]" (utils/render/placeholders.py,
_MARCADOR_BLOCO): abrem e fecham os blocos do TemaLab no Doc; no relatório a linha vale como
linha em branco."""

import pytest

from utils.render.placeholders import (
    interpretar_blocos_condicionais,
    isolar_paragrafo_de_cada_condicao,
)

DOC = """{m1}
Para quando $a for igual a 1:
Versão um. [junta com o próximo]

Para quando $a for igual a 2:
Versão dois.

{m2}
Para quando $b for maior que 0:
Detalhe opcional.

Fecho."""

# O estado não tem linhas em branco entre as versões (isolar_paragrafo_de_cada_condicao).
DOC_ESTADO = """{m1}
Para quando $a for igual a 1:
Versão um.
{m2}
Para quando $b for maior que 0:
Detalhe opcional.
Fecho."""

MARCADORES = [
    "[bloco: Analfabetismo]",
    "[bloco]",
    "[Bloco: Síntese, fim]",
    r"\[bloco: Escapado\]",
    "  [ bloco ]  ",
    "[fimbloco]",
    "[FimBloco]",
    "[fim bloco]",
    "[fim do bloco]",
    r"\[fimbloco\]",
]
CONTEXTOS = [{"a": 1, "b": 0}, {"a": 2, "b": 1}, {"a": 3, "b": 5}]


@pytest.mark.parametrize("marcador", MARCADORES)
@pytest.mark.parametrize("contexto", CONTEXTOS)
def test_saida_igual_a_do_doc_sem_marcador(marcador, contexto):
    com = interpretar_blocos_condicionais(DOC.format(m1=marcador, m2=marcador), contexto)
    sem = interpretar_blocos_condicionais(DOC.format(m1="", m2=""), contexto)
    assert "bloco" not in com.lower()
    assert com.split() == sem.split()


@pytest.mark.parametrize("contexto", CONTEXTOS)
def test_estado_sem_linhas_em_branco(contexto):
    def gerar(m):
        return interpretar_blocos_condicionais(isolar_paragrafo_de_cada_condicao(DOC_ESTADO.format(m1=m, m2=m)), contexto)

    assert "bloco" not in gerar("[bloco: X]").lower()
    assert gerar("[bloco: X]").split() == gerar("").split()


def test_frase_com_bloco_no_meio_nao_some():
    texto = "O [bloco] de texto continua."
    assert interpretar_blocos_condicionais(texto, {}).strip() == texto


@pytest.mark.parametrize("contexto", CONTEXTOS)
def test_abre_e_fecha_em_volta_de_texto_fixo(contexto):
    doc = "[bloco: X]\nPara quando $a for igual a 1:\nVersão um.\n\nFrase fixa.\n[fimbloco]\n\nTítulo fora"
    sem = "Para quando $a for igual a 1:\nVersão um.\n\nFrase fixa.\n\nTítulo fora"
    com = interpretar_blocos_condicionais(doc, contexto)
    assert "bloco" not in com.lower()
    assert com.split() == interpretar_blocos_condicionais(sem, contexto).split()


@pytest.mark.parametrize("marcador", ["[fimbloco]", "[bloco: X]"])
def test_marcador_colado_no_texto_fecha_o_paragrafo_de_cima(marcador):
    doc = f"Para quando $a for igual a 1:\nVersão um.\n{marcador}\nTítulo fora"
    assert "Título fora" in interpretar_blocos_condicionais(doc, {"a": 2})
    assert "Versão um." not in interpretar_blocos_condicionais(doc, {"a": 2})
    assert "Versão um." in interpretar_blocos_condicionais(doc, {"a": 1})
