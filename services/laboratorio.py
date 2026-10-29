"""Laboratório de Temas: conferência do texto de um tema contra os 2.074 municípios.

O texto passa inteiro, município a município, pelo mesmo caminho do relatório
(texto_final_do_tema), com o contexto do snapshot. Avaliar condição por condição
divergiria do relatório: interpretar_blocos_condicionais tem estado entre linhas
(spec do laboratório, "Conferência pelo gerador"). Nada aqui escreve em banco, Doc
ou cache; só o estado das conferências, em output/laboratorio/conferencias/.
"""

import fcntl
import hashlib
import json
import logging
import os
import re
import threading
import time
import uuid
from collections import Counter
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path

from services.generation import separar_secoes_do_tema
from services.laboratorio_snapshot import SNAPSHOT_DIR, carregar_snapshot
from services.macrotemas import get_macrotema
from utils.external.docs import baixar_doc
from utils.render.placeholders import (
    _numero_do_campo,
    conferir_condicoes,
    registrar_versoes,
)
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


# --- Conferência em segundo plano (decisão do André, 29/10/2026) ---
# O tema inteiro leva ~25 s (demografia, local; ~40 s estimados no gamma), demais para
# uma requisição: a conferência roda numa thread e a tela acompanha o progresso. O
# estado vai para arquivo, e não para a memória, porque o gamma tem 3 workers do
# uvicorn e o polling pode cair em outro processo. O flock deixa uma conferência por
# vez na máquina inteira (1 núcleo; o banco divide o host): a segunda espera na fila.
CONFERENCIAS_DIR = SNAPSHOT_DIR / "conferencias"
_LOCK = CONFERENCIAS_DIR / ".lock"
_ID_VALIDO = re.compile(r"^[0-9a-f]{32}$")
_GRAVAR_A_CADA = 50
_VALIDADE_S = 24 * 3600
# Worker morto no meio (oomd, deploy) deixa o arquivo parado em "rodando" ou
# "na_fila" para sempre. Rodando, ele é regravado a cada 50 municípios (segundos);
# na fila, espera uma conferência inteira (~40 s no gamma) por vez à frente.
_PARADA_MAX_S = {"rodando": 120, "na_fila": 900}


def _caminho(id_conferencia: str) -> Path:
    return CONFERENCIAS_DIR / f"{id_conferencia}.json"


def _gravar(id_conferencia: str, estado: dict) -> None:
    temporario = _caminho(id_conferencia).with_suffix(".tmp")
    temporario.write_text(json.dumps(estado, ensure_ascii=False), encoding="utf-8")
    os.replace(temporario, _caminho(id_conferencia))  # quem lê nunca vê pela metade


def ler_conferencia(id_conferencia: str) -> dict | None:
    if not _ID_VALIDO.match(id_conferencia):  # o id vira nome de arquivo
        return None
    caminho = _caminho(id_conferencia)
    try:
        estado = json.loads(caminho.read_text(encoding="utf-8"))
        parada = time.time() - caminho.stat().st_mtime
    except FileNotFoundError:
        return None
    if parada > _PARADA_MAX_S.get(estado["estado"], float("inf")):
        return {"estado": "erro", "erro": "conferência interrompida (o servidor reiniciou?)"}
    return estado


def _apagar_antigas() -> None:
    limite = time.time() - _VALIDADE_S
    for arquivo in CONFERENCIAS_DIR.glob("*.json"):
        if arquivo.stat().st_mtime < limite:
            arquivo.unlink(missing_ok=True)


def _rodar(id_conferencia: str, slug: str, doc_texto: str) -> None:
    with open(_LOCK, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)  # espera a conferência anterior acabar
        try:
            snapshot = carregar_snapshot(slug)
            if snapshot is None:
                _gravar(id_conferencia, {"estado": "erro", "erro": "tema sem snapshot"})
                return
            contextos = {cidade: m["contexto"] for cidade, m in snapshot["municipios"].items()}

            def progresso(feitos: int, total: int) -> None:
                if feitos % _GRAVAR_A_CADA == 0:
                    _gravar(id_conferencia, {"estado": "rodando", "feitos": feitos, "total": total})

            _gravar(id_conferencia, {"estado": "rodando", "feitos": 0, "total": len(contextos)})
            resultado = conferir_doc(doc_texto, slug, contextos, progresso)
            _gravar(id_conferencia, {
                "estado": "pronta",
                "feitos": len(contextos),
                "total": len(contextos),
                "snapshot_gerado_em": snapshot["gerado_em"],
                "resultado": resultado,
            })
        except Exception as err:  # a tela precisa saber que acabou, mesmo com erro
            logger.exception("conferência %s (%s) falhou", id_conferencia, slug)
            _gravar(id_conferencia, {"estado": "erro", "erro": f"{type(err).__name__}: {err}"})


def iniciar_conferencia(slug: str, doc_texto: str) -> str:
    CONFERENCIAS_DIR.mkdir(parents=True, exist_ok=True)
    _apagar_antigas()
    id_conferencia = uuid.uuid4().hex
    _gravar(id_conferencia, {"estado": "na_fila"})
    threading.Thread(
        target=_rodar, args=(id_conferencia, slug, doc_texto),
        name=f"conferencia:{slug}", daemon=True,
    ).start()
    return id_conferencia


def texto_do_municipio(slug: str, doc_texto: str, cidade: str) -> dict | None:
    """Texto final do tema numa cidade, para "texto pronto numa cidade" e "ler com
    cada valor". None se o tema não tem snapshot ou a cidade não está nele.

    ponytail: lê o snapshot inteiro a cada chamada (~0,5 s local). Cache por processo
    custaria ~100 MB × 3 workers num host que já sofreu com memória; cachear se a
    tela ficar lenta.
    """
    snapshot = carregar_snapshot(slug)
    municipio = (snapshot or {}).get("municipios", {}).get(cidade)
    if municipio is None:
        return None
    secoes, _ = separar_secoes_do_tema(doc_texto, slug)
    return conferir_municipio(secoes.descricao_tema or "", municipio["contexto"], slug)


async def abrir_doc(slug: str) -> dict | None:
    """O Doc do tema, sempre fresco e sem gravar no cache do relatório, com o hash que
    o rascunho guarda para saber se o Doc mudou depois. None se o tema não tem Doc."""
    docs_url = get_macrotema(slug).get("docs_url")
    if not docs_url:
        return None
    texto = await baixar_doc(docs_url)
    return {"texto": texto, "hash": hashlib.sha256(texto.encode()).hexdigest()}


# "Ler com cada valor": o protótipo mostrava até 40 valores por coluna.
_MAX_VALORES = 40


def _como_numero(valor: object) -> float | None:
    """O número de um valor do contexto, lido como o avaliador de condições lê
    (_numero_do_campo: "62.39", "0,566", "12,2 pontos percentuais"), ou None."""
    if isinstance(valor, int | float | Decimal | str) and not isinstance(valor, bool):
        return _numero_do_campo(valor)
    return None


def _valores_mais_comuns(preenchidos: list[tuple[str, object]]) -> dict:
    contagem = Counter(str(v) for _, v in preenchidos)
    exemplo: dict[str, str] = {}
    for cidade, v in preenchidos:
        exemplo.setdefault(str(v), cidade)
    return {"distintos": len(contagem), "valores": [
        {"valor": v, "municipios": n, "exemplo": exemplo[v]}
        for v, n in contagem.most_common(_MAX_VALORES)
    ]}


def valores_das_colunas(contextos: dict[str, dict]) -> list[dict]:
    """Para cada coluna do contexto, quantos municípios têm o campo vazio e:
    - número (maioria conversível): mínimo, máximo, zeros, e os valores que não são
      número ("sem dados" e afins) com a contagem;
    - texto: os valores mais comuns, com a contagem e um município de exemplo, que a
      tela usa no "ler com cada valor";
    - outro (listas `*_serie`): só os vazios.

    Sem descrição em português: nenhuma view de tema tem COMMENT ON COLUMN no gamma
    (0 de ~600 colunas, 29/10/2026); a tela mostra o nome técnico (spec, "Valores de
    uma coluna").
    """
    colunas: dict[str, list[tuple[str, object]]] = {}
    for cidade, contexto in contextos.items():
        for coluna, valor in contexto.items():
            colunas.setdefault(coluna, []).append((cidade, valor))

    saida = []
    for coluna, pares in sorted(colunas.items()):
        preenchidos = [(cidade, v) for cidade, v in pares if v is not None and v != ""]
        # Município sem a chave no contexto conta como vazio também.
        info: dict = {"coluna": coluna, "vazios": len(contextos) - len(preenchidos)}
        numeros = [n for _, v in preenchidos if (n := _como_numero(v)) is not None]
        if preenchidos and len(numeros) * 2 >= len(preenchidos):
            nao_numeros = [(c, v) for c, v in preenchidos if _como_numero(v) is None]
            info |= {"tipo": "numero", "min": min(numeros), "max": max(numeros),
                     "zeros": sum(1 for n in numeros if n == 0),
                     "nao_numeros": _valores_mais_comuns(nao_numeros)["valores"]}
        elif preenchidos and all(isinstance(v, str) for _, v in preenchidos):
            info |= {"tipo": "texto", **_valores_mais_comuns(preenchidos)}
        else:
            info["tipo"] = "outro"
        saida.append(info)
    return saida
