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


def test_cards_caracteristicas_vem_da_view_com_area_em_duas_casas():
    # Rótulo, fonte e legenda vêm do quarteto de vw_indicadores. A área da view
    # tem 3 casas ("218.843"), mas o card usa 2, como o placeholder `$area` do
    # texto (default de `_formatar_valor` em utils/render/placeholders.py) —
    # senão card e texto mostram números diferentes para o mesmo município.
    cover = montar_capa_relatorio(
        {
            "nm_mun": "Recife (PE)",
            "nm_area_municipio": "Área do município",
            "valor_area_municipio": "218.843",
            "fonte_area_municipio": "IBGE",
            "unid_area_municipio": "Extensão territorial",
            "nm_pop_residente": "População residente",
            "valor_pop_residente": "1488920",
            "fonte_pop_residente": "Censo demográfico (IBGE, 2022)",
            "unid_pop_residente": "Pessoas residentes",
        },
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        "Meio Ambiente",
        "meio-ambiente",
    )

    area, pop = cover["metricas"]
    assert (area["rotulo"], area["valor"], area["sufixo"]) == (
        "Área do município", "218,84", "km²"
    )
    assert (area["fonte"], area["caption"]) == ("IBGE", "Extensão territorial")
    assert (pop["rotulo"], pop["valor"]) == ("População residente", "1.488.920")
    assert (pop["fonte"], pop["caption"]) == (
        "Censo demográfico (IBGE, 2022)", "Pessoas residentes"
    )


def test_area_sem_dado_nao_ganha_km2():
    for linha in ({"nm_mun": "Recife (PE)"}, {"nm_mun": "Recife (PE)", "valor_area_municipio": "Não há dados"}):
        cover = montar_capa_relatorio(
            linha, datetime(2026, 1, 1, tzinfo=timezone.utc), "Meio Ambiente", "meio-ambiente"
        )
        assert cover["metricas"][0]["sufixo"] == ""
