import pytest

from utils.queries import educacao


def _linha_perfil(nm_mun: str, sigla_uf: str):
    valores = {"nm_mun": nm_mun, "sigla_uf": sigla_uf}
    return tuple(
        valores.get(coluna, f"valor_{coluna}")
        for coluna in educacao.COLUNAS_PERFIL_EDUCACIONAL
    )


def test_busca_com_uf_usa_nm_mun_sem_sufixo(monkeypatch):
    chamadas = []

    def executar_query_fake(query, params, contexto_erro, buscar_todas=False):
        chamadas.append(params)
        return _linha_perfil("Campina Grande", "PB")

    monkeypatch.setattr(educacao, "executar_query", executar_query_fake)

    dados = educacao.buscar_perfil_educacional_municipio("Campina Grande", "PB")

    assert chamadas[-1] == ("Campina Grande", "PB")
    assert dados["nm_mun"] == "Campina Grande"
    assert dados["sigla_uf"] == "PB"


def test_busca_com_uf_retorna_none_sem_correspondencia(monkeypatch):
    monkeypatch.setattr(educacao, "executar_query", lambda *a, **k: None)

    dados = educacao.buscar_perfil_educacional_municipio("Cidade Inexistente", "PB")

    assert dados is None


def test_busca_sem_uf_resolve_cidade_unica(monkeypatch):
    monkeypatch.setattr(
        educacao,
        "executar_query",
        lambda *a, **k: [_linha_perfil("Campina Grande", "PB")],
    )

    dados = educacao.buscar_perfil_educacional_municipio("campina grande")

    assert dados["nm_mun"] == "Campina Grande"
    assert dados["sigla_uf"] == "PB"


def test_busca_sem_uf_levanta_erro_em_ambiguidade(monkeypatch):
    monkeypatch.setattr(
        educacao,
        "executar_query",
        lambda *a, **k: [
            _linha_perfil("Formosa", "GO"),
            _linha_perfil("Formosa", "BA"),
        ],
    )

    with pytest.raises(ValueError, match="Cidade ambígua"):
        educacao.buscar_perfil_educacional_municipio("Formosa")


def test_busca_sem_uf_retorna_none_sem_correspondencia(monkeypatch):
    monkeypatch.setattr(educacao, "executar_query", lambda *a, **k: [])

    dados = educacao.buscar_perfil_educacional_municipio("Cidade Inexistente")

    assert dados is None


def test_taxas_educacao_agrega_por_cor_e_faixa(monkeypatch):
    linhas_banco = [
        ("Branca", "15 a 19 anos", "M", 45, 50),
        ("Branca", "15 a 19 anos", "F", 45, 50),
        ("Preta", "20 a 29 anos", "M", 8, 10),
    ]
    monkeypatch.setattr(educacao, "executar_query", lambda *a, **k: linhas_banco)

    dados = educacao.buscar_taxas_educacao_cor_faixa_etaria("Campina Grande", "PB")

    assert dados["taxa_15_a_19_branca"] == 10.0
    assert dados["taxa_20_a_29_preta"] == 20.0


def test_taxas_educacao_retorna_none_sem_dados(monkeypatch):
    monkeypatch.setattr(educacao, "executar_query", lambda *a, **k: None)

    dados = educacao.buscar_taxas_educacao_cor_faixa_etaria("Cidade Sem Dados", "PB")

    assert dados is None
