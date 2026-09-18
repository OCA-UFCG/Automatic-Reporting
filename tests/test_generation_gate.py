import asyncio

from services import cache, generation
from services.generation import gerar_relatorio_handler, montar_safe_report
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


def test_gate_hit_serve_cache_sem_rodar_pipeline(tmp_path, monkeypatch):
    # HIT: com pdf E html frescos em disco, o handler devolve o HTML cacheado sem
    # tocar no pipeline. Envenenamos o pipeline (docs + pdf) pra que QUALQUER
    # execução dele estoure — se o gate não curto-circuitasse, o teste falharia.
    monkeypatch.setattr(generation, "OUTPUT_DIR", tmp_path)
    # sem .data_version -> _data_version_mtime() = 0.0 -> qualquer arquivo é fresco
    monkeypatch.setattr(cache, "DATA_VERSION_FILE", tmp_path / ".data_version")

    _, safe = _safe("Recife (PE)", "demografia")
    (tmp_path / f"relatorio_{safe}.pdf").write_bytes(b"%PDF-cache")
    (tmp_path / f"relatorio_{safe}.html").write_text(
        "<html>CACHED</html>", encoding="utf-8"
    )

    async def _explode_docs(*_a, **_k):
        raise AssertionError("pipeline rodou: carregou docs num HIT")

    async def _explode_pdf(*_a, **_k):
        raise AssertionError("pipeline rodou: gerou PDF num HIT")

    monkeypatch.setattr(generation, "carregar_texto_do_docs", _explode_docs)
    monkeypatch.setattr(generation, "_gerar_pdf", _explode_pdf)

    resp = asyncio.run(gerar_relatorio_handler("Recife (PE)", "demografia"))

    assert resp.body.decode("utf-8") == "<html>CACHED</html>"
