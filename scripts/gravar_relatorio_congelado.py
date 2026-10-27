"""Grava os dados e Docs reais que alimentam tests/test_relatorio_congelado.py.

Rode quando o Doc ou uma view mudou DE PROPÓSITO e o relatório esperado deve mudar junto
(depois regenere o esperado com ATUALIZAR_RELATORIO_CONGELADO=1). Roda no gamma, dentro
do container, porque só lá há banco e Docs reais; o container não tem pytest, por isso o
harness recebe um `setattr` simples. Só lê do banco. Uso, na raiz do app:

    PGAPPNAME=relatorio-congelado python3 scripts/gravar_relatorio_congelado.py [saida]

Sem argumento grava em tests/fixtures/relatorio_congelado/.
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import utils.database
import utils.queries.base
from services import generation
from tests import relatorio_congelado as harness


def main() -> None:
    saida = Path(sys.argv[1]) if len(sys.argv) > 1 else harness.FIXTURES
    (saida / "docs").mkdir(parents=True, exist_ok=True)

    # As reais, capturadas antes de o harness trocá-las por stubs.
    reais = {nome: getattr(generation, nome) for nome in harness.BUSCAS}
    carregar_real = generation.carregar_texto_do_docs
    conexao_real = utils.database.get_connection
    urls_reais = {}  # url real -> slug do arquivo
    dados: dict[str, list[dict]] = {nome: [] for nome in harness.BUSCAS}

    def buscar(nome, args):
        retorno = reais[nome](*args)
        gravado = {"args": harness.codificar(args), "retorno": harness.codificar(retorno)}
        if gravado not in dados[nome]:
            dados[nome].append(gravado)
        return retorno

    async def carregar_doc(url_fixture):
        slug = url_fixture.removeprefix("fixture:")
        texto = await carregar_real(urls_reais[slug])
        (saida / "docs" / f"{slug}.txt").write_text(texto, encoding="utf-8")
        return texto

    # URLs reais lidas antes do primeiro patch (o harness troca get_macrotema e a
    # constante por "fixture:<slug>").
    for slug in generation.get_macrotema_slugs_para_relatorio("todos"):
        urls_reais[slug] = generation.get_macrotema(slug)["docs_url"]
    urls_reais["caracteristicas"] = generation.CARACTERISTICAS_DOCS_URL
    vazias = [slug for slug, url in urls_reais.items() if not url]
    if vazias:
        sys.exit(f"URL de Doc vazia ({vazias}): o container não tem as URLs dos Docs")

    for caso, cidade, macrotema in harness.CASOS:
        print(f"gravando {caso}", flush=True)
        with tempfile.TemporaryDirectory() as tmp:
            capturadas = harness.instalar_ambiente(setattr, Path(tmp), buscar, carregar_doc)
            # O harness bloqueia o banco (é o que o replay precisa); aqui o banco é a
            # fonte, então devolve a conexão real. O CSV segue bloqueado: se a view
            # não tiver a cidade, o caso falha em vez de gravar acesso a CSV.
            utils.database.get_connection = utils.queries.base.get_connection = conexao_real
            harness.props_do_relatorio(cidade, macrotema, capturadas)

    (saida / "dados.json").write_text(
        json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print("ok")


if __name__ == "__main__":
    main()
