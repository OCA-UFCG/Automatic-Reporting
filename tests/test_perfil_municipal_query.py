import pytest

from services import contexto as servico_contexto
from utils.data.macrotemas import MACROTEMAS
from utils.queries import perfil_municipal
from utils.queries.perfil_municipal import buscar_perfil_municipal


def test_busca_com_uf_usa_nm_mun_sem_sufixo(monkeypatch):
    chamadas = []

    def executar_fake(query, params, contexto_erro):
        chamadas.append((query, params))
        return {"nm_mun": "Campina Grande (PB)", "sigla_uf": "PB", "tend_ens_sup": 24475}

    monkeypatch.setattr(perfil_municipal, "executar_query_dict", executar_fake)

    dados = buscar_perfil_municipal("educacao", "Campina Grande", "PB")

    query, params = chamadas[-1]
    assert params == ("Campina Grande", "PB")
    # Regressão do 404 de educação: a view guarda nm_mun como "Cidade (UF)",
    # mas separar_cidade_uf entrega o nome sem sufixo.
    assert "regexp_replace(nm_mun" in query
    assert dados["tend_ens_sup"] == 24475


def test_select_estrela_traz_colunas_novas_da_view(monkeypatch):
    """A view é o contrato: nada de lista fixa de colunas.

    Educação tinha uma, escrita à mão, que ficou para trás quando a view ganhou
    `tend_ens_sup` — e o placeholder saía cru no PDF.
    """
    monkeypatch.setattr(
        perfil_municipal,
        "executar_query_dict",
        lambda query, params, contexto_erro: {"nm_mun": "X", "sigla_uf": "PB"}
        if "SELECT *" in query
        else None,
    )

    assert buscar_perfil_municipal("educacao", "X", "PB") is not None


def test_busca_sem_uf_resolve_cidade_unica(monkeypatch):
    monkeypatch.setattr(
        perfil_municipal,
        "executar_query_dicts",
        lambda *a, **k: [{"nm_mun": "Campina Grande (PB)", "sigla_uf": "PB"}],
    )

    dados = buscar_perfil_municipal("educacao", "campina grande")

    assert dados["sigla_uf"] == "PB"


def test_busca_sem_uf_levanta_erro_em_ambiguidade(monkeypatch):
    monkeypatch.setattr(
        perfil_municipal,
        "executar_query_dicts",
        lambda *a, **k: [
            {"nm_mun": "Formosa (GO)", "sigla_uf": "GO"},
            {"nm_mun": "Formosa (BA)", "sigla_uf": "BA"},
        ],
    )

    with pytest.raises(ValueError, match="Cidade ambígua"):
        buscar_perfil_municipal("demografia", "Formosa")


def test_busca_sem_uf_retorna_none_sem_correspondencia(monkeypatch):
    monkeypatch.setattr(perfil_municipal, "executar_query_dicts", lambda *a, **k: [])

    assert buscar_perfil_municipal("saude", "Cidade Inexistente") is None


def test_macrotema_sem_view_mapeada_retorna_none():
    assert buscar_perfil_municipal("desenvolvimento-social", "Campina Grande", "PB") is None


@pytest.mark.parametrize("slug", sorted(MACROTEMAS))
def test_todo_macrotema_usa_o_mesmo_caminho_de_perfil(slug, monkeypatch):
    """Nenhum tema tem caminho próprio: `carregar_linha_base` chama sempre
    `buscar_perfil_municipal`. Educação já teve um `if slug ==` aqui, e foi
    justamente esse ramo que ficou desatualizado em relação à view."""
    chamados = []

    monkeypatch.setattr(
        servico_contexto,
        "buscar_perfil_municipal",
        lambda macrotema, nome, uf: chamados.append((macrotema, nome, uf))
        or {"nm_mun": "Campina Grande (PB)", "sigla_uf": "PB"},
    )

    linhas, origem = servico_contexto.carregar_linha_base(
        slug, MACROTEMAS[slug], "Campina Grande (PB)"
    )

    assert chamados == [(slug, "Campina Grande", "PB")]
    assert origem == servico_contexto.ORIGEM_VIEW
    assert linhas[0]["nm_mun"] == "Campina Grande (PB)"
