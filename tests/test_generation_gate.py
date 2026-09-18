import asyncio
import os
import time

import pytest
from fastapi import HTTPException

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


def test_gate_miss_por_ttl_regenera(tmp_path, monkeypatch):
    # Inverso do teste acima: com os artefatos fora do TTL o gate NÃO pode servir
    # cache. Provamos pelo caminho percorrido — o pipeline envenenado tem que
    # estourar, em vez de o handler devolver o HTML de disco.
    monkeypatch.setattr(generation, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(cache, "DATA_VERSION_FILE", tmp_path / ".data_version")
    monkeypatch.setattr(generation, "REPORT_CACHE_TTL_S", 300)

    _, safe = _safe("Recife (PE)", "demografia")
    velho = time.time() - 600  # 10 min > TTL de 5 min
    for ext, conteudo in ((".pdf", b"%PDF-cache"), (".html", b"<html>CACHED</html>")):
        caminho = tmp_path / f"relatorio_{safe}{ext}"
        caminho.write_bytes(conteudo)
        os.utime(caminho, (velho, velho))

    # Envenenamos get_macrotema, a PRIMEIRA chamada depois do gate. Nada mais
    # adiante serve: buscar_perfil_municipal só é alcançado se o macrotema tiver
    # docs_url, que vem do .env — o teste passaria a depender do ambiente e, sem
    # .env, correria o pipeline inteiro até o SSR. Aqui também nenhuma query sai,
    # e testes não tocam o banco.
    def _explode(*_a, **_k):
        raise AssertionError("esperado: pipeline roda no MISS por TTL")

    monkeypatch.setattr(generation, "get_macrotema", _explode)

    with pytest.raises(AssertionError, match="MISS por TTL"):
        asyncio.run(gerar_relatorio_handler("Recife (PE)", "demografia"))


def test_cidade_malformada_nao_da_hit_no_cache_da_cidade_real(tmp_path, monkeypatch):
    # O safe_city colapsa pontuação: "Recife (PE)!!!" e "Recife (PE)" dão a mesma
    # chave. Sem validação antes do gate, o lixo devolveria 200 com o relatório de
    # Recife em vez de 404.
    monkeypatch.setattr(generation, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(cache, "DATA_VERSION_FILE", tmp_path / ".data_version")
    monkeypatch.setattr(generation, "carregar_cidades", lambda: ["Recife (PE)"])

    _, safe = _safe("Recife (PE)", "demografia")
    (tmp_path / f"relatorio_{safe}.pdf").write_bytes(b"%PDF-cache")
    (tmp_path / f"relatorio_{safe}.html").write_text("<html>CACHED</html>", "utf-8")

    # a cidade real continua servindo do cache
    resp = asyncio.run(gerar_relatorio_handler("Recife (PE)", "demografia"))
    assert resp.body.decode("utf-8") == "<html>CACHED</html>"

    # a malformada, que colapsa na mesma chave, tem que dar 404
    with pytest.raises(HTTPException) as err:
        asyncio.run(gerar_relatorio_handler("Recife (PE)!!!", "demografia"))
    assert err.value.status_code == 404


def test_lista_de_cidades_vazia_nao_bloqueia(tmp_path, monkeypatch):
    # cities.json ausente devolve [] — degradar, não transformar em 404 geral
    # (guarda do CLAUDE.md). Sem lista, segue pro pipeline.
    monkeypatch.setattr(generation, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(cache, "DATA_VERSION_FILE", tmp_path / ".data_version")
    monkeypatch.setattr(generation, "carregar_cidades", list)

    def _explode(*_a, **_k):
        raise AssertionError("esperado: seguiu pro pipeline sem lista de cidades")

    monkeypatch.setattr(generation, "get_macrotema", _explode)

    with pytest.raises(AssertionError, match="sem lista de cidades"):
        asyncio.run(gerar_relatorio_handler("Cidade Qualquer (XX)", "demografia"))
