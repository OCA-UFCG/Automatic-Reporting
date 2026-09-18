from utils.queries import perfil_municipal


def test_educacao_mapeia_para_matview_de_perfil_educacional():
    assert (
        perfil_municipal.VIEW_POR_MACROTEMA["educacao"]
        == "mv_perfil_educacional_municipal"
    )


def test_busca_normaliza_sufixo_uf_no_nm_mun(monkeypatch):
    # `mv_perfil_educacional_municipal` guarda nm_mun como "Cidade (UF)" em
    # algumas linhas; sem normalizar (regexp_replace), o match por nome digitado
    # sem sufixo não casa e o macrotema cai pro fallback de CSV à toa.
    chamadas = []

    def executar_query_dict_fake(query, params, contexto_erro):
        chamadas.append(query)
        return {"nm_mun": "Recife (PE)", "sigla_uf": "PE"}

    monkeypatch.setattr(
        perfil_municipal, "executar_query_dict", executar_query_dict_fake
    )

    dados = perfil_municipal.buscar_perfil_municipal("educacao", "Recife", "PE")

    assert "regexp_replace(nm_mun" in chamadas[-1]
    assert dados["nm_mun"] == "Recife (PE)"


def test_busca_usa_select_star_e_traz_colunas_novas_da_view(monkeypatch):
    # Regressão do bug em que $tend_ens_sup saía cru no relatório: uma lista fixa
    # de colunas (removida de utils/queries/educacao.py) ficava atrás de colunas
    # novas da matview. buscar_perfil_municipal usa SELECT *, então qualquer
    # coluna nova chega ao contexto sem precisar editar código.
    monkeypatch.setattr(
        perfil_municipal,
        "executar_query_dict",
        lambda query, params, contexto_erro: {
            "nm_mun": "Recife (PE)",
            "sigla_uf": "PE",
            "tend_ens_sup": 12345,
        },
    )

    dados = perfil_municipal.buscar_perfil_municipal("educacao", "Recife", "PE")

    assert dados["tend_ens_sup"] == 12345


def test_macrotema_sem_view_mapeada_retorna_none():
    assert perfil_municipal.buscar_perfil_municipal("inexistente", "Recife", "PE") is None
