#!/usr/bin/env python3
"""Compara o HTML produzido pelo Google Doc e pelo painel, para o mesmo município.

É o critério de aceite da Fase 1 do docs/PLANO-PAINEL-EDITORIAL.md: o caminho
novo só substitui o antigo se produzir a mesma prosa. A comparação é feita no
HTML do ``descricao_tema`` — depois das condicionais resolvidas, dos
placeholders substituídos e dos gráficos inseridos —, que é exatamente o que o
SSR recebe e o WeasyPrint transforma em PDF.

Não precisa de banco nem de rede: usa o Doc em cache e monta contextos de prova
a partir das próprias regras do contrato, um por ramo, de modo que toda condição
seja exercida nos dois lados.

    python scripts/conferir_paridade.py --macrotema demografia
    python scripts/conferir_paridade.py --macrotema educacao --detalhar
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from utils.editorial.contrato import carregar_contrato
from utils.editorial.render import (
    CHAVE_FONTE_PAINEL,
    FONTE_PAINEL,
    renderizar_contrato,
)
from utils.external.docs import extrair_descricao_tema
from utils.render.renderer import render_descricao_tema_html, reset_figura_contador

# Nomes de PNG fictícios: o que importa é que o marcador de gráfico resolva nos
# dois caminhos, não que o arquivo exista.
_GRAFICOS_DE_PROVA = {
    nome: f"{nome}.png"
    for nome in (
        "grafico_faixa_etaria_e_sexo",
        "grafico_composicao_cor_raca",
        "grafico_visao_historica",
        "grafico_cor_faixa_etaria",
        "grafico_cobertura_vacinal",
        "grafico_mortalidade_infantil",
        "grafico_de_estabelecimento",
        "grafico_publico_etario",
        "grafico_pib",
        "grafico_vab",
        "grafico_fob",
        "grafico_exportacao",
        "grafico_balanca",
        "grafico_esgotamento_sanitario",
        "grafico_tecnologias_acesso_agua",
        "grafico_aridez",
        "grafico_de_desenvolvimento_social",
    )
}

CONTRATOS_DIR = ROOT_DIR / "output" / "contratos"

# Base neutra: um município "médio" onde nenhum campo falta. Cada contexto de
# prova parte daqui e mexe em um campo só, para que a diferença observada possa
# ser atribuída àquela regra.
_BASE = {"nm_mun": "Município de Prova", "sigla_uf": "PB"}


def _campos_das_regras(contrato: dict) -> list[str]:
    campos: list[str] = []

    def andar(blocos: list[dict]) -> None:
        for bloco in blocos:
            regra = bloco.get("regra")
            if regra:
                for condicao in regra.get("condicoes", []):
                    campo = condicao["campo"].split(".")[-1]
                    if campo not in campos:
                        campos.append(campo)
            andar(bloco.get("blocos", []))

    for slot, conteudo in contrato["moldura"].items():
        if slot != "referencias":
            andar(conteudo["blocos"])
    andar(contrato["corpo"]["blocos"])
    return campos


def contextos_de_prova(contrato: dict) -> list[tuple[str, dict]]:
    """Um contexto por ramo de regra: valor negativo, zero, positivo e ausente."""
    campos = _campos_das_regras(contrato)
    base = dict(_BASE) | {campo: 1 for campo in campos}

    provas: list[tuple[str, dict]] = [("todos positivos", dict(base))]
    for campo in campos:
        for rotulo, valor in (("zero", 0), ("negativo", -1), ("ausente", None)):
            contexto = dict(base)
            if valor is None:
                contexto.pop(campo, None)
            else:
                contexto[campo] = valor
            provas.append((f"{campo}={rotulo}", contexto))
    return provas


def _html_normalizado(descricao: str, contexto: dict, namespace: str) -> str:
    """HTML do corpo do macrotema, na forma em que o SSR o recebe.

    A comparação é feita aqui, e não no texto marcado, porque é este HTML que
    vira PDF. Os itens da lista são concatenados: cada item vira um ``<div>``
    em ThemeDetail.jsx, e um ``<div>`` a mais ou a menos não muda o layout —
    o espaçamento vem da margem do próprio ``<p>``. O que precisa bater é a
    sequência de tags e o texto dentro delas.
    """
    reset_figura_contador()
    itens = render_descricao_tema_html(
        descricao,
        contexto,
        namespace=namespace,
        safe_report="paridade",
        graficos_por_placeholder=_GRAFICOS_DE_PROVA,
    )
    bruto = "".join(str(item) for item in itens)
    return re.sub(r">\s+<", "><", re.sub(r"\s+", " ", bruto)).strip()


def _do_doc(texto_doc: str, contexto: dict, namespace: str) -> str:
    descricao, _ = extrair_descricao_tema(texto_doc)
    return _html_normalizado(descricao or "", contexto, namespace)


def _do_painel(contrato: dict, contexto: dict, namespace: str) -> str:
    contexto = dict(contexto)
    contexto[CHAVE_FONTE_PAINEL] = FONTE_PAINEL
    descricao, _ = extrair_descricao_tema(renderizar_contrato(contrato, contexto))
    return _html_normalizado(descricao or "", contexto, namespace)


def _tags(html: str) -> list[str]:
    """Quebra o HTML em unidades comparáveis, uma por tag de abertura."""
    return [trecho for trecho in re.split(r"(?=<[a-z])", html) if trecho.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--macrotema", required=True)
    parser.add_argument("--detalhar", action="store_true", help="mostra o diff")
    args = parser.parse_args()

    from utils.data.macrotemas import MACROTEMAS
    from utils.external.docs import _cache_path, extrair_doc_id

    docs_url = MACROTEMAS[args.macrotema]["docs_url"]
    caminho_cache = _cache_path(extrair_doc_id(docs_url))
    if not caminho_cache.exists():
        raise SystemExit(f"Sem Doc em cache para {args.macrotema} ({caminho_cache})")
    texto_doc = json.loads(caminho_cache.read_text(encoding="utf-8"))["texto"]

    contrato = carregar_contrato(CONTRATOS_DIR / f"{args.macrotema}.json")

    provas = contextos_de_prova(contrato)
    iguais = 0
    divergentes: list[tuple[str, list[str]]] = []

    for rotulo, contexto in provas:
        linhas_doc = _tags(_do_doc(texto_doc, contexto, args.macrotema))
        linhas_painel = _tags(_do_painel(contrato, contexto, args.macrotema))

        if linhas_doc == linhas_painel:
            iguais += 1
            continue

        diff = [
            linha
            for linha in difflib.unified_diff(
                linhas_doc, linhas_painel, "docs", "painel", n=0, lineterm=""
            )
            if linha.startswith(("+", "-")) and not linha.startswith(("+++", "---"))
        ]
        divergentes.append((rotulo, diff))

    print(f"Macrotema: {args.macrotema}")
    print(f"Contextos de prova: {len(provas)}")
    print(f"  idênticos:   {iguais}")
    print(f"  divergentes: {len(divergentes)}")

    if divergentes:
        print()
        print("As divergências abaixo devem casar, uma a uma, com o relatório")
        print(f"output/contratos/{args.macrotema}.divergencias.md.")
        for rotulo, diff in divergentes:
            print(f"\n  ── {rotulo} ({len(diff)} linhas)")
            for linha in diff[: (None if args.detalhar else 4)]:
                print(f"     {linha[:150]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
