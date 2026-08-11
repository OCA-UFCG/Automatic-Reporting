from config import resolve_csv_source


def test_google_drive_csv_download_is_not_rewritten_as_google_sheets():
    url = (
        "https://drive.usercontent.google.com/download"
        "?id=arquivo_csv&export=download&confirm=t"
    )

    assert resolve_csv_source(url, "EDUCACAO_CSV_URL") == url
