"""Renderiza um contrato do painel no formato de texto que o pipeline consome.

Esta é a peça que torna a Fase 1 barata: em vez de ensinar o renderer, o SSR e
o WeasyPrint a entender a árvore de blocos, o contrato é serializado de volta
para o mesmo texto marcado que ``utils/external/docs.py`` entrega hoje — só
que já com as regras avaliadas e sem nenhuma frase ``Para quando ... :``.

Duas coisas ficam **de fora** desta serialização de propósito:

- Os ``$placeholders`` não são resolvidos aqui. Eles seguem para
  ``substituir_placeholders``, que é quem sabe formatar número em pt-BR,
  aplicar aliases e derivar percentuais. Reimplementar isso seria criar
  divergência justamente no critério de paridade da Fase 1.
- Os marcadores de gráfico saem como ``*nome_do_grafico``. O laço de
  ``GRAFICOS_AUTO_MARCADOR`` em services/generation.py já pula os gráficos
  cujo marcador está presente, então ele vira um no-op no caminho novo sem
  precisar de nenhuma alteração.
"""

from __future__ import annotations

from typing import Any

from utils.editorial.contrato import SLOT_FONTES, SLOTS_MOLDURA
from utils.editorial.regras import avaliar_regra

# Reexportados: marcam no contexto que a prosa veio do painel, com as regras já
# avaliadas. interpretar_blocos_condicionais usa isso para não rodar a máquina
# de estado dos Docs sobre um texto que não tem instruções editoriais — ela
# reagiria às frases do próprio conteúdo (ver o caso quilombola/situação de rua
# em utils/render/placeholders.py). Moram lá, e não aqui, para o caminho Docs
# não passar a depender do pacote do painel.
from utils.render.placeholders import CHAVE_FONTE_PAINEL, FONTE_PAINEL

__all__ = [
    "CHAVE_FONTE_PAINEL",
    "FONTE_PAINEL",
    "renderizar_blocos",
    "renderizar_contrato",
    "renderizar_trechos",
]


def renderizar_trechos(conteudo: list[dict], contexto: dict) -> str:
    """Junta os trechos de um bloco numa linha de texto com ``$placeholders``."""
    partes: list[str] = []
    for trecho in conteudo:
        if trecho.get("t") == "texto":
            partes.append(trecho.get("v", ""))
            continue

        campo = trecho["campo"]
        if "." in campo:
            namespace, nome = campo.rsplit(".", 1)
            marcador = f"{namespace}.${nome}"
        else:
            marcador = f"${campo}"

        formato = trecho.get("formato") or {}
        decimais = formato.get("decimais")
        if isinstance(decimais, int):
            # Sufixo de precisão que _extrair_precisoes já entende.
            marcador = f"{marcador}:{decimais}"

        partes.append(marcador)

    return "".join(partes)


def _renderizar_bloco(
    bloco: dict, contexto: dict, saida: list[str], ignorar_regras: bool = False
) -> None:
    if not ignorar_regras:
        resultado = avaliar_regra(bloco.get("regra"), contexto)
        if not resultado.inclui:
            if resultado.texto_alternativo:
                saida.append(resultado.texto_alternativo)
            return

    tipo = bloco["tipo"]

    if tipo in ("paragrafo", "legenda", "nota"):
        linha = renderizar_trechos(bloco.get("conteudo", []), contexto).strip()
        if linha:
            saida.append(linha)
        return

    if tipo == "grafico":
        saida.append(f"*{bloco['grafico']}")
        return

    if tipo == "lista":
        itens = [
            renderizar_trechos(item, contexto).strip()
            for item in bloco.get("itens", [])
        ]
        linhas = "\n".join(f"- {item}" for item in itens if item)
        if linhas:
            saida.append(linhas)
        return

    if tipo in ("secao", "caixa"):
        titulo = bloco.get("titulo", "").strip()
        if titulo:
            # "#!" é o prefixo que o renderer usa para abrir uma caixa
            # (#!Fontes, #!Conteúdos relacionados); uma seção comum é só o
            # título numa linha isolada.
            saida.append(f"#!{titulo}" if tipo == "caixa" else titulo)
        for filho in bloco.get("blocos", []):
            _renderizar_bloco(filho, contexto, saida, ignorar_regras)
        return

    raise ValueError(f"tipo de bloco não renderizável: {tipo!r}")


def renderizar_blocos(
    blocos: list[dict], contexto: dict, ignorar_regras: bool = False
) -> str:
    """``ignorar_regras`` emite todos os blocos, independentemente de regra.

    Serve à conferência de fidelidade da importação: só assim o texto gerado é
    comparável linha a linha com o Doc de origem, que também traz todas as
    variantes escritas.
    """
    saida: list[str] = []
    for bloco in blocos:
        _renderizar_bloco(bloco, contexto, saida, ignorar_regras)
    return "\n\n".join(parte for parte in saida if parte.strip())


def renderizar_contrato(
    contrato: dict[str, Any], contexto: dict, ignorar_regras: bool = False
) -> str:
    """Contrato + contexto do município -> texto marcado, pronto para o pipeline.

    Cada bloco é fechado com ``@@`` porque ``extrair_bloco_marcado`` casa de
    forma preguiçosa até ``@@`` ou até o fim do texto: sem o fechamento, o
    primeiro marcador engoliria todos os seguintes.
    """
    partes: list[str] = []

    moldura = contrato.get("moldura") or {}
    for slot in SLOTS_MOLDURA:
        conteudo_slot = moldura.get(slot)
        if not conteudo_slot:
            continue
        texto = renderizar_blocos(
            conteudo_slot.get("blocos", []), contexto, ignorar_regras
        )
        if texto:
            partes.append(f"{slot} = {texto}\n@@")

    corpo = renderizar_blocos(
        (contrato.get("corpo") or {}).get("blocos", []), contexto, ignorar_regras
    )
    if corpo:
        partes.append(f"descricao_tema = {corpo}\n@@")

    referencias = moldura.get("referencias") or []
    for referencia in referencias:
        if referencia.strip():
            partes.append(f"referencia = {referencia.strip()}\n@@")

    # Sem marcador e por último: é assim que o texto chega a generation.py como
    # sobra e vira a caixa `fontes_html` do tema.
    fontes = moldura.get(SLOT_FONTES)
    if fontes:
        texto_fontes = renderizar_blocos(
            fontes.get("blocos", []), contexto, ignorar_regras
        )
        if texto_fontes:
            partes.append(texto_fontes)

    return "\n\n".join(partes)
