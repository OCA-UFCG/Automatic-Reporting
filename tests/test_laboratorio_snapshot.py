import logging
from contextlib import contextmanager
from decimal import Decimal

import psycopg2
import pytest

from services import generation, laboratorio_snapshot
from services.macrotemas import get_macrotema
from tests.relatorio_congelado import (
    CASOS,
    buscar_do_replay,
    carregar_dados_gravados,
    carregar_doc_do_replay,
    instalar_ambiente,
    props_do_relatorio,
)
from utils.geografia import separar_cidade_uf

# Só os casos de um tema: num relatório de vários temas algumas mesclas mudam (ex.:
# sexo_faixa entra cru fora de demografia), e o snapshot é sempre de um tema só.
_CASOS_DE_UM_TEMA = [(cidade, tema) for _caso, cidade, tema in CASOS if tema != "todos"]


@pytest.mark.parametrize("cidade, tema", _CASOS_DE_UM_TEMA)
def test_contexto_igual_ao_do_handler(cidade, tema, monkeypatch, tmp_path):
    capturadas = instalar_ambiente(
        monkeypatch.setattr,
        tmp_path,
        buscar_do_replay(carregar_dados_gravados()),
        carregar_doc_do_replay(),
    )
    do_handler: list[dict] = []
    original = generation.montar_contexto_tema

    def capturar(*args):
        do_handler.append(original(*args))
        return do_handler[-1]

    monkeypatch.setattr(generation, "montar_contexto_tema", capturar)
    props_do_relatorio(cidade, tema, capturadas)

    nome, uf = separar_cidade_uf(cidade)
    perfil_db = generation.buscar_perfil_municipal(tema, nome, uf)
    fonte, contexto, _n = laboratorio_snapshot.contexto_do_municipio(
        cidade, tema, get_macrotema(tema), perfil_db
    )

    esperado = dict(do_handler[0])
    # O handler põe data/hora do relatório antes de mesclar; o laboratório põe na conferência.
    del esperado["data_relatorio"], esperado["hora_relatorio"]
    assert fonte == "view"
    assert contexto == esperado


# --- rodada de um tema, com banco e montagem dublados ---------------------------------

_CIDADES = [f"Cidade {i} (PB)" for i in range(200)]


@pytest.fixture
def rodada(monkeypatch, tmp_path):
    """Dubla o banco: todas as cidades na view, contexto com Decimal. Devolve o estado
    que cada teste mexe para provocar o caso."""
    estado = {"indice": None, "falhar_em": set(), "falhar_uma_vez": set(), "erro_view": False}

    @contextmanager
    def conexao():
        yield object()

    def ler_view(_conn, _slug):
        if estado["erro_view"]:
            raise psycopg2.errors.QueryCanceled("statement timeout")
        indice = estado["indice"]
        if indice is None:
            indice = {(c, "PB"): {"nm_mun": c} for c in _CIDADES}
        return indice, []

    def contexto(cidade, _slug, _dados, perfil_db):
        if cidade in estado["falhar_uma_vez"]:
            estado["falhar_uma_vez"].discard(cidade)
            logging.getLogger("utils.queries.base").warning(
                "Falha ao executar query (%s): timeout", cidade
            )
            return "view", {"nm_mun": cidade, "sem_o_bloco": True}, 1
        if cidade in estado["falhar_em"]:
            logging.getLogger("utils.queries.base").warning(
                "Falha ao executar query (%s): timeout", cidade
            )
        if perfil_db is None:
            return None
        return "view", {"nm_mun": cidade, "taxa": Decimal("1.50")}, 1

    monkeypatch.setattr(laboratorio_snapshot, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.setattr(laboratorio_snapshot, "conexao_reaproveitada", conexao)
    monkeypatch.setattr(laboratorio_snapshot, "ler_view_do_tema", ler_view)
    monkeypatch.setattr(
        laboratorio_snapshot, "chaves_das_cidades", lambda _c, cs: {c: (c, "PB") for c in cs}
    )
    monkeypatch.setattr(laboratorio_snapshot, "contexto_do_municipio", contexto)
    return estado


def _gerar():
    return laboratorio_snapshot.gerar_snapshot_tema("saude", cidades=_CIDADES)


def test_grava_e_carrega_com_os_tipos(rodada):
    caminho = _gerar()
    assert caminho == laboratorio_snapshot.caminho_snapshot("saude")
    snapshot = laboratorio_snapshot.carregar_snapshot("saude")
    assert snapshot["metadados"]["na_view"] == 200
    contexto = snapshot["municipios"]["Cidade 7 (PB)"]["contexto"]
    assert contexto["taxa"] == Decimal("1.50") and type(contexto["taxa"]) is Decimal
    assert not list(caminho.parent.glob("*.tmp"))


def test_cidade_fora_da_view_e_do_csv_fica_em_ausentes(rodada):
    rodada["indice"] = {(c, "PB"): {"nm_mun": c} for c in _CIDADES[1:]}
    _gerar()
    metadados = laboratorio_snapshot.carregar_snapshot("saude")["metadados"]
    assert metadados["ausentes"] == ["Cidade 0 (PB)"]


@pytest.mark.parametrize(
    "provocar",
    [
        lambda estado: estado.update(indice={}),  # view vazia
        lambda estado: estado.update(erro_view=True),  # timeout lendo a view
        lambda estado: estado.update(falhar_em=set(_CIDADES[:3])),  # 1,5% com falha
        # na view caiu de 200 para 180 (10%)
        lambda estado: estado.update(indice={(c, "PB"): {"nm_mun": c} for c in _CIDADES[20:]}),
    ],
    ids=["view_vazia", "erro_na_view", "falhas_acima_do_limiar", "queda_na_view"],
)
def test_rodada_suspeita_mantem_o_anterior(rodada, provocar):
    _gerar()
    anterior = laboratorio_snapshot.caminho_snapshot("saude").read_bytes()
    provocar(rodada)
    assert _gerar() is None
    assert laboratorio_snapshot.caminho_snapshot("saude").read_bytes() == anterior


def test_falha_abaixo_do_limiar_grava_e_registra(rodada):
    rodada["falhar_em"] = {"Cidade 3 (PB)"}  # 0,5%
    assert _gerar() is not None
    metadados = laboratorio_snapshot.carregar_snapshot("saude")["metadados"]
    assert metadados["falhas_de_consulta"] == {"Cidade 3 (PB)": 1}


def test_falha_passageira_e_refeita_no_fim_do_tema(rodada):
    # Timeouts com o banco carregado, abaixo do portão, seriam gravados sem o bloco
    rodada["falhar_uma_vez"] = set(_CIDADES[:3])  # 1,5%: sem a repetição, abortaria
    assert _gerar() is not None
    snapshot = laboratorio_snapshot.carregar_snapshot("saude")
    assert snapshot["metadados"]["falhas_de_consulta"] == {}
    assert snapshot["metadados"]["recuperados_na_repeticao"] == _CIDADES[:3]
    assert "sem_o_bloco" not in snapshot["municipios"]["Cidade 0 (PB)"]["contexto"]


def test_carregar_sem_arquivo_devolve_none(monkeypatch, tmp_path):
    monkeypatch.setattr(laboratorio_snapshot, "SNAPSHOT_DIR", tmp_path)
    assert laboratorio_snapshot.carregar_snapshot("saude") is None


def test_script_recusa_tema_invalido():
    from scripts.snapshot_laboratorio import main

    with pytest.raises(SystemExit) as saida:
        main(["--tema", "astrologia"])
    assert saida.value.code == 2


# --- Estado (pedido de 03/11/2026) ---

_ESTADOS = ["Maranhão", "Piauí", "Ceará", "Rio Grande do Norte", "Paraíba",
            "Pernambuco", "Alagoas", "Sergipe", "Bahia"]


def _linha_estadual(cd_uf: int, nome: str) -> dict:
    return {"uf_cd_uf": cd_uf, "uf_estado": nome, "uf_sujeito": nome,
            "uf_em": f"no {nome}", "uf_pop_total_2022": Decimal(1234567)}


@pytest.fixture
def rodada_estado(monkeypatch, tmp_path):
    estado = {"linhas": [_linha_estadual(21 + i, nome) for i, nome in enumerate(_ESTADOS)]}

    @contextmanager
    def conexao():
        yield object()

    def ler(_conn, _slug, _unidade):
        if isinstance(estado["linhas"], Exception):
            raise estado["linhas"]
        return estado["linhas"]

    monkeypatch.setattr(laboratorio_snapshot, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.setattr(laboratorio_snapshot, "conexao_reaproveitada", conexao)
    monkeypatch.setattr(laboratorio_snapshot, "ler_matview_da_unidade", ler)
    return estado


def test_estado_grava_os_9_numa_pasta_propria(rodada_estado, tmp_path):
    caminho = laboratorio_snapshot.gerar_snapshot_unidade("saude", "estado")
    assert caminho == tmp_path / "estado" / "saude.json.gz"
    # O município continua na raiz: o cron do gamma e os snapshots de hoje.
    assert laboratorio_snapshot.caminho_snapshot("saude") == tmp_path / "saude.json.gz"
    assert laboratorio_snapshot.carregar_snapshot("saude") is None

    snapshot = laboratorio_snapshot.carregar_snapshot("saude", "estado")
    assert list(snapshot["municipios"]) == _ESTADOS
    contexto = snapshot["municipios"]["Paraíba"]["contexto"]
    assert type(contexto["uf_pop_total_2022"]) is Decimal


@pytest.mark.parametrize(
    "provocar",
    [
        lambda e: e.update(linhas=e["linhas"][:8]),  # faltou um estado
        lambda e: e.update(linhas=e["linhas"][:8] + [e["linhas"][0]]),  # nome repetido
        lambda e: e["linhas"][0].update(uf_estado=None),  # nome vazio
        lambda e: e.update(linhas=psycopg2.errors.QueryCanceled("statement timeout")),
    ],
    ids=["faltou_estado", "nome_repetido", "nome_vazio", "erro_na_matview"],
)
def test_estado_suspeito_mantem_o_anterior(rodada_estado, provocar):
    laboratorio_snapshot.gerar_snapshot_unidade("saude", "estado")
    caminho = laboratorio_snapshot.caminho_snapshot("saude", "estado")
    anterior = caminho.read_bytes()
    provocar(rodada_estado)
    assert laboratorio_snapshot.gerar_snapshot_unidade("saude", "estado") is None
    assert caminho.read_bytes() == anterior


def test_estado_passa_pela_conferencia(rodada_estado):
    # A promessa do handoff: o resto do laboratório não depende de ser município.
    from services import laboratorio

    laboratorio_snapshot.gerar_snapshot_unidade("demografia", "estado")
    snapshot = laboratorio_snapshot.carregar_snapshot("demografia", "estado")
    contextos = {nome: m["contexto"] for nome, m in snapshot["municipios"].items()}
    texto = "$uf_sujeito tinha $uf_pop_total_2022 habitantes em 2022.\n"

    conferencia = laboratorio.conferir_tema(texto, "demografia", contextos)
    assert conferencia["campos_crus"] == [] and conferencia["erros"] == {}

    # graficos={}: estado não tem gráfico (GRAFICOS_POR_TEMA é por município).
    resultado = laboratorio.conferir_municipio(texto, contextos["Paraíba"], "demografia", {})
    assert resultado["partes"] == ["Paraíba tinha 1.234.567 habitantes em 2022."]


def test_script_recusa_tema_sem_matview_estadual():
    from scripts.snapshot_laboratorio import main

    with pytest.raises(SystemExit) as saida:
        main(["--tema", "instrumentos-sudene", "--unidade", "estado"])
    assert saida.value.code == 2


# --- Área de interesse (08/11/2026) ---

_AREAS = ["Caatinga", "Área de atuação da Sudene", "Semiárido", "Nordeste"]


@pytest.fixture
def rodada_area(monkeypatch, tmp_path):
    area = {"linhas": [{"area_cd": i + 1, "area_nome": nome, "area_sujeito": nome,
                        "area_pop_total_2022": Decimal(1000 + i)} for i, nome in enumerate(_AREAS)]}
    lidas = []

    @contextmanager
    def conexao():
        yield object()

    def ler(_conn, slug, unidade):
        lidas.append((slug, unidade))
        return area["linhas"]

    monkeypatch.setattr(laboratorio_snapshot, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.setattr(laboratorio_snapshot, "conexao_reaproveitada", conexao)
    monkeypatch.setattr(laboratorio_snapshot, "ler_matview_da_unidade", ler)
    area["lidas"] = lidas
    return area


def test_area_grava_quantas_vierem_numa_pasta_propria(rodada_area, tmp_path):
    caminho = laboratorio_snapshot.gerar_snapshot_unidade("saude", "area")
    assert caminho == tmp_path / "area" / "saude.json.gz"
    assert rodada_area["lidas"] == [("saude", "area")]
    assert list(laboratorio_snapshot.carregar_snapshot("saude", "area")["municipios"]) == _AREAS

    # Quais áreas existem é da equipe de dados (André, 08/11): uma 5ª entra sem código.
    rodada_area["linhas"].append({"area_cd": 5, "area_nome": "Amazônia Legal"})
    laboratorio_snapshot.gerar_snapshot_unidade("saude", "area")
    assert len(laboratorio_snapshot.carregar_snapshot("saude", "area")["municipios"]) == 5


@pytest.mark.parametrize(
    "provocar",
    [
        lambda a: a.update(linhas=[]),  # matview vazia
        lambda a: a["linhas"].append(dict(a["linhas"][0])),  # nome repetido
        lambda a: a["linhas"][0].update(area_nome=""),  # nome vazio
    ],
    ids=["vazia", "nome_repetido", "nome_vazio"],
)
def test_area_suspeita_mantem_o_anterior(rodada_area, provocar):
    laboratorio_snapshot.gerar_snapshot_unidade("saude", "area")
    caminho = laboratorio_snapshot.caminho_snapshot("saude", "area")
    anterior = caminho.read_bytes()
    provocar(rodada_area)
    assert laboratorio_snapshot.gerar_snapshot_unidade("saude", "area") is None
    assert caminho.read_bytes() == anterior


def test_area_le_o_schema_e_a_matview_do_tema():
    # Saneamento lê a areaint_infraestrutura, como o estado lê a est_infraestrutura.
    executadas = []

    class Cursor:
        description = (("area_nome",),)

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, sql):
            executadas.append(sql)

        def fetchall(self):
            return [("Caatinga",)]

    class Conn:
        def cursor(self):
            return Cursor()

    linhas = laboratorio_snapshot.ler_matview_da_unidade(Conn(), "saneamento", "area")
    assert linhas == [{"area_nome": "Caatinga"}]
    assert executadas == ["SELECT * FROM auto_relatorios_areaint.areaint_infraestrutura ORDER BY area_cd"]


def test_script_recusa_tema_sem_matview_de_area():
    from scripts.snapshot_laboratorio import main

    with pytest.raises(SystemExit) as saida:
        main(["--unidade", "area", "--tema", "desenvolvimento-social"])
    assert saida.value.code == 2
