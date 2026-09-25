import pytest

from services.generation import (
    _bioma_concordando_com_n_uc,
    _caracteristicas_sem_sobrescrever_bioma,
    _contexto_caracteristicas,
)

CARACTERISTICAS = {
    "nm_mun": "Campina Grande (PB)",
    "regiao": "Nordeste",
    "bioma": "Caatinga",
}


def test_bioma_das_ucs_da_view_nao_e_sobrescrito_pelo_do_municipio():
    # Regressão: buscar_caracteristicas_municipio sobrescrevia o `bioma` da view
    # ambiente (frase pronta sobre as UCs) com o bioma do município, e os 671
    # municípios com UC saíam "…com área de 1.234 hectares, Caatinga." (revisão
    # editorial de Meio Ambiente, 25/09/2026).
    linha = {"nm_mun": "Campina Grande (PB)", "n_uc": 1, "bioma": "inserida no bioma Caatinga"}

    linha.update(_caracteristicas_sem_sobrescrever_bioma(CARACTERISTICAS, linha))

    assert linha["bioma"] == "inserida no bioma Caatinga"
    assert linha["regiao"] == "Nordeste"


def test_tema_sem_coluna_bioma_recebe_o_bioma_do_municipio():
    linha = {"nm_mun": "Campina Grande (PB)", "pop_total_2022": 419379}

    linha.update(_caracteristicas_sem_sobrescrever_bioma(CARACTERISTICAS, linha))

    assert linha["bioma"] == "Caatinga"


def test_capa_usa_o_bioma_do_municipio_mesmo_na_linha_de_meio_ambiente():
    # O Doc de Características escreve "está inserido no bioma caract_mun.$bioma":
    # com a frase da view, sairia "inserido no bioma inserida no bioma Caatinga".
    linha = {"nm_mun": "Campina Grande (PB)", "n_uc": 1, "bioma": "inserida no bioma Caatinga"}

    contexto = _contexto_caracteristicas(linha, CARACTERISTICAS)

    assert contexto["bioma"] == "Caatinga"
    assert contexto["n_uc"] == 1
    assert linha["bioma"] == "inserida no bioma Caatinga"


def test_capa_sem_caracteristicas_usa_a_linha_do_tema():
    linha = {"nm_mun": "Campina Grande (PB)"}

    assert _contexto_caracteristicas(linha, None) == linha


def test_capa_sem_bioma_nas_caracteristicas_nao_herda_a_frase_das_ucs():
    # buscar_caracteristicas_municipio descarta valores None, e uma consulta que
    # falha devolve None: sem isso, a capa sairia "inserido no bioma inserida no
    # bioma Caatinga".
    linha = {"nm_mun": "Campina Grande (PB)", "n_uc": 1, "bioma": "inserida no bioma Caatinga"}

    assert "bioma" not in _contexto_caracteristicas(linha, {"nm_mun": "Campina Grande (PB)"})
    assert "bioma" not in _contexto_caracteristicas(linha, None)


@pytest.mark.parametrize(
    ("bioma", "n_uc", "esperado"),
    [
        # A view escolhe o particípio pelo número de biomas; no Doc ele concorda
        # com a UC ("1 Unidade…, inserida") ou com as Unidades ("N Unidades…,
        # inseridas"): 126 municípios com 1 UC saíam "inseridas nos biomas".
        ("inseridas nos biomas Amazônia e Cerrado", 1, "inserida nos biomas Amazônia e Cerrado"),
        ("inserida no bioma Caatinga", 3, "inseridas no bioma Caatinga"),
        ("inserida no bioma Caatinga", 1, "inserida no bioma Caatinga"),
        ("inseridas nos biomas área marinha e Amazônia", 2, "inseridas nos biomas área marinha e Amazônia"),
        ("inserida no bioma Caatinga", "1", "inserida no bioma Caatinga"),
        ("inseridas nos biomas Amazônia e Cerrado", "1,0", "inserida nos biomas Amazônia e Cerrado"),
        ("Inseridas nos biomas Amazônia e Cerrado", 1, "inserida nos biomas Amazônia e Cerrado"),
        ("inserida  no bioma Caatinga", 2, "inseridas  no bioma Caatinga"),
    ],
)
def test_participio_do_bioma_concorda_com_o_numero_de_ucs(bioma, n_uc, esperado):
    assert _bioma_concordando_com_n_uc(bioma, n_uc) == esperado


@pytest.mark.parametrize(
    ("bioma", "n_uc"),
    [
        (None, 0),  # município sem UC: a view manda NULL
        ("inserida no bioma Caatinga", None),
        ("Caatinga", 1),  # outra redação: não mexe
        ("inserida no bioma Caatinga", float("inf")),  # número inválido não derruba o relatório
    ],
)
def test_bioma_fora_do_formato_da_view_fica_como_esta(bioma, n_uc):
    assert _bioma_concordando_com_n_uc(bioma, n_uc) == bioma


def test_capa_so_troca_o_bioma_e_mantem_o_que_foi_mesclado_depois():
    # A linha já traz consultas mescladas depois das características (ex.:
    # indicadores). A capa só pode trocar o bioma, não reaplicar o resto.
    linha = {"nm_mun": "Campina Grande (PB)", "pop_total": 419379, "bioma": "inserida no bioma Caatinga"}
    caracteristicas = {"nm_mun": "Campina Grande (PB)", "pop_total": 0, "bioma": "Caatinga"}

    contexto = _contexto_caracteristicas(linha, caracteristicas)

    assert contexto["pop_total"] == 419379
    assert contexto["bioma"] == "Caatinga"
