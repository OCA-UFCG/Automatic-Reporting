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
from utils.render.placeholders import (
    CHAVE_FONTE_PAINEL,
    FONTE_PAINEL,
    placeholders_sem_valor,
)

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


def _sem_dado(linha: str, contexto: dict, namespace: str) -> bool:
    """O trecho depende de variável que este município não tem?

    Regra do produto: variável nula esconde o trecho que depende dela. O
    comportamento antigo — deixar `$campo` literal no PDF — não era uma escolha
    editorial, era o que sobrava quando ninguém decidia; e o relatório vai para
    gestores municipais, onde `$sol_predom` no meio da frase é pior do que a
    frase não existir.

    Vale para os oito macrotemas sem nenhuma regra escrita à mão no contrato:
    hidráulica tinha sete campos assim em cinco dos seis municípios de teste, e
    educação imprimia "aumento de $tend_nivel_sup_per%" onde o banco traz NULL.
    Quem quiser o trecho mesmo sem o dado escreve a variante no contrato e a
    protege com uma regra — é para isso que existe `sem_dado`.
    """
    return bool(linha) and bool(placeholders_sem_valor(linha, contexto, namespace))


def _renderizar_bloco(
    bloco: dict,
    contexto: dict,
    saida: list[str],
    ignorar_regras: bool = False,
    namespace: str = "",
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
        if linha and not (not ignorar_regras and _sem_dado(linha, contexto, namespace)):
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
        if not ignorar_regras:
            itens = [item for item in itens if not _sem_dado(item, contexto, namespace)]
        linhas = "\n".join(f"- {item}" for item in itens if item)
        if linhas:
            saida.append(linhas)
        return

    if tipo in ("secao", "caixa"):
        # Os filhos são renderizados antes do título: uma seção que perdeu todo
        # o conteúdo por falta de dado não pode deixar o cabeçalho órfão no
        # relatório, anunciando um assunto que não vem.
        filhos: list[str] = []
        for filho in bloco.get("blocos", []):
            _renderizar_bloco(filho, contexto, filhos, ignorar_regras, namespace)
        if not filhos:
            return

        titulo = bloco.get("titulo", "").strip()
        if titulo:
            # "#!" é o prefixo que o renderer usa para abrir uma caixa
            # (#!Fontes, #!Conteúdos relacionados); uma seção comum é só o
            # título numa linha isolada.
            saida.append(f"#!{titulo}" if tipo == "caixa" else titulo)
        saida.extend(filhos)
        return

    raise ValueError(f"tipo de bloco não renderizável: {tipo!r}")


def renderizar_blocos(
    blocos: list[dict],
    contexto: dict,
    ignorar_regras: bool = False,
    namespace: str = "",
) -> str:
    """``ignorar_regras`` emite todos os blocos, independentemente de regra.

    Serve à conferência de fidelidade da importação: só assim o texto gerado é
    comparável linha a linha com o Doc de origem, que também traz todas as
    variantes escritas.
    """
    saida: list[str] = []
    for bloco in blocos:
        _renderizar_bloco(bloco, contexto, saida, ignorar_regras, namespace)
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

    # O mesmo namespace que generation.py passa a substituir_placeholders para
    # a prosa deste macrotema. Tem de ser idêntico: é ele que decide se
    # "saneamento.$campo" resolve contra o contexto mesclado ou fica literal —
    # e, portanto, se o bloco é considerado sem dado.
    namespace = contrato.get("macrotema") or ""

    moldura = contrato.get("moldura") or {}
    for slot in SLOTS_MOLDURA:
        conteudo_slot = moldura.get(slot)
        if not conteudo_slot:
            continue
        texto = renderizar_blocos(
            conteudo_slot.get("blocos", []), contexto, ignorar_regras, namespace
        )
        if texto:
            partes.append(f"{slot} = {texto}\n@@")

    corpo = renderizar_blocos(
        (contrato.get("corpo") or {}).get("blocos", []),
        contexto,
        ignorar_regras,
        namespace,
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
            fontes.get("blocos", []), contexto, ignorar_regras, namespace
        )
        if texto_fontes:
            partes.append(texto_fontes)

    return "\n\n".join(partes)
