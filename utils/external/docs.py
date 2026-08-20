import json
import logging
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

from config import BASE_DIR

logger = logging.getLogger(__name__)

DOCS_CACHE_DIR = BASE_DIR / "output" / "docs_cache"


def _cache_path(doc_id: str) -> Path:
    return DOCS_CACHE_DIR / f"{doc_id}.json"


def _carregar_do_cache(doc_id: str) -> dict[str, str] | None:
    cache_path = _cache_path(doc_id)
    if not cache_path.exists():
        return None
    try:
        dados = json.loads(cache_path.read_text(encoding="utf-8"))
        if isinstance(dados, dict) and isinstance(dados.get("texto"), str):
            return {
                "texto": limpar_texto_exportado_docs(dados["texto"]),
                "timestamp": str(dados.get("timestamp", "")),
                "etag": str(dados.get("etag", "")),
                "last_modified": str(dados.get("last_modified", "")),
            }
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as e:
        logger.debug("Falha ao ler cache de docs (%s): %s", cache_path, e)
    return None


def _salvar_no_cache(
    doc_id: str,
    texto: str,
    *,
    etag: str | None = None,
    last_modified: str | None = None,
) -> None:
    try:
        DOCS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        dados = {
            "timestamp": time.time(),
            "texto": texto,
            "etag": etag,
            "last_modified": last_modified,
        }
        _cache_path(doc_id).write_text(
            json.dumps(dados, ensure_ascii=False), encoding="utf-8"
        )
    except (OSError, TypeError, ValueError) as e:
        logger.debug("Falha ao salvar cache de docs (%s): %s", _cache_path(doc_id), e)


def extrair_doc_id(link_ou_id: str) -> str:
    valor = link_ou_id.strip()
    parsed = urlparse(valor)
    if not parsed.scheme and "/" not in valor:
        return valor

    partes = [p for p in parsed.path.split("/") if p]
    if "d" in partes:
        idx = partes.index("d")
        if idx + 1 < len(partes):
            return partes[idx + 1]
    raise ValueError("Não foi possível extrair o ID do Google Docs.")


def linha_parece_comentario_docs(linha: str) -> bool:
    linha_limpa = linha.strip()
    if not linha_limpa:
        return False

    if re.match(r"^\[[A-Za-z0-9]{1,3}\]", linha_limpa):
        return True

    marcador_no_inicio = re.match(r"^\[[A-Za-z0-9]{1,3}\]\s+", linha_limpa)
    palavras_de_comentario = re.search(
        r"\b(coment[aá]rio|comment|resolvido|resolved|reply|responder)\b",
        linha_limpa,
        flags=re.IGNORECASE,
    )
    comentario_com_autor = re.match(r"^\[[A-Za-z0-9]{1,3}\]\s*[^:]{1,80}:\s+", linha_limpa)
    return bool(marcador_no_inicio and (palavras_de_comentario or comentario_com_autor))


def limpar_texto_exportado_docs(texto: str) -> str:
    texto = texto.lstrip("\ufeff")
    linhas_limpas = []
    for linha in texto.splitlines():
        if linha_parece_comentario_docs(linha):
            continue

        linha_sem_marcador = re.sub(r"(?<!\S)\[[A-Za-z0-9]{1,3}\](?!\S)", "", linha).rstrip()
        linhas_limpas.append(linha_sem_marcador)

    return "\n".join(linhas_limpas)


def _remover_separador_apos_marcador(bloco: str) -> str:
    """Remove só as quebras de linha e o separador curto "= texto" iniciais.

    O Google Docs converte um Tab digitado no início do parágrafo em recuo de
    formatação (não um caractere), que não sobrevive à exportação em texto
    puro — por isso um recuo intencional é digitado como 4+ espaços (ou um
    tab literal, se sobreviver). Isso precisa ser distinguido do espaço único
    de "marcador = texto", que deve ser removido normalmente.
    """
    bloco = bloco.lstrip("\n\r")
    if bloco.startswith("\t"):
        return bloco
    sem_espacos = bloco.lstrip(" ")
    n_espacos = len(bloco) - len(sem_espacos)
    if 0 < n_espacos < 4:
        return sem_espacos
    return bloco


def extrair_bloco_marcado(
    texto: str,
    marcador: str,
    exigir_fechamento: bool = False,
) -> tuple[str | None, str]:
    marcador_escapado = re.escape(marcador)
    fim = "@@" if exigir_fechamento else "@@|\\Z"
    padrao = re.compile(
        rf"(?is){marcador_escapado}\s*=(.*?)(?:{fim})"
    )
    match = padrao.search(texto)
    if not match:
        return None, texto

    bloco = _remover_separador_apos_marcador(match.group(1)).rstrip()
    if len(bloco) >= 2 and (bloco[0], bloco[-1]) in {
        ('"', '"'),
        ("'", "'"),
        ("“", "”"),
    }:
        bloco = _remover_separador_apos_marcador(bloco[1:-1]).rstrip()
    else:
        bloco = _remover_separador_apos_marcador(
            bloco.removeprefix("“").removesuffix("”")
        ).rstrip()
    texto_sem_bloco = (texto[:match.start()] + texto[match.end():]).strip()
    return bloco or None, texto_sem_bloco


def extrair_resumo_tema(texto: str) -> tuple[str | None, str]:
    resumo, texto_sem_resumo = extrair_bloco_marcado(texto, "resumo_tema")
    if resumo:
        resumo = re.sub(r"\s+", " ", resumo).strip()
    return resumo, texto_sem_resumo


def extrair_descricao_tema(texto: str) -> tuple[str | None, str]:
    blocos: list[str] = []
    texto_restante = texto
    while True:
        bloco, novo_texto = extrair_bloco_marcado(texto_restante, "descricao_tema")
        if not bloco:
            break
        blocos.append(bloco)
        texto_restante = novo_texto
    return ("\n\n".join(blocos) or None), texto_restante

def extrair_relatorio_geral(texto: str) -> tuple[str | None, str]:
    apresentacao, texto_sem_apresentacao = extrair_bloco_marcado(texto, "apresentacao")
    if apresentacao:
        _, texto_sem_legado = extrair_bloco_marcado(
            texto_sem_apresentacao, "relatorio_geral"
        )
        return apresentacao, texto_sem_legado
    return extrair_bloco_marcado(texto, "relatorio_geral")


def extrair_inicio_relatorio(texto: str) -> tuple[str | None, str]:
    padrao = re.compile(
        r"(?ims)^\s*inicio_relatorio\s*=(.*?)(?=^\s*[a-z_]+\s*=|^\s*#!|\Z)"
    )
    match = padrao.search(texto)
    if not match:
        return None, texto

    bloco = _remover_separador_apos_marcador(match.group(1)).rstrip().removesuffix("@@").rstrip()
    texto_sem_bloco = (texto[:match.start()] + texto[match.end():]).strip()
    return bloco or None, texto_sem_bloco


def extrair_introducao(texto: str) -> tuple[str | None, str]:
    padrao = re.compile(
        r"(?ims)^\s*introducao\s*=(.*?)(?=^\s*[a-z_]+\s*=|^\s*#!|\Z)"
    )
    match = padrao.search(texto)
    if not match:
        return None, texto

    bloco = _remover_separador_apos_marcador(match.group(1)).rstrip().removesuffix("@@").rstrip()
    if len(bloco) >= 2 and (bloco[0], bloco[-1]) in {
        ('"', '"'),
        ("'", "'"),
        ("“", "”"),
    }:
        bloco = _remover_separador_apos_marcador(bloco[1:-1]).rstrip()
    else:
        bloco = _remover_separador_apos_marcador(
            bloco.removeprefix("“").removesuffix("”")
        ).rstrip()

    texto_sem_bloco = (texto[:match.start()] + texto[match.end():]).strip()
    return bloco or None, texto_sem_bloco


def extrair_resumo_relatorio(texto: str) -> tuple[str | None, str]:
    return extrair_bloco_marcado(texto, "resumo_relatorio")


def extrair_resumo_cidade(texto: str) -> tuple[str | None, str]:
    return extrair_bloco_marcado(texto, "resumo_cidade")


def extrair_diagnostico_cidade(texto: str) -> tuple[str | None, str]:
    return extrair_bloco_marcado(texto, "diagnostico_cidade")


def extrair_referencias(texto: str) -> tuple[list[str], str]:
    referencias: list[str] = []
    texto_restante = texto
    while True:
        bloco, novo_texto = extrair_bloco_marcado(texto_restante, "referencia")
        if not bloco:
            break
        referencias.extend(
            linha.strip()
            for linha in bloco.splitlines()
            if linha.strip()
        )
        texto_restante = novo_texto
    return referencias, texto_restante


def remover_titulos_docs(texto: str, *titulos: str) -> str:
    if not titulos:
        return texto
    alternativas = "|".join(re.escape(titulo) for titulo in titulos)
    return re.sub(
        rf"(?im)^\s*(?:#!\s*)?(?:{alternativas})\s*$\n?",
        "",
        texto,
    ).strip()


async def carregar_texto_do_docs(link_ou_id: str) -> str:
    doc_id = extrair_doc_id(link_ou_id)

    cache = _carregar_do_cache(doc_id)
    export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"

    headers: dict[str, str] = {}
    if cache:
        if cache.get("etag"):
            headers["If-None-Match"] = cache["etag"]
        if cache.get("last_modified"):
            headers["If-Modified-Since"] = cache["last_modified"]

    texto: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    not_modified = False

    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.get(export_url, headers=headers)
            if response.status_code == 304 and cache is not None:
                not_modified = True
                texto = cache["texto"]
            else:
                response.raise_for_status()
                texto = response.text
                etag = response.headers.get("ETag")
                last_modified = response.headers.get("Last-Modified")
    except httpx.HTTPStatusError as err:
        status = err.response.status_code if err.response is not None else 0
        if status in (401, 403):
            raise ValueError(
                "Google Docs sem acesso público para exportação. "
                "Defina o documento como 'Qualquer pessoa com o link - Leitor' "
                "ou use um documento publicado na web."
            ) from err
        if status == 404:
            raise ValueError("Documento do Google Docs não encontrado (404). Verifique o link/ID.") from err
        if cache is not None:
            logger.warning(
                "Falha ao acessar o Google Docs %s (status %s); usando cache local temporariamente.",
                doc_id,
                status,
            )
            return cache["texto"]
        raise ValueError(f"Erro ao exportar Google Docs ({status}). Verifique o link e as permissões.") from err
    except (httpx.HTTPError, TimeoutError) as err:
        if cache is not None:
            logger.warning(
                "Falha ao acessar o Google Docs %s; usando cache local temporariamente.",
                doc_id,
            )
            return cache["texto"]
        raise ValueError("Não foi possível acessar o Google Docs. Verifique a conexão, o link e as permissões.") from err

    if not_modified:
        cache_path = _cache_path(doc_id)
        try:
            dados = json.loads(cache_path.read_text(encoding="utf-8"))
            dados["timestamp"] = time.time()
            cache_path.write_text(
                json.dumps(dados, ensure_ascii=False), encoding="utf-8"
            )
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            logger.debug("Falha ao atualizar timestamp do cache de docs (%s)", cache_path)
        return texto or ""

    texto_limpo = limpar_texto_exportado_docs(texto or "")
    if cache is None or texto_limpo != cache["texto"]:
        _salvar_no_cache(doc_id, texto_limpo, etag=etag, last_modified=last_modified)
    else:
        _salvar_no_cache(
            doc_id,
            texto_limpo,
            etag=etag or cache.get("etag"),
            last_modified=last_modified or cache.get("last_modified"),
        )
    return texto_limpo
