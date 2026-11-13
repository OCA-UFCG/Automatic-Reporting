import gzip
import importlib
import json
import os
import time

import pytest
from fastapi.testclient import TestClient

from services import laboratorio, laboratorio_snapshot
from services.laboratorio import conferir_doc, conferir_tema
from utils.json_tipado import codificar
from utils.render.placeholders import interpretar_blocos_condicionais, registrar_versoes
from utils.render.renderer import texto_final_do_tema

TEXTO = (
    "Para quando $pop for maior que 10:\nGrande $nm_mun.\n\n"
    "Para quando $pop for menor ou igual a 10:\nPequena, com $inexistente e $vazio.\n\n"
    "Fim."
)


def test_registrar_versoes_diz_qual_versao_disparou_sem_mudar_o_texto():
    contexto = {"pop": 20, "nm_mun": "X"}
    sem_registro = interpretar_blocos_condicionais(TEXTO, contexto)
    with registrar_versoes() as versoes:
        com_registro = interpretar_blocos_condicionais(TEXTO, contexto)
    assert com_registro == sem_registro
    assert [disparou for _, disparou in versoes] == [True, False]
    assert versoes[0][0].startswith("Para quando $pop for maior que 10")


def test_registro_fica_desligado_fora_do_with():
    with registrar_versoes() as versoes:
        pass
    texto_final_do_tema(TEXTO, {"pop": 1}, "demografia")
    assert versoes == []


def test_conferir_tema_conta_versoes_e_separa_campo_inexistente_de_vazio():
    contextos = {
        "Grande (PB)": {"pop": 20, "nm_mun": "Grande (PB)", "vazio": 1},
        "Pequena (PB)": {"pop": 5, "nm_mun": "Pequena (PB)", "vazio": None},
        "Mínima (PB)": {"pop": 1, "nm_mun": "Mínima (PB)", "vazio": None},
    }
    progresso = []
    resultado = conferir_tema(TEXTO, "demografia", contextos, lambda f, t: progresso.append(f))

    assert [v["municipios"] for v in resultado["versoes"]] == [1, 2]
    assert resultado["versoes_por_municipio"] == {
        "Grande (PB)": [0], "Pequena (PB)": [1], "Mínima (PB)": [1],
    }
    crus = {c["campo"]: c for c in resultado["campos_crus"]}
    assert crus["inexistente"]["existe"] is False
    assert crus["vazio"]["existe"] is True
    assert crus["vazio"]["municipios"] == ["Pequena (PB)", "Mínima (PB)"]
    assert progresso == [1, 2, 3]
    assert resultado["erros"] == {}


def test_conferir_tema_acusa_condicao_que_o_gerador_nao_entende():
    # "for menor $campo" sem "que": o caso das revisões de Demografia (28-29/09).
    texto = "Para quando $pop for menor 10:\nTexto.\n"
    resultado = conferir_tema(texto, "demografia", {"A (PB)": {"pop": 1}})
    assert resultado["condicoes_nao_entendidas"]


def test_conferir_doc_avisa_condicao_no_resumo_do_tema():
    doc = "resumo_tema = Para quando $pop for maior que 10:\nTexto do resumo.@@\n"
    resultado = conferir_doc(doc, "demografia", {"A (PB)": {"pop": 20}})
    assert resultado["condicoes_sem_efeito"] == ["Para quando $pop for maior que 10:"]


# --- Rotas (flag + conferência em segundo plano) ---

def _app(monkeypatch, flag: str | None):
    if flag is None:
        monkeypatch.delenv("LABORATORIO_HABILITADO", raising=False)
    else:
        monkeypatch.setenv("LABORATORIO_HABILITADO", flag)
    import main

    return TestClient(importlib.reload(main).app)


@pytest.fixture
def snapshot_falso(monkeypatch, tmp_path):
    monkeypatch.setattr(laboratorio_snapshot, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.setattr(laboratorio, "CONFERENCIAS_DIR", tmp_path / "conferencias")
    monkeypatch.setattr(laboratorio, "_LOCK", tmp_path / "conferencias" / ".lock")
    municipios = {
        "Grande (PB)": {"fonte": "view", "contexto": {"pop": 20, "nm_mun": "Grande (PB)"}},
        "Pequena (PB)": {"fonte": "view", "contexto": {"pop": 5, "nm_mun": "Pequena (PB)"}},
    }
    with gzip.open(tmp_path / "demografia.json.gz", "wt", encoding="utf-8") as arquivo:
        json.dump({
            "gerado_em": "2026-10-29T04:30:00+00:00",
            "municipios": codificar(municipios),
            "metadados": {"ausentes": ["Sumida (PB)"]},
        }, arquivo)


@pytest.mark.parametrize("flag", [None, "0"])
def test_sem_a_flag_as_rotas_do_laboratorio_nao_existem(flag, monkeypatch):
    # Pela lista de rotas, e não só pelo status: com o frontend buildado, o mount do
    # SPA em "/" responde 405 (e não 404) a um POST numa rota que não existe.
    cliente = _app(monkeypatch, flag)
    rotas = [getattr(rota, "path", "") for rota in cliente.app.routes]
    assert not [rota for rota in rotas if rota.startswith("/laboratorio")]
    assert cliente.get("/laboratorio/conferencias/" + "0" * 32).status_code == 404


def test_conferencia_roda_em_segundo_plano_e_termina_pronta(monkeypatch, snapshot_falso):
    cliente = _app(monkeypatch, "1")
    doc = "descricao_tema = " + TEXTO + "@@"
    resposta = cliente.post("/laboratorio/demografia/conferencias", json={"texto": doc})
    id_conferencia = resposta.json()["id"]

    for _ in range(100):
        estado = cliente.get(f"/laboratorio/conferencias/{id_conferencia}").json()
        if estado["estado"] in ("pronta", "erro"):
            break
        time.sleep(0.05)

    assert estado["estado"] == "pronta", estado
    assert estado["total"] == 2
    assert estado["snapshot_gerado_em"] == "2026-10-29T04:30:00+00:00"
    assert [v["municipios"] for v in estado["resultado"]["versoes"]] == [1, 1]
    # Sem dado no tema, fora do snapshot: a tela diz que ficou fora da conferência.
    assert estado["resultado"]["ausentes"] == ["Sumida (PB)"]


def test_texto_de_uma_cidade_e_tema_sem_snapshot(monkeypatch, snapshot_falso):
    cliente = _app(monkeypatch, "1")
    doc = "descricao_tema = " + TEXTO + "@@"
    resposta = cliente.post(
        "/laboratorio/demografia/municipio", json={"texto": doc, "cidade": "Grande (PB)"}
    )
    assert resposta.status_code == 200
    assert resposta.json()["partes"][0] == "Grande Grande (PB)."
    assert cliente.post(
        "/laboratorio/saude/municipio", json={"texto": doc, "cidade": "Grande (PB)"}
    ).status_code == 404


def test_conferir_tema_com_e_ou_parenteses_sem_dados_e_campo_a_campo():
    # Os casos que o spec pede na conferência sem banco (spec, "Testes").
    texto = (
        "Para quando $a for maior que 1 e $b for igual a 0:\nE.\n\n"
        "Para quando $a for igual a 1 ou $b for maior que 0:\nOU.\n\n"
        "Para quando ($a for igual a 1 ou $a for igual a 2) e $b for igual a 0:\nPAR.\n\n"
        "Para quando $c for sem dados:\nSD.\n\n"
        "Para quando $a for igual a $b:\nCC.\n"
    )
    contextos = {
        "X (PB)": {"a": 2, "b": 0, "c": None},
        "Y (PB)": {"a": 1, "b": 1, "c": 5},
        "Z (PB)": {"a": 0, "b": 0, "c": "sem dados"},
    }
    resultado = conferir_tema(texto, "demografia", contextos)

    assert [v["municipios"] for v in resultado["versoes"]] == [1, 1, 1, 2, 2]
    assert resultado["versoes_por_municipio"] == {
        "X (PB)": [0, 2, 3], "Y (PB)": [1, 4], "Z (PB)": [3, 4],
    }
    assert resultado["condicoes_nao_entendidas"] == []


def test_id_de_conferencia_invalido_nao_vira_caminho(monkeypatch, snapshot_falso):
    assert laboratorio.ler_conferencia("../../etc/passwd") is None


# --- Parte 3: Doc fresco e valores das colunas ---


class _RespostaGoogle:
    text = "﻿descricao_tema = Texto do Doc.@@\n"

    def raise_for_status(self):
        pass


class _ClienteGoogle:
    def __init__(self, *_a, **_k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_a):
        pass

    async def get(self, _url):
        return _RespostaGoogle()


def test_abrir_doc_nao_grava_no_cache_do_relatorio(monkeypatch, tmp_path):
    from utils.external import docs

    monkeypatch.setattr(docs, "DOCS_CACHE_DIR", tmp_path)
    monkeypatch.setattr(docs.httpx, "AsyncClient", _ClienteGoogle)
    monkeypatch.setattr(laboratorio, "docs_url", lambda _s, _u="municipio": "1AbCdEfGhIjKlMnOp")

    import asyncio

    doc = asyncio.run(laboratorio.abrir_doc("demografia"))
    assert doc["texto"].startswith("descricao_tema = Texto do Doc.")
    assert len(doc["hash"]) == 64
    assert list(tmp_path.iterdir()) == []  # o relatório segue com o texto de antes

    asyncio.run(docs.baixar_e_salvar_doc("1AbCdEfGhIjKlMnOp"))
    assert list(tmp_path.iterdir())  # o caminho do cron continua gravando


def test_valores_das_colunas_por_tipo():
    contextos = {
        "A (PB)": {"pop": "62.39", "faixa": "jovem", "serie": [1], "vazio": None},
        "B (PB)": {"pop": 0, "faixa": "jovem", "serie": [2], "vazio": ""},
        "C (PB)": {"pop": "sem dados", "faixa": "adulta", "serie": [3]},
    }
    colunas = {c["coluna"]: c for c in laboratorio.valores_das_colunas(contextos)}

    assert colunas["pop"]["tipo"] == "numero"
    assert (colunas["pop"]["min"], colunas["pop"]["max"], colunas["pop"]["zeros"]) == (0, 62.39, 1)
    assert colunas["pop"]["nao_numeros"] == [
        {"valor": "sem dados", "municipios": 1, "exemplo": "C (PB)"}
    ]
    assert colunas["faixa"]["valores"][0] == {"valor": "jovem", "municipios": 2, "exemplo": "A (PB)"}
    assert colunas["serie"]["tipo"] == "outro"
    assert colunas["vazio"]["vazios"] == 3


def test_rotas_de_temas_e_colunas(monkeypatch, snapshot_falso):
    cliente = _app(monkeypatch, "1")
    temas = {t["slug"]: t for t in cliente.get("/laboratorio/temas").json()}
    assert temas["demografia"]["snapshot_gerado_em"].endswith("+00:00")
    assert temas["saude"]["snapshot_gerado_em"] is None
    assert temas["demografia"]["cor"].startswith("#")  # o ponto colorido do seletor de tema

    colunas = cliente.get("/laboratorio/demografia/colunas").json()
    assert colunas["snapshot_gerado_em"] == "2026-10-29T04:30:00+00:00"
    assert {c["coluna"] for c in colunas["colunas"] if c["tipo"] != "apelido"} == {"pop", "nm_mun"}
    apelidos = {c["coluna"]: c["de"] for c in colunas["colunas"] if c["tipo"] == "apelido"}
    assert apelidos == {"city": "nm_mun", "municipio": "nm_mun"}
    assert cliente.get("/laboratorio/saude/colunas").status_code == 404


def test_rota_do_doc_traduz_falha_do_google(monkeypatch):
    cliente = _app(monkeypatch, "1")

    async def _falha(_slug, _unidade="municipio"):
        raise ValueError("Google Docs sem acesso público para exportação.")

    monkeypatch.setattr(laboratorio, "abrir_doc", _falha)
    import main

    monkeypatch.setattr(main, "abrir_doc", _falha)
    resposta = cliente.get("/laboratorio/demografia/doc")
    assert resposta.status_code == 502
    assert "acesso público" in resposta.json()["detail"]


def test_sem_a_flag_nem_a_lista_de_temas_existe(monkeypatch):
    assert _app(monkeypatch, None).get("/laboratorio/temas").status_code == 404


@pytest.mark.parametrize("estado, idade_s, interrompida", [
    ("rodando", 60, False), ("rodando", 300, True),
    ("na_fila", 300, False), ("na_fila", 1800, True),
    ("pronta", 10 * 3600, False),
])
def test_conferencia_parada_vira_interrompida(estado, idade_s, interrompida, monkeypatch, snapshot_falso):
    laboratorio.CONFERENCIAS_DIR.mkdir(parents=True)
    id_conferencia = "a" * 32
    laboratorio._gravar(id_conferencia, {"estado": estado})
    antes = time.time() - idade_s
    os.utime(laboratorio._caminho(id_conferencia), (antes, antes))
    lido = laboratorio.ler_conferencia(id_conferencia)
    assert (lido["estado"] == "erro") is interrompida


# --- 5c-3b: ler com cada valor ---


def _gravar_snapshot(pasta, tema, contextos):
    municipios = {c: {"fonte": "view", "contexto": ctx} for c, ctx in contextos.items()}
    with gzip.open(pasta / f"{tema}.json.gz", "wt", encoding="utf-8") as arquivo:
        json.dump({"gerado_em": "2026-11-01T04:30:00+00:00", "municipios": codificar(municipios)}, arquivo)


def test_ler_com_cada_valor_so_da_exemplo_onde_o_trecho_sai(monkeypatch, tmp_path):
    monkeypatch.setattr(laboratorio_snapshot, "SNAPSHOT_DIR", tmp_path)
    _gravar_snapshot(tmp_path, "demografia", {
        "A (PB)": {"dado": 1, "analise": "uma redução", "fonte": "IBGE", "sigla_uf": "PB"},
        "B (PB)": {"dado": 2, "analise": "um aumento", "fonte": "IBGE", "sigla_uf": "PE"},
        "C (PB)": {"dado": 0, "analise": "não houve variação", "fonte": "IBGE"},
        "D (PB)": {"dado": 3, "analise": "um aumento", "fonte": "IBGE"},
    })
    versao = "Para quando $dado for diferente de 0, então:\nApresentou $analise segundo $fonte ($sigla_uf).\n"

    colunas = laboratorio.ler_com_cada_valor("demografia", versao)

    # $dado é número, $fonte tem um valor só e $sigla_uf fica de fora: nada a comparar.
    assert [c["coluna"] for c in colunas] == ["analise"]
    valores = {v["valor"]: v for v in colunas[0]["valores"]}
    assert valores["um aumento"] == {
        "valor": "um aumento", "municipios": 2, "vale_em": 2,
        "cidade": "B (PB)", "texto": "Apresentou um aumento segundo IBGE (PE).",
    }
    # O único município com este valor tem $dado 0: a versão nunca sai com ele.
    assert valores["não houve variação"] == {
        "valor": "não houve variação", "municipios": 1, "vale_em": 0, "cidade": None, "texto": None,
    }
    assert colunas[0]["valores"][0]["valor"] == "um aumento"  # mais comum primeiro

    fixo = laboratorio.ler_com_cada_valor("demografia", "O grupo $analise.")
    assert all(v["vale_em"] == v["municipios"] for v in fixo[0]["valores"])
    assert laboratorio.ler_com_cada_valor("saude", "O grupo $analise.") is None


def test_rota_cada_valor(monkeypatch, snapshot_falso):
    cliente = _app(monkeypatch, "1")
    resposta = cliente.post("/laboratorio/demografia/cada-valor", json={"texto": "Em $nm_mun."})
    assert resposta.status_code == 200
    (coluna,) = resposta.json()["colunas"]
    assert coluna["coluna"] == "nm_mun"
    assert {v["texto"] for v in coluna["valores"]} == {"Em Grande (PB).", "Em Pequena (PB)."}
    assert cliente.post("/laboratorio/saude/cada-valor", json={"texto": "x"}).status_code == 404


# --- 5c-5: CSV de uma view que ainda não existe ---


def test_ler_csv_casa_pela_regra_do_gerador_e_junta_por_cima(monkeypatch, snapshot_falso):
    # Ponto e vírgula, prefixo do tema nas colunas, nome sem "(UF)" + sigla_uf, uma
    # célula vazia e uma cidade que não está no snapshot.
    texto = (
        "nm_mun;sigla_uf;demografia.nova;pop\n"
        "Grande;PB;12,5;99\n"
        "Pequena;PB;;7\n"
        "Nova Cidade;PE;3;1\n"
    )
    lido = laboratorio.ler_csv("demografia", texto)

    assert lido["casados"] == 2
    assert lido["so_no_csv"] == ["Nova Cidade (PE)"]
    assert lido["colunas_do_csv"] == ["sigla_uf", "nova", "pop"]
    assert lido["linhas"]["Grande (PB)"] == {"nm_mun": "Grande", "sigla_uf": "PB", "nova": "12,5", "pop": 99}
    assert lido["linhas"]["Pequena (PB)"]["nova"] is None
    colunas = {c["coluna"]: c for c in lido["colunas"]}
    assert colunas["pop"]["max"] == 99  # o CSV por cima do snapshot (pop 20 → 99)

    contextos = laboratorio.com_csv({"Grande (PB)": {"pop": 20, "nm_mun": "Grande (PB)", "x": 1}}, lido["linhas"])
    assert contextos["Grande (PB)"] == {"pop": 99, "nm_mun": "Grande (PB)", "x": 1, "sigla_uf": "PB", "nova": "12,5"}
    assert contextos["Nova Cidade (PE)"]["nm_mun"] == "Nova Cidade (PE)"


@pytest.mark.parametrize("texto, erro", [
    ("pop,area\n1,2\n", "nm_mun"),
    ("", "Não consegui ler"),
])
def test_ler_csv_recusa_o_que_nao_serve(texto, erro, monkeypatch, snapshot_falso):
    with pytest.raises(ValueError, match=erro):
        laboratorio.ler_csv("demografia", texto)


def test_rotas_com_csv(monkeypatch, snapshot_falso):
    cliente = _app(monkeypatch, "1")
    lido = cliente.post("/laboratorio/demografia/csv", json={"csv": "nm_mun\tsigla_uf\tpop\nGrande\tPB\t1\nNova\tPE\t50\n"})
    assert lido.status_code == 200
    linhas = lido.json()["linhas"]

    doc = "descricao_tema = Para quando $pop for maior que 10:\nGrande.\n@@"
    # Pelo CSV, Grande tem pop 1: a versão não sai mais nela.
    so_grande = {"Grande (PB)": linhas["Grande (PB)"]}
    resposta = cliente.post("/laboratorio/demografia/municipio", json={"texto": doc, "cidade": "Grande (PB)", "csv": so_grande})
    assert resposta.json()["versoes"][0][1] is False
    # Cidade só do CSV também tem texto pronto.
    nova = cliente.post("/laboratorio/demografia/municipio", json={"texto": doc, "cidade": "Nova (PE)", "csv": linhas})
    assert nova.json()["versoes"][0][1] is True

    id_conferencia = cliente.post("/laboratorio/demografia/conferencias", json={"texto": doc, "csv": linhas}).json()["id"]
    for _ in range(100):
        estado = cliente.get(f"/laboratorio/conferencias/{id_conferencia}").json()
        if estado["estado"] == "pronta":
            break
        time.sleep(0.05)
    assert estado["total"] == 3  # Grande, Pequena e Nova
    assert estado["resultado"]["versoes"][0]["municipios"] == 1  # só Nova (pop 50)

    assert cliente.post("/laboratorio/demografia/csv", json={"csv": "a,b\n1,2\n"}).status_code == 400


# --- Painel de texto pronto: gráficos de verdade ---


def test_texto_numa_cidade_com_graficos_de_verdade(monkeypatch, tmp_path):
    from services import cache

    monkeypatch.setattr(laboratorio_snapshot, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.setattr(laboratorio, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(cache, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(cache, "DATA_VERSION_FILE", tmp_path / ".data_version")
    monkeypatch.setattr(laboratorio, "CARACTERISTICAS_DOCS_URL", None)  # sem a primeira página
    faixas = [{"faixa": "0-4", "mulheres": 1200, "homens": 1300}, {"faixa": "5-9", "mulheres": 1400, "homens": 1500}]
    _gravar_snapshot(tmp_path, "demografia", {
        "Com Dado (PB)": {"nm_mun": "Com Dado (PB)", "faixas_etarias_sexo": faixas},
        "Sem Dado (PB)": {"nm_mun": "Sem Dado (PB)"},
    })
    doc = (
        "descricao_tema = A pirâmide de $nm_mun (Figura x).\n\n"
        "Figura x – População por faixa etária e sexo em $nm_mun\n@@"
    )

    com = laboratorio.texto_do_municipio("demografia", doc, "Com Dado (PB)", com_graficos=True)
    img = [parte for parte in com["html"] if "<img" in parte]
    assert len(img) == 1 and 'src="/output/grafico_faixa_etaria_e_sexo_lab_com_dado_pb_' in img[0]
    assert len(list(tmp_path.glob("grafico_faixa_etaria_e_sexo_lab_*.png"))) == 1

    # Sem dado, o gráfico não é gerado: some a imagem, a legenda e a menção
    # "(Figura x)", pelo mesmo render do relatório.
    sem = laboratorio.texto_do_municipio("demografia", doc, "Sem Dado (PB)", com_graficos=True)
    assert sem["html"] == ['<p class="theme-detail-text">A pirâmide de Sem Dado (PB).</p>']
    # Sem pedir os gráficos (conferência), supõe todo gráfico gerado, como antes.
    suposto = laboratorio.texto_do_municipio("demografia", doc, "Sem Dado (PB)")
    assert any("Figura" in parte for parte in suposto["partes"])


def test_texto_numa_cidade_fecha_com_a_caixa_de_fontes(monkeypatch, tmp_path):
    # O relatório põe depois do tema a caixa "Fontes / Conteúdos relacionados" (o que
    # sobra do Doc depois do "@@"); o painel do laboratório não mostrava (André, 03/11).
    monkeypatch.setattr(laboratorio_snapshot, "SNAPSHOT_DIR", tmp_path)
    _gravar_snapshot(tmp_path, "demografia", {"Nova (PB)": {"nm_mun": "Nova (PB)"}})
    doc = (
        "descricao_tema = Texto de $nm_mun.\n@@\n\n#!Fontes\n\n"
        "Os dados vêm do IBGE.\n\n#!Conteúdos relacionados\n\nVeja também o boletim."
    )

    resultado = laboratorio.texto_do_municipio("demografia", doc, "Nova (PB)")
    assert "fontes-box" in resultado["html"][-1] and "Veja também o boletim." in resultado["html"][-1]
    # Só no HTML do painel: o texto que a conferência lê continua só o do tema.
    assert resultado["partes"] == ["Texto de Nova (PB)."]


def test_nomes_resolvidos_sem_coluna_saem_preenchidos():
    # A tela acusa "não está nas colunas" com esta lista: um nome dela que o gerador
    # não resolvesse viraria campo cru sem aviso.
    from utils.render.placeholders import (
        _resolver_campo_com_alias,
        nomes_resolvidos_sem_coluna,
    )

    colunas = {"area_territorial", "nm_mun", "ano", "cres_pop", "pop_total", "pop_rural"}
    nomes = nomes_resolvidos_sem_coluna(colunas)
    assert {"area", "city", "year", "cres_pop_analise", "pop_rural_per"} <= set(nomes)
    assert "ano" not in nomes and "raca_maior" not in nomes  # é coluna / origem ausente
    contexto = dict.fromkeys(colunas, 7)
    assert [n for n in nomes if _resolver_campo_com_alias(contexto, n) is None] == []


# --- Unidade estado (passo 2, 04/11/2026) ---

@pytest.fixture
def snapshot_estadual(monkeypatch, snapshot_falso, tmp_path):
    (tmp_path / "estado").mkdir()
    estados = {
        "Paraíba": {"fonte": "view", "contexto": {"uf_sujeito": "A Paraíba", "uf_pop": 20}},
        "Ceará": {"fonte": "view", "contexto": {"uf_sujeito": "O Ceará", "uf_pop": 5}},
    }
    with gzip.open(tmp_path / "estado" / "demografia.json.gz", "wt", encoding="utf-8") as arquivo:
        json.dump({"gerado_em": "2026-11-04T04:30:00+00:00", "municipios": codificar(estados),
                   "metadados": {"estados": 2}}, arquivo)


_TEXTO_ESTADUAL = (
    "descricao_tema = Para quando $uf_pop for maior que 10:\n$uf_sujeito é grande.\n"
    "Para quando $uf_pop for menor ou igual a 10:\n$uf_sujeito é pequeno.\n@@"
)


def test_estado_texto_pronto_e_conferencia(monkeypatch, snapshot_estadual):
    cliente = _app(monkeypatch, "1")
    resposta = cliente.post(
        "/laboratorio/demografia/municipio?unidade=estado", json={"texto": _TEXTO_ESTADUAL, "cidade": "Ceará"}
    )
    assert resposta.status_code == 200
    assert resposta.json()["partes"] == ["O Ceará é pequeno."]

    id_conferencia = cliente.post(
        "/laboratorio/demografia/conferencias?unidade=estado", json={"texto": _TEXTO_ESTADUAL}
    ).json()["id"]
    for _ in range(100):
        estado = cliente.get(f"/laboratorio/conferencias/{id_conferencia}").json()
        if estado["estado"] in ("pronta", "erro"):
            break
        time.sleep(0.05)
    assert estado["estado"] == "pronta", estado
    assert estado["total"] == 2
    assert estado["resultado"]["campos_crus"] == []
    assert estado["resultado"]["versoes_por_municipio"] == {"Paraíba": [0], "Ceará": [1]}
    assert estado["resultado"]["graficos_sem_legenda"] == []  # gráfico é só municipal

    # Sem a unidade, a mesma rota segue municipal: o Ceará não está lá.
    municipal = cliente.post("/laboratorio/demografia/municipio", json={"texto": _TEXTO_ESTADUAL, "cidade": "Ceará"})
    assert municipal.status_code == 404


def test_estado_rotas_recusam_o_que_nao_existe(monkeypatch, snapshot_estadual):
    cliente = _app(monkeypatch, "1")
    assert cliente.get("/laboratorio/saude/colunas?unidade=estado").status_code == 404  # sem snapshot
    assert cliente.get("/laboratorio/demografia/colunas?unidade=pais").status_code == 422
    assert cliente.post("/laboratorio/demografia/csv?unidade=estado", json={"csv": "nm_mun\nX"}).status_code == 400
    colunas = cliente.get("/laboratorio/demografia/colunas?unidade=estado").json()["colunas"]
    assert {c["coluna"] for c in colunas} >= {"uf_sujeito", "uf_pop"}


def test_lista_de_temas_diz_se_o_estado_tem_doc(monkeypatch, snapshot_estadual):
    monkeypatch.setenv("DEMOGRAFIA_ESTADO_DOCS_URL", "https://docs.google.com/document/d/x/edit")
    monkeypatch.delenv("SAUDE_ESTADO_DOCS_URL", raising=False)
    temas = {t["slug"]: t for t in _app(monkeypatch, "1").get("/laboratorio/temas").json()}

    assert temas["demografia"]["unidades"]["estado"]["tem_doc"] is True
    assert temas["demografia"]["unidades"]["estado"]["snapshot_gerado_em"]
    # Os nomes vêm do snapshot, para a tela não ter lista fixa (área, 08/11/2026).
    assert temas["demografia"]["unidades"]["estado"]["lugares"] == ["Paraíba", "Ceará"]
    assert temas["saude"]["unidades"]["estado"] == {"snapshot_gerado_em": None, "tem_doc": False, "lugares": []}
    assert temas["instrumentos-sudene"]["unidades"] == {}
    # Área: só os temas com matview de área (desenvolvimento social não tem).
    assert set(temas["demografia"]["unidades"]) == {"estado", "area"}
    assert set(temas["desenvolvimento-social"]["unidades"]) == {"estado"}
    # O item municipal continua igual para a tela de hoje.
    assert temas["demografia"]["snapshot_gerado_em"]


def test_doc_da_unidade_vem_da_variavel_de_ambiente(monkeypatch):
    monkeypatch.setenv("SANEAMENTO_ESTADO_DOCS_URL", " https://docs.google.com/document/d/y/edit ")
    assert laboratorio.docs_env("saneamento", "estado") == "SANEAMENTO_ESTADO_DOCS_URL"
    assert laboratorio.docs_url("saneamento", "estado") == "https://docs.google.com/document/d/y/edit"
    assert laboratorio.docs_env("economia-renda") == "ECONOMIA_RENDA_DOCS_URL"
    monkeypatch.delenv("SAUDE_ESTADO_DOCS_URL", raising=False)
    assert laboratorio.docs_url("saude", "estado") is None


def test_ler_com_cada_valor_ignora_a_concordancia_do_estado(monkeypatch, tmp_path):
    # Como a sigla_uf no município (01/11): um valor por estado, em quase toda frase.
    monkeypatch.setattr(laboratorio_snapshot, "SNAPSHOT_DIR", tmp_path)
    (tmp_path / "estado").mkdir()
    _gravar_snapshot(tmp_path / "estado", "demografia", {
        "Paraíba": {"uf_sujeito": "A Paraíba", "uf_analise": "uma redução"},
        "Ceará": {"uf_sujeito": "O Ceará", "uf_analise": "um aumento"},
    })
    colunas = laboratorio.ler_com_cada_valor("demografia", "$uf_sujeito teve $uf_analise.", unidade="estado")
    assert [c["coluna"] for c in colunas] == ["uf_analise"]


# --- Unidade área de interesse (08/11/2026) ---

def test_area_texto_pronto_e_doc_proprio(monkeypatch, snapshot_falso, tmp_path):
    (tmp_path / "area").mkdir()
    areas = {"Caatinga": {"fonte": "view", "contexto": {"area_sujeito": "A Caatinga", "area_pop": 7}}}
    with gzip.open(tmp_path / "area" / "demografia.json.gz", "wt", encoding="utf-8") as arquivo:
        json.dump({"gerado_em": "2026-11-08T04:30:00+00:00", "municipios": codificar(areas),
                   "metadados": {"area": 1}}, arquivo)
    monkeypatch.setenv("DEMOGRAFIA_AREA_DOCS_URL", "https://docs.google.com/document/d/a/edit")
    cliente = _app(monkeypatch, "1")

    temas = {t["slug"]: t for t in cliente.get("/laboratorio/temas").json()}
    assert temas["demografia"]["unidades"]["area"]["lugares"] == ["Caatinga"]
    assert temas["demografia"]["unidades"]["area"]["tem_doc"] is True

    texto = "descricao_tema = $area_sujeito tinha $area_pop habitantes.\n@@"
    resposta = cliente.post("/laboratorio/demografia/municipio?unidade=area", json={"texto": texto, "cidade": "Caatinga"})
    assert resposta.status_code == 200
    assert "Caatinga tinha 7 habitantes." in resposta.json()["partes"][0]


def test_painel_traz_a_primeira_pagina_so_em_municipio(monkeypatch, tmp_path):
    # A primeira página do relatório (Apresentação, Características Gerais e o mapa)
    # vem do Doc de Características, não do Doc do tema (André, 09/11/2026).
    monkeypatch.setattr(laboratorio_snapshot, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.setattr(laboratorio, "CARACTERISTICAS_DOCS_URL", "doc-caract")
    caracteristicas = (
        "relatorio_geral= “Síntese de caract_mun.$nm_mun.”@@\n\n"
        "resumo_cidade= “caract_mun.$nm_mun fica na região caract_mun.$regiao (Figura X) "
        "e está inserido caract_mun.$bioma.”@@\n\n"
        "Figura X- Localização do município de caract_mun.$nm_mun.\n"
    )

    async def texto_do_doc(_url):
        return caracteristicas

    monkeypatch.setattr(laboratorio, "carregar_texto_do_docs", texto_do_doc)
    monkeypatch.setattr(laboratorio, "buscar_mapa_estatico", lambda nome, uf: "Nova (PB).png")
    laboratorio._bioma_da_capa.cache_clear()
    _gravar_snapshot(tmp_path, "demografia", {"Nova (PB)": {"nm_mun": "Nova", "regiao": "Nordeste", "bioma": "no bioma Caatinga"}})
    _gravar_snapshot(tmp_path, "meio-ambiente", {"Nova (PB)": {"nm_mun": "Nova", "regiao": "Nordeste", "bioma": "inserida no bioma Caatinga"}})
    doc = "descricao_tema = Texto de $nm_mun.\n@@"

    html = laboratorio.texto_do_municipio("demografia", doc, "Nova (PB)", com_graficos=True)["html"]
    capa = html[0]
    assert "Apresentação" in capa and "Síntese de Nova." in capa
    assert "região Nordeste (Figura 1)" in capa and "inserido no bioma Caatinga" in capa
    assert 'src="/laboratorio/mapas/Nova%20%28PB%29.png"' in capa and "Figura 1 – Localização do município de Nova." in capa
    assert html[1:] == ['<p class="theme-detail-text">Texto de Nova.</p>']

    # Em Meio Ambiente o bioma da linha é outra frase: a capa usa o de demografia, como
    # o relatório usa o das características.
    meio = laboratorio.texto_do_municipio("meio-ambiente", doc, "Nova (PB)", com_graficos=True)["html"][0]
    assert "inserido no bioma Caatinga" in meio and "inserida" not in meio

    # Fora do painel (conferência, "ler com cada valor"), sem capa.
    assert laboratorio.texto_do_municipio("demografia", doc, "Nova (PB)")["html"] == html[1:]


def test_laboratorio_le_o_doc_de_estado_como_o_relatorio_de_estado():
    # O PDF de estado isola o parágrafo de cada condição (relatorio_estado.py); o
    # painel com unidade=estado precisa ler igual, e o municipal não muda.
    doc = "Para quando demografia.$uf_x for igual a 1, então:\nA\nB"

    assert laboratorio.texto_da_unidade(doc, "municipio") is doc
    assert laboratorio.texto_da_unidade(doc, "estado") == (
        "Para quando demografia.$uf_x for igual a 1, então:\nA\n\nB"
    )


def test_laboratorio_le_o_doc_de_area_como_o_relatorio_de_area():
    # O relatório de área também isola o parágrafo de cada condição
    # (relatorio_estado.tema_da_unidade); até 13/11/2026 a prévia de área não isolava.
    doc = "Para quando demografia.$area_x for igual a 1, então:\nA\nB"

    assert laboratorio.texto_da_unidade(doc, "area") == (
        "Para quando demografia.$area_x for igual a 1, então:\nA\n\nB"
    )


def test_previa_de_estado_sai_como_o_relatorio_de_estado(monkeypatch, snapshot_estadual, tmp_path):
    # Gráficos do estado, figura começando em 1 (sem mapa), Panorama como cards e
    # não como texto nas Fontes, e a capa da primeira página estadual (13/11/2026).
    monkeypatch.setattr(laboratorio, "OUTPUT_DIR", tmp_path)
    pedidos = []

    def graficos_falsos(slug, linha, _saida, safe):
        pedidos.append((slug, linha["uf_sujeito"], safe))
        return {"grafico_teste": "teste.png"}

    async def primeira_pagina_falsa(nome, _safe):
        return {"relatorio_geral_html": [f"<p>Apresentação de {nome}</p>"]}

    monkeypatch.setattr(laboratorio, "gerar_graficos_do_estado", graficos_falsos)
    monkeypatch.setattr(laboratorio, "primeira_pagina_do_estado", primeira_pagina_falsa)
    doc = (
        "Panorama de indicadores\nPopulação\ndemografia.$uf_pop\nIBGE • pessoas\n\n"
        "descricao_tema = “$uf_sujeito tem um gráfico (Figura X).\n\n*grafico_teste\n\n"
        "Figura X – Legenda do teste.” @@\n"
    )

    html = "".join(laboratorio.texto_do_municipio("demografia", doc, "Ceará", com_graficos=True, unidade="estado")["html"])

    assert pedidos and pedidos[0][:2] == ("demografia", "O Ceará")
    assert pedidos[0][2].startswith("lab_estado_cear")
    assert "teste.png" in html and "Figura 1" in html and "Figura 2" not in html
    assert "Panorama de indicadores" in html and "<strong>População</strong>: 5" in html
    assert "demografia.$uf_pop" not in html
    assert html.index("Apresentação de Ceará") < html.index("O Ceará tem um gráfico")


def test_previa_de_area_tem_capa_do_doc_do_tema_e_nenhum_grafico(monkeypatch, snapshot_falso, tmp_path):
    (tmp_path / "area").mkdir()
    areas = {"Caatinga": {"fonte": "view", "contexto": {"area_sujeito": "A Caatinga"}}}
    with gzip.open(tmp_path / "area" / "demografia.json.gz", "wt", encoding="utf-8") as arquivo:
        json.dump({"gerado_em": "2026-11-13T04:30:00+00:00", "municipios": codificar(areas)}, arquivo)
    monkeypatch.setattr(laboratorio, "gerar_graficos_do_estado", lambda *a: pytest.fail("área não tem gráfico"))
    doc = (
        "resumo_cidade = “Resumo de $area_sujeito.” @@\n"
        "descricao_tema = “$area_sujeito (Figura X).\n\n*grafico_teste\n\nFigura X – Legenda.” @@\n"
    )

    html = "".join(laboratorio.texto_do_municipio("demografia", doc, "Caatinga", com_graficos=True, unidade="area")["html"])

    assert "Características Gerais" in html and "Resumo de A Caatinga." in html
    assert "Figura" not in html
