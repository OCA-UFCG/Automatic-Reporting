import asyncio
import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from config import BASE_DIR, MAPAS_DIR, OUTPUT_DIR
from services import (
    apagar_relatorio_handler,
    gerar_relatorio_handler,
    listar_relatorios_handler,
)
from utils.data.cities import carregar_cidades
from utils.data.macrotemas import (
    MACROTEMAS,
    TODOS_MACROTEMAS_NOME,
    TODOS_MACROTEMAS_SLUG,
)
from utils.ssr import start_server as start_ssr_server
from utils.ssr import stop_server as stop_ssr_server

logger = logging.getLogger(__name__)


def _checar_mv_indicadores() -> None:
    """Corpo síncrono da checagem (psycopg2 bloqueia): connect + query + close.
    Roda numa thread, ver _avisar_se_mv_indicadores_faltar abaixo."""
    try:
        from utils.database import get_connection

        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM pg_matviews "
                    "WHERE schemaname = 'relatorios_auto' "
                    "AND matviewname = 'mv_indicadores'"
                )
                existe = cur.fetchone() is not None
        finally:
            conn.close()
        if not existe:
            logger.warning(
                "relatorios_auto.mv_indicadores não encontrada — rode a DDL de "
                "materialização (mv_indicadores + índice único + refresh_matviews.sh). "
                "Sem ela, buscar_indicadores_municipio degrada e o relatório fica sem "
                "os indicadores transversais."
            )
    except Exception:
        # Banco indisponível no startup (ex.: tunnel ainda não subiu) não pode
        # derrubar a app — só logamos e seguimos.
        logger.warning(
            "Não foi possível verificar relatorios_auto.mv_indicadores no startup "
            "(banco inacessível?); seguindo sem bloquear.",
            exc_info=True,
        )


async def _avisar_se_mv_indicadores_faltar() -> None:
    """Aviso não-fatal no startup: os indicadores leem relatorios_auto.mv_indicadores,
    criada por uma DDL manual e gated. Se a app subir antes da DDL, os indicadores
    degradam silenciosamente — melhor um warning claro no log. Nunca levanta, nunca
    bloqueia o startup e tolera o banco inacessível (tunnel fora do ar).

    async + to_thread porque o Starlette roda handler de on_startup síncrono direto
    no event loop: com o túnel fora do ar, o connect_timeout=5 de utils/database.py
    prenderia o loop por 5s antes de a app aceitar a primeira conexão.
    """
    await asyncio.to_thread(_checar_mv_indicadores)


app = FastAPI(
    on_startup=[
        start_ssr_server,
        _avisar_se_mv_indicadores_faltar,
    ],
    on_shutdown=[stop_ssr_server],
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# Serve output files with headers that prevent caching so clients always fetch
# the most recent version (avoids stale PDFs from browser/proxy cache).
@app.api_route("/output/{path:path}", methods=["GET", "HEAD"])
async def output_file(path: str):
    # Support versioned paths like /output/v{version}/filename.pdf where the
    # version component is only used for cache-busting and not part of the
    # filesystem layout. Strip a leading v{digits}/ segment if present.
    import re

    m = re.match(r"^v\d+/(.+)$", path)
    if m:
        safe_name = m.group(1)
    else:
        safe_name = path

    # Prevent path traversal
    if safe_name.startswith(("../", "/")) or ".." in safe_name:
        raise HTTPException(status_code=400)

    file_path = OUTPUT_DIR / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404)
    response = FileResponse(file_path)
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


# Mapas PNG pré-gerados (1 por município), servidos da pasta montada como volume.
# Imutáveis, então cache longo — ao contrário do /output.
@app.api_route("/mapas/{path:path}", methods=["GET", "HEAD"])
async def mapa_estatico_file(path: str):
    if path.startswith(("../", "/")) or ".." in path:
        raise HTTPException(status_code=400)
    file_path = MAPAS_DIR / path
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404)
    response = FileResponse(file_path)
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/cities")
async def listar_cidades():
    return carregar_cidades()


@app.get("/macrotemas")
async def listar_macrotemas():
    return [
        {"slug": TODOS_MACROTEMAS_SLUG, "nome": TODOS_MACROTEMAS_NOME},
        *[
        {"slug": slug, "nome": dados["nome"]}
        for slug, dados in MACROTEMAS.items()
        ],
    ]


@app.get("/relatorios")
def listar_relatorios():
    return listar_relatorios_handler()


@app.delete("/relatorios/{arquivo_pdf}")
def apagar_relatorio(arquivo_pdf: str):
    return apagar_relatorio_handler(arquivo_pdf)


@app.get("/relatorio/{cidade}", response_class=HTMLResponse)
async def gerar_relatorio(
    cidade: str, macrotema: str = "demografia", aguardar: str = "sim"
):
    return await gerar_relatorio_handler(cidade, macrotema, aguardar=aguardar != "nao")


# Laboratório de Temas: as rotas só existem com a flag ligada, e ela só é setada no
# gamma (-e no cd-gamma.yaml). Promover o código para beta/prod não liga nada (spec do
# laboratório, "Acesso"). Antes do mount do frontend, que responde por "/".
if os.getenv("LABORATORIO_HABILITADO") == "1":
    from datetime import UTC, datetime

    from pydantic import BaseModel, Field

    from services.laboratorio import (
        abrir_doc,
        iniciar_conferencia,
        ler_com_cada_valor,
        ler_conferencia,
        ler_csv,
        texto_do_municipio,
        valores_das_colunas,
    )
    from services.laboratorio_snapshot import caminho_snapshot, carregar_snapshot

    class TextoDoTema(BaseModel):
        # Os Docs de hoje têm até ~30 kB; o teto só barra abuso.
        texto: str = Field(max_length=500_000)
        # Linhas do CSV que a editora subiu, por cidade (POST /laboratorio/{tema}/csv).
        # Vêm do navegador em cada pedido: o servidor não guarda o CSV (spec).
        csv: dict[str, dict] | None = None

    class ArquivoCsv(BaseModel):
        # Uma view inteira em CSV tem ~1–3 MB; o teto só barra abuso.
        csv: str = Field(max_length=20_000_000)

    class TextoNaCidade(TextoDoTema):
        cidade: str
        # Painel de texto pronto: gera os gráficos de verdade da cidade (0,1–1,8 s na
        # 1ª vez, depois reaproveitados). A conferência e o "ler com cada valor" não.
        graficos: bool = False

    def _tema_com_snapshot(tema: str) -> str:
        if tema not in MACROTEMAS or not caminho_snapshot(tema).exists():
            raise HTTPException(status_code=404, detail=f"tema sem snapshot: {tema}")
        return tema

    @app.get("/laboratorio/temas")
    def laboratorio_temas():
        # O SPA também usa esta rota para saber se o laboratório está ligado (spec).
        # A hora do arquivo, e não o "gerado_em" de dentro dele: ler 8 snapshots
        # inteiros custaria segundos. O arquivo é gravado no fim da rodada.
        def gerado_em(slug: str) -> str | None:
            caminho = caminho_snapshot(slug)
            if not caminho.exists():
                return None
            return datetime.fromtimestamp(caminho.stat().st_mtime, UTC).isoformat(timespec="seconds")

        return [
            {"slug": slug, "nome": dados["nome"], "snapshot_gerado_em": gerado_em(slug)}
            for slug, dados in MACROTEMAS.items()
        ]

    @app.get("/laboratorio/{tema}/doc")
    async def laboratorio_doc(tema: str):
        if tema not in MACROTEMAS:
            raise HTTPException(status_code=404, detail=f"tema desconhecido: {tema}")
        try:
            doc = await abrir_doc(tema)
        except ValueError as err:  # Google fora do ar ou Doc sem acesso público
            raise HTTPException(status_code=502, detail=str(err)) from err
        if doc is None:
            raise HTTPException(status_code=404, detail=f"tema sem Doc configurado: {tema}")
        return doc

    @app.get("/laboratorio/{tema}/colunas")
    def laboratorio_colunas(tema: str):
        snapshot = carregar_snapshot(_tema_com_snapshot(tema))
        contextos = {cidade: m["contexto"] for cidade, m in snapshot["municipios"].items()}
        return {"snapshot_gerado_em": snapshot["gerado_em"], "colunas": valores_das_colunas(contextos)}

    @app.post("/laboratorio/{tema}/csv")
    def laboratorio_csv(tema: str, corpo: ArquivoCsv):
        try:
            return ler_csv(_tema_com_snapshot(tema), corpo.csv)
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err)) from err

    @app.post("/laboratorio/{tema}/cada-valor")
    def laboratorio_cada_valor(tema: str, corpo: TextoDoTema):
        # Rota própria, e não N chamadas a /municipio (que relê o snapshot a cada
        # uma, ~0,5 s): um parágrafo de saúde com as vacinas passa de 80 valores.
        return {"colunas": ler_com_cada_valor(_tema_com_snapshot(tema), corpo.texto, corpo.csv) or []}

    @app.post("/laboratorio/{tema}/conferencias")
    def laboratorio_conferir(tema: str, corpo: TextoDoTema):
        return {"id": iniciar_conferencia(_tema_com_snapshot(tema), corpo.texto, corpo.csv)}

    @app.get("/laboratorio/conferencias/{id_conferencia}")
    def laboratorio_conferencia(id_conferencia: str):
        estado = ler_conferencia(id_conferencia)
        if estado is None:
            raise HTTPException(status_code=404, detail="conferência não encontrada")
        return estado

    @app.post("/laboratorio/{tema}/municipio")
    def laboratorio_municipio(tema: str, corpo: TextoNaCidade):
        resultado = texto_do_municipio(_tema_com_snapshot(tema), corpo.texto, corpo.cidade, corpo.csv, corpo.graficos)
        if resultado is None:
            raise HTTPException(status_code=404, detail=f"cidade fora do snapshot: {corpo.cidade}")
        return resultado


# If the frontend has been built (e.g., via Docker), serve it from the same app.
FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist"
if FRONTEND_DIST_DIR.exists():
    @app.get("/")
    async def frontend_index():
        return FileResponse(FRONTEND_DIST_DIR / "index.html")

    # Vite outputs assets under dist/assets; mounting the whole dist keeps it simple.
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST_DIR), html=True), name="frontend")
