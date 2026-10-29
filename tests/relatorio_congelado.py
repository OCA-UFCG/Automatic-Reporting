"""Harness do teste de regressão do relatório com dados e Docs congelados.

Compartilhado pelo teste (replay, tests/test_relatorio_congelado.py) e pelo gravador
(scripts/gravar_relatorio_congelado.py). `patch` é injetado porque o gravador roda na
imagem do gamma, que não tem pytest: lá é um `setattr` simples.
"""

import asyncio
import json
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from services import cache, generation
from services.macrotemas import get_macrotema
from utils.json_tipado import codificar, decodificar
from utils.queries.base import limpar_cache_queries
from utils.ssr import normalizar_para_json

FIXTURES = Path(__file__).parent / "fixtures" / "relatorio_congelado"

# Alcântara tem rua, indígena e quilombola (15.608); Baía da Traição tem indígena alto e
# quilombola 0; Recife cobre remover_graficos_sem_mencao (só saúde); "todos" cobre as
# mesclas entre temas e a numeração de figuras.
CASOS: list[tuple[str, str, str]] = [
    ("alcantara_demografia", "Alcântara (MA)", "demografia"),
    ("baia_da_traicao_demografia", "Baía da Traição (PB)", "demografia"),
    ("recife_saude", "Recife (PE)", "saude"),
    ("campina_grande_todos", "Campina Grande (PB)", "todos"),
]

# Os buscar_* que services.generation importa por nome.
BUSCAS: tuple[str, ...] = (
    "buscar_perfil_municipal",
    "buscar_caracteristicas_municipio",
    "buscar_populacao_demografia",
    "buscar_demografia_sexo_faixa_etaria",
    "buscar_populacao_indigena",
    "buscar_populacao_quilombola",
    "buscar_publico_etario_vacinas",
    "buscar_mortalidade_infantil_serie",
    "buscar_estabelecimentos_saude_serie",
    "buscar_perfil_saude_municipal",
    "buscar_taxas_educacao_cor_faixa_etaria",
    "buscar_tecnologias_acesso_agua",
    "buscar_esgotamento_sanitario",
    "buscar_perfil_desenvolvimento_social",
    "buscar_linhas_pib_municipal",
    "buscar_linhas_importacao",
    "buscar_comercio_exterior_economia",
    "buscar_populacao_rua",
    "buscar_indicadores_municipio",
)

_AGORA_FIXO = datetime(2026, 10, 26, 10, 0, tzinfo=ZoneInfo("America/Fortaleza"))


def carregar_dados_gravados() -> dict[str, list[dict]]:
    return json.loads((FIXTURES / "dados.json").read_text(encoding="utf-8"))


def buscar_do_replay(dados: dict[str, list[dict]]) -> Callable[[str, tuple], object]:
    def buscar(nome: str, args: tuple):
        chave = codificar(args)
        for gravado in dados.get(nome, ()):
            if gravado["args"] == chave:
                return decodificar(gravado["retorno"])
        # Falha alto: uma extração que mude os argumentos (ex.: o nome canônico) não
        # pode virar um None silencioso que o relatório mascara com placeholder cru.
        raise AssertionError(f"chamada não gravada: {nome}{args}")

    return buscar


def carregar_doc_do_replay() -> Callable[[str], Awaitable[str]]:
    async def carregar_doc(url: str) -> str:
        slug = url.removeprefix("fixture:")
        return (FIXTURES / "docs" / f"{slug}.txt").read_text(encoding="utf-8")

    return carregar_doc


def _recusar(descricao: str):
    def _levantar(*_a, **_k):
        raise AssertionError(f"acesso fora do gravado: {descricao}")

    return _levantar


def instalar_ambiente(
    patch: Callable[[object, str, object], None],
    tmp_path: Path,
    buscar: Callable[[str, tuple], object],
    carregar_doc: Callable[[str], Awaitable[str]],
) -> list[dict]:
    """Aplica os patches em services.generation e devolve a lista onde as props do SSR
    são capturadas."""
    import utils.database
    import utils.queries.base

    for nome in BUSCAS:
        # nome=nome: sem isso todos os stubs fechariam sobre o último da lista.
        patch(generation, nome, lambda *args, nome=nome: buscar(nome, args))

    # Nenhum acesso ao banco ou ao CSV fora do gravado. base.py importa
    # get_connection por nome, então patcha os dois lugares.
    patch(utils.database, "get_connection", _recusar("get_connection"))
    patch(utils.queries.base, "get_connection", _recusar("get_connection"))
    patch(generation, "carregar_csv", _recusar("carregar_csv"))

    # Sem isso, no CI todo docs_url é vazio, o handler pula todos os temas e o teste
    # passaria vazio para sempre.
    # Tema sem Doc gravado (ex.: instrumentos-sudene, mais novo que a gravação) fica
    # sem docs_url e é pulado, como em produção quando o secret do Doc não existe.
    def macrotema_congelado(slug: str):
        gravado = (FIXTURES / "docs" / f"{slug}.txt").exists()
        return {**get_macrotema(slug), "docs_url": f"fixture:{slug}" if gravado else None}

    patch(generation, "get_macrotema", macrotema_congelado)
    patch(generation, "CARACTERISTICAS_DOCS_URL", "fixture:caracteristicas")
    patch(generation, "require_config_value", lambda valor, _env: valor)
    patch(generation, "carregar_texto_do_docs", carregar_doc)

    class _DatetimeFixo(datetime):
        @classmethod
        def now(cls, tz=None):
            return _AGORA_FIXO

    patch(generation, "datetime", _DatetimeFixo)

    # Os gráficos rodam de verdade (nome determinístico, sem bytes no HTML): existir ou
    # não um gráfico muda a supressão de legenda.
    patch(generation, "OUTPUT_DIR", tmp_path)
    patch(cache, "OUTPUT_DIR", tmp_path)
    patch(cache, "DATA_VERSION_FILE", tmp_path / ".data_version")

    # Shapefiles não estão no repo.
    patch(generation, "render_mapa_marker", lambda *_a, **_k: '<div class="mapa-congelado"></div>')

    async def _gerar_pdf_falso(*_a, **_k):
        return True

    capturadas: list[dict] = []

    # O SSR é função pura das props: props iguais, HTML igual. Comparar as props é a
    # leitura deliberada de "HTML idêntico".
    async def _ssr_captura(props: dict, *_a, **_k) -> str:
        capturadas.append(props)
        return "<html></html>"

    patch(generation, "_gerar_pdf", _gerar_pdf_falso)
    patch(generation, "render_react_ssr", _ssr_captura)
    return capturadas


def props_do_relatorio(cidade: str, macrotema: str, capturadas: list[dict]) -> str:
    limpar_cache_queries()
    asyncio.run(generation.gerar_relatorio_handler(cidade, macrotema))
    return json.dumps(
        normalizar_para_json(capturadas[-1]), sort_keys=True, ensure_ascii=False, indent=1
    )
