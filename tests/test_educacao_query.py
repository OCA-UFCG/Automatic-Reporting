from utils.queries import educacao

# O perfil educacional migrou para tests/test_perfil_municipal_query.py: ele
# passou a usar o mesmo `buscar_perfil_municipal` dos outros macrotemas.


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
