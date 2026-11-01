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
        json.dump({"gerado_em": "2026-10-29T04:30:00+00:00", "municipios": codificar(municipios)}, arquivo)


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
    monkeypatch.setattr(laboratorio, "get_macrotema", lambda _s: {"docs_url": "1AbCdEfGhIjKlMnOp"})

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

    colunas = cliente.get("/laboratorio/demografia/colunas").json()
    assert colunas["snapshot_gerado_em"] == "2026-10-29T04:30:00+00:00"
    assert {c["coluna"] for c in colunas["colunas"]} == {"pop", "nm_mun"}
    assert cliente.get("/laboratorio/saude/colunas").status_code == 404


def test_rota_do_doc_traduz_falha_do_google(monkeypatch):
    cliente = _app(monkeypatch, "1")

    async def _falha(_slug):
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
