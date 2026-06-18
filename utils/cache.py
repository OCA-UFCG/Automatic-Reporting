from typing import Any, Optional, Dict
from diskcache import Cache

class CacheManager:
    """
    Gestor unificado de cache para a aplicação.
    Responsável por gerir os namespaces: docs_cache, geo_cache e csv_cache.
    """

    def __init__(self) -> None:
        """
        Inicializa os backends de cache (memória ou disco) para cada namespace.
        """
        csv = Cache()
        docs = Cache()
        geocoding = Cache()
        pass

    def obter_dado(self, namespace: str, chave: str) -> Optional[Any]:
        """
        Recupera um valor do cache com base na gaveta (namespace) e na chave.

        Args:
            namespace (str): O nome do namespace (ex: 'docs_cache').
            chave (str): O identificador único do dado (ex: o hash do CSV ou nome da cidade).

        Returns:
            O dado armazenado ou None se o dado não existir ou tiver expirado (cache miss).
        """
        pass

    def guardar_dado(self, namespace: str, chave: str, valor: Any, ttl_segundos: Optional[int] = None) -> None:
        """
        Guarda um valor num namespace específico.

        Args:
            namespace (str): O nome do namespace.
            chave (str): O identificador único do dado.
            valor (Any): O dado a ser guardado (texto do Google Docs, dicionário geográfico, etc.).
            ttl_segundos (int, optional): Tempo de vida em segundos. Se for None, usa o padrão da gaveta.
        """
        pass

    def remover_dado(self, namespace: str, chave: str) -> None:
        """
        Remove um item específico de um namespace.

        Args:
            namespace (str): O nome do namespace.
            chave (str): O identificador único do dado a ser apagado.
        """
        pass

    def limpar_namespace(self, namespace: str) -> None:
        """
        Esvazia completamente o cache de um namespace especificado. Útil para botões de reset no painel de administração.

        Args:
            namespace (str): O nome do namespace a ser limpo (ex: 'geo_cache').
        """
        pass

    def obter_estatisticas(self) -> Dict[str, Any]:
        """
        Recupera métricas do cache para a rota de observabilidade (/admin/cache/stats).

        Returns:
            Um dicionário com informações como número de itens e tamanho de cada namespace.
        """
        pass
