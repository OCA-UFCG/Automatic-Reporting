"""Contrato do painel editorial: a árvore de blocos tipados que substitui o
Google Doc como fonte da prosa de um macrotema.

Um contrato é um JSON com duas partes (ver docs/PLANO-PAINEL-EDITORIAL.md §4):

- ``moldura`` — os blocos de papel fixo no layout do PDF (``resumo_tema``,
  ``resumo_cidade``, ``diagnostico_cidade``, ``relatorio_geral``) e a lista de
  ``referencias``. O operador preenche; não cria nem reordena.
- ``corpo`` — a árvore livre que vira o ``descricao_tema`` do macrotema.

O formato é dict/list puro, sem dataclasses, de propósito: é exatamente o que
trafega entre o painel e o FastAPI, e o painel é burro — ele devolve o que
recebeu. Toda a regra de forma está em :func:`validar_contrato`, que é a mesma
validação usada na importação, no salvamento e na leitura.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from utils.editorial.regras import validar_regra

VERSAO_CONTRATO = 1

# Os blocos da moldura correspondem 1:1 aos marcadores que a cadeia extrair_*
# de utils/external/docs.py fatia hoje. Manter os nomes idênticos é o que
# permite ao adaptador emitir texto que o pipeline atual consome sem alteração.
SLOTS_MOLDURA = (
    "resumo_tema",
    "resumo_cidade",
    "diagnostico_cidade",
    "relatorio_geral",
)

# A caixa "#!Fontes"/"#!Conteúdos relacionados" do tema não tem marcador no Doc:
# ela é o que sobra depois que a cadeia extrair_* tira todos os blocos marcados,
# e services/generation.py a transforma em `fontes_html`. No contrato ela vira um
# slot nomeado; na renderização sai sem marcador, no fim do texto, para cair de
# volta nessa mesma sobra.
SLOT_FONTES = "fontes"

TIPOS_DE_BLOCO = (
    "secao",  # título de seção (linha isolada, ex.: "Síntese")
    "paragrafo",
    "lista",
    "grafico",  # marcador *grafico_x, resolvido por services/generation.py
    "legenda",  # linha "Figura N – ..."
    "caixa",  # bloco "#!Fontes" / "#!Conteúdos relacionados"
    "nota",
)

TIPOS_COM_FILHOS = ("secao", "caixa")
TIPOS_COM_CONTEUDO = ("paragrafo", "legenda", "nota")

# "educacao.$matriculas_total" vira campo "educacao.matriculas_total"; o
# namespace é opcional porque os Docs usam as duas formas.
_CAMPO_VALIDO = re.compile(r"^(?:[A-Za-z_][\w-]*\.)?[A-Za-z_]\w*$")


class ErroDeContrato(ValueError):
    """Contrato malformado. A mensagem lista todos os erros encontrados."""


def novo_contrato(macrotema: str) -> dict[str, Any]:
    """Contrato vazio e válido, usado como ponto de partida pelo painel."""
    return {
        "versao_contrato": VERSAO_CONTRATO,
        "macrotema": macrotema,
        "versao": 1,
        "publicado_em": None,
        "publicado_por": None,
        "moldura": {slot: {"blocos": []} for slot in (*SLOTS_MOLDURA, SLOT_FONTES)}
        | {"referencias": []},
        "corpo": {"blocos": []},
    }


def _validar_trecho(trecho: Any, onde: str, erros: list[str]) -> None:
    if not isinstance(trecho, dict):
        erros.append(f"{onde}: trecho deve ser objeto, veio {type(trecho).__name__}")
        return

    tipo = trecho.get("t")
    if tipo == "texto":
        if not isinstance(trecho.get("v"), str):
            erros.append(f"{onde}: trecho de texto exige 'v' string")
        return

    if tipo == "var":
        campo = trecho.get("campo")
        if not isinstance(campo, str) or not _CAMPO_VALIDO.match(campo):
            erros.append(
                f"{onde}: 'campo' inválido ({campo!r}); use 'campo' ou 'namespace.campo'"
            )
        formato = trecho.get("formato")
        if formato is not None:
            if not isinstance(formato, dict):
                erros.append(f"{onde}: 'formato' deve ser objeto")
            elif "decimais" in formato and not isinstance(formato["decimais"], int):
                erros.append(f"{onde}: 'formato.decimais' deve ser inteiro")
        return

    erros.append(f"{onde}: tipo de trecho desconhecido {tipo!r} (use 'texto' ou 'var')")


def _validar_conteudo(conteudo: Any, onde: str, erros: list[str]) -> None:
    if not isinstance(conteudo, list):
        erros.append(f"{onde}: 'conteudo' deve ser lista de trechos")
        return
    for i, trecho in enumerate(conteudo):
        _validar_trecho(trecho, f"{onde}.conteudo[{i}]", erros)


def _validar_bloco(
    bloco: Any, onde: str, erros: list[str], ids_vistos: set[str]
) -> None:
    if not isinstance(bloco, dict):
        erros.append(f"{onde}: bloco deve ser objeto, veio {type(bloco).__name__}")
        return

    bloco_id = bloco.get("id")
    if not isinstance(bloco_id, str) or not bloco_id:
        erros.append(f"{onde}: 'id' obrigatório e não vazio")
    elif bloco_id in ids_vistos:
        # Ids duplicados quebram a concorrência otimista do painel: o cliente
        # endereça a edição pelo id, e dois blocos com o mesmo id tornam a
        # aplicação da alteração ambígua.
        erros.append(f"{onde}: id duplicado {bloco_id!r}")
    else:
        ids_vistos.add(bloco_id)

    tipo = bloco.get("tipo")
    if tipo not in TIPOS_DE_BLOCO:
        erros.append(
            f"{onde}: tipo {tipo!r} desconhecido; use um de {list(TIPOS_DE_BLOCO)}"
        )
        return

    regra = bloco.get("regra")
    if regra is not None:
        erros.extend(f"{onde}.regra: {erro}" for erro in validar_regra(regra))

    if tipo in TIPOS_COM_FILHOS:
        if not isinstance(bloco.get("titulo"), str):
            erros.append(f"{onde}: bloco '{tipo}' exige 'titulo' string")
        filhos = bloco.get("blocos", [])
        if not isinstance(filhos, list):
            erros.append(f"{onde}: 'blocos' deve ser lista")
        else:
            for i, filho in enumerate(filhos):
                _validar_bloco(filho, f"{onde}.blocos[{i}]", erros, ids_vistos)
    elif tipo in TIPOS_COM_CONTEUDO:
        _validar_conteudo(bloco.get("conteudo"), onde, erros)
    elif tipo == "lista":
        itens = bloco.get("itens")
        if not isinstance(itens, list):
            erros.append(f"{onde}: 'itens' deve ser lista de listas de trechos")
        else:
            for i, item in enumerate(itens):
                _validar_conteudo(item, f"{onde}.itens[{i}]", erros)
    elif tipo == "grafico":
        if not isinstance(bloco.get("grafico"), str):
            erros.append(f"{onde}: bloco 'grafico' exige 'grafico' com o nome do gráfico")


def validar_contrato(dados: Any) -> list[str]:
    """Devolve a lista de erros de forma. Lista vazia significa contrato válido.

    Devolve todos os erros de uma vez (em vez de levantar no primeiro) porque
    quem consome é o painel, que precisa mostrar tudo o que falta corrigir.
    """
    erros: list[str] = []

    if not isinstance(dados, dict):
        return [f"contrato deve ser objeto, veio {type(dados).__name__}"]

    if dados.get("versao_contrato") != VERSAO_CONTRATO:
        erros.append(
            f"'versao_contrato' deve ser {VERSAO_CONTRATO}, "
            f"veio {dados.get('versao_contrato')!r}"
        )

    if not isinstance(dados.get("macrotema"), str) or not dados.get("macrotema"):
        erros.append("'macrotema' obrigatório")

    versao = dados.get("versao")
    if not isinstance(versao, int) or versao < 1:
        erros.append("'versao' deve ser inteiro >= 1")

    ids_vistos: set[str] = set()

    moldura = dados.get("moldura")
    if not isinstance(moldura, dict):
        erros.append("'moldura' deve ser objeto")
    else:
        for slot in (*SLOTS_MOLDURA, SLOT_FONTES):
            if slot not in moldura:
                continue
            conteudo_slot = moldura[slot]
            if not isinstance(conteudo_slot, dict) or not isinstance(
                conteudo_slot.get("blocos"), list
            ):
                erros.append(f"moldura.{slot}: deve ser objeto com 'blocos' lista")
                continue
            for i, bloco in enumerate(conteudo_slot["blocos"]):
                _validar_bloco(bloco, f"moldura.{slot}.blocos[{i}]", erros, ids_vistos)

        referencias = moldura.get("referencias", [])
        if not isinstance(referencias, list) or not all(
            isinstance(r, str) for r in referencias
        ):
            erros.append("moldura.referencias: deve ser lista de strings")

        desconhecidos = set(moldura) - set(SLOTS_MOLDURA) - {SLOT_FONTES, "referencias"}
        if desconhecidos:
            erros.append(
                f"moldura: slots desconhecidos {sorted(desconhecidos)}; "
                f"a moldura é fixa ({[*SLOTS_MOLDURA, SLOT_FONTES]})"
            )

    corpo = dados.get("corpo")
    if not isinstance(corpo, dict) or not isinstance(corpo.get("blocos"), list):
        erros.append("'corpo' deve ser objeto com 'blocos' lista")
    else:
        for i, bloco in enumerate(corpo["blocos"]):
            _validar_bloco(bloco, f"corpo.blocos[{i}]", erros, ids_vistos)

    return erros


def exigir_contrato_valido(dados: Any) -> dict[str, Any]:
    erros = validar_contrato(dados)
    if erros:
        raise ErroDeContrato(
            "Contrato inválido:\n" + "\n".join(f"  - {erro}" for erro in erros)
        )
    return dados


def carregar_contrato(caminho: str | Path) -> dict[str, Any]:
    dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    return exigir_contrato_valido(dados)


def salvar_contrato(contrato: dict[str, Any], caminho: str | Path) -> Path:
    exigir_contrato_valido(contrato)
    destino = Path(caminho)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(contrato, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return destino
