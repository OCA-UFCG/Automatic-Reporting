from datetime import datetime, timezone

import pytest
from fastapi import BackgroundTasks, HTTPException

import reports
from config import (
    DESENVOLVIMENTO_SOCIAL_DOCS_URL,
    MEIO_AMBIENTE_DOCS_URL,
    resolve_csv_source,
)
from utils.cover import montar_capa_relatorio
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


def test_cover_does_not_use_lorem_ipsum_when_diagnostic_is_missing():
    cover = montar_capa_relatorio(
        {"nm_mun": "Recife (PE)"},
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        "Demografia",
        "demografia",
    )

    assert cover["score"]["texto_apoio"] == ""
    assert cover["macrotema"]["resumo"] == ""


@pytest.mark.asyncio
async def test_requested_theme_reports_its_missing_docs_configuration(monkeypatch):
    monkeypatch.setitem(reports.MACROTEMAS["saude"], "docs_url", None)

    with pytest.raises(HTTPException) as exc_info:
        await reports.gerar_relatorio_handler(
            "Recife", "saude", background_tasks=BackgroundTasks()
        )

    assert exc_info.value.status_code == 500
    assert "SAUDE_DOCS_URL não configurado" in exc_info.value.detail
