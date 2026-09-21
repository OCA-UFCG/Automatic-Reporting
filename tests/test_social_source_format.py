import pytest

from utils.render.renderer import render_descricao_tema_html, texto_para_html


@pytest.mark.parametrize('render', [texto_para_html, render_descricao_tema_html])
def test_social_sources_with_docs_markdown(render):
    texto = r'''**#!Fontes**

Os dados deste relatório foram extraídos do seguinte painel de dados do Data Nordeste:

desen\_social.”$nm\_painel1” = [https://datanordeste.sudene.gov.br/data-panel/idhm](https://datanordeste.sudene.gov.br/data-panel/idhm)

- Instituto de Pesquisa Econômica Aplicada; e
- Fundação João Pinheiro.

**#!Conteúdos relacionados**

desen\_social.“$nm\_datastory1”=[https://datanordeste.sudene.gov.br/data-stories/2072ff402a554914b16074fd440e2159](https://datanordeste.sudene.gov.br/data-stories/2072ff402a554914b16074fd440e2159)
desen\_social.“$nm\_datastory2” =[https://datanordeste.sudene.gov.br/boletim/4stpvtzkvFG1G5yZTNVz12](https://datanordeste.sudene.gov.br/boletim/4stpvtzkvFG1G5yZTNVz12)
'''
    contexto = {'nm_painel1': 'IDHM', 'nm_datastory1': 'Desenvolvimento social', 'nm_datastory2': 'Boletim social'}
    html = ''.join(render(texto, contexto, namespace='desenvolvimento-social'))
    assert html.count('class="fonte-badge"') == 3
    assert '<strong>Painel de dados:</strong> IDHM</a>' in html
    assert '<strong>Narrativa de dados:</strong> Desenvolvimento social</a>' in html
    assert '<strong>Boletim:</strong> Boletim social</a>' in html
    assert '<h3 class="fontes-box-heading">Fontes</h3>' in html
    assert '<h3 class="fontes-box-heading">Conteúdos relacionados</h3>' in html
    assert 'Fundação João Pinheiro' in html
    assert '$nm' not in html
