from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from config import BASE_DIR, MAPAS_DIR, OUTPUT_DIR
from services import (
    apagar_relatorio_handler,
    gerar_relatorio_handler,
    listar_relatorios_handler,
)
from services.admin import (
    conexao_handler,
    historico_handler,
    importar_do_doc_handler,
    ler_contrato_handler,
    ler_versao_handler,
    listar_contratos_handler,
    login_handler,
    previa_handler,
    publicar_contrato_handler,
    validar_handler,
    verificar_token,
)
from utils.data.cities import carregar_cidades
from utils.data.macrotemas import (
    MACROTEMAS,
    TODOS_MACROTEMAS_NOME,
    TODOS_MACROTEMAS_SLUG,
)
from utils.editorial.manifesto import montar_manifesto
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
        # Vite do painel editorial (admin/vite.config.js).
        "http://localhost:5174",
        "http://127.0.0.1:5174",
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


# Vocabulário do painel editorial: campos, gráficos, tipos de bloco e
# operadores que o operador pode usar. O painel não sabe nada disso por conta
# própria — ele pergunta aqui (docs/PLANO-PAINEL-EDITORIAL.md §5).
@app.get("/manifesto")
def manifesto(usar_banco: bool = True):
    return montar_manifesto(usar_banco=usar_banco)


@app.get("/relatorios")
def listar_relatorios():
    return listar_relatorios_handler()


@app.delete("/relatorios/{arquivo_pdf}")
def apagar_relatorio(arquivo_pdf: str):
    return apagar_relatorio_handler(arquivo_pdf)


@app.get("/relatorio/{cidade}", response_class=HTMLResponse)
async def gerar_relatorio(cidade: str, macrotema: str = "demografia"):
    return await gerar_relatorio_handler(cidade, macrotema)


# ---------------------------------------------------------------------------
# Painel editorial (docs/PLANO-PAINEL-EDITORIAL.md).
# A API fica em /admin; a tela em /painel. Separados porque /painel é um mount
# de arquivos estáticos e engoliria as rotas se dividissem o prefixo.
# ---------------------------------------------------------------------------


def editor_autenticado(authorization: str | None = Header(default=None)) -> str:
    """Quem está editando. Não autoriza nada — nomeia, para o `publicado_por`."""
    return verificar_token(authorization)


@app.post("/admin/login")
def admin_login(corpo: dict):
    return login_handler(corpo.get("nome", ""), corpo.get("senha", ""))


@app.get("/admin/sessao")
def admin_sessao(editor: str = Depends(editor_autenticado)):
    return {"nome": editor}


@app.get("/admin/contratos")
def admin_listar_contratos(editor: str = Depends(editor_autenticado)):
    return listar_contratos_handler()


@app.get("/admin/contratos/{slug}")
def admin_ler_contrato(slug: str, editor: str = Depends(editor_autenticado)):
    return ler_contrato_handler(slug)


@app.put("/admin/contratos/{slug}")
def admin_publicar_contrato(
    slug: str, corpo: dict, editor: str = Depends(editor_autenticado)
):
    return publicar_contrato_handler(
        slug, corpo.get("contrato") or {}, corpo.get("versao_esperada"), editor
    )


@app.get("/admin/contratos/{slug}/historico")
def admin_historico(slug: str, editor: str = Depends(editor_autenticado)):
    return historico_handler(slug)


@app.get("/admin/contratos/{slug}/versoes/{versao}")
def admin_ler_versao(slug: str, versao: int, editor: str = Depends(editor_autenticado)):
    return ler_versao_handler(slug, versao)


@app.post("/admin/contratos/{slug}/importar")
async def admin_importar(
    slug: str, baixar: bool = False, editor: str = Depends(editor_autenticado)
):
    return await importar_do_doc_handler(slug, baixar)


@app.post("/admin/contratos/{slug}/previa")
async def admin_previa(
    slug: str, corpo: dict, editor: str = Depends(editor_autenticado)
):
    return await previa_handler(
        slug, corpo.get("contrato") or {}, corpo.get("cidade") or ""
    )


@app.get("/admin/conexao")
def admin_conexao(editor: str = Depends(editor_autenticado)):
    return conexao_handler()


@app.post("/admin/validar")
def admin_validar(corpo: dict, editor: str = Depends(editor_autenticado)):
    return validar_handler(corpo.get("contrato") or {})


# A tela do painel, quando construída (npm run build -w admin).
ADMIN_DIST_DIR = BASE_DIR / "admin" / "dist"


# Um Mount em "/painel" só casa "/painel/...", e o mount do frontend em "/"
# (registrado depois) engole o "/painel" sem barra antes que o redirecionamento
# automático do Starlette possa agir. Sem esta rota, digitar o endereço sem a
# barra final dá 404.
@app.get("/painel", include_in_schema=False)
def painel_raiz():
    if not ADMIN_DIST_DIR.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "A tela do painel ainda não foi construída. "
                "Rode `npm install && npm run build -w admin` e reinicie a API."
            ),
        )
    return RedirectResponse(url="/painel/")


if ADMIN_DIST_DIR.exists():
    app.mount(
        "/painel", StaticFiles(directory=str(ADMIN_DIST_DIR), html=True), name="painel"
    )


# If the frontend has been built (e.g., via Docker), serve it from the same app.
FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist"
if FRONTEND_DIST_DIR.exists():
    @app.get("/")
    async def frontend_index():
        return FileResponse(FRONTEND_DIST_DIR / "index.html")

    # Vite outputs assets under dist/assets; mounting the whole dist keeps it simple.
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST_DIR), html=True), name="frontend")
