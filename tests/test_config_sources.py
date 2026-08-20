from datetime import datetime, timezone

from config import (
    DESENVOLVIMENTO_SOCIAL_DOCS_URL,
    MEIO_AMBIENTE_DOCS_URL,
    resolve_csv_source,
)
from services.macrotemas import get_macrotema_slugs_para_relatorio
from utils.cover import montar_capa_relatorio
from utils.data.macrotemas import MACROTEMAS


def test_google_drive_csv_download_is_not_rewritten_as_google_sheets():
    url = (
        "https://drive.usercontent.google.com/download"
        "?id=arquivo_csv&export=download&confirm=t"
    )

    assert resolve_csv_source(url, "EDUCACAO_CSV_URL") == url


def test_new_macrothemes_use_their_configured_docs_sources():
    assert MACROTEMAS["desenvolvimento-social"]["docs_url"] == DESENVOLVIMENTO_SOCIAL_DOCS_URL
    assert MACROTEMAS["meio-ambiente"]["docs_url"] == MEIO_AMBIENTE_DOCS_URL


def test_all_macrothemes_use_the_expected_colors_and_order():
    expected = [
        ("demografia", "#D65384"),
        ("educacao", "#FFD65A"),
        ("saude", "#E5333F"),
        ("economia-renda", "#F79339"),
        ("hidraulica", "#35B2DB"),
        ("desenvolvimento-social", "#7C46E1"),
        ("meio-ambiente", "#B0CC41"),
        ("saneamento", "#001A72"),
    ]

    assert get_macrotema_slugs_para_relatorio("todos") == [slug for slug, _ in expected]
    assert [MACROTEMAS[slug]["cor"] for slug, _ in expected] == [
        color for _, color in expected
    ]


def test_cover_does_not_use_lorem_ipsum_when_diagnostic_is_missing():
    cover = montar_capa_relatorio(
        {"nm_mun": "Recife (PE)"},
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        "Demografia",
        "demografia",
    )

    assert cover["score"]["texto_apoio"] == ""
    assert cover["macrotema"]["resumo"] == ""
