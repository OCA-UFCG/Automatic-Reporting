"""Serviço do painel editorial: autenticação, contratos e prévia.

Autenticação deliberadamente simples, como foi decidido: **sem papéis**. São
poucas pessoas e todas escrevem e publicam. O login pede um nome — não para
autorizar nada, mas para que ``publicado_por`` diga quem fez a alteração — e uma
senha compartilhada, vinda de ``PAINEL_SENHA``.

Sem ``PAINEL_SENHA`` configurada o painel **não abre**. Falhar fechado é a
escolha certa aqui: o que se edita nesta tela sai publicado em relatório.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import re
import secrets
import time
from datetime import datetime
from typing import Any

from fastapi import HTTPException

from config import CONTRATOS_DIR, PAINEL_SEGREDO, PAINEL_SENHA
from utils.data.macrotemas import MACROTEMAS
from utils.editorial.contrato import ErroDeContrato, novo_contrato, validar_contrato
from utils.editorial.repositorio import ConflitoDeVersao, RepositorioDeContratos
from utils.external.editorial import fonte_editorial
from utils.geografia import separar_cidade_uf

logger = logging.getLogger(__name__)

# Um `$campo` que sobreviveu à renderização — com ou sem namespace na frente.
_PLACEHOLDER_CRU = re.compile(r"(?:[A-Za-z_][\w-]*\.)?\$([A-Za-z_]\w*)")

repositorio = RepositorioDeContratos(CONTRATOS_DIR)

VALIDADE_DO_TOKEN_EM_SEGUNDOS = 12 * 60 * 60


# -- autenticação ---------------------------------------------------------


def _segredo() -> bytes:
    if PAINEL_SEGREDO:
        return PAINEL_SEGREDO.encode("utf-8")
    # Sem segredo fixo, deriva-se um da senha: os tokens deixam de valer quando
    # a senha muda, que é o comportamento desejado de qualquer forma.
    return hashlib.sha256((PAINEL_SENHA or "").encode("utf-8")).digest()


def _exigir_painel_configurado() -> None:
    if not PAINEL_SENHA:
        raise HTTPException(
            status_code=503,
            detail=(
                "Painel editorial desativado: defina PAINEL_SENHA no .env. "
                "Sem senha o painel não abre, porque o que se edita aqui vai "
                "publicado em relatório."
            ),
        )


def emitir_token(nome: str) -> str:
    conteudo = json.dumps(
        {"nome": nome, "expira": int(time.time()) + VALIDADE_DO_TOKEN_EM_SEGUNDOS},
        ensure_ascii=False,
    ).encode("utf-8")
    corpo = base64.urlsafe_b64encode(conteudo).decode("ascii").rstrip("=")
    assinatura = hmac.new(_segredo(), corpo.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{corpo}.{assinatura}"


def verificar_token(token: str | None) -> str:
    _exigir_painel_configurado()
    if not token:
        raise HTTPException(status_code=401, detail="Faça login no painel.")

    token = token.removeprefix("Bearer ").strip()
    corpo, _, assinatura = token.partition(".")
    esperada = hmac.new(_segredo(), corpo.encode("ascii"), hashlib.sha256).hexdigest()
    # compare_digest: comparar assinatura com "==" vaza informação pelo tempo.
    if not corpo or not hmac.compare_digest(assinatura, esperada):
        raise HTTPException(status_code=401, detail="Sessão inválida. Faça login de novo.")

    preenchimento = "=" * (-len(corpo) % 4)
    try:
        dados = json.loads(base64.urlsafe_b64decode(corpo + preenchimento))
    except (ValueError, json.JSONDecodeError) as err:
        raise HTTPException(status_code=401, detail="Sessão inválida.") from err

    if dados.get("expira", 0) < time.time():
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login de novo.")

    return dados.get("nome") or "desconhecido"


def login_handler(nome: str, senha: str) -> dict[str, Any]:
    _exigir_painel_configurado()
    nome = (nome or "").strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Informe seu nome.")

    if not secrets.compare_digest(senha or "", PAINEL_SENHA or ""):
        logger.warning("Tentativa de login no painel com senha incorreta (nome=%r)", nome)
        raise HTTPException(status_code=401, detail="Senha incorreta.")

    return {"token": emitir_token(nome), "nome": nome}


# -- contratos ------------------------------------------------------------


def listar_contratos_handler() -> list[dict[str, Any]]:
    temas = []
    for slug, dados in MACROTEMAS.items():
        temas.append(
            {
                "slug": slug,
                "nome": dados["nome"],
                "cor": dados["cor"],
                "icone": dados["icone"],
                "fonte_editorial": fonte_editorial(slug),
                "tem_doc": bool(dados["docs_url"]),
                "contrato": repositorio.metadados(slug),
            }
        )
    return temas


def _exigir_macrotema(slug: str) -> dict:
    if slug not in MACROTEMAS:
        raise HTTPException(status_code=404, detail=f"Macrotema desconhecido: {slug}")
    return MACROTEMAS[slug]


def ler_contrato_handler(slug: str) -> dict[str, Any]:
    _exigir_macrotema(slug)
    contrato = repositorio.ler(slug)
    if contrato is None:
        # Tema ainda não importado: o painel abre num contrato vazio e válido em
        # vez de dar 404, para que dê para começar do zero se for o caso.
        return {"contrato": novo_contrato(slug), "novo": True}
    return {"contrato": contrato, "novo": False}


def historico_handler(slug: str) -> list[dict[str, Any]]:
    _exigir_macrotema(slug)
    return repositorio.historico(slug)


def ler_versao_handler(slug: str, versao: int) -> dict[str, Any]:
    _exigir_macrotema(slug)
    contrato = repositorio.ler_versao(slug, versao)
    if contrato is None:
        raise HTTPException(status_code=404, detail=f"Versão {versao} não encontrada.")
    return contrato


def validar_handler(contrato: dict) -> dict[str, Any]:
    erros = validar_contrato(contrato)
    return {"valido": not erros, "erros": erros}


def publicar_contrato_handler(
    slug: str, contrato: dict, versao_esperada: int | None, autor: str
) -> dict[str, Any]:
    _exigir_macrotema(slug)

    if contrato.get("macrotema") != slug:
        raise HTTPException(
            status_code=400,
            detail=f"O contrato diz ser de '{contrato.get('macrotema')}', não de '{slug}'.",
        )

    try:
        publicado = repositorio.publicar(slug, contrato, autor, versao_esperada)
    except ConflitoDeVersao as err:
        raise HTTPException(
            status_code=409,
            detail={
                "mensagem": str(err),
                "versao_atual": err.versao_atual,
                "versao_esperada": err.versao_esperada,
                "publicado_por": err.autor,
            },
        ) from err
    except ErroDeContrato as err:
        raise HTTPException(status_code=422, detail=str(err)) from err

    logger.info(
        "Painel: '%s' publicado na versão %s por %s",
        slug,
        publicado["versao"],
        autor,
    )
    return publicado


async def importar_do_doc_handler(slug: str, baixar: bool) -> dict[str, Any]:
    """Traz o Google Doc do tema para dentro do contrato, sem publicar.

    O resultado volta para o painel como rascunho: quem revisa as divergências
    e decide publicar é a pessoa, não o importador.
    """
    dados = _exigir_macrotema(slug)
    from utils.editorial.importador import importar_texto
    from utils.external.docs import _cache_path, carregar_texto_do_docs, extrair_doc_id

    if not dados["docs_url"]:
        raise HTTPException(
            status_code=400,
            detail=f"{dados['docs_env']} não configurado: não há Doc para importar.",
        )

    if baixar:
        try:
            texto = await carregar_texto_do_docs(dados["docs_url"])
        except ValueError as err:
            raise HTTPException(status_code=502, detail=str(err)) from err
    else:
        caminho = _cache_path(extrair_doc_id(dados["docs_url"]))
        if not caminho.exists():
            raise HTTPException(
                status_code=404,
                detail="Sem cópia local deste Doc. Use a opção de baixar do Google Docs.",
            )
        texto = json.loads(caminho.read_text(encoding="utf-8"))["texto"]

    resultado = importar_texto(texto, slug)
    atual = repositorio.ler(slug)
    if atual:
        # Importar não reinicia a contagem: o rascunho continua a partir da
        # versão publicada, e é ela que a concorrência otimista vai conferir.
        resultado.contrato["versao"] = atual["versao"]

    return {
        "contrato": resultado.contrato,
        "divergencias": [
            {
                "tipo": d.tipo,
                "linha": d.linha,
                "trecho": d.trecho,
                "legado": d.legado,
                "contrato": d.contrato,
                "prova": d.prova,
            }
            for d in resultado.divergencias
        ],
    }


# -- prévia ---------------------------------------------------------------


def montar_contexto_de_previa(slug: str, cidade: str) -> tuple[dict, str | None]:
    """Dados reais do município para a prévia — o mesmo contexto do relatório.

    Usa `montar_linhas_macrotema`, a mesma função que `gerar_relatorio_handler`
    chama. Isso não é preciosismo: uma versão reduzida aqui já custou caro. A
    prévia consultava só a view do perfil e parava aí — sem fallback para CSV e
    sem as consultas de enriquecimento — então ficava com dois campos enquanto o
    relatório tinha dezenas, e o editor via `$placeholder` cru na tela achando
    que o contrato estava errado.
    """
    from services.contexto import (
        ORIGEM_CSV_SEM_BANCO,
        ORIGEM_CSV_SEM_CIDADE,
        CacheDeEnriquecimento,
        montar_linhas_macrotema,
    )
    from services.macrotemas import get_macrotema

    macrotema_dados = get_macrotema(slug)
    try:
        linhas, origem = montar_linhas_macrotema(
            slug,
            macrotema_dados,
            cidade,
            datetime.now().astimezone(),
            [slug],
            CacheDeEnriquecimento(),
        )
    except HTTPException:
        raise
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    contexto = dict(linhas[0])

    nome, uf = separar_cidade_uf(cidade)
    contexto.setdefault("nm_mun", f"{nome} ({uf})" if uf else nome)
    if uf:
        contexto.setdefault("sigla_uf", uf)

    # O aviso não é sobre "ter dado ou não" — é sobre de onde ele veio. Com o
    # túnel fora do ar o relatório cai para o CSV e continua saindo, mas com
    # menos campos do que a view entrega; o editor precisa saber que o que ele
    # está vendo é o cenário degradado, não o definitivo.
    aviso = None
    if origem == ORIGEM_CSV_SEM_BANCO:
        aviso = (
            "Sem conexão com o banco do Data Nordeste: a prévia está usando a "
            "planilha CSV, igual ao que o relatório faz nessa situação. Campos "
            "que só existem na view aparecem como placeholder. Confira se o "
            "túnel SSH está aberto na porta configurada em DB_PORT."
        )
    elif origem == ORIGEM_CSV_SEM_CIDADE:
        aviso = (
            f"O banco respondeu, mas não tem '{cidade}' na view deste "
            "macrotema. A prévia está usando a planilha CSV, igual ao que o "
            "relatório faz nessa situação."
        )
    return contexto, aviso


async def previa_handler(slug: str, contrato: dict, cidade: str) -> dict[str, Any]:
    """Gera o relatório de verdade com o contrato **em edição**.

    Não é uma aproximação do relatório: é o relatório. Roda
    `gerar_relatorio_handler`, o mesmo caminho que atende o portal — mesma
    montagem de contexto, mesmos gráficos, mesma capa, mesmo SSR em React. A
    única diferença é que a prosa do macrotema vem do contrato que o editor
    ainda não publicou, injetado por `contrato_em_edicao`.

    Isso importa porque a pergunta que o editor faz é "como vai ficar?", e
    qualquer renderização paralela responde a uma pergunta diferente — foi
    assim que a prévia antiga passou a divergir do relatório sem ninguém notar.

    Os artefatos saem com prefixo `previa__` para nunca sobrescrever o
    `output/relatorio_<tema>__<cidade>.pdf` que o portal entrega ao público, e
    o PDF não é gerado: o HTML é a fonte dele, então o conteúdo é o mesmo e o
    editor não espera a conversão.
    """
    _exigir_macrotema(slug)
    from services.generation import gerar_relatorio_handler
    from utils.external.editorial import contrato_em_edicao

    erros = validar_contrato(contrato)
    if erros:
        raise HTTPException(
            status_code=422, detail={"mensagem": "Contrato inválido", "erros": erros}
        )

    _, aviso = montar_contexto_de_previa(slug, cidade)

    with contrato_em_edicao(slug, contrato):
        resposta = await gerar_relatorio_handler(
            cidade, macrotema=slug, prefixo_artefato="previa__", gerar_pdf=False
        )

    html = resposta.body.decode("utf-8")

    # Placeholders que sobraram crus são a informação mais útil da prévia: cada
    # um é um campo que não existe para este município.
    nao_resolvidos = sorted(set(_PLACEHOLDER_CRU.findall(html)))

    return {
        "html": html,
        "aviso": aviso,
        "campos_nao_resolvidos": nao_resolvidos,
    }


# -- conexão com o banco --------------------------------------------------
#
# O painel lê o /manifesto uma vez, quando a aba abre. Se o túnel subir depois
# disso, a tela continua mostrando a lista de campos do CSV e parece quebrada,
# mesmo com o backend já enxergando o banco. Este handler existe para que o
# editor reconfira sem recarregar a página e perder o que estava escrevendo.
#
# Ele apenas *consulta* o estado. Abrir o túnel continua sendo trabalho de um
# terminal, por dois motivos: um endpoint HTTP que dispara processos é
# superfície que este serviço não precisa ter, e a chave usada aqui pede
# passphrase — que só uma pessoa num terminal pode digitar.


def conexao_handler() -> dict[str, Any]:
    """Estado atual da conexão com o banco do Data Nordeste.

    Devolve também o comando do túnel já montado com o host e a porta que este
    processo realmente está tentando usar, lidos da configuração. Assim o que a
    tela manda copiar nunca diverge do que a aplicação procura.
    """
    import psycopg2

    from config import DB_HOST, DB_PORT
    from utils.database import get_connection

    detalhe = ""
    conectado = False
    try:
        conexao = get_connection()
    except psycopg2.Error as err:
        detalhe = str(err).strip().splitlines()[0]
    else:
        try:
            with conexao.cursor() as cursor:
                cursor.execute("SELECT version()")
                versao = cursor.fetchone()[0]
            conectado = True
            detalhe = versao.split(",")[0]
        finally:
            conexao.close()

    return {
        "conectado": conectado,
        "detalhe": detalhe,
        "host": DB_HOST,
        "porta": DB_PORT,
        "comando_tunel": (
            "ssh -o IdentityAgent=none -o IdentitiesOnly=yes -i ~/.ssh/<sua-chave> "
            f"-N -L {DB_PORT}:127.0.0.1:5432 ubuntu@10.5.8.5"
        ),
    }
