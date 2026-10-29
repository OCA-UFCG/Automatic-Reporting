"""Laboratório de Temas: conferência do texto de um tema contra os 2.074 municípios.

O texto passa inteiro, município a município, pelo mesmo caminho do relatório
(texto_final_do_tema), com o contexto do snapshot. Avaliar condição por condição
divergiria do relatório: interpretar_blocos_condicionais tem estado entre linhas
(spec do laboratório, "Conferência pelo gerador"). Nada aqui escreve em banco, Doc
ou cache.
"""

import logging
import re
from collections.abc import Callable

from services.generation import separar_secoes_do_tema
from utils.render.placeholders import conferir_condicoes, registrar_versoes
from utils.render.renderer import texto_final_do_tema

logger = logging.getLogger(__name__)

# "$campo" ou "tema.$campo" que sobrou no texto final: não resolveu neste município.
_CAMPO_CRU = re.compile(r"(?:\b\w+\.)?\$([A-Za-z_]\w*)")
# Sem âncora de linha: extrair_resumo_tema junta o resumo numa linha só.
_CONDICAO_NO_TEXTO = re.compile(r"(?i)\bpara(?:\s+quando)?\s+[^:]*\$\w+[^:]*:")


def conferir_municipio(descricao_tema: str, contexto: dict, slug: str) -> dict:
    """Texto final do tema num município, as versões avaliadas (condição, disparou)
    na ordem do texto e os campos que ficaram crus."""
    with registrar_versoes() as versoes:
        partes = texto_final_do_tema(descricao_tema, contexto, slug)
    return {
        "partes": partes,
        "versoes": versoes,
        "campos_crus": sorted(set(_CAMPO_CRU.findall("\n".join(partes)))),
    }


def conferir_tema(
    descricao_tema: str,
    slug: str,
    contextos: dict[str, dict],
    progresso: Callable[[int, int], None] | None = None,
) -> dict:
    """Agrega conferir_municipio sobre todos os municípios do snapshot.

    Devolve as versões com quantos municípios cada uma pega, quais versões
    dispararam em cada município (índices; a tela conta "sem versão" e "2+" por
    bloco, um conceito só dela) e os campos crus, separando o que não existe em
    nenhum contexto do que só está vazio em alguns. O texto de cada município não
    vem junto (~10 MB por tema): a tela pede um município por vez.
    """
    condicoes: list[str] | None = None
    contagem: list[int] = []
    versoes_por_municipio: dict[str, list[int]] = {}
    crus: dict[str, list[str]] = {}
    erros: dict[str, str] = {}
    for feitos, (cidade, contexto) in enumerate(contextos.items(), start=1):
        try:
            resultado = conferir_municipio(descricao_tema, contexto, slug)
        except Exception as err:  # um município quebrado não derruba a conferência
            logger.exception("conferência %s: erro em %s", slug, cidade)
            erros[cidade] = f"{type(err).__name__}: {err}"
            continue
        if condicoes is None:
            condicoes = [condicao for condicao, _ in resultado["versoes"]]
            contagem = [0] * len(condicoes)
        elif [condicao for condicao, _ in resultado["versoes"]] != condicoes:
            # Toda linha de condição é avaliada em todo município; se a sequência
            # mudar, os índices não batem e a contagem sairia errada sem aviso.
            erros[cidade] = "sequência de versões diferente da do primeiro município"
            continue
        disparadas = [i for i, (_, disparou) in enumerate(resultado["versoes"]) if disparou]
        for i in disparadas:
            contagem[i] += 1
        versoes_por_municipio[cidade] = disparadas
        for campo in resultado["campos_crus"]:
            crus.setdefault(campo, []).append(cidade)
        if progresso:
            progresso(feitos, len(contextos))

    campos_conhecidos = set().union(*contextos.values()) if contextos else set()
    return {
        "versoes": [
            {"condicao": condicao, "municipios": n}
            for condicao, n in zip(condicoes or [], contagem, strict=True)
        ],
        "versoes_por_municipio": versoes_por_municipio,
        "campos_crus": [
            {"campo": campo, "existe": campo in campos_conhecidos, "municipios": cidades}
            for campo, cidades in sorted(crus.items())
        ],
        "condicoes_nao_entendidas": conferir_condicoes(descricao_tema),
        "erros": erros,
    }


def conferir_doc(
    doc_texto: str,
    slug: str,
    contextos: dict[str, dict],
    progresso: Callable[[int, int], None] | None = None,
) -> dict:
    """Conferência do Doc inteiro do tema: o texto principal e as condições escritas
    no resumo do tema, que só passa por substituir_placeholders e mostraria o
    "Para quando ...:" cru no relatório (generation.py, `resumo_tema`)."""
    secoes, graficos_sem_legenda = separar_secoes_do_tema(doc_texto, slug)
    conferencia = conferir_tema(secoes.descricao_tema or "", slug, contextos, progresso)
    conferencia["condicoes_sem_efeito"] = _CONDICAO_NO_TEXTO.findall(secoes.resumo_tema or "")
    conferencia["graficos_sem_legenda"] = graficos_sem_legenda
    return conferencia
