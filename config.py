import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import HTTPException

BASE_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = BASE_DIR / "output"
CITIES_FILE = BASE_DIR / "citys.txt"

load_dotenv(dotenv_path=BASE_DIR / ".config")
load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)


def get_config_value(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


DEMOGRAFIA_CSV_URL = get_config_value("DEMOGRAFIA_CSV_URL")
EDUCACAO_CSV_URL = get_config_value("EDUCACAO_CSV_URL")
SAUDE_CSV_URL = get_config_value("SAUDE_CSV_URL")
ECONOMIA_RENDA_CSV_URL = get_config_value("ECONOMIA_RENDA_CSV_URL")
SANEAMENTO_CSV_URL = get_config_value("SANEAMENTO_CSV_URL")
HIDRAULICA_CSV_URL = get_config_value("HIDRAULICA_CSV_URL")
DEFAULT_DOCS_URL = get_config_value("DEFAULT_DOCS_URL")
DEMOGRAFIA_DOCS_URL = get_config_value("DEMOGRAFIA_DOCS_URL") or DEFAULT_DOCS_URL
EDUCACAO_DOCS_URL = get_config_value("EDUCACAO_DOCS_URL")
SAUDE_DOCS_URL = get_config_value("SAUDE_DOCS_URL")
ECONOMIA_RENDA_DOCS_URL = get_config_value("ECONOMIA_RENDA_DOCS_URL")
SANEAMENTO_DOCS_URL = get_config_value("SANEAMENTO_DOCS_URL")
HIDRAULICA_DOCS_URL = get_config_value("HIDRAULICA_DOCS_URL")

MACROTEMAS = {
    "demografia": {
        "nome": "Demografia",
        "docs_url": DEMOGRAFIA_DOCS_URL,
        "docs_env": "DEMOGRAFIA_DOCS_URL",
        "csv_url": DEMOGRAFIA_CSV_URL,
        "csv_env": "DEMOGRAFIA_CSV_URL",
    },
    "educacao": {
        "nome": "Educação",
        "docs_url": EDUCACAO_DOCS_URL,
        "docs_env": "EDUCACAO_DOCS_URL",
        "csv_url": EDUCACAO_CSV_URL,
        "csv_env": "EDUCACAO_CSV_URL",
    },
    "saude": {
        "nome": "Saúde",
        "docs_url": SAUDE_DOCS_URL,
        "docs_env": "SAUDE_DOCS_URL",
        "csv_url": SAUDE_CSV_URL,
        "csv_env": "SAUDE_CSV_URL",
    },
    "economia-renda": {
        "nome": "Economia e Renda",
        "docs_url": ECONOMIA_RENDA_DOCS_URL,
        "docs_env": "ECONOMIA_RENDA_DOCS_URL",
        "csv_url": ECONOMIA_RENDA_CSV_URL,
        "csv_env": "ECONOMIA_RENDA_CSV_URL",
    },
    "saneamento": {
        "nome": "Saneamento",
        "docs_url": SANEAMENTO_DOCS_URL,
        "docs_env": "SANEAMENTO_DOCS_URL",
        "csv_url": SANEAMENTO_CSV_URL,
        "csv_env": "SANEAMENTO_CSV_URL",
    },
    "hidraulica": {
        "nome": "Hidráulica",
        "docs_url": HIDRAULICA_DOCS_URL,
        "docs_env": "HIDRAULICA_DOCS_URL",
        "csv_url": HIDRAULICA_CSV_URL,
        "csv_env": "HIDRAULICA_CSV_URL",
    },
}

MACROTEMA_SECOES = {
    "demografia": {
        "numero": "01",
        "titulo": "Demografia",
        "aliases": ["demografia"],
    },
    "educacao": {
        "numero": "02",
        "titulo": "Educação",
        "aliases": ["educacao", "educação"],
    },
    "saude": {
        "numero": "03",
        "titulo": "Saúde",
        "aliases": ["saude", "saúde"],
    },
    "economia-renda": {
        "numero": "04",
        "titulo": "Economia e Renda",
        "aliases": ["economia", "economia e renda"],
    },
    "saneamento": {
        "numero": "05",
        "titulo": "Infraestrutura e Saneamento",
        "aliases": ["saneamento", "infraestrutura e saneamento"],
    },
    "hidraulica": {
        "numero": "06",
        "titulo": "Segurança Hídrica",
        "aliases": ["hidraulica", "hidráulica", "seguranca hidrica", "segurança hídrica"],
    },
}

OUTPUT_DIR = BASE_DIR / "output"
CITIES_FILE = BASE_DIR / "citys.txt"

def resolve_csv_source(source: str | None, env_name: str = "CSV_URL") -> str | Path:
    if not source:
        raise HTTPException(
            status_code=500,
            detail=f"{env_name} não configurado. Defina no arquivo .config, .env ou nas variáveis de ambiente.",
        )

    parsed = urlparse(source)

    if parsed.scheme in {"http", "https"}:
        return source

    csv_path = Path(source).expanduser()

    if not csv_path.is_absolute():
        csv_path = BASE_DIR / csv_path

    if not csv_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Arquivo CSV não encontrado: {csv_path}",
        )

    return csv_path


def require_config_value(value: str | None, env_name: str) -> str:
    if not value:
        raise HTTPException(
            status_code=500,
            detail=f"{env_name} não configurado. Defina no arquivo .config, .env ou nas variáveis de ambiente.",
        )
    return value