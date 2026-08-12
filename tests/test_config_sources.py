from config import (
    DESENVOLVIMENTO_SOCIAL_DOCS_URL,
    MEIO_AMBIENTE_DOCS_URL,
    resolve_csv_source,
)
from utils.macrotemas import MACROTEMAS


def test_google_drive_csv_download_is_not_rewritten_as_google_sheets():
    url = (
        "https://drive.usercontent.google.com/download"
        "?id=arquivo_csv&export=download&confirm=t"
    )

    assert resolve_csv_source(url, "EDUCACAO_CSV_URL") == url


def test_new_macrothemes_use_their_configured_docs_sources():
    assert MACROTEMAS["desenvolvimento-social"]["docs_url"] == DESENVOLVIMENTO_SOCIAL_DOCS_URL
    assert MACROTEMAS["meio-ambiente"]["docs_url"] == MEIO_AMBIENTE_DOCS_URL
