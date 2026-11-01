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
