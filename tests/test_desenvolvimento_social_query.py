from utils.queries.desenvolvimento_social import _categoria_variacao


def test_categoria_variacao_returns_the_word_with_its_article():
    assert _categoria_variacao(0.161) == "um aumento"
    assert _categoria_variacao(-0.05) == "uma diminuição"
    assert _categoria_variacao(0) == "uma estabilidade"


def test_categoria_variacao_handles_missing_or_invalid_values():
    assert _categoria_variacao(None) is None
    assert _categoria_variacao("n/a") is None


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
