import os
import time
from pathlib import Path

import pytest

from services import cache


@pytest.fixture
def output_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(cache, "DATA_VERSION_FILE", tmp_path / ".data_version")
    return tmp_path


def test_sem_marcador_arquivo_existente_eh_fresco(output_tmp):
    pdf = output_tmp / "relatorio_demografia__x.pdf"
    pdf.write_bytes(b"pdf")
    assert cache.artefato_fresco(pdf) is True


def test_arquivo_inexistente_nao_eh_fresco(output_tmp):
    assert cache.artefato_fresco(output_tmp / "nao_existe.pdf") is False


def test_arquivo_mais_velho_que_marcador_eh_stale(output_tmp):
    pdf = output_tmp / "relatorio_demografia__x.pdf"
    pdf.write_bytes(b"pdf")
    time.sleep(0.01)
    (output_tmp / ".data_version").write_bytes(b"")  # marcador mais novo
    assert cache.artefato_fresco(pdf) is False


def test_arquivo_mais_novo_que_marcador_eh_fresco(output_tmp):
    (output_tmp / ".data_version").write_bytes(b"")
    time.sleep(0.01)
    pdf = output_tmp / "relatorio_demografia__x.pdf"
    pdf.write_bytes(b"pdf")
    assert cache.artefato_fresco(pdf) is True


def test_eviction_remove_mais_antigos_ate_caber(output_tmp, monkeypatch):
    # Eviction opera só nos artefatos únicos do relatório (pdf/html/mapa), todos
    # resolvidos a partir de cache.OUTPUT_DIR (já apontado pro tmp_path pela
    # fixture) — não precisa mais mexer no OUTPUT_DIR do módulo handlers.
    monkeypatch.setattr(cache, "REPORT_CACHE_MAX_BYTES", 2500)
    # cria 3 relatórios de ~1KB cada, com mtime crescente
    nomes = ["a", "b", "c"]
    for i, n in enumerate(nomes):
        p = output_tmp / f"relatorio_demografia__{n}.pdf"
        p.write_bytes(b"x" * 1000)
        (output_tmp / f"relatorio_demografia__{n}.html").write_bytes(b"x" * 100)
        os.utime(p, (1000 + i, 1000 + i))  # a mais velho, c mais novo

    removidos = cache.evict_cache_if_needed()

    # ~3300 bytes > 2500: precisa apagar o mais antigo (a)
    assert "relatorio_demografia__a.pdf" in removidos
    assert not (output_tmp / "relatorio_demografia__a.pdf").exists()
    assert (output_tmp / "relatorio_demografia__c.pdf").exists()


def test_eviction_nunca_remove_protegido(output_tmp, monkeypatch):
    monkeypatch.setattr(cache, "REPORT_CACHE_MAX_BYTES", 500)
    p = output_tmp / "relatorio_demografia__novo.pdf"
    p.write_bytes(b"x" * 1000)
    os.utime(p, (1000, 1000))  # mais velho, mas protegido
    removidos = cache.evict_cache_if_needed(protegido="demografia__novo")
    assert removidos == []
    assert p.exists()


def test_eviction_nao_apaga_graficos_compartilhados_por_cidade(output_tmp, monkeypatch):
    # D6: gráficos são chaveados por cidade e reusados entre combos. Evictar um
    # relatório NÃO pode apagar os PNGs de gráfico, ou o HTML de outros relatórios
    # frescos da mesma cidade passa a apontar pra imagem que não existe mais.
    monkeypatch.setattr(cache, "REPORT_CACHE_MAX_BYTES", 500)
    pdf = output_tmp / "relatorio_demografia__x.pdf"
    pdf.write_bytes(b"x" * 1000)
    os.utime(pdf, (1000, 1000))  # velho -> será evictado
    grafico = output_tmp / "grafico_composicao_cor_raca_x.png"
    grafico.write_bytes(b"png")

    removidos = cache.evict_cache_if_needed()

    assert "relatorio_demografia__x.pdf" in removidos
    assert not pdf.exists()
    assert grafico.exists()  # gráfico compartilhado sobrevive


def test_evict_graficos_remove_mais_antigos_ate_caber(output_tmp, monkeypatch):
    # Pool de gráficos compartilhados por cidade (D6): sem dono único, precisa do
    # próprio teto FIFO por mtime, igual ao dos relatórios.
    monkeypatch.setattr(cache, "GRAFICO_CACHE_MAX_BYTES", 2500)
    nomes = ["x", "y", "z"]
    for i, n in enumerate(nomes):
        p = output_tmp / f"grafico_{n}.png"
        p.write_bytes(b"x" * 1000)
        os.utime(p, (1000 + i, 1000 + i))  # x mais velho, z mais novo

    removidos = cache.evict_graficos_if_needed()

    # ~3000 bytes > 2500: precisa apagar o mais antigo (x)
    assert "grafico_x.png" in removidos
    assert not (output_tmp / "grafico_x.png").exists()
    assert (output_tmp / "grafico_z.png").exists()
    restantes = sum(
        p.stat().st_size for p in output_tmp.glob("grafico_*.png")
    )
    assert restantes <= 2500


def test_evict_graficos_nao_toca_relatorios(output_tmp, monkeypatch):
    # Escopo da eviction de gráficos é só grafico_*.png; relatorio_*.pdf é do
    # outro pool (evict_cache_if_needed) e não pode ser tocado aqui.
    monkeypatch.setattr(cache, "GRAFICO_CACHE_MAX_BYTES", 100)
    pdf = output_tmp / "relatorio_demografia__x.pdf"
    pdf.write_bytes(b"x" * 1000)
    os.utime(pdf, (1000, 1000))
    grafico = output_tmp / "grafico_x.png"
    grafico.write_bytes(b"x" * 1000)
    os.utime(grafico, (1001, 1001))

    cache.evict_graficos_if_needed()

    assert pdf.exists()


def test_invalida_query_cache_quando_data_version_avanca(output_tmp, monkeypatch):
    chamadas = []
    monkeypatch.setattr(cache, "limpar_cache_queries", lambda: chamadas.append(1))
    monkeypatch.setattr(cache, "_ultimo_data_version", 0.0, raising=False)

    (output_tmp / ".data_version").write_bytes(b"")
    assert cache.invalidar_query_cache_se_dados_mudaram() is True   # avançou
    assert cache.invalidar_query_cache_se_dados_mudaram() is False  # sem mudança
    assert len(chamadas) == 1


def test_ttl_expira_artefato_que_o_marcador_nao_invalidaria(output_tmp):
    # O marcador só enxerga mudança de banco. Um relatório velho continua "fresco"
    # por ele mesmo depois de a editora corrigir o Google Doc — o TTL é o que fecha
    # essa janela (config.REPORT_CACHE_TTL_S).
    pdf = output_tmp / "relatorio_demografia__x.pdf"
    pdf.write_bytes(b"pdf")
    os.utime(pdf, (time.time() - 600, time.time() - 600))  # 10 min de idade

    assert cache.artefato_fresco(pdf) is True             # marcador: fresco
    assert cache.artefato_fresco(pdf, ttl_s=300) is False  # TTL de 5 min: expirou
    assert cache.artefato_fresco(pdf, ttl_s=900) is True   # TTL de 15 min: ainda vale


def test_sem_ttl_o_marcador_manda_sozinho(output_tmp):
    # Caminho dos gráficos (plotting.reusar_grafico): dados vêm todos do banco, já
    # cobertos pelo marcador — não devem expirar por tempo e regerar matplotlib à toa.
    png = output_tmp / "grafico_pib_x.png"
    png.write_bytes(b"png")
    os.utime(png, (time.time() - 86400, time.time() - 86400))  # 1 dia
    assert cache.artefato_fresco(png) is True


def test_limpa_tmp_orfaos_sem_tocar_nos_artefatos(output_tmp):
    # .tmp de render morto no meio: nome aleatório do mkstemp, não casa nenhum glob
    # de eviction — era a única categoria sem teto de disco. Varrido no startup.
    orfao = output_tmp / "relatorio_demografia__x.pdf.a1b2c3.tmp"
    orfao.write_bytes(b"pdf parcial")
    pdf = output_tmp / "relatorio_demografia__x.pdf"
    pdf.write_bytes(b"pdf")
    grafico = output_tmp / "grafico_pib_x.png"
    grafico.write_bytes(b"png")

    removidos = cache.limpar_tmp_orfaos()

    assert removidos == [orfao.name]
    assert not orfao.exists()
    assert pdf.exists() and grafico.exists()


def test_invalidar_artefatos_em_disco_torna_o_png_de_grafico_stale(output_tmp):
    # Regressão do deploy invisível: reusar_grafico não tem TTL, então um PNG
    # desenhado por código antigo seguiria "fresco" até o refresh noturno. O
    # startup move a marca d'água e força o redesenho no próximo acesso.
    png = output_tmp / "grafico_pib_x.png"
    png.write_bytes(b"png de codigo antigo")
    assert cache.artefato_fresco(png) is True  # antes: reusado

    time.sleep(0.01)
    cache.invalidar_artefatos_em_disco()

    assert cache.artefato_fresco(png) is False  # depois: redesenha
    assert png.exists()  # invalidar != apagar


def test_invalidar_artefatos_em_disco_cria_o_marcador_ausente(output_tmp):
    # Primeiro boot num volume novo: o marcador não existe e o touch tem que
    # criá-lo, não estourar.
    assert not (output_tmp / ".data_version").exists()
    cache.invalidar_artefatos_em_disco()
    assert (output_tmp / ".data_version").exists()


def _some_no_stat_apos(alvo: Path, monkeypatch, apos: int = 1):
    """Deixa `alvo` sobreviver aos `apos` primeiros stat() e sumir dos seguintes.

    Modela a corrida de verdade: o arquivo está lá quando a varredura o lista e
    some antes da leitura seguinte. Fazer stat() falhar SEMPRE não serve — o
    is_file() do código antigo também é stat() por baixo, então filtraria o
    fantasma antes do sorted e esconderia o bug. Determinístico: racing real em
    teste dá flake.
    """
    original = Path.stat
    vistas = {"n": 0}

    def espiao(self, *args, **kwargs):
        if self == alvo:
            vistas["n"] += 1
            if vistas["n"] > apos:
                raise FileNotFoundError(2, "sumiu depois da listagem", str(alvo))
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", espiao)


def test_eviction_tolera_pdf_que_some_depois_da_listagem(output_tmp, monkeypatch):
    # O DELETE de /relatorios é rota síncrona: o FastAPI a roda num threadpool
    # paralelo ao handler de geração, então um PDF sai do disco entre a listagem
    # e a leitura seguinte. Antes, o stat nu da chave de ordenação levantava
    # FileNotFoundError e derrubava com 500 um relatório já escrito em disco.
    monkeypatch.setattr(cache, "REPORT_CACHE_MAX_BYTES", 1500)
    for i, n in enumerate(["a", "b", "c"]):
        pdf = output_tmp / f"relatorio_demografia__{n}.pdf"
        pdf.write_bytes(b"x" * 1000)
        os.utime(pdf, (1000 + i, 1000 + i))
    fantasma = output_tmp / "relatorio_demografia__a.pdf"
    _some_no_stat_apos(fantasma, monkeypatch)

    removidos = cache.evict_cache_if_needed()

    # Sumiu antes de ser apagado por nós: não entra no crédito, e o `b` real
    # continua sendo evictado normalmente.
    assert removidos == ["relatorio_demografia__b.pdf"]
    assert not (output_tmp / "relatorio_demografia__b.pdf").exists()
    # os.path.exists e nao fantasma.exists(): Path.exists() roda por cima de
    # Path.stat(), que este teste mockou — perguntaria ao mock, nao ao disco.
    assert os.path.exists(fantasma)


def test_eviction_de_graficos_tolera_png_que_some_depois_da_listagem(
    output_tmp, monkeypatch
):
    # Mesma corrida no pool de gráficos, que antes statava cada PNG três vezes
    # (ordenar, somar, subtrair) — três chances de pegar o disco mudado.
    monkeypatch.setattr(cache, "GRAFICO_CACHE_MAX_BYTES", 1500)
    for i, n in enumerate(["x", "y", "z"]):
        png = output_tmp / f"grafico_{n}.png"
        png.write_bytes(b"x" * 1000)
        os.utime(png, (1000 + i, 1000 + i))
    _some_no_stat_apos(output_tmp / "grafico_x.png", monkeypatch)

    removidos = cache.evict_graficos_if_needed()

    assert removidos == ["grafico_x.png", "grafico_y.png"]
    assert (output_tmp / "grafico_z.png").exists()


def test_removidos_nao_credita_o_que_outra_request_apagou(output_tmp, monkeypatch):
    # Retrato tirado, e o unlink perde a corrida. O espaço conta pro orçamento
    # (foi liberado), mas a eviction não pode afirmar que apagou.
    monkeypatch.setattr(cache, "REPORT_CACHE_MAX_BYTES", 500)
    pdf = output_tmp / "relatorio_demografia__a.pdf"
    pdf.write_bytes(b"x" * 1000)

    def unlink_perdedor(self, *args, **kwargs):
        raise FileNotFoundError(2, "outra request chegou primeiro", str(self))

    monkeypatch.setattr(Path, "unlink", unlink_perdedor)

    assert cache.evict_cache_if_needed() == []
