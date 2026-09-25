from utils.queries.desenvolvimento_social import (
    _categoria_variacao,
    buscar_perfil_desenvolvimento_social,
)


def test_categoria_variacao_returns_the_word_with_its_article():
    assert _categoria_variacao(0.161) == "um aumento"
    assert _categoria_variacao(-0.05) == "uma diminuição"
    assert _categoria_variacao(0) == "uma estabilidade"


def test_categoria_variacao_handles_missing_or_invalid_values():
    assert _categoria_variacao(None) is None
    assert _categoria_variacao("n/a") is None


def test_busca_normaliza_sufixo_uf_no_nm_mun(monkeypatch):
    # vw_perfil_desen_social_municipal guarda nm_mun sem sufixo "(UF)"; sem
    # normalizar (regexp_replace), passar o nome já canonicalizado como
    # "Cidade (UF)" (generation.py) nunca casaria — mesma classe de bug do
    # Recife (PE) em saúde, corrigida em utils/queries/perfil_municipal.py.
    chamadas = []

    def query(sql, params, descricao):
        chamadas.append(sql)
        return (None,) * 17 + ("IDHM", "Explore Nordeste", "Emprego e Rendimento")

    monkeypatch.setattr(
        "utils.queries.desenvolvimento_social.executar_query", query
    )

    buscar_perfil_desenvolvimento_social("Recife (PE)", "PE")

    assert "regexp_replace(nm_mun" in chamadas[-1]


def test_perfil_carrega_nomes_dos_conteudos_e_alias_do_docs(monkeypatch):
    from utils.queries import desenvolvimento_social as social
    from utils.render.renderer import texto_para_html

    def query(sql, params, descricao):
        assert 'nm_painel1' in sql
        assert 'nm_datastory1' in sql
        assert 'nm_boletim1' in sql
        return (None,) * 17 + ('IDHM', 'Explore Nordeste', 'Emprego e Rendimento')

    monkeypatch.setattr(social, 'executar_query', query)
    contexto = social.buscar_perfil_desenvolvimento_social('Recife', 'PE')
    html = texto_para_html(
        '#!Fontes\n\ndesen_social.“$nm_painel1” = https://datanordeste.sudene.gov.br/data-panel/idhm\n\n'
        '#!Conteúdos relacionados\n\ndesen_social.“$nm_datastory1” = https://datanordeste.sudene.gov.br/data-stories/exemplo\n'
        'desen_social.“$nm_datastory2” = https://datanordeste.sudene.gov.br/boletim/exemplo',
        contexto, namespace='desenvolvimento-social',
    )
    assert html.count('class="fonte-badge"') == 3
    assert '<strong>Boletim:</strong> Emprego e Rendimento</a>' in html
