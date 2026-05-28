from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import BASE_DIR
from utils.macrotemas import MACROTEMAS, TODOS_MACROTEMAS_NOME, TODOS_MACROTEMAS_SLUG
from utils.cities import carregar_cidades
from utils.ssr import start_server as start_ssr_server, stop_server as stop_ssr_server
from reports import (
    listar_relatorios_handler,
    apagar_relatorio_handler,
    gerar_relatorio_handler,
)

app = FastAPI(on_startup=[start_ssr_server], on_shutdown=[stop_ssr_server])

app.mount("/output", StaticFiles(directory=str(BASE_DIR / "output")), name="output")

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
async def gerar_relatorio(cidade: str, macrotema: str = "demografia", charts: str = "all"):
    return await gerar_relatorio_handler(cidade, macrotema, charts)


# If the frontend has been built (e.g., via Docker), serve it from the same app.
FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist"
if FRONTEND_DIST_DIR.exists():
    @app.get("/")
    async def frontend_index():
        return FileResponse(FRONTEND_DIST_DIR / "index.html")

    # Vite outputs assets under dist/assets; mounting the whole dist keeps it simple.
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST_DIR), html=True), name="frontend")
