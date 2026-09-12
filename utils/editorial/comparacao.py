"""O que conta como "o mesmo texto" para este pipeline.

Tanto a conferência de importação quanto a de paridade precisam responder à
mesma pergunta: dois textos produzem o mesmo relatório? Nem toda diferença de
caractere conta. O pipeline aceita duas grafias para o marcador de gráfico
(``*nome`` e ``%%nome``), três para item de lista (``-``, ``•``, ``*``) e ignora
recuo e linhas em branco. Normalizar essas formas num só lugar evita que as
ferramentas acusem perda onde só houve troca de estilo — e deixa explícito, num
lugar só, o que de fato é equivalente.
"""

from __future__ import annotations

import re

_MARCADOR_GRAFICO = re.compile(r"^(?:\*|%%)([a-z_][a-z0-9_]*)$", re.IGNORECASE)
_ITEM_DE_LISTA = re.compile(r"^(?:[-•]|\*)\s+(.*)$")


def normalizar_linha(linha: str) -> str:
    limpa = linha.strip()

    grafico = _MARCADOR_GRAFICO.match(limpa)
    if grafico:
        return f"*{grafico.group(1)}"

    item = _ITEM_DE_LISTA.match(limpa)
    if item:
        return f"- {item.group(1).strip()}"

    # Espaços repetidos aparecem no meio da prosa dos Docs ("de  0%") e somem
    # na reconstrução; não mudam o HTML nem o PDF.
    return re.sub(r"\s+", " ", limpa)


def normalizar_texto(texto: str) -> list[str]:
    """Linhas significativas do texto, na forma canônica."""
    return [
        normalizada
        for linha in texto.splitlines()
        if (normalizada := normalizar_linha(linha))
    ]
