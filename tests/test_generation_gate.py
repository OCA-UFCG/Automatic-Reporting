from services.generation import montar_safe_report
from services.macrotemas import get_macrotema_slugs_para_relatorio


def _safe(cidade, macrotema):
    slugs = get_macrotema_slugs_para_relatorio(macrotema)
    return montar_safe_report(cidade, macrotema, slugs)


def test_single_tema():
    _, safe = _safe("Campina Grande (PB)", "demografia")
    # regex de safe_city colapsa runs de não-alfanuméricos em 1 "_" (existente,
    # inalterado); confirmado contra artefatos reais em output/ (ex.:
    # relatorio_demografia__campina_grande_pb_.pdf).
    assert safe == "demografia__campina_grande_pb_"


def test_combo_ordem_nao_importa():
    _, a = _safe("Recife (PE)", "demografia,saude")
    _, b = _safe("Recife (PE)", "saude,demografia")
    assert a == b  # chave normalizada: combos equivalentes = mesma entrada


def test_todos_explicito_colapsa():
    _, a = _safe("Recife (PE)", "todos")
    _, b = _safe("Recife (PE)",
                 "demografia,educacao,saude,economia-renda,hidraulica,"
                 "desenvolvimento-social,meio-ambiente,saneamento")
    assert a == b == "todos__recife_pe_"
