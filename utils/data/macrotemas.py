from typing import TypedDict

from config import (
    DEMOGRAFIA_CSV_URL,
    DEMOGRAFIA_DOCS_URL,
    DESENVOLVIMENTO_SOCIAL_DOCS_URL,
    ECONOMIA_RENDA_CSV_URL,
    ECONOMIA_RENDA_DOCS_URL,
    EDUCACAO_CSV_URL,
    EDUCACAO_DOCS_URL,
    HIDRAULICA_CSV_URL,
    HIDRAULICA_DOCS_URL,
    INSTRUMENTOS_SUDENE_CSV_URL,
    INSTRUMENTOS_SUDENE_DOCS_URL,
    MEIO_AMBIENTE_CSV_URL,
    MEIO_AMBIENTE_DOCS_URL,
    SANEAMENTO_CSV_URL,
    SANEAMENTO_DOCS_URL,
    SAUDE_CSV_URL,
    SAUDE_DOCS_URL,
)


class Macrotema(TypedDict):
    nome: str
    cor: str
    icone: str
    docs_url: str | None
    docs_env: str
    csv_url: str | None
    csv_env: str


MACROTEMAS: dict[str, Macrotema] = {
    "demografia": {
        "nome": "Demografia",
        "cor": "#D65384",
        "icone": "people",
        "docs_url": DEMOGRAFIA_DOCS_URL,
        "docs_env": "DEMOGRAFIA_DOCS_URL",
        "csv_url": DEMOGRAFIA_CSV_URL,
        "csv_env": "DEMOGRAFIA_CSV_URL",
    },
    "educacao": {
        "nome": "Educação",
        "cor": "#FFD65A",
        "icone": "book",
        "docs_url": EDUCACAO_DOCS_URL,
        "docs_env": "EDUCACAO_DOCS_URL",
        "csv_url": EDUCACAO_CSV_URL,
        "csv_env": "EDUCACAO_CSV_URL",
    },
    "saude": {
        "nome": "Saúde",
        "cor": "#E5333F",
        "icone": "health",
        "docs_url": SAUDE_DOCS_URL,
        "docs_env": "SAUDE_DOCS_URL",
        "csv_url": SAUDE_CSV_URL,
        "csv_env": "SAUDE_CSV_URL",
    },
    "economia-renda": {
        "nome": "Economia e Renda",
        "cor": "#F79339",
        "icone": "dollar",
        "docs_url": ECONOMIA_RENDA_DOCS_URL,
        "docs_env": "ECONOMIA_RENDA_DOCS_URL",
        "csv_url": ECONOMIA_RENDA_CSV_URL,
        "csv_env": "ECONOMIA_RENDA_CSV_URL",
    },
    "hidraulica": {
        "nome": "Segurança Hídrica",
        "cor": "#35B2DB",
        "icone": "water",
        "docs_url": HIDRAULICA_DOCS_URL,
        "docs_env": "HIDRAULICA_DOCS_URL",
        "csv_url": HIDRAULICA_CSV_URL,
        "csv_env": "HIDRAULICA_CSV_URL",
    },
    "desenvolvimento-social": {
        "nome": "Desenvolvimento Social",
        "cor": "#7C46E1",
        "icone": "social",
        "docs_url": DESENVOLVIMENTO_SOCIAL_DOCS_URL,
        "docs_env": "DESENVOLVIMENTO_SOCIAL_DOCS_URL",
        "csv_url": "",
        "csv_env": "DESENVOLVIMENTO_SOCIAL_CSV_URL",
    },
    "meio-ambiente": {
        "nome": "Meio Ambiente",
        "cor": "#B0CC41",
        "icone": "leaf",
        "docs_url": MEIO_AMBIENTE_DOCS_URL,
        "docs_env": "MEIO_AMBIENTE_DOCS_URL",
        "csv_url": MEIO_AMBIENTE_CSV_URL,
        "csv_env": "MEIO_AMBIENTE_CSV_URL",
    },
    "saneamento": {
        "nome": "Infraestrutura e Saneamento",
        "cor": "#001A72",
        "icone": "wrench",
        "docs_url": SANEAMENTO_DOCS_URL,
        "docs_env": "SANEAMENTO_DOCS_URL",
        "csv_url": SANEAMENTO_CSV_URL,
        "csv_env": "SANEAMENTO_CSV_URL",
    },
    # Cor e ícone são os que utils/cover.py já usava para "instrumentos"/"sudene"
    # no caminho sem slug.
    "instrumentos-sudene": {
        "nome": "Instrumentos da Sudene",
        "cor": "#018F39",
        "icone": "chart",
        "docs_url": INSTRUMENTOS_SUDENE_DOCS_URL,
        "docs_env": "INSTRUMENTOS_SUDENE_DOCS_URL",
        "csv_url": INSTRUMENTOS_SUDENE_CSV_URL,
        "csv_env": "INSTRUMENTOS_SUDENE_CSV_URL",
    },
}

TODOS_MACROTEMAS_SLUG = "todos"
TODOS_MACROTEMAS_NOME = "Todos"
# IMPORTANT: mesma ordem do menu de temas do portal (THEMES_NAVIGATION_ORDER em
# data-nordeste-frontend/src/features/macrothemes/constants.ts). O formulário do
# relatório lista os temas nessa ordem e o PDF reordena por esta lista; com as
# duas diferentes, "Selecionar todos" mostrava Saneamento em 5º e o PDF trazia
# Segurança Hídrica logo após Economia (18/11/2026). Mudou uma, mude a outra.
TODOS_MACROTEMAS_ORDEM = [
    "demografia",
    "educacao",
    "saude",
    "economia-renda",
    "saneamento",
    "desenvolvimento-social",
    "hidraulica",
    "meio-ambiente",
    "instrumentos-sudene",
]

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
    # M6 (13/11/2026): o Doc estadual de Meio Ambiente abre com a linha "Meio
    # Ambiente". Sem o tema aqui, ela não era reconhecida como título e saía solta,
    # em letra pequena, depois da Síntese (junto do resto do Doc, na caixa de Fontes).
    "meio-ambiente": {
        "numero": "07",
        "titulo": "Meio Ambiente",
        "aliases": ["meio ambiente", "meio-ambiente"],
    },
    # DS8 (16/11/2026): o mesmo do M6 no Doc estadual de Desenvolvimento Social, que
    # abre com "Desenvolvimento Social". Títulos de uma palavra (Saúde, Demografia)
    # não precisavam disto por acaso: o renderer já descarta essas linhas.
    "desenvolvimento-social": {
        "numero": "08",
        "titulo": "Desenvolvimento Social",
        "aliases": ["desenvolvimento social", "desenvolvimento-social"],
    },
}
