"""Montagem do contexto de um macrotema para um município.

Este módulo existe porque o contexto precisa ser montado **uma vez só**, em um
lugar só. Antes, a prévia do painel editorial refazia uma versão reduzida do
que `gerar_relatorio_handler` faz: consultava a view do perfil e parava por
aí. O resultado é que a prévia ficava com dois campos (`nm_mun`, `sigla_uf`)
enquanto o relatório real tinha dezenas, e todo `$placeholder` aparecia cru na
tela do editor — dando a impressão de que o contrato estava errado quando o
errado era o contexto.

A ordem aqui é a mesma do relatório, e a razão de cada etapa está no comentário
ao lado dela.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime

from fastapi import HTTPException

from config import resolve_csv_source
from services.csv_loader import (
    carregar_csv,
    get_csv_config_for_macrotema,
    normalizar_colunas_macrotema,
)
from utils.data.cities import filtrar_linhas_por_cidade
from utils.geografia import resolver_nome_uf, separar_cidade_uf
from utils.queries.caracteristicas import buscar_caracteristicas_municipio
from utils.queries.demografia import (
    buscar_demografia_sexo_faixa_etaria,
    buscar_populacao_demografia,
    buscar_populacao_indigena,
    buscar_populacao_quilombola,
    buscar_populacao_rua,
)
from utils.queries.desenvolvimento_social import buscar_perfil_desenvolvimento_social
from utils.queries.economia_exportacao import buscar_comercio_exterior_economia
from utils.queries.economia_importacao import (
    buscar_linhas_importacao,
    processar_importacao,
)
from utils.queries.economia_renda import (
    buscar_linhas_pib_municipal,
    processar_indicadores_economia,
    processar_pib_evolucao,
)
from utils.queries.educacao import (
    buscar_perfil_educacional_municipio,
    buscar_taxas_educacao_cor_faixa_etaria,
)
from utils.queries.hidraulica import buscar_tecnologias_acesso_agua
from utils.queries.indicadores import buscar_indicadores_municipio
from utils.queries.perfil_municipal import buscar_perfil_municipal
from utils.queries.saneamento import buscar_esgotamento_sanitario
from utils.queries.saude import (
    buscar_cobertura_vacinal,
    buscar_estabelecimentos_saude_serie,
    buscar_mortalidade_infantil_serie,
    buscar_perfil_saude_municipal,
    buscar_publico_etario_vacinas,
)

logger = logging.getLogger(__name__)

# De onde veio a linha base do município — e, quando veio do CSV, por quê.
# A distinção existe porque as duas causas pedem ações opostas de quem opera o
# painel: sem conexão, abrir o túnel resolve; cidade ausente da view é assunto
# para quem mantém os dados. Dizer "banco fora do ar" nos dois casos manda a
# pessoa procurar o problema no lugar errado.
ORIGEM_VIEW = "view"
ORIGEM_CSV_SEM_BANCO = "csv_sem_banco"
ORIGEM_CSV_SEM_CIDADE = "csv_sem_cidade"


def veio_do_csv(origem: str) -> bool:
    return origem in (ORIGEM_CSV_SEM_BANCO, ORIGEM_CSV_SEM_CIDADE)


def _banco_alcancavel() -> bool:
    """Serve só para redigir o aviso, nunca para decidir o caminho dos dados.

    `executar_query` engole erros e devolve `None` por projeto (o relatório
    degrada, não quebra), então "a view não respondeu" é ambíguo entre "sem
    conexão" e "sem linha para esta cidade". Esta sonda desfaz a ambiguidade, e
    só roda quando já estamos no caminho degradado — nunca no caminho feliz.
    """
    import psycopg2

    from utils.database import get_connection

    try:
        conexao = get_connection()
    except psycopg2.Error:
        return False
    conexao.close()
    return True


@dataclass
class CacheDeEnriquecimento:
    """As consultas que valem para o relatório inteiro, feitas uma vez só.

    Um relatório com vários macrotemas percorre o laço uma vez por tema, mas
    `vw_indicadores`, características e população em situação de rua são uma
    linha por município — repetir a consulta a cada volta só castiga o banco.
    """

    consultado: bool = False
    dados: dict[str, dict | None] = field(default_factory=dict)

    def get(self, chave: str) -> dict | None:
        return self.dados.get(chave)


def carregar_linha_base(
    macrotema_slug: str, macrotema_dados: dict, cidade: str
) -> tuple[list[dict], str]:
    """A linha do município no macrotema, e de qual fonte ela veio.

    O banco (`relatorios_auto.vw_perfil_*`) é a fonte primária: só cai para o
    CSV se a view não tiver a cidade ou o banco estiver fora do ar (PR #91).

    Devolve `("view", …)` ou `("csv", …)` porque quem chama precisa saber: a
    prévia do painel avisa o editor quando está mostrando o cenário degradado.
    """
    nome_cidade, uf = separar_cidade_uf(cidade)

    if macrotema_slug == "educacao":
        # Educação usa sua própria view (vw_perfil_educacional_municipal, via
        # buscar_perfil_educacional_municipio) em vez de buscar_perfil_municipal,
        # mas segue a mesma regra das demais.
        try:
            perfil = buscar_perfil_educacional_municipio(nome_cidade, uf)
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err)) from err
        if perfil:
            return [dict(perfil)], ORIGEM_VIEW
    else:
        try:
            perfil = buscar_perfil_municipal(macrotema_slug, nome_cidade, uf) if uf else None
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err)) from err
        if perfil:
            linha = dict(perfil)
            # Usa o nome canônico da própria view (grafia/acentuação corretas),
            # nunca o texto digitado pelo usuário — do contrário o
            # enriquecimento a jusante (características, demografia, saúde…), que
            # casa nm_mun de forma case-sensitive, não encontra a cidade. Garante
            # o formato "Cidade (UF)" que resolver_nome_uf/capa/mapas esperam,
            # removendo antes um sufixo "(UF)" que algumas views já trazem.
            nome_canonico = re.sub(
                r"\s*\([^)]*\)\s*$", "", str(perfil.get("nm_mun") or nome_cidade)
            ).strip()
            linha["nm_mun"] = f"{nome_canonico} ({uf})"
            return [linha], ORIGEM_VIEW

    if uf:
        # Só é fallback de verdade quando o banco foi consultado e não tinha a
        # cidade; sem UF a view sequer é chamada.
        logger.warning(
            "Sem dados no banco para '%s' (%s); usando CSV como fallback.",
            cidade,
            macrotema_slug,
        )
    csv_url, csv_env = get_csv_config_for_macrotema(macrotema_dados)
    df = carregar_csv(resolve_csv_source(csv_url, csv_env))
    df = normalizar_colunas_macrotema(df, macrotema_slug)

    try:
        linhas = filtrar_linhas_por_cidade(df, cidade).to_dict("records")
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    if not linhas:
        raise HTTPException(status_code=404, detail=f"Cidade '{cidade}' não encontrada.")
    origem = ORIGEM_CSV_SEM_CIDADE if _banco_alcancavel() else ORIGEM_CSV_SEM_BANCO
    return linhas, origem


def _preencher_cache(
    cache: CacheDeEnriquecimento, linha_base: dict, macrotema_slugs: list[str]
) -> None:
    """Roda as consultas de enriquecimento uma única vez por relatório."""
    if cache.consultado:
        return

    nome, uf = resolver_nome_uf(linha_base)
    d = cache.dados
    d["caracteristicas"] = buscar_caracteristicas_municipio(nome, uf)

    if "demografia" in macrotema_slugs:
        d["demografia"] = buscar_populacao_demografia(nome, uf)
        d["sexo_faixa"] = buscar_demografia_sexo_faixa_etaria(nome, uf)
        d["indigena"] = buscar_populacao_indigena(nome, uf)
        d["quilombola"] = buscar_populacao_quilombola(nome, uf)
    if "saude" in macrotema_slugs:
        d["publico_etario"] = buscar_publico_etario_vacinas(nome, uf)
        d["cobertura_vacinal"] = buscar_cobertura_vacinal(nome, uf)
        d["mortalidade_infantil"] = buscar_mortalidade_infantil_serie(nome, uf)
        d["estabelecimentos_saude"] = buscar_estabelecimentos_saude_serie(nome, uf)
        d["perfil_saude"] = buscar_perfil_saude_municipal(nome, uf)
    if "educacao" in macrotema_slugs:
        d["taxas_educacao"] = buscar_taxas_educacao_cor_faixa_etaria(nome, uf)
    if "hidraulica" in macrotema_slugs:
        d["tecnologias_acesso_agua"] = buscar_tecnologias_acesso_agua(nome, uf)
    if "saneamento" in macrotema_slugs:
        d["esgotamento"] = buscar_esgotamento_sanitario(nome, uf)
    if "desenvolvimento-social" in macrotema_slugs:
        d["perfil_desenvolvimento_social"] = buscar_perfil_desenvolvimento_social(nome, uf)
    if "economia-renda" in macrotema_slugs:
        linhas_pib = buscar_linhas_pib_municipal(nome, uf)
        d["pib"] = processar_pib_evolucao(linhas_pib)
        d["indicadores_economia"] = processar_indicadores_economia(linhas_pib)
        d["importacao"] = processar_importacao(buscar_linhas_importacao(nome, uf))
        d["comercio_exterior"] = buscar_comercio_exterior_economia(nome, uf)

    d["rua"] = buscar_populacao_rua(nome, uf)
    # Painel de indicadores da capa: uma única linha em vw_indicadores cobre
    # todos os macrotemas, então a busca fica fora dos ifs.
    d["indicadores"] = buscar_indicadores_municipio(nome, uf)
    cache.consultado = True


# Qual bloco de enriquecimento entra em qual macrotema. `None` significa "em
# todos" — características, população em situação de rua e o painel de
# indicadores valem para o relatório inteiro.
_ENRIQUECIMENTO: tuple[tuple[str, str | None], ...] = (
    ("caracteristicas", None),
    ("demografia", "demografia"),
    ("sexo_faixa", "demografia"),
    ("indigena", "demografia"),
    ("quilombola", "demografia"),
    ("rua", None),
    ("indicadores", None),
    ("publico_etario", "saude"),
    ("cobertura_vacinal", "saude"),
    ("mortalidade_infantil", "saude"),
    ("estabelecimentos_saude", "saude"),
    ("perfil_saude", "saude"),
    ("taxas_educacao", "educacao"),
    ("tecnologias_acesso_agua", "hidraulica"),
    ("esgotamento", "saneamento"),
    ("perfil_desenvolvimento_social", "desenvolvimento-social"),
    ("pib", "economia-renda"),
    ("indicadores_economia", "economia-renda"),
    ("importacao", "economia-renda"),
    ("comercio_exterior", "economia-renda"),
)


def montar_linhas_macrotema(
    macrotema_slug: str,
    macrotema_dados: dict,
    cidade: str,
    gerado_em: datetime,
    macrotema_slugs: list[str],
    cache: CacheDeEnriquecimento,
) -> tuple[list[dict], str]:
    """A linha base do macrotema, enriquecida com as demais consultas.

    É o `contexto` que alimenta tanto o relatório quanto a prévia do painel:
    resolve `$placeholder`, decide as condicionais e nomeia os gráficos.
    """
    linhas, origem = carregar_linha_base(macrotema_slug, macrotema_dados, cidade)

    for linha in linhas:
        linha["data_relatorio"] = gerado_em.strftime("%d/%m/%Y")
        linha["hora_relatorio"] = gerado_em.strftime("%H:%M")

    _preencher_cache(cache, linhas[0], macrotema_slugs)

    for chave, exigido in _ENRIQUECIMENTO:
        # O bloco de demografia tem uma exceção histórica: `buscar_populacao_
        # demografia` só entra no próprio relatório de demografia, enquanto os
        # demais entram sempre que demografia está entre os macrotemas pedidos.
        if chave == "demografia" and macrotema_slug != "demografia":
            continue
        if exigido is not None and exigido not in macrotema_slugs:
            continue
        dados = cache.get(chave)
        if not dados:
            continue
        for linha in linhas:
            linha.update(dados)

    return linhas, origem
