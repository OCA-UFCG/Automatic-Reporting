import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict

import psycopg2

from config import QUERY_CACHE_MAX, QUERY_CACHE_TTL_S
from utils.database import get_connection

logger = logging.getLogger(__name__)

# Cache em memória do resultado de queries: as vw_perfil_* são pesadas (saúde ~11,6s,
# economia >30s medido) e o gerador repete a mesma cidade/macrotema entre chamadas —
# cachear evita bater no banco de novo. Espelha o padrão de utils/ssr.py (_ssr_cache):
# OrderedDict (timestamp, valor) com TTL e tamanho máximo, LRU via move_to_end/popitem.
# Protegido por lock porque as queries devem passar a rodar em worker threads
# (to_thread) quando o pipeline for delegado — o cache precisa ser seguro para acesso
# concorrente desde já.
_query_cache: OrderedDict[str, tuple[float, object]] = OrderedDict()
_query_cache_lock = threading.Lock()


def _cache_key(*partes: object) -> str:
    """Chave estável a partir de (query, params, ...): mesma query+params sempre
    gera a mesma chave, independente de identidade de objeto."""
    serializado = json.dumps(partes, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(serializado.encode("utf-8")).hexdigest()


def _cache_get(chave: str) -> object | None:
    with _query_cache_lock:
        item = _query_cache.get(chave)
        if item is None:
            return None
        timestamp, valor = item
        if time.time() - timestamp > QUERY_CACHE_TTL_S:
            _query_cache.pop(chave, None)
            return None
        _query_cache.move_to_end(chave)
        return valor


def _cache_put(chave: str, valor: object) -> None:
    with _query_cache_lock:
        _query_cache[chave] = (time.time(), valor)
        _query_cache.move_to_end(chave)
        while len(_query_cache) > QUERY_CACHE_MAX:
            _query_cache.popitem(last=False)


def limpar_cache_queries() -> None:
    """Esvazia o cache de queries. Usado nos testes (evitar vazamento entre casos) e
    para forçar releitura do banco em operação."""
    with _query_cache_lock:
        _query_cache.clear()


def escalar_valor(valor: object) -> tuple[object, object]:
    if valor is None:
        return None, None
    valor = float(valor)
    if valor >= 1_000_000_000:
        return valor / 1_000_000_000, "bilhões"
    if valor >= 1_000_000:
        return valor / 1_000_000, "milhões"
    if valor >= 1_000:
        return valor / 1_000, "mil"
    return valor, ""


def executar_query(
    query: str, params: tuple, contexto_erro: str, buscar_todas: bool = False
) -> list | tuple | None:
    chave_cache = _cache_key(query, params, buscar_todas)
    resultado_cacheado = _cache_get(chave_cache)
    if resultado_cacheado is not None:
        return resultado_cacheado

    try:
        conn = get_connection()
    except psycopg2.Error as err:
        logger.warning("Falha ao conectar ao banco de dados: %s", err)
        return None

    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            resultado = cursor.fetchall() if buscar_todas else cursor.fetchone()
    except psycopg2.Error as err:
        logger.warning("Falha ao executar query (%s): %s", contexto_erro, err)
        return None
    finally:
        conn.close()

    # Só cacheia sucesso não-nulo: um timeout/erro vira None acima (return antecipado,
    # nunca chega aqui) e não deve "congelar" no cache — a próxima chamada tenta de
    # novo o banco.
    if resultado is not None:
        _cache_put(chave_cache, resultado)
    return resultado


def executar_query_dict(query: str, params: tuple, contexto_erro: str) -> dict | None:
    """Como `executar_query`, mas mapeia a primeira linha para um dict usando
    os nomes de coluna do cursor (útil para `SELECT *` em views largas)."""
    chave_cache = _cache_key(query, params)
    resultado_cacheado = _cache_get(chave_cache)
    if resultado_cacheado is not None:
        return resultado_cacheado

    try:
        conn = get_connection()
    except psycopg2.Error as err:
        logger.warning("Falha ao conectar ao banco de dados: %s", err)
        return None

    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            linha = cursor.fetchone()
            if linha is None:
                return None
            colunas = [descricao[0] for descricao in cursor.description]
            resultado = dict(zip(colunas, linha))
    except psycopg2.Error as err:
        logger.warning("Falha ao executar query (%s): %s", contexto_erro, err)
        return None
    finally:
        conn.close()

    # Mesma regra: só o dict resolvido (linha encontrada) entra no cache.
    _cache_put(chave_cache, resultado)
    return resultado
