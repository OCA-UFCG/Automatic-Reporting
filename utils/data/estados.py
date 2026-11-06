"""Estados que têm relatório próprio, ao lado dos municípios de cities.json.

Os nomes são exatamente os da coluna `uf_estado` das matviews estaduais
(`auto_relatorios_est.est_*`, conferido no banco em 05/11/2026): é por ela que
utils/queries/estado.py acha a linha do estado, então "Paraíba" e não "Paraiba".
"""

# Só os 9 do Nordeste, como estão nas matviews. MG fica de fora até a equipe de dados
# incluí-lo nelas (05/11/2026); entrar aqui antes disso daria um relatório vazio.
ESTADOS_COM_RELATORIO: tuple[str, ...] = (
    "Maranhão",
    "Piauí",
    "Ceará",
    "Rio Grande do Norte",
    "Paraíba",
    "Pernambuco",
    "Alagoas",
    "Sergipe",
    "Bahia",
)

_ESTADO_POR_CHAVE = {estado.casefold(): estado for estado in ESTADOS_COM_RELATORIO}


def resolver_estado(nome: str) -> str | None:
    """Nome canônico do estado, tolerante a caixa e espaços nas pontas; None quando o
    nome não é de um estado com relatório (um município, por exemplo).

    Mesma tolerância da validação de cidade em generation.py (casefold), sem ignorar
    acento: o portal manda o nome escolhido da lista, nunca um digitado.

    Ex.: resolver_estado(" paraíba ") == "Paraíba"; resolver_estado("Recife (PE)") is None
    """
    return _ESTADO_POR_CHAVE.get(nome.strip().casefold())
