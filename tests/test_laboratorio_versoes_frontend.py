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
