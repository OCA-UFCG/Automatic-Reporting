import re
from urllib.parse import urlparse
from urllib.request import urlopen
from urllib.error import URLError, HTTPError


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


def carregar_texto_do_docs(link_ou_id: str) -> str:
    doc_id = extrair_doc_id(link_ou_id)
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

    return limpar_texto_exportado_docs(texto)