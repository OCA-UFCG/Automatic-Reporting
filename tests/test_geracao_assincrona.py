import asyncio
import re
import threading
import time

import pytest
from fastapi import HTTPException

from services import background, cache, generation
from utils.render.renderer import reset_figura_contador, texto_para_html


@pytest.fixture
def output(tmp_path, monkeypatch):
    for mod in (cache, generation):
        monkeypatch.setattr(mod, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(cache, "DATA_VERSION_FILE", tmp_path / ".data_version")
    return tmp_path


def test_miss_assincrono_responde_202_sem_rodar_o_pipeline(output, monkeypatch):
    rodou = []
    # Patch em generation, e não em background: o handler importa o nome
    # (from services.background import agendar_geracao), então é a referência no
    # namespace de generation que ele chama.
    monkeypatch.setattr(generation, "agendar_geracao", lambda *a, **k: rodou.append("agendou"))

    resposta = asyncio.run(
        generation.gerar_relatorio_handler("Recife (PE)", "demografia", aguardar=False)
    )

    assert resposta.status_code == 202
    assert resposta.headers[generation.HEADER_ARQUIVO_RELATORIO] == "relatorio_demografia__recife_pe_.pdf"
    assert rodou == ["agendou"]


def test_202_marca_como_obsoleta_a_versao_em_disco(output, monkeypatch):
    # Sem isto o portal aceitaria o PDF velho que ainda está em disco como se
    # fosse a resposta ao clique de agora — o 202 diz justamente "este arquivo
    # que você vê aí já não vale".
    monkeypatch.setattr(generation, "agendar_geracao", lambda *a, **k: None)
    _, safe = generation.montar_safe_report("Recife (PE)", "demografia", ["demografia"])
    pdf = output / f"relatorio_{safe}.pdf"
    pdf.write_bytes(b"pdf velho")

    resposta = asyncio.run(
        generation.gerar_relatorio_handler("Recife (PE)", "demografia", aguardar=False)
    )

    assert resposta.status_code == 202
    assert resposta.headers[generation.HEADER_VERSAO_OBSOLETA] == str(pdf.stat().st_mtime_ns)


def test_202_sem_pdf_em_disco_nao_carrega_versao_obsoleta(output, monkeypatch):
    monkeypatch.setattr(generation, "agendar_geracao", lambda *a, **k: None)

    resposta = asyncio.run(
        generation.gerar_relatorio_handler("Recife (PE)", "demografia", aguardar=False)
    )

    assert generation.HEADER_VERSAO_OBSOLETA not in resposta.headers


def test_hit_responde_200_mesmo_em_modo_assincrono(output):
    _, safe = generation.montar_safe_report(
        "Recife (PE)", "demografia", ["demografia"]
    )
    (output / f"relatorio_{safe}.pdf").write_bytes(b"pdf")
    (output / f"relatorio_{safe}.html").write_text("<html></html>", encoding="utf-8")

    resposta = asyncio.run(
        generation.gerar_relatorio_handler("Recife (PE)", "demografia", aguardar=False)
    )

    assert resposta.status_code == 200


def test_no_teto_responde_503(output, monkeypatch):
    monkeypatch.setattr(generation, "MAX_GERACOES_EM_VOO", 0)

    with pytest.raises(HTTPException) as err:
        asyncio.run(
            generation.gerar_relatorio_handler("Recife (PE)", "demografia", aguardar=False)
        )

    assert err.value.status_code == 503
    assert err.value.headers["Retry-After"] == "30"
    # O 503 não pode deixar sentinela para trás: quem recusou admissão não está
    # gerando nada, e a sentinela órfã bloquearia o relatório por SENTINELA_TTL_S.
    assert cache.geracoes_em_voo() == 0


def test_thread_de_fundo_nao_mexe_na_sentinela(output, monkeypatch):
    _, safe = generation.montar_safe_report("Recife (PE)", "demografia", ["demografia"])
    cache.adquirir_geracao(safe)

    # Envenena a primeira chamada depois do gate, como test_generation_gate.py já
    # faz: o que importa aqui é o corpo do handler rodar e estourar, não ONDE ele
    # estoura. Depender do pipeline real falhar sozinho tornaria o teste refém do
    # ambiente (sem bundle SSR falha num ponto, com bundle e banco pode nem falhar).
    def _explode(*_a, **_k):
        raise AssertionError("esperado: a thread de fundo roda o pipeline")

    monkeypatch.setattr(generation, "get_macrotema", _explode)

    # Roda como a thread de fundo roda: sentinela já adquirida por quem respondeu 202.
    with pytest.raises(AssertionError, match="thread de fundo"):
        asyncio.run(
            generation.gerar_relatorio_handler(
                "Recife (PE)", "demografia", aguardar=True, _sentinela_ja_adquirida=True
            )
        )

    # A sentinela continua de pé: liberá-la é responsabilidade de background.py.
    assert cache.adquirir_geracao(safe) is False


def test_geracao_ja_em_voo_nao_agenda_outra(output, monkeypatch):
    rodou = []
    monkeypatch.setattr(generation, "agendar_geracao", lambda *a, **k: rodou.append(1))
    _, safe = generation.montar_safe_report("Recife (PE)", "demografia", ["demografia"])
    cache.adquirir_geracao(safe)

    resposta = asyncio.run(
        generation.gerar_relatorio_handler("Recife (PE)", "demografia", aguardar=False)
    )

    assert resposta.status_code == 202
    assert rodou == []


def test_thread_de_fundo_libera_a_sentinela_mesmo_falhando(output):
    """O único teste que roda o agendador de verdade (thread + semáforo): os
    demais trocam agendar_geracao por um espião. Sentinela presa é o pior modo de
    falha do desenho — ela bloqueia aquele relatório por SENTINELA_TTL_S inteiro."""
    _, safe = generation.montar_safe_report("Recife (PE)", "demografia", ["demografia"])
    assert cache.adquirir_geracao(safe) is True
    rodou = threading.Event()

    async def _falha():
        rodou.set()
        raise RuntimeError("pipeline estourou")

    background.agendar_geracao(_falha, safe)

    assert rodou.wait(5), "a geração de fundo não rodou"
    limite = time.time() + 5
    while cache.geracoes_em_voo() and time.time() < limite:
        time.sleep(0.01)
    assert cache.geracoes_em_voo() == 0


def _proximo_numero_de_figura() -> int:
    """Consome um número do contador global de figuras e devolve qual saiu.

    É a forma observável de perguntar em que pé o contador está: ele é global de
    módulo em utils/render/renderer.py e só aparece na legenda renderizada."""
    html = texto_para_html("Figura X- Legenda qualquer.", {}, graficos_por_placeholder={})
    return int(re.search(r"Figura (\d+) –", html).group(1))


def test_hit_do_gate_nao_reseta_o_contador_de_figuras(output):
    """O contador é escopo de render: uma chamada que não renderiza nada não pode
    mexer nele. Com a geração em thread de fundo, esse reset cairia no meio da
    numeração de um render em voo — que é exatamente o caso que o semáforo de 1 de
    services/background.py existe pra evitar."""
    _, safe = generation.montar_safe_report("Recife (PE)", "demografia", ["demografia"])
    (output / f"relatorio_{safe}.pdf").write_bytes(b"pdf")
    (output / f"relatorio_{safe}.html").write_text("<html></html>", encoding="utf-8")

    reset_figura_contador()
    assert _proximo_numero_de_figura() == 2  # simula um render em andamento

    resposta = asyncio.run(
        generation.gerar_relatorio_handler("Recife (PE)", "demografia")
    )

    assert resposta.status_code == 200
    assert _proximo_numero_de_figura() == 3  # a numeração seguiu de onde parou


def test_202_de_dedup_nao_reseta_o_contador_de_figuras(output):
    # O caso que este plano existe pra servir: dois usuários pedem o mesmo
    # relatório. O segundo cai no 202 de dedup enquanto o primeiro renderiza.
    _, safe = generation.montar_safe_report("Recife (PE)", "demografia", ["demografia"])
    cache.adquirir_geracao(safe)

    reset_figura_contador()
    assert _proximo_numero_de_figura() == 2

    resposta = asyncio.run(
        generation.gerar_relatorio_handler("Recife (PE)", "demografia", aguardar=False)
    )

    assert resposta.status_code == 202
    assert _proximo_numero_de_figura() == 3
