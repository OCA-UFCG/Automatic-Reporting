from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from config import BASE_DIR, OUTPUT_DIR
from reports import (
    apagar_relatorio_handler,
    gerar_relatorio_handler,
    listar_relatorios_handler,
)
from utils.cities import carregar_cidades
from utils.macrotemas import MACROTEMAS, TODOS_MACROTEMAS_NOME, TODOS_MACROTEMAS_SLUG
from utils.ssr import start_server as start_ssr_server
from utils.ssr import stop_server as stop_ssr_server

app = FastAPI(on_startup=[start_ssr_server], on_shutdown=[stop_ssr_server])

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
    if safe_name.startswith("../") or safe_name.startswith("/") or ".." in safe_name:
        raise HTTPException(status_code=400)

    file_path = OUTPUT_DIR / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404)
    response = FileResponse(file_path)
    response.headers["Cache-Control"] = "no-store, max-age=0"
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
async def listar_relatorios():
    return await listar_relatorios_handler()


@app.delete("/relatorios/{arquivo_pdf}")
async def apagar_relatorio(arquivo_pdf: str):
    return await apagar_relatorio_handler(arquivo_pdf)


@app.get("/relatorio/{cidade}", response_class=HTMLResponse)
async def gerar_relatorio(cidade: str, macrotema: str = "demografia", charts: str = "all", *, background_tasks: BackgroundTasks):
    return await gerar_relatorio_handler(cidade, macrotema, charts, background_tasks=background_tasks)


# If the frontend has been built (e.g., via Docker), serve it from the same app.
FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist"
if FRONTEND_DIST_DIR.exists():
    @app.get("/")
    async def frontend_index():
        return FileResponse(FRONTEND_DIST_DIR / "index.html")

    # Vite outputs assets under dist/assets; mounting the whole dist keeps it simple.
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST_DIR), html=True), name="frontend")
