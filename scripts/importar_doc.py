#!/usr/bin/env python3
"""Converte o Google Doc de um macrotema no contrato do painel editorial.

É a ferramenta da Fase 0 do docs/PLANO-PAINEL-EDITORIAL.md. Não altera nada do
pipeline: lê o Doc (ou o cache local), escreve um contrato JSON e um relatório
de divergências em markdown.

    # a partir do cache local, sem rede e sem tocar no Doc de ninguém
    python scripts/importar_doc.py --macrotema demografia --do-cache

    # baixando o Doc configurado no .env (somente leitura)
    python scripts/importar_doc.py --macrotema educacao --baixar

    # de um .txt exportado à mão (o caso da "cópia do Doc")
    python scripts/importar_doc.py --macrotema educacao --arquivo copia.txt

``--conferir`` renderiza o contrato de volta para texto, ignorando as regras, e
compara com o Doc de origem linha a linha. É a prova de que a importação não
perdeu conteúdo.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from utils.editorial.comparacao import normalizar_texto
from utils.editorial.contrato import salvar_contrato, validar_contrato
from utils.editorial.importador import (
    importar_texto,
    relatorio_markdown,
)
from utils.editorial.render import renderizar_blocos

DESTINO_PADRAO = ROOT_DIR / "output" / "contratos"


def _texto_do_cache(doc_url: str) -> str:
    from utils.external.docs import _cache_path, extrair_doc_id

    caminho = _cache_path(extrair_doc_id(doc_url))
    if not caminho.exists():
        raise SystemExit(
            f"Sem cache local para este Doc ({caminho}). "
            "Gere um relatório uma vez, ou use --baixar / --arquivo."
        )
    return json.loads(caminho.read_text(encoding="utf-8"))["texto"]


def _texto_baixado(doc_url: str) -> str:
    from utils.external.docs import carregar_texto_do_docs

    return asyncio.run(carregar_texto_do_docs(doc_url))


def _conferir(contrato: dict, texto_original: str) -> int:
    """Compara o texto reconstruído com o Doc; devolve o número de linhas divergentes."""
    from utils.external.docs import extrair_descricao_tema

    descricao, _ = extrair_descricao_tema(texto_original)
    if not descricao:
        print("  (sem descricao_tema no original — nada a conferir)")
        return 0

    reconstruido = renderizar_blocos(
        contrato["corpo"]["blocos"], {}, ignorar_regras=True
    )

    # As instruções editoriais ("Para quando ...:", a variante do Gini)
    # desaparecem de propósito: viraram regra.
    def normalizar(texto: str) -> list[str]:
        from utils.editorial.importador import (
            _CONDICAO_GINI,
            _INSTRUCAO_CONDICIONAL,
            _SEM_CONDICAO,
        )

        linhas = []
        for linha in normalizar_texto(texto):
            if _SEM_CONDICAO.match(linha) or _CONDICAO_GINI.match(linha):
                continue
            if _INSTRUCAO_CONDICIONAL.match(linha) and "$" in linha:
                continue
            linhas.append(linha)
        return linhas

    esperado = normalizar(descricao)
    obtido = normalizar(reconstruido)

    # Perda é falha: uma linha do Doc que não reaparece no contrato é conteúdo
    # que sumiria do relatório. Acréscimo não é falha — é a prosa que hoje mora
    # dentro do Python sendo trazida para o contrato, e vem listada no relatório
    # de divergências.
    perdidas = [linha for linha in esperado if linha not in obtido]
    acrescidas = [linha for linha in obtido if linha not in esperado]

    print(f"  Linhas de conteúdo no Doc:      {len(esperado)}")
    print(f"  Linhas reconstruídas:           {len(obtido)}")

    if acrescidas:
        print(f"  + {len(acrescidas)} linha(s) acrescentada(s) (ver divergências):")
        for linha in acrescidas:
            print(f"      + {linha[:150]}")

    if not perdidas:
        print("  ✓ conferência: nenhuma linha do Doc se perdeu")
    else:
        print(f"  ✗ conferência: {len(perdidas)} linha(s) do Doc não reapareceram")
        for linha in perdidas[:20]:
            print(f"      - {linha[:150]}")
    return len(perdidas)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--macrotema", required=True)
    origem = parser.add_mutually_exclusive_group(required=True)
    origem.add_argument("--do-cache", action="store_true", help="usa output/docs_cache")
    origem.add_argument("--baixar", action="store_true", help="exporta o Doc do .env")
    origem.add_argument("--arquivo", type=Path, help="um .txt exportado à mão")
    parser.add_argument("--saida", type=Path)
    parser.add_argument("--relatorio", type=Path)
    parser.add_argument("--conferir", action="store_true")
    args = parser.parse_args()

    from utils.data.macrotemas import MACROTEMAS

    if args.macrotema not in MACROTEMAS:
        raise SystemExit(
            f"Macrotema desconhecido: {args.macrotema}. "
            f"Use um de {sorted(MACROTEMAS)}"
        )

    if args.arquivo:
        texto = args.arquivo.read_text(encoding="utf-8")
        descricao_origem = str(args.arquivo)
    else:
        doc_url = MACROTEMAS[args.macrotema]["docs_url"]
        if not doc_url:
            raise SystemExit(
                f"{MACROTEMAS[args.macrotema]['docs_env']} não configurado no .env"
            )
        texto = _texto_baixado(doc_url) if args.baixar else _texto_do_cache(doc_url)
        descricao_origem = f"Google Doc {args.macrotema} ({'rede' if args.baixar else 'cache'})"

    resultado = importar_texto(texto, args.macrotema)

    erros = validar_contrato(resultado.contrato)
    if erros:
        print("Contrato inválido após a importação:", file=sys.stderr)
        for erro in erros:
            print(f"  - {erro}", file=sys.stderr)
        return 1

    saida = args.saida or DESTINO_PADRAO / f"{args.macrotema}.json"
    relatorio = args.relatorio or DESTINO_PADRAO / f"{args.macrotema}.divergencias.md"

    salvar_contrato(resultado.contrato, saida)
    relatorio.parent.mkdir(parents=True, exist_ok=True)
    relatorio.write_text(
        relatorio_markdown(resultado, args.macrotema, descricao_origem),
        encoding="utf-8",
    )

    print(f"Contrato:    {saida}")
    print(f"Divergências: {relatorio} ({len(resultado.divergencias)} itens)")

    if args.conferir:
        print("Conferência de fidelidade:")
        return 1 if _conferir(resultado.contrato, texto) else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
