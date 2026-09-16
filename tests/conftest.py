import pytest

from utils.queries.base import limpar_cache_queries


@pytest.fixture(autouse=True)
def _limpar_cache_queries_entre_testes():
    """O cache de queries (utils/queries/base.py) é um estado global de processo;
    sem limpar entre testes, o resultado cacheado por um caso vazaria para o
    próximo (ex.: um teste de query real "vencendo" um mock de outro teste)."""
    limpar_cache_queries()
    yield
    limpar_cache_queries()
