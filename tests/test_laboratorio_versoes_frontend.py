"""O frontend do laboratório (frontend/src/laboratorio/modelo.js) acha as versões no Doc
com regras de linha próprias, em JavaScript; o backend devolve as contagens na ordem em
que interpretar_blocos_condicionais avalia. A tela casa uma lista com a outra pela
posição, então as duas têm que ser a mesma sequência, nos Docs reais."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from services.generation import separar_secoes_do_tema
from utils.render.placeholders import interpretar_blocos_condicionais, registrar_versoes

RAIZ = Path(__file__).resolve().parent.parent
DOCS = RAIZ / "tests" / "fixtures" / "relatorio_congelado" / "docs"
TEMAS = [
    "demografia", "educacao", "saude", "economia-renda", "hidraulica",
    "desenvolvimento-social", "meio-ambiente", "saneamento",
]

_SCRIPT = """
import { readFileSync } from 'node:fs'
import { lerDoc } from '%s'
const [docs, ...temas] = process.argv.slice(1)
const saida = {}
for (const tema of temas) {
  const itens = lerDoc(readFileSync(`${docs}/${tema}.txt`, 'utf-8'))
  saida[tema] = itens.filter((i) => i.tipo === 'versao').map((i) => i.condicao)
}
console.log(JSON.stringify(saida))
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="sem Node")
def test_frontend_acha_as_mesmas_versoes_que_o_backend_avalia():
    modelo = (RAIZ / "frontend" / "src" / "laboratorio" / "modelo.js").as_uri()
    saida = subprocess.run(
        ["node", "--input-type=module", "-e", _SCRIPT % modelo, str(DOCS), *TEMAS],
        capture_output=True, text=True, check=True,
    ).stdout
    frontend = json.loads(saida)

    for tema in TEMAS:
        descricao = separar_secoes_do_tema((DOCS / f"{tema}.txt").read_text(), tema)[0].descricao_tema
        with registrar_versoes() as versoes:
            interpretar_blocos_condicionais(descricao or "", {})
        assert frontend[tema] == [condicao for condicao, _ in versoes], tema


# O formulário "nova condição" escreve a frase; aqui ela passa pelo gerador de
# verdade. Se alguém mexer num operador do gerador ou do modelo.js, quebra aqui.
_SCRIPT_FRASES = """
import { OPERADORES, fraseDaCondicao, condicaoDoItem } from '%s'
const frases = OPERADORES.map((o) => {
  const frase = fraseDaCondicao({ prefixo: 'demografia', coluna: 'x', operador: o.id, valor: '10', valor2: '30,5' })
  return [o.id, frase, condicaoDoItem({ original: frase + '\\nTexto.\\n' }) !== null]
})
console.log(JSON.stringify(frases))
"""

# Valor de $x → a versão vale? (10 e 30,5 são os números da frase)
_ESPERADO = {
    "igual": {10: True, 20: False, None: False},
    "diferente": {10: False, 20: True},
    "maior": {10: False, 20: True},
    "menor": {10: False, 5: True},
    "maior_igual": {10: True, 5: False},
    "menor_igual": {10: True, 20: False},
    "entre": {20: True, 30.5: True, 31: False, 5: False},
    "sem_dados": {None: True, "sem dados": True, 20: False},
    "com_dados": {None: False, 20: True},
}


@pytest.mark.skipif(shutil.which("node") is None, reason="sem Node")
def test_frases_do_formulario_sao_entendidas_pelo_gerador():
    from utils.render.placeholders import conferir_condicoes

    modelo = (RAIZ / "frontend" / "src" / "laboratorio" / "modelo.js").as_uri()
    saida = subprocess.run(
        ["node", "--input-type=module", "-e", _SCRIPT_FRASES % modelo],
        capture_output=True, text=True, check=True,
    ).stdout
    frases = json.loads(saida)
    assert {operador for operador, _, _ in frases} == set(_ESPERADO)

    for operador, frase, frontend_reconhece in frases:
        texto = f"{frase}\nTexto.\n"
        assert frontend_reconhece, frase
        assert conferir_condicoes(texto) == [], frase
        for valor, vale in _ESPERADO[operador].items():
            saiu = "Texto." in interpretar_blocos_condicionais(texto, {"x": valor})
            assert saiu is vale, (frase, valor)


# "Remover" a 1ª e a última versão do Doc não pode levar junto o marcador do tema
# (descricao_tema = “ ... ”@@): sem ele, o backend não acha o texto do tema.
_SCRIPT_REMOVER = """
import { readFileSync } from 'node:fs'
import { lerDoc, exportar } from '%s'
const [docs, ...temas] = process.argv.slice(1)
const saida = {}
for (const tema of temas) {
  const itens = lerDoc(readFileSync(`${docs}/${tema}.txt`, 'utf-8'))
  const versoes = itens.filter((i) => i.tipo === 'versao')
  versoes[0].editado = ''
  versoes.at(-1).editado = ''
  saida[tema] = exportar(itens)
}
console.log(JSON.stringify(saida))
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="sem Node")
def test_remover_a_primeira_e_a_ultima_versao_mantem_o_tema():
    modelo = (RAIZ / "frontend" / "src" / "laboratorio" / "modelo.js").as_uri()
    saida = subprocess.run(
        ["node", "--input-type=module", "-e", _SCRIPT_REMOVER % modelo, str(DOCS), *TEMAS],
        capture_output=True, text=True, check=True,
    ).stdout
    exportados = json.loads(saida)

    for tema in TEMAS:
        antes = _versoes_do_backend((DOCS / f"{tema}.txt").read_text(), tema)
        assert _versoes_do_backend(exportados[tema], tema) == antes[1:-1], tema


def _versoes_do_backend(texto: str, tema: str) -> list[str]:
    descricao = separar_secoes_do_tema(texto, tema)[0].descricao_tema
    with registrar_versoes() as lidas:
        interpretar_blocos_condicionais(descricao or "", {})
    return [condicao for condicao, _ in lidas]


# "Copiar bloco" e colar no Doc por cima das linhas inteiras do bloco (o que a tela
# pede). Na 1ª e na última versão, o marcador do tema (descricao_tema = “ / ”@@) está
# na mesma linha do texto: o bloco copiado precisa trazê-lo, senão o colar o apaga.
_SCRIPT_COLAR = """
import { readFileSync } from 'node:fs'
import { lerDoc, exportar, agruparEmBlocos, textoDoBloco, textoDoItem } from '%s'
const [docs, ...temas] = process.argv.slice(1)
const saida = {}
for (const tema of temas) {
  const doc = readFileSync(`${docs}/${tema}.txt`, 'utf-8')
  const itens = lerDoc(doc)
  saida[tema] = agruparEmBlocos(itens).filter((g) => g.tipo === 'bloco').map((g) => {
    const inicio = itens.slice(0, g.versoes[0]).map(textoDoItem).join('').length
    const fim = itens.slice(0, g.versoes.at(-1) + 1).map(textoDoItem).join('').length
    const linhaInicio = doc.lastIndexOf('\\n', inicio - 1) + 1
    const quebra = doc.indexOf('\\n', fim - 1)
    const linhaFim = quebra === -1 ? doc.length : quebra
    return doc.slice(0, linhaInicio) + textoDoBloco(itens, g.versoes) + doc.slice(linhaFim)
  })
}
console.log(JSON.stringify(saida))
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="sem Node")
def test_colar_um_bloco_no_doc_por_cima_das_linhas_mantem_o_tema():
    modelo = (RAIZ / "frontend" / "src" / "laboratorio" / "modelo.js").as_uri()
    saida = subprocess.run(
        ["node", "--input-type=module", "-e", _SCRIPT_COLAR % modelo, str(DOCS), *TEMAS],
        capture_output=True, text=True, check=True,
    ).stdout
    colados = json.loads(saida)

    for tema in TEMAS:
        antes = _versoes_do_backend((DOCS / f"{tema}.txt").read_text(), tema)
        for numero, doc in enumerate(colados[tema], start=1):
            assert _versoes_do_backend(doc, tema) == antes, f"{tema}, bloco {numero}"
