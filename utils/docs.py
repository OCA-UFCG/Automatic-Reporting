import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

from config import BASE_DIR


DOCS_CACHE_DIR = BASE_DIR / "output" / "docs_cache"
DOCS_CACHE_TTL = 3600  # 1 hour


def _cache_path(doc_id: str) -> Path:
    return DOCS_CACHE_DIR / f"{doc_id}.json"


def _carregar_do_cache(doc_id: str) -> str | None:
    cache_path = _cache_path(doc_id)
    if not cache_path.exists():
        return None
    try:
        dados = json.loads(cache_path.read_text(encoding="utf-8"))
        if time.time() - dados["timestamp"] < DOCS_CACHE_TTL:
            return dados["texto"]
    except Exception:
        pass
    return None


def _salvar_no_cache(doc_id: str, texto: str) -> None:
    try:
        DOCS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        dados = {"timestamp": time.time(), "texto": texto}
        _cache_path(doc_id).write_text(
            json.dumps(dados, ensure_ascii=False), encoding="utf-8"
        )
    except Exception:
        pass


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
    linhas_limpas = []
    for linha in texto.splitlines():
        if linha_parece_comentario_docs(linha):
            continue

        linha_sem_marcador = re.sub(r"(?<!\S)\[[A-Za-z0-9]{1,3}\](?!\S)", "", linha).rstrip()
        linhas_limpas.append(linha_sem_marcador)

    return "\n".join(linhas_limpas)


def extrair_bloco_marcado(
    texto: str,
    marcador: str,
    exigir_fechamento: bool = False,
) -> tuple[str | None, str]:
    marcador_escapado = re.escape(marcador)
    fim = "@@" if exigir_fechamento else "@@|\\Z"
    padrao = re.compile(
        rf"(?is){marcador_escapado}\s*=\s*(.*?)(?:{fim})"
    )
    match = padrao.search(texto)
    if not match:
        return None, texto

    bloco = match.group(1).strip()
    texto_sem_bloco = (texto[:match.start()] + texto[match.end():]).strip()
    return bloco or None, texto_sem_bloco


def extrair_resumo_tema(texto: str) -> tuple[str | None, str]:
    resumo, texto_sem_resumo = extrair_bloco_marcado(texto, "resumo_tema")
    if resumo:
        resumo = re.sub(r"\s+", " ", resumo).strip()
    return resumo, texto_sem_resumo


def extrair_descricao_tema(texto: str) -> tuple[str | None, str]:
    return extrair_bloco_marcado(texto, "descricao_tema")

def extrair_resumo_relatorio(texto: str) -> tuple[str | None, str]:
    return extrair_bloco_marcado(texto, "resumo_relatorio")


def extrair_resumo_cidade(texto: str) -> tuple[str | None, str]:
    return extrair_bloco_marcado(texto, "resumo_cidade")


def extrair_diagnostico_cidade(texto: str) -> tuple[str | None, str]:
    return extrair_bloco_marcado(texto, "diagnostico_cidade")


def carregar_texto_do_docs(link_ou_id: str) -> str:
    doc_id = extrair_doc_id(link_ou_id)

    texto_cache = _carregar_do_cache(doc_id)
    if texto_cache is not None:
        return texto_cache
    export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
    try:
        with urlopen(export_url, timeout=20) as response:
            texto = response.read().decode("utf-8")
    except HTTPError as err:
        if err.code in (401, 403):
            raise ValueError(
                "Google Docs sem acesso público para exportação. "
                "Defina o documento como 'Qualquer pessoa com o link - Leitor' "
                "ou use um documento publicado na web."
            ) from err
        if err.code == 404:
            raise ValueError("Documento do Google Docs não encontrado (404). Verifique o link/ID.") from err
        raise ValueError(f"Erro ao exportar Google Docs ({err.code}). Verifique o link e as permissões.") from err
    except (URLError, TimeoutError) as err:
        raise ValueError("Não foi possível acessar o Google Docs. Verifique a conexão, o link e as permissões.") from err

    texto = limpar_texto_exportado_docs(texto)
    _salvar_no_cache(doc_id, texto)
    return texto
