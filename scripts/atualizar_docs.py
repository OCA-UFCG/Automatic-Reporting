#!/usr/bin/env python3
"""Baixa os Docs editoriais do Google e grava em output/docs_cache/.

Por que existe: o relatório lê a prosa do disco (utils/external/docs.py), não do
Google. Sem este script o cache nunca se atualiza e a correção da editora não
aparece. Ele é o par de invalidação por tempo + por evento que
services/cache.py:artefato_fresco descreve:

  - por TEMPO: cron noturno, junto do refresh_matviews.sh. A VM roda em UTC,
    então 01:00 BRT = 04:00 UTC:

      0 4 * * *  cd /caminho/Automatic-Reporting && .venv/bin/python scripts/atualizar_docs.py

  - por EVENTO: chamado à mão logo depois de uma edição, quando não dá pra
    esperar o cron:

      .venv/bin/python scripts/atualizar_docs.py
      docker exec automatic-reporting-beta python3 scripts/atualizar_docs.py

Ganho: tira ~610ms por Doc (medido) do caminho do request — ~15,7s num relatório
"todos", que busca 8 Docs de macrotema + o de Características Gerais.

Falhar aqui é barato de propósito: um Doc inacessível vira aviso no log e mantém
a cópia anterior em disco; o relatório continua saindo com a prosa de ontem em vez
de quebrar. Sai com código 1 se algum Doc falhou, pro cron registrar.

Cada Doc baixado passa também por conferir_condicoes: regra "Para quando ...:"
que o parser descarta em parte ou lê diferente do escrito vira AVISO com o texto
da regra. Não muda o código de saída: o Doc foi baixado e o relatório sai, mas
com um parágrafo sumido ou no município errado. É o momento de avisar quem
editou o Doc (revisão editorial de Demografia, 29/09/2026).
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import CARACTERISTICAS_DOCS_URL
from utils.data.macrotemas import MACROTEMAS
from utils.external.docs import baixar_e_salvar_doc
from utils.render.placeholders import conferir_condicoes


def _docs_configurados() -> list[tuple[str, str]]:
    """(rótulo, url) de todo Doc que o relatório pode pedir. Macrotema sem
    docs_url no .env é pulado — é o mesmo tratamento de services/generation.py,
    que apenas loga e segue."""
    docs = [
        (slug, dados["docs_url"])
        for slug, dados in MACROTEMAS.items()
        if dados["docs_url"]
    ]
    if CARACTERISTICAS_DOCS_URL:
        docs.append(("caracteristicas", CARACTERISTICAS_DOCS_URL))
    return docs


async def main() -> int:
    docs = _docs_configurados()
    if not docs:
        print("Nenhum *_DOCS_URL configurado no .env — nada a fazer.")
        return 1

    # Em paralelo: são 9 esperas de rede independentes. Sequencial mede ~15,7s,
    # com gather ~1,1s. return_exceptions pra um Doc quebrado não abortar os outros
    # — cada um tem seu próprio cache e seu próprio dono.
    resultados = await asyncio.gather(
        *(baixar_e_salvar_doc(url) for _, url in docs), return_exceptions=True
    )

    falhas = 0
    regras_com_problema = 0
    for (rotulo, _), resultado in zip(docs, resultados):
        if isinstance(resultado, Exception):
            falhas += 1
            print(f"AVISO: {rotulo}: {resultado} (mantida a cópia anterior em disco)")
            continue
        print(f"ok: {rotulo} ({len(resultado)} caracteres)")
        for aviso in conferir_condicoes(resultado):
            regras_com_problema += 1
            print(f"AVISO: {rotulo}: regra que o relatório não entende:\n  {aviso}")

    print(f"=== atualizar_docs: {len(docs) - falhas}/{len(docs)} atualizados ===")
    if regras_com_problema:
        print(
            f"=== {regras_com_problema} regra(s) com problema: o parágrafo pode sumir ou "
            "sair no município errado. Corrija no Google Doc e rode de novo. ==="
        )
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
