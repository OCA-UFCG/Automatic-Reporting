#!/usr/bin/env python3
"""Baixa os Docs editoriais do Google, confere e grava em output/docs_cache/.

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

    ou pelo botão "Atualizar relatórios" do Data Nordeste (POST /docs/atualizar),
    que roda a mesma rotina (services/atualizacao_docs.py).

Ganho: tira ~610ms por Doc (medido) do caminho do request — ~15,7s num relatório
"todos", que busca 8 Docs de macrotema + o de Características Gerais.

Falhar aqui é barato de propósito: um Doc inacessível vira aviso no log e mantém
a cópia anterior em disco; o relatório continua saindo com a prosa de ontem em vez
de quebrar.

Cada Doc baixado passa pela conferência rápida (services/atualizacao_docs.py:
regra "Para quando ...:" que o parser lê diferente do escrito, regra escrita no
resumo do tema). Desde 24/11/2026 o Doc com problema NÃO é gravado: fica a cópia
anterior até alguém corrigir o Google Doc. Antes ele era gravado e só avisado
(revisão editorial de Demografia, 29/09/2026), e o parágrafo sumia do relatório.
Sai com código 1 se algum Doc não foi atualizado, pro cron registrar.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.atualizacao_docs import (
    AtualizacaoEmAndamento,
    ResultadoDoDoc,
    conferir_e_atualizar,
    docs_configurados,
)


def _imprimir(resultado: ResultadoDoDoc) -> None:
    if resultado.estado == "atualizado":
        print(f"ok: {resultado.rotulo} ({resultado.caracteres} caracteres)")
        return
    motivo = "regra que o relatório não entende" if resultado.estado == "com_problema" else "falhou"
    for aviso in resultado.avisos:
        print(f"AVISO: {resultado.rotulo}: {motivo} (mantida a cópia anterior em disco):\n  {aviso}")


async def main() -> int:
    docs = docs_configurados()
    if not docs:
        print("Nenhum *_DOCS_URL configurado no .env — nada a fazer.")
        return 1
    try:
        resultados = await conferir_e_atualizar(docs)
    except AtualizacaoEmAndamento as err:
        print(f"AVISO: {err}")
        return 1

    for resultado in resultados:
        _imprimir(resultado)
    atualizados = sum(r.estado == "atualizado" for r in resultados)
    print(f"=== atualizar_docs: {atualizados}/{len(docs)} atualizados ===")
    if any(r.estado == "com_problema" for r in resultados):
        print(
            "=== Doc com regra problemática não foi gravado: corrija no Google Doc e "
            "rode de novo. ==="
        )
    return 0 if atualizados == len(docs) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
