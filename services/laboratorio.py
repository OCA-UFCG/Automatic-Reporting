"""Laboratório de Temas: conferência do texto de um tema contra os 2.074 municípios.

O texto passa inteiro, município a município, pelo mesmo caminho do relatório
(html_do_tema), com o contexto do snapshot. Avaliar condição por condição
divergiria do relatório: interpretar_blocos_condicionais tem estado entre linhas
(spec do laboratório, "Conferência pelo gerador"). Nada aqui escreve em banco, Doc
ou no cache de texto do relatório. Grava só o estado das conferências
(output/laboratorio/conferencias/) e os gráficos do painel de texto pronto, com
"_lab_" no nome, na pasta de gráficos do relatório (graficos_do_municipio).
"""

import asyncio
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
from contextvars import copy_context
from csv import Error as ErroDeCsv
from decimal import Decimal
from functools import lru_cache
from html import escape
from io import StringIO
from pathlib import Path
from urllib.parse import quote

import pandas as pd

from config import CARACTERISTICAS_DOCS_URL, OUTPUT_DIR
from services.cache import evict_graficos_if_needed
from services.csv_loader import normalizar_colunas_macrotema
from services.generation import (
    _contexto_caracteristicas,
    gerar_graficos_do_tema,
    separar_secoes_do_tema,
)
from services.graficos_estado import gerar_graficos_do_estado
from services.laboratorio_snapshot import SNAPSHOT_DIR, carregar_snapshot

# docs_env/docs_url moram em services.macrotemas desde o relatório por estado (05/11/2026);
# importados aqui porque main.py e os testes do laboratório os pedem a este módulo.
from services.macrotemas import docs_env, docs_url  # noqa: F401
from services.primeira_pagina_estado import primeira_pagina_do_estado
from services.relatorio_estado import _BLOCOS_DA_CAPA, nome_de_arquivo_da_unidade
from utils.cover import montar_indicadores_do_doc
from utils.data.cities import filtrar_linhas_por_cidade, separar_cidade_uf
from utils.external.docs import (
    baixar_doc,
    carregar_texto_do_docs,
    extrair_legenda_mapa_localizacao,
    extrair_panorama_indicadores,
    extrair_relatorio_geral,
    extrair_resumo_cidade,
)
from utils.json_tipado import codificar
from utils.maps import buscar_mapa_estatico
from utils.render.placeholders import (
    _numero_do_campo,
    conferir_condicoes,
    isolar_paragrafo_de_cada_condicao,
    nomes_resolvidos_sem_coluna,
    registrar_versoes,
    substituir_placeholders,
)
from utils.render.renderer import (
    _legenda_mapa_localizacao_html,
    html_do_tema,
    html_para_texto,
    render_descricao_tema_html,
    reset_figura_contador,
    resolver_referencia_figura_do_mapa,
    texto_para_html,
)

logger = logging.getLogger(__name__)

# "$campo" ou "tema.$campo" que sobrou no texto final: não resolveu neste município.
_CAMPO_CRU = re.compile(r"(?:\b\w+\.)?\$([A-Za-z_]\w*)")
# Sem âncora de linha: extrair_resumo_tema junta o resumo numa linha só.
_CONDICAO_NO_TEXTO = re.compile(r"(?i)\bpara(?:\s+quando)?\s+[^:]*\$\w+[^:]*:")


def com_csv(contextos: dict[str, dict], csv: dict[str, dict] | None) -> dict[str, dict]:
    """As colunas do CSV por cima do contexto do snapshot (spec, "Dados: view ou CSV"):
    o CSV de uma view que ainda não existe é testado junto com o resto do tema. Cidade
    só do CSV entra só com as colunas dele. `nm_mun` fica o nome canônico "Cidade (UF)",
    como o gerador faz antes das buscas (generation.py)."""
    if not csv:
        return contextos
    return {**contextos, **{
        cidade: {**contextos.get(cidade, {}), **linha, "nm_mun": cidade} for cidade, linha in csv.items()
    }}


def texto_da_unidade(texto: str, unidade: str) -> str:
    """O texto do Doc como o relatório da unidade o lê: no estado e na área, cada
    condição vale só para a linha seguinte (services/relatorio_estado.py,
    tema_da_unidade). Sem isto o painel mostraria parágrafos que o PDF da unidade
    mostra, ou o contrário. Até 13/11/2026 só o estado passava por aqui, e a prévia
    de área divergia do relatório de área.

    Ex.: texto_da_unidade(doc, "municipio") is doc
    """
    if unidade != "municipio":
        return isolar_paragrafo_de_cada_condicao(texto)
    return texto


def ler_csv(slug: str, texto: str, unidade: str = "municipio") -> dict | None:
    """Lê o CSV que a editora subiu e casa cada linha com um município do snapshot,
    pela mesma regra do fallback de CSV do gerador (filtrar_linhas_por_cidade). Nada
    é gravado: as linhas voltam para o navegador, que as manda junto em cada pedido.

    Devolve as linhas por cidade, as cidades que só estão no CSV e as colunas do tema
    já com o CSV por cima (para a ficha e o autocomplete). None sem snapshot; ValueError
    com a mensagem para a tela se o CSV não serve.
    """
    snapshot = carregar_snapshot(slug, unidade)
    if snapshot is None:
        return None
    try:
        # sep=None: o pandas descobre se é vírgula, ponto e vírgula ou tab.
        df = pd.read_csv(StringIO(texto), sep=None, engine="python")
    except (pd.errors.ParserError, pd.errors.EmptyDataError, ValueError, ErroDeCsv) as err:
        raise ValueError(f"Não consegui ler o CSV: {err}") from err
    df = normalizar_colunas_macrotema(df, slug)
    if "nm_mun" not in df.columns:
        raise ValueError("O CSV precisa de uma coluna nm_mun com o nome do município.")
    df = df.reset_index(drop=True)
    # Pelo JSON: NaN vira None (o gerador trata os dois como "sem dado") e os tipos do
    # numpy viram int/float do Python.
    registros = json.loads(df.to_json(orient="records", force_ascii=False))

    # filtrar_linhas_por_cidade varre o CSV inteiro: 2.074 vezes davam ~9 s. Ela só
    # casa linhas com o mesmo nome sem "(UF)", em minúsculas; agrupar por essa chave
    # antes e passar só as candidatas dá o mesmo resultado.
    chaves = df["nm_mun"].astype(str).str.strip().str.replace(r"\s*\([A-Za-z]{2}\)\s*$", "", regex=True).str.lower()
    candidatas = {chave: df.loc[indices] for chave, indices in chaves.groupby(chaves).groups.items()}
    linhas: dict[str, dict] = {}
    usadas: set[int] = set()
    for cidade in snapshot["municipios"]:
        grupo = candidatas.get(separar_cidade_uf(cidade)[0].strip().lower())
        if grupo is None:
            continue
        achadas = filtrar_linhas_por_cidade(grupo, cidade)
        if len(achadas):
            linhas[cidade] = registros[achadas.index[0]]
            usadas.add(achadas.index[0])
    so_no_csv = []
    for indice, registro in enumerate(registros):
        if indice in usadas:
            continue
        nome = str(registro["nm_mun"]).strip()
        uf = str(registro.get("sigla_uf") or "").strip().upper()
        cidade = f"{nome} ({uf})" if uf and not nome.endswith(")") else nome
        if cidade not in linhas:
            linhas[cidade] = registro
            so_no_csv.append(cidade)

    contextos = com_csv({c: m["contexto"] for c, m in snapshot["municipios"].items()}, linhas)
    return {
        "linhas": linhas,
        "casados": len(linhas) - len(so_no_csv),
        "so_no_csv": so_no_csv,
        "colunas_do_csv": [c for c in df.columns if c != "nm_mun"],
        "colunas": colunas_para_a_tela(contextos),
    }


def conferir_municipio(
    descricao_tema: str,
    contexto: dict,
    slug: str,
    graficos: dict[str, str] | None = None,
    com_mapa: bool = True,
) -> dict:
    """Texto final do tema num município (em texto e em HTML de relatório), as
    versões avaliadas (condição, disparou) na ordem do texto e os campos que ficaram
    crus. `graficos`: os gerados de verdade (graficos_do_municipio); sem eles, supõe
    todo gráfico gerado (html_do_tema). `com_mapa=False` para estado e área, que não
    têm mapa: a primeira legenda sai como Figura 1, como no relatório da unidade."""
    with registrar_versoes() as versoes:
        html = html_do_tema(descricao_tema, contexto, slug, graficos, com_mapa)
    partes = [texto for texto in map(html_para_texto, html) if texto]
    return {
        "partes": partes,
        "html": html,
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


def _rodar(
    id_conferencia: str, slug: str, doc_texto: str, csv: dict[str, dict] | None, unidade: str = "municipio"
) -> None:
    with open(_LOCK, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)  # espera a conferência anterior acabar
        try:
            snapshot = carregar_snapshot(slug, unidade)
            if snapshot is None:
                _gravar(id_conferencia, {"estado": "erro", "erro": "tema sem snapshot"})
                return
            contextos = com_csv({cidade: m["contexto"] for cidade, m in snapshot["municipios"].items()}, csv)

            def progresso(feitos: int, total: int) -> None:
                if feitos % _GRAVAR_A_CADA == 0:
                    _gravar(id_conferencia, {"estado": "rodando", "feitos": feitos, "total": total})

            _gravar(id_conferencia, {"estado": "rodando", "feitos": 0, "total": len(contextos)})
            resultado = conferir_doc(texto_da_unidade(doc_texto, unidade), slug, contextos, progresso)
            # Cidades da lista do relatório sem dado nenhum neste tema: ficam fora do
            # snapshot e da conferência, e a tela precisa dizer isso (cobertura).
            resultado["ausentes"] = snapshot.get("metadados", {}).get("ausentes", [])
            if unidade != "municipio":
                # Gráfico é só municipal (GRAFICOS_POR_TEMA): sem legenda no Doc de
                # estado não é falta, e o aviso confundiria.
                resultado["graficos_sem_legenda"] = []
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


def iniciar_conferencia(
    slug: str, doc_texto: str, csv: dict[str, dict] | None = None, unidade: str = "municipio"
) -> str:
    CONFERENCIAS_DIR.mkdir(parents=True, exist_ok=True)
    _apagar_antigas()
    id_conferencia = uuid.uuid4().hex
    _gravar(id_conferencia, {"estado": "na_fila"})
    threading.Thread(
        target=_rodar, args=(id_conferencia, slug, doc_texto, csv, unidade),
        name=f"conferencia:{slug}", daemon=True,
    ).start()
    return id_conferencia


def graficos_do_municipio(slug: str, contexto: dict, cidade: str) -> dict[str, str]:
    """Os gráficos do tema para o município, pelo mesmo caminho do relatório
    (gerar_graficos_do_tema), na pasta de gráficos do relatório: reuso, escrita
    atômica e limite de disco vêm de lá (plotting.reusar_grafico,
    cache.evict_graficos_if_needed).

    O nome leva "lab" e um hash do contexto: o gerador reaproveita o PNG pelo nome, e
    o contexto do laboratório muda com o snapshot da noite ou com um CSV. Sem o hash,
    o painel mostraria o gráfico de antes (ou, sem a cidade no nome, o de outra).
    Medido em 01/11: 0,1 a 1,8 s por tema na 1ª vez de uma cidade; editar o texto
    não gera de novo."""
    safe_city = f"lab_{re.sub(r'[^a-zA-Z0-9_-]+', '_', cidade.strip().lower())}_{_chave_do_contexto(contexto)}"
    graficos = gerar_graficos_do_tema(slug, contexto, OUTPUT_DIR, safe_city, f"laboratório: {cidade}")
    evict_graficos_if_needed()
    return graficos


def _chave_do_contexto(contexto: dict) -> str:
    return hashlib.sha256(json.dumps(codificar(contexto), sort_keys=True).encode()).hexdigest()[:12]


def graficos_do_estado(slug: str, contexto: dict, estado: str) -> dict[str, str]:
    """Os gráficos do tema para o estado, pela mesma função do relatório de estado
    (gerar_graficos_do_estado), com "lab" e o hash do contexto no nome pelo mesmo
    motivo de graficos_do_municipio. O contexto do snapshot é a linha da matview, a
    mesma que o relatório passa. Área não tem gráfico nem no relatório."""
    safe = f"lab_{nome_de_arquivo_da_unidade('estado', estado)}_{_chave_do_contexto(contexto)}"
    graficos = gerar_graficos_do_estado(slug, contexto, OUTPUT_DIR, safe)
    evict_graficos_if_needed()
    return graficos


def texto_do_municipio(
    slug: str,
    doc_texto: str,
    cidade: str,
    csv: dict[str, dict] | None = None,
    com_graficos: bool = False,
    unidade: str = "municipio",
) -> dict | None:
    """Texto final do tema numa cidade, para "texto pronto numa cidade" e "ler com
    cada valor". None se o tema não tem snapshot ou a cidade não está nele.

    ponytail: lê o snapshot inteiro a cada chamada (~0,5 s local). Cache por processo
    custaria ~100 MB × 3 workers num host que já sofreu com memória; cachear se a
    tela ficar lenta.
    """
    snapshot = carregar_snapshot(slug, unidade)
    if snapshot is None:
        return None
    municipio = snapshot["municipios"].get(cidade)
    contexto = com_csv({cidade: municipio["contexto"]} if municipio else {}, csv).get(cidade)
    if contexto is None:
        return None
    secoes, _ = separar_secoes_do_tema(texto_da_unidade(doc_texto, unidade), slug)
    if unidade == "municipio":
        graficos = graficos_do_municipio(slug, contexto, cidade) if com_graficos else None
    elif unidade == "estado":
        # Desde 12/11/2026 o relatório de estado desenha os gráficos do Doc
        # (services/relatorio_estado.py, tema_da_unidade); a prévia faz o mesmo.
        graficos = graficos_do_estado(slug, contexto, cidade) if com_graficos else None
    else:
        # Área: sem gráfico também no relatório; "(Figura X)" some como num gráfico sem dado.
        graficos = {}
    resultado = conferir_municipio(
        secoes.descricao_tema or "", contexto, slug, graficos, com_mapa=unidade == "municipio"
    )
    resto = secoes.resto
    if unidade != "municipio":
        # No relatório da unidade, o "Panorama de indicadores" do Doc vira os cards do
        # tema e sai do resto (relatorio_estado.item_do_tema). Sem isto ele aparecia
        # como texto na caixa de Fontes da prévia.
        # Os cards, como a capa, só no painel (com_graficos): quem lê "html" sem o painel
        # espera o tema começando em html[0].
        panorama, resto = extrair_panorama_indicadores(resto)
        cards = _cards_do_panorama_html(montar_indicadores_do_doc(panorama, contexto, slug)) if com_graficos else ""
        if cards:
            resultado["html"].insert(0, cards)
    # O relatório fecha o tema com a caixa "Fontes / Conteúdos relacionados", o que
    # sobra do Doc depois do "@@" (generation.py, fontes_html). Só no HTML do painel:
    # "partes" e a conferência seguem só com o texto do tema.
    if resto.strip():
        resultado["html"].append(texto_para_html(resto, contexto, namespace=slug))
    # A primeira página do relatório, acima do tema (André, 09/11/2026). Só no painel
    # (com_graficos). Fica fora da conferência, das "partes" e do "ler com cada valor".
    if com_graficos:
        capa = (
            primeira_pagina_html(slug, contexto, cidade)
            if unidade == "municipio"
            else primeira_pagina_da_unidade_html(unidade, secoes, contexto, slug, cidade)
        )
        if capa:
            resultado["html"].insert(0, capa)
    return resultado


def _cards_do_panorama_html(indicadores: list[dict[str, str]]) -> str:
    """Os cards do Panorama como uma lista simples: rótulo, valor e a legenda "fonte •
    unidade" quando o Doc a traz. O desenho dos cards é do SSR do relatório."""
    if not indicadores:
        return ""
    itens = "".join(
        f"<li><strong>{escape(card['nome'])}</strong>: {escape(card['valor'])}"
        + (f" <small>({escape(card['fonte'])})</small>" if card.get("fonte") else "")
        + "</li>"
        for card in indicadores
    )
    return f'<section class="panorama-indicadores"><div class="cover-kicker">Panorama de indicadores</div><ul>{itens}</ul></section>'


def primeira_pagina_da_unidade_html(
    unidade: str, secoes, contexto: dict, slug: str, nome: str
) -> str | None:
    """A capa de estado e área como o relatório monta (relatorio_estado.capa_da_unidade):
    os blocos de capa do Doc do tema e, no estado, o Doc da primeira página
    (CARACTERISTICAS_ESTADO_DOCS_URL), que tem precedência. Sem os cards de área e
    população, como na primeira página municipal do painel."""

    def renderizar() -> dict[str, object]:
        reset_figura_contador(com_mapa=False)
        capa: dict[str, object] = {}
        for bloco in _BLOCOS_DA_CAPA:
            texto = getattr(secoes, bloco)
            if texto:
                capa[f"{bloco}_html"] = render_descricao_tema_html(texto, contexto, namespace=slug)
        if unidade == "estado":
            try:
                capa.update(asyncio.run(primeira_pagina_do_estado(nome, "laboratorio")))
            except Exception:  # sem a primeira página, a capa fica com os blocos do tema
                logger.warning("Primeira página de %s indisponível no painel", nome, exc_info=True)
        return capa

    # Contexto copiado: a capa não mexe na numeração de figuras do tema.
    capa = copy_context().run(renderizar)
    partes: list[str] = []
    if capa.get("relatorio_geral_html"):
        partes += ['<div class="cover-kicker">Apresentação</div>', *capa["relatorio_geral_html"]]
    if capa.get("resumo_cidade_html"):
        partes += ['<div class="cover-kicker">Características Gerais</div>', *capa["resumo_cidade_html"]]
    if not partes:
        return None
    return '<section class="primeira-pagina">' + "".join(partes) + "</section>"


@lru_cache(maxsize=4096)
def _bioma_da_capa(cidade: str) -> str | None:
    """Bioma da cidade para a capa, lido do snapshot de demografia.

    Na linha de Meio Ambiente o `bioma` é outra frase ("inserida no bioma
    Caatinga"), e o relatório usa o das características
    (generation._contexto_caracteristicas). O bioma não muda de uma noite para a
    outra: o cache por processo evita ler o snapshot inteiro (~0,5 s) a cada tecla.
    """
    snapshot = carregar_snapshot("demografia")
    municipio = (snapshot or {}).get("municipios", {}).get(cidade)
    return municipio["contexto"].get("bioma") if municipio else None


def primeira_pagina_html(slug: str, contexto: dict, cidade: str) -> str | None:
    """Apresentação, Características Gerais e mapa de localização, como na capa do
    relatório (generation.gerar_relatorio_handler e report/.../Cover.jsx). Sem os
    cartões de métricas, que vêm da vw_indicadores e não estão no snapshot.

    O texto é o do cache em disco, o mesmo do relatório: o Doc de Características não
    é aberto ao vivo como o do tema, porque não se edita no TemaLab. O mapa é só o PNG
    pré-gerado, servido por /laboratorio/mapas/ (o nginx do gamma-lab só deixa passar
    /laboratorio/...); sem PNG, sai sem mapa, sem o plano B do shapefile.
    """
    if not CARACTERISTICAS_DOCS_URL:
        return None
    try:
        texto = asyncio.run(carregar_texto_do_docs(CARACTERISTICAS_DOCS_URL))
    except Exception:  # sem a capa, o painel segue só com o tema
        logger.warning("Primeira página: Doc de Características indisponível", exc_info=True)
        return None
    bioma = _bioma_da_capa(cidade) if slug == "meio-ambiente" else contexto.get("bioma")
    contexto_capa = _contexto_caracteristicas(contexto, {"bioma": bioma})
    relatorio_geral, texto = extrair_relatorio_geral(texto)
    resumo_cidade, texto = extrair_resumo_cidade(texto)
    legenda, _ = extrair_legenda_mapa_localizacao(texto)

    def renderizar() -> list[str]:
        partes = []
        if relatorio_geral:
            partes += ['<div class="cover-kicker">Apresentação</div>']
            partes += render_descricao_tema_html(relatorio_geral, contexto_capa, namespace="caract_mun")
        partes.append('<div class="cover-kicker">Características Gerais</div>')
        if resumo_cidade:
            resumo = resolver_referencia_figura_do_mapa(resumo_cidade) if legenda else resumo_cidade
            partes += render_descricao_tema_html(resumo, contexto_capa, namespace="caract_mun")
        mapa = buscar_mapa_estatico(str(contexto_capa.get("nm_mun", "")), contexto_capa.get("sigla_uf"))
        if mapa:
            rotulo = _legenda_mapa_localizacao_html(
                substituir_placeholders(legenda, contexto_capa, "caract_mun") if legenda else None
            )
            partes.append(
                '<figure class="map-block map-block--region">'
                f'<img class="region-map-image" src="/laboratorio/mapas/{quote(mapa)}" alt="Mapa da região de {escape(cidade)}">'
                f"<figcaption>{rotulo}</figcaption></figure>"
            )
        return partes

    # Contexto copiado: a capa não mexe na numeração de figuras do tema (html_do_tema).
    return '<section class="primeira-pagina">' + "".join(copy_context().run(renderizar)) + "</section>"


async def abrir_doc(slug: str, unidade: str = "municipio") -> dict | None:
    """O Doc do tema, sempre fresco e sem gravar no cache do relatório, com o hash que
    o rascunho guarda para saber se o Doc mudou depois. None se o tema não tem Doc."""
    docs_url_do_tema = docs_url(slug, unidade)
    if not docs_url_do_tema:
        return None
    texto = await baixar_doc(docs_url_do_tema)
    return {"texto": texto, "hash": hashlib.sha256(texto.encode()).hexdigest()}


# "Ler com cada valor": o protótipo mostrava até 40 valores por coluna.
_MAX_VALORES = 40
# A sigla da UF (11 valores) não muda a concordância da frase e punha o botão em quase
# todo cartão (André, 01/11). Mesma lista no frontend (Laboratorio.jsx, `comparavel`).
# Em estado e área, o mesmo vale para as colunas da est_geral e da areaint_geral: um
# valor por unidade, com a concordância já pronta ("A Paraíba", "na Caatinga"), e
# presentes em quase toda frase.
_FORA_DO_LER_COM_CADA_VALOR = {
    "sigla_uf", "uf_estado", "uf_sigla_uf", "uf_sujeito", "uf_em", "uf_de",
    "area_nome", "area_sigla", "area_sujeito", "area_em", "area_de",
}


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


def colunas_para_a_tela(contextos: dict[str, dict]) -> list[dict]:
    """As colunas com a ficha de cada uma, mais os apelidos que o gerador resolve
    (tipo "apelido"): a tela não acusa $area como inexistente, mas não oferece ele no
    autocomplete."""
    colunas = valores_das_colunas(contextos)
    apelidos = nomes_resolvidos_sem_coluna({c["coluna"] for c in colunas})
    return colunas + [{"coluna": nome, "tipo": "apelido", "de": origem} for nome, origem in sorted(apelidos.items())]


def ler_com_cada_valor(
    slug: str, trecho: str, csv: dict[str, dict] | None = None, unidade: str = "municipio"
) -> list[dict] | None:
    """"Ler com cada valor" (spec): o trecho (uma versão ou um texto fixo) pronto, por
    um município que tenha cada valor das colunas de texto que ele usa. Pega a
    concordância que serve para um valor e não para outro ("apresentou uma redução" ×
    "apresentou não houve variação").

    Só colunas de texto com 2 a 40 valores: com 1 não há o que comparar, e acima
    disso é nome próprio, um por município (nm_mun, nome_uc).

    O exemplo de cada valor é um município onde o trecho sai no relatório (decisão do
    André, 01/11): mostrar a frase num município em que a condição não vale seria
    alarme falso. Valor que nunca sai fica com `vale_em` 0 e sem exemplo. Um snapshot
    lido e o trecho renderizado uma vez por município, pelo mesmo caminho do relatório.
    None se o tema não tem snapshot.
    """
    snapshot = carregar_snapshot(slug, unidade)
    if snapshot is None:
        return None
    contextos = com_csv({cidade: m["contexto"] for cidade, m in snapshot["municipios"].items()}, csv)
    trecho = texto_da_unidade(trecho, unidade)
    usadas = set(_CAMPO_CRU.findall(trecho))
    so_as_usadas = {c: {k: v for k, v in ctx.items() if k in usadas} for c, ctx in contextos.items()}
    colunas = [
        c["coluna"] for c in valores_das_colunas(so_as_usadas)
        if c["tipo"] == "texto" and 2 <= c["distintos"] <= _MAX_VALORES
        and c["coluna"] not in _FORA_DO_LER_COM_CADA_VALOR
    ]
    por_coluna: dict[str, dict[str, dict]] = {coluna: {} for coluna in colunas}
    for cidade, contexto in contextos.items():
        valores = {c: str(contexto[c]) for c in colunas if contexto.get(c) not in (None, "")}
        if not valores:
            continue
        # Versão que não vale aqui some do texto final; texto fixo sai sempre.
        texto = "\n\n".join(conferir_municipio(trecho, contexto, slug)["partes"]).strip()
        for coluna, valor in valores.items():
            item = por_coluna[coluna].setdefault(
                valor, {"valor": valor, "municipios": 0, "vale_em": 0, "cidade": None, "texto": None}
            )
            item["municipios"] += 1
            if texto:
                item["vale_em"] += 1
                if item["cidade"] is None:
                    item |= {"cidade": cidade, "texto": texto}
    return [
        {"coluna": c, "valores": sorted(por_coluna[c].values(), key=lambda i: -i["municipios"])}
        for c in colunas
    ]
