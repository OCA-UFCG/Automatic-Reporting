from config import (
    DEMOGRAFIA_CSV_URL,
    EDUCACAO_CSV_URL,
    SAUDE_CSV_URL,
    ECONOMIA_RENDA_CSV_URL,
    SANEAMENTO_CSV_URL,
    HIDRAULICA_CSV_URL,
    DEMOGRAFIA_DOCS_URL,
    EDUCACAO_DOCS_URL,
    SAUDE_DOCS_URL,
    ECONOMIA_RENDA_DOCS_URL,
    SANEAMENTO_DOCS_URL,
    HIDRAULICA_DOCS_URL,
)

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

TODOS_MACROTEMAS_SLUG = "todos"
TODOS_MACROTEMAS_NOME = "Todos"
