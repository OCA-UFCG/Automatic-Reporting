"""Snapshot do Laboratório de Temas: o contexto completo de cada município, por tema.

O laboratório confere o texto de um tema contra os 2.074 municípios. Montar esse contexto
na hora, a cada clique, levaria horas de banco, então ele sai de um arquivo por tema
(`output/laboratorio/<tema>.json.gz`), gerado pelas mesmas funções do relatório
(`linhas_base_do_tema` → `buscar_extras_municipio` → `montar_contexto_tema`). Rodada
noturna logo depois do refresh_matviews.sh, mais `--tema X` à mão depois de uma carga
(decisões do André, 26 e 28/10/2026; spec do laboratório, "Dados: view ou CSV").

Falhar é barato, como no atualizar_docs.py: uma rodada que aborta ou não passa no portão
deixa o arquivo anterior no lugar, e a tela mostra a data dele.

Estado e área de interesse (pedido de 03/11/2026: "Estado e Área de interesse se
comportarão como município"): o mesmo arquivo, em `output/laboratorio/<unidade>/<tema>.json.gz`,
com os 9 estados do NE ou as áreas no lugar dos municípios, lidos direto da matview do
tema na unidade (gerar_snapshot_unidade, UNIDADES_POR_MATVIEW).
"""

import gzip
import json
import logging
import os
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import psycopg2
from fastapi import HTTPException

from config import OUTPUT_DIR
from services.generation import (
    buscar_extras_municipio,
    linhas_base_do_tema,
    montar_contexto_tema,
)
from services.macrotemas import get_macrotema
from utils.data.cities import carregar_cidades
from utils.geografia import resolver_nome_uf, separar_cidade_uf
from utils.json_tipado import codificar, decodificar
from utils.queries.base import conexao_reaproveitada
from utils.queries.estado import MATVIEW_ESTADUAL_POR_MACROTEMA
from utils.queries.perfil_municipal import VIEW_POR_MACROTEMA, chave_municipio_sql

logger = logging.getLogger(__name__)

SNAPSHOT_DIR = OUTPUT_DIR / "laboratorio"

# Portão antes de trocar o arquivo: executar_query devolve None em erro (guard do
# CLAUDE.md), então uma rodada com o banco engasgado sairia "sem dados" e substituiria
# um snapshot bom. ponytail: limiares fixos e chutados; ajustar se abortar à toa.
MAX_FRACAO_MUNICIPIOS_COM_FALHA = 0.01
MAX_QUEDA_NA_VIEW = 0.05

# Unidades além do município (pedido de 03/11/2026: "Estado e Área de interesse se
# comportarão como município"). Cada uma lê as matviews de um schema da equipe de dados,
# uma linha por unidade, com as colunas municipais sob um prefixo (`uf_`, `area_`) e as 6
# primeiras vindas da *_geral (nome e concordância pronta: "A Paraíba", "na Caatinga").
# Uma unidade nova entra aqui com um schema, o nome da coluna-chave e o mapa de temas.
UNIDADES_POR_MATVIEW = {
    "estado": {
        "schema": "auto_relatorios_est",
        "nome": "uf_estado",
        "ordem": "uf_cd_uf",
        # Só os 9 do Nordeste, como estão nas matviews (André, 03/11/2026: MG e ES
        # ficam fora). O portão exige os 9.
        "quantas": 9,
        # Instrumentos Sudene não tem matview estadual. O mapa mora em
        # utils/queries/estado.py porque o relatório por estado também o lê: uma lista
        # só, para o TemaLab e o relatório nunca lerem matviews diferentes.
        "matviews": MATVIEW_ESTADUAL_POR_MACROTEMA,
    },
    "area": {
        "schema": "auto_relatorios_areaint",
        "nome": "area_nome",
        "ordem": "area_cd",
        # Quais áreas existem é da equipe de dados (4 em 08/11/2026: Caatinga, Área de
        # atuação da Sudene, Semiárido, Nordeste), e o André pediu para não supor
        # (03/11, 08/11): o portão aceita quantas a matview tiver, a partir de 1.
        "quantas": None,
        # Desenvolvimento social e Instrumentos Sudene não têm matview de área.
        "matviews": {
            "demografia": "areaint_demografia",
            "educacao": "areaint_educacao",
            "saude": "areaint_saude",
            "economia-renda": "areaint_economia",
            "hidraulica": "areaint_seg_hidrica",
            "meio-ambiente": "areaint_ambiente",
            "saneamento": "areaint_infraestrutura",
        },
    },
}
UNIDADES = ("municipio", *UNIDADES_POR_MATVIEW)


class _ContaFalhas(logging.Handler):
    """O único rastro de um timeout/erro engolido por executar_query é o warning
    "Falha ao ..." que ele loga; conta por município."""

    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.cidade: str | None = None
        self.por_cidade: Counter[str] = Counter()

    def emit(self, record: logging.LogRecord) -> None:
        if self.cidade and record.getMessage().startswith("Falha ao"):
            self.por_cidade[self.cidade] += 1


def caminho_snapshot(slug: str, unidade: str = "municipio") -> Path:
    # Município fica na raiz, onde o cron do gamma e os snapshots de hoje já estão.
    pasta = SNAPSHOT_DIR if unidade == "municipio" else SNAPSHOT_DIR / unidade
    return pasta / f"{slug}.json.gz"


def ler_view_do_tema(conn, slug: str) -> tuple[dict[tuple[str, str], dict], list[str]]:
    """Índice (chave do município, UF) → linha da view, e as chaves repetidas."""
    view = VIEW_POR_MACROTEMA[slug]
    # Exceção ao guard "nunca SELECT * numa vw_perfil_* sem município" (CLAUDE.md),
    # aprovada só aqui (André, 26/10/2026): as views agregam os 2.074 municípios antes de
    # filtrar, então ler um custa quase o mesmo que ler todos (demografia: 0,80 × 0,87 s).
    # Município a município somava ~68 min; as 8 views inteiras, 2,3 s. Uma view por vez,
    # nunca em paralelo, com o statement_timeout da conexão, fora do cache de consultas.
    # A chave sai do Postgres pela mesma expressão do WHERE de buscar_perfil_municipal.
    with conn.cursor() as cursor:
        cursor.execute(
            f"SELECT {chave_municipio_sql('nm_mun')} AS _chave_mun, * "
            f"FROM relatorios_auto.{view}"
        )
        colunas = [descricao[0] for descricao in cursor.description]
        linhas = cursor.fetchall()

    indice: dict[tuple[str, str], dict] = {}
    repetidas: list[str] = []
    for valores in linhas:
        linha = dict(zip(colunas, valores))
        chave = (linha.pop("_chave_mun"), linha.get("sigla_uf"))
        if chave in indice:
            # O relatório usa LIMIT 1 sem ORDER BY: com chave repetida ele pega uma linha
            # qualquer, então o snapshot não escolhe em silêncio — registra e fica a 1ª.
            repetidas.append(f"{chave[0]} ({chave[1]})")
            continue
        indice[chave] = linha
    return indice, repetidas


def chaves_das_cidades(conn, cidades: list[str]) -> dict[str, tuple[str, str]]:
    """Cidade "Nome (UF)" → chave do índice, calculada no Postgres (uma consulta só)."""
    nomes_uf = {cidade: separar_cidade_uf(cidade) for cidade in cidades}
    com_uf = [cidade for cidade, (_nome, uf) in nomes_uf.items() if uf]
    with conn.cursor() as cursor:
        cursor.execute(
            f"SELECT nome, {chave_municipio_sql('nome')} "
            "FROM unnest(%s::text[]) AS nome",
            ([nomes_uf[cidade][0] for cidade in com_uf],),
        )
        chave_por_nome = dict(cursor.fetchall())
    return {cidade: (chave_por_nome[nomes_uf[cidade][0]], nomes_uf[cidade][1]) for cidade in com_uf}


def contexto_do_municipio(
    cidade: str, slug: str, macrotema_dados: dict, perfil_db: dict | None
) -> tuple[str, dict, int] | None:
    """(fonte "view"|"csv", contexto, nº de linhas base) — None se a cidade não está nem
    na view nem no CSV. Mesma ordem do handler, num relatório só deste tema."""
    try:
        linhas = linhas_base_do_tema(cidade, slug, macrotema_dados, perfil_db)
    except HTTPException:
        return None
    nome_db, uf_db = resolver_nome_uf(linhas[0])
    extras = buscar_extras_municipio(nome_db, uf_db, [slug])
    # Com várias linhas no CSV, o relatório usa a primeira para a capa e as buscas.
    contexto = montar_contexto_tema(linhas[0], perfil_db, slug, [slug], extras)
    return ("view" if perfil_db else "csv"), contexto, len(linhas)


def _metadados_anteriores(slug: str) -> dict | None:
    anterior = carregar_snapshot(slug)
    return anterior["metadados"] if anterior else None


def gerar_snapshot_tema(slug: str, cidades: list[str] | None = None) -> Path | None:
    """Gera o snapshot de um tema. Devolve o caminho gravado, ou None se a rodada abortou
    (o arquivo anterior fica)."""
    inicio = time.monotonic()
    cidades = cidades if cidades is not None else carregar_cidades()
    macrotema_dados = get_macrotema(slug)

    contador = _ContaFalhas()
    logging.getLogger("utils.queries.base").addHandler(contador)
    try:
        with conexao_reaproveitada() as conn:
            try:
                indice, repetidas = ler_view_do_tema(conn, slug)
                chaves = chaves_das_cidades(conn, cidades)
            except psycopg2.Error as err:
                logger.error("snapshot %s: falha ao ler a view (%s); mantém o anterior", slug, err)
                return None
            if not indice:
                logger.error("snapshot %s: view vazia; mantém o anterior", slug)
                return None

            municipios: dict[str, dict] = {}
            ausentes: list[str] = []
            csv_varias_linhas: list[str] = []

            def montar(cidade: str) -> None:
                contador.cidade = cidade
                chave = chaves.get(cidade)
                perfil_db = indice.get(chave) if chave else None
                try:
                    resultado = contexto_do_municipio(cidade, slug, macrotema_dados, perfil_db)
                except Exception:  # um município quebrado não derruba o tema
                    logger.exception("snapshot %s: erro ao montar %s", slug, cidade)
                    contador.por_cidade[cidade] += 1
                    return
                if resultado is None:
                    ausentes.append(cidade)
                    return
                fonte, contexto, n_linhas = resultado
                if n_linhas > 1:
                    csv_varias_linhas.append(cidade)
                municipios[cidade] = {"fonte": fonte, "contexto": contexto}

            for cidade in cidades:
                montar(cidade)
            # Uma segunda tentativa para quem falhou: com o banco carregado, os timeouts da
            # importação de economia caem juntos, e justo nos maiores importadores; abaixo do
            # portão de 1%, o arquivo sairia sem o bloco deles. Refaz o
            # município inteiro (o cache LRU de executar_query já pode ter descartado as
            # consultas dele que deram certo): são poucos, custa segundos.
            # ponytail: uma repetição só, logo em seguida; espera entre tentativas se não bastar.
            repetidos = list(contador.por_cidade)
            for cidade in repetidos:
                del contador.por_cidade[cidade]
                for lista in (ausentes, csv_varias_linhas):
                    if cidade in lista:
                        lista.remove(cidade)
                montar(cidade)
            contador.cidade = None
    finally:
        logging.getLogger("utils.queries.base").removeHandler(contador)

    na_view = sum(1 for m in municipios.values() if m["fonte"] == "view")
    metadados = {
        "na_view": na_view,
        "do_csv": len(municipios) - na_view,
        "ausentes": ausentes,
        "csv_varias_linhas": csv_varias_linhas,
        "chaves_repetidas": repetidas,
        "falhas_de_consulta": dict(contador.por_cidade),
        "recuperados_na_repeticao": [c for c in repetidos if c not in contador.por_cidade],
    }

    motivo = _motivo_para_abortar(metadados, len(cidades), _metadados_anteriores(slug))
    if motivo:
        logger.error("snapshot %s: %s; mantém o anterior", slug, motivo)
        return None

    caminho, duracao_s = _gravar(caminho_snapshot(slug), slug, inicio, metadados, municipios)
    logger.info(
        "snapshot %s: %d na view, %d do CSV, %d ausentes, %d com falha (%.0f s)",
        slug, na_view, metadados["do_csv"], len(ausentes),
        len(metadados["falhas_de_consulta"]), duracao_s,
    )
    return caminho


def _gravar(
    caminho: Path, slug: str, inicio: float, metadados: dict, unidades: dict[str, dict]
) -> tuple[Path, float]:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conteudo = {
        "tema": slug,
        "gerado_em": datetime.now(UTC).isoformat(timespec="seconds"),
        "duracao_s": round(time.monotonic() - inicio, 1),
        "metadados": metadados,
        # A chave fica "municipios" em toda unidade: conferir_tema, texto_do_municipio
        # e as rotas leem dela sem saber se são municípios ou estados.
        "municipios": codificar(unidades),
    }
    temporario = caminho.with_suffix(".tmp")
    with gzip.open(temporario, "wt", encoding="utf-8") as arquivo:
        json.dump(conteudo, arquivo, ensure_ascii=False)
    os.replace(temporario, caminho)  # atômico: quem lê nunca vê um arquivo pela metade
    return caminho, conteudo["duracao_s"]


def ler_matview_da_unidade(conn, slug: str, unidade: str) -> list[dict]:
    """As linhas da matview do tema na unidade, uma por estado ou área."""
    config = UNIDADES_POR_MATVIEW[unidade]
    # SELECT * sem WHERE é seguro aqui, ao contrário das vw_perfil_* (guard do
    # CLAUDE.md): é matview, já materializada, com 4–9 linhas e 40–400 kB, e a conexão
    # leva o statement_timeout (15 s no gamma, 03/11/2026).
    with conn.cursor() as cursor:
        cursor.execute(
            f"SELECT * FROM {config['schema']}.{config['matviews'][slug]} ORDER BY {config['ordem']}"
        )
        colunas = [descricao[0] for descricao in cursor.description]
        return [dict(zip(colunas, valores)) for valores in cursor.fetchall()]


def gerar_snapshot_unidade(slug: str, unidade: str) -> Path | None:
    """Snapshot de estado ou área de um tema: as unidades como chaves, com a linha da
    matview como contexto. Sem o casamento municipal nem os extras do relatório
    (montar_contexto_tema): a matview já traz o tema inteiro da unidade. Devolve o
    caminho gravado, ou None se a rodada abortou (o arquivo anterior fica)."""
    config = UNIDADES_POR_MATVIEW[unidade]
    inicio = time.monotonic()
    with conexao_reaproveitada() as conn:
        try:
            linhas = ler_matview_da_unidade(conn, slug, unidade)
        except psycopg2.Error as err:
            logger.error("snapshot %s (%s): falha ao ler a matview (%s); mantém o anterior", slug, unidade, err)
            return None

    por_nome = {linha.get(config["nome"]): linha for linha in linhas}
    # Portão: nomes distintos e preenchidos, e a quantidade certa quando ela é fixa. O
    # portão municipal (queda na view) não serve: compararia 9 com os 2.074 municípios.
    esperadas = config["quantas"]
    if (
        not linhas
        or len(por_nome) != len(linhas)
        or not all(por_nome)
        or (esperadas is not None and len(linhas) != esperadas)
    ):
        logger.error(
            "snapshot %s (%s): %d linhas e %d nomes distintos, esperava %s; mantém o anterior",
            slug, unidade, len(linhas), len(por_nome), esperadas or "ao menos 1, sem repetir",
        )
        return None

    unidades = {nome: {"fonte": "view", "contexto": linha} for nome, linha in por_nome.items()}
    caminho, duracao_s = _gravar(
        caminho_snapshot(slug, unidade), slug, inicio, {unidade: len(unidades)}, unidades
    )
    logger.info("snapshot %s (%s): %d unidades (%.0f s)", slug, unidade, len(unidades), duracao_s)
    return caminho


def _motivo_para_abortar(metadados: dict, total: int, anteriores: dict | None) -> str | None:
    com_falha = len(metadados["falhas_de_consulta"])
    if total and com_falha / total > MAX_FRACAO_MUNICIPIOS_COM_FALHA:
        return f"{com_falha} de {total} municípios com falha de consulta"
    if anteriores and metadados["na_view"] < anteriores["na_view"] * (1 - MAX_QUEDA_NA_VIEW):
        return f"na view caiu de {anteriores['na_view']} para {metadados['na_view']}"
    return None


def carregar_snapshot(slug: str, unidade: str = "municipio") -> dict | None:
    """O snapshot do tema com os tipos de volta (Decimal, date…), ou None se não existe."""
    caminho = caminho_snapshot(slug, unidade)
    if not caminho.exists():
        return None
    with gzip.open(caminho, "rt", encoding="utf-8") as arquivo:
        conteudo = json.load(arquivo)
    conteudo["municipios"] = decodificar(conteudo["municipios"])
    return conteudo
