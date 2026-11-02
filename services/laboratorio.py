"""Laboratório de Temas: conferência do texto de um tema contra os 2.074 municípios.

O texto passa inteiro, município a município, pelo mesmo caminho do relatório
(html_do_tema), com o contexto do snapshot. Avaliar condição por condição
divergiria do relatório: interpretar_blocos_condicionais tem estado entre linhas
(spec do laboratório, "Conferência pelo gerador"). Nada aqui escreve em banco, Doc
ou no cache de texto do relatório. Grava só o estado das conferências
(output/laboratorio/conferencias/) e os gráficos do painel de texto pronto, com
"_lab_" no nome, na pasta de gráficos do relatório (graficos_do_municipio).
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
from csv import Error as ErroDeCsv
from decimal import Decimal
from io import StringIO
from pathlib import Path

import pandas as pd

from config import OUTPUT_DIR
from services.cache import evict_graficos_if_needed
from services.csv_loader import normalizar_colunas_macrotema
from services.generation import gerar_graficos_do_tema, separar_secoes_do_tema
from services.laboratorio_snapshot import SNAPSHOT_DIR, carregar_snapshot
from services.macrotemas import get_macrotema
from utils.data.cities import filtrar_linhas_por_cidade, separar_cidade_uf
from utils.external.docs import baixar_doc
from utils.json_tipado import codificar
from utils.render.placeholders import (
    _numero_do_campo,
    conferir_condicoes,
    registrar_versoes,
)
from utils.render.renderer import html_do_tema, html_para_texto

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


def ler_csv(slug: str, texto: str) -> dict | None:
    """Lê o CSV que a editora subiu e casa cada linha com um município do snapshot,
    pela mesma regra do fallback de CSV do gerador (filtrar_linhas_por_cidade). Nada
    é gravado: as linhas voltam para o navegador, que as manda junto em cada pedido.

    Devolve as linhas por cidade, as cidades que só estão no CSV e as colunas do tema
    já com o CSV por cima (para a ficha e o autocomplete). None sem snapshot; ValueError
    com a mensagem para a tela se o CSV não serve.
    """
    snapshot = carregar_snapshot(slug)
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
        "colunas": valores_das_colunas(contextos),
    }


def conferir_municipio(
    descricao_tema: str, contexto: dict, slug: str, graficos: dict[str, str] | None = None
) -> dict:
    """Texto final do tema num município (em texto e em HTML de relatório), as
    versões avaliadas (condição, disparou) na ordem do texto e os campos que ficaram
    crus. `graficos`: os gerados de verdade (graficos_do_municipio); sem eles, supõe
    todo gráfico gerado (html_do_tema)."""
    with registrar_versoes() as versoes:
        html = html_do_tema(descricao_tema, contexto, slug, graficos)
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


def _rodar(id_conferencia: str, slug: str, doc_texto: str, csv: dict[str, dict] | None) -> None:
    with open(_LOCK, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)  # espera a conferência anterior acabar
        try:
            snapshot = carregar_snapshot(slug)
            if snapshot is None:
                _gravar(id_conferencia, {"estado": "erro", "erro": "tema sem snapshot"})
                return
            contextos = com_csv({cidade: m["contexto"] for cidade, m in snapshot["municipios"].items()}, csv)

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


def iniciar_conferencia(slug: str, doc_texto: str, csv: dict[str, dict] | None = None) -> str:
    CONFERENCIAS_DIR.mkdir(parents=True, exist_ok=True)
    _apagar_antigas()
    id_conferencia = uuid.uuid4().hex
    _gravar(id_conferencia, {"estado": "na_fila"})
    threading.Thread(
        target=_rodar, args=(id_conferencia, slug, doc_texto, csv),
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
    chave = hashlib.sha256(json.dumps(codificar(contexto), sort_keys=True).encode()).hexdigest()[:12]
    safe_city = f"lab_{re.sub(r'[^a-zA-Z0-9_-]+', '_', cidade.strip().lower())}_{chave}"
    graficos = gerar_graficos_do_tema(slug, contexto, OUTPUT_DIR, safe_city, f"laboratório: {cidade}")
    evict_graficos_if_needed()
    return graficos


def texto_do_municipio(
    slug: str, doc_texto: str, cidade: str, csv: dict[str, dict] | None = None, com_graficos: bool = False
) -> dict | None:
    """Texto final do tema numa cidade, para "texto pronto numa cidade" e "ler com
    cada valor". None se o tema não tem snapshot ou a cidade não está nele.

    ponytail: lê o snapshot inteiro a cada chamada (~0,5 s local). Cache por processo
    custaria ~100 MB × 3 workers num host que já sofreu com memória; cachear se a
    tela ficar lenta.
    """
    snapshot = carregar_snapshot(slug)
    if snapshot is None:
        return None
    municipio = snapshot["municipios"].get(cidade)
    contexto = com_csv({cidade: municipio["contexto"]} if municipio else {}, csv).get(cidade)
    if contexto is None:
        return None
    secoes, _ = separar_secoes_do_tema(doc_texto, slug)
    graficos = graficos_do_municipio(slug, contexto, cidade) if com_graficos else None
    return conferir_municipio(secoes.descricao_tema or "", contexto, slug, graficos)


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
# A sigla da UF (11 valores) não muda a concordância da frase e punha o botão em quase
# todo cartão (André, 01/11). Mesma lista no frontend (Laboratorio.jsx, `comparavel`).
_FORA_DO_LER_COM_CADA_VALOR = {"sigla_uf"}


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


def ler_com_cada_valor(slug: str, trecho: str, csv: dict[str, dict] | None = None) -> list[dict] | None:
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
    snapshot = carregar_snapshot(slug)
    if snapshot is None:
        return None
    contextos = com_csv({cidade: m["contexto"] for cidade, m in snapshot["municipios"].items()}, csv)
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
