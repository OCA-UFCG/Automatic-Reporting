from utils.renderer import substituir_placeholders, texto_para_html


def test_references_and_related_content_render_as_html():
    texto = """#! Referências

referencia= "IBGE, 2023."@@

#! Conteúdos relacionados

* https://example.com/relatorio
* https://example.com/estudos
"""

    html = texto_para_html(
        texto,
        {"nm_mun": "Campina Grande", "ano": "2022"},
        namespace="demografia",
    )

    assert "<h1>Referências</h1>" in html
    assert "IBGE, 2023." in html
    assert "<h1>Conteúdos relacionados</h1>" in html
    assert "<ul>" in html
    assert "https://example.com/relatorio" in html
    assert '<a href="https://example.com/relatorio">' in html


def test_heading_marker_does_not_require_a_space():
    html = texto_para_html("#!Conteúdos relacionados", {}, namespace="demografia")
    assert html == "<h1>Conteúdos relacionados</h1>"


def test_unavailable_characteristics_variables_are_preserved():
    texto = "caract_mun.$nm_mun fica em caract_mun.$estado"
    html = texto_para_html(texto, {}, namespace="caract_mun")
    assert "$nm_mun" in html
    assert "$estado" in html


def test_new_demography_placeholder_formats_use_the_current_table_row():
    contexto = {"nm_mun": "Campina Grande", "pop_total_2022": 419379}
    texto = "$Table.demo$nm_mun tem $pop_total_2022 habitantes"

    assert substituir_placeholders(texto, contexto) == (
        "Campina Grande tem 419379 habitantes"
    )


def test_education_namespace_before_dollar_is_replaced_without_prefix():
    contexto = {"nm_mun": "Campina Grande", "alfabetizado_per": "91,4"}
    texto = "educacao.$nm_mun possui educacao.$alfabetizado_per % alfabetizados"

    assert substituir_placeholders(texto, contexto, namespace="educacao") == (
        "Campina Grande possui 91,4 % alfabetizados"
    )


def test_education_macrotheme_csv_and_column_alias_marker():
    contexto = {"cor_maior": "Parda", "fundamental_comp_per": "16,43"}
    texto = (
        "educacao.educacao.$raca_maior; "
        "educacao.educacao.$fundamental_com_per"
    )

    assert substituir_placeholders(texto, contexto, namespace="educacao") == (
        "Parda; 16,43"
    )
