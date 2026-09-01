from utils.render.placeholders import interpretar_blocos_condicionais
from utils.render.renderer import (
    reset_figura_contador,
    substituir_placeholders,
    texto_para_html,
)


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
        "Campina Grande tem 419.379 habitantes"
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


def test_database_column_names_support_editorial_document_placeholders():
    contexto = {
        "area_territorial": 593.026,
        "centros_pop": 2,
        "pop_total_indigena": 1042,
        "homem_indigena": 501,
        "mulher_indigena": 541,
        "pop_rua_total": 120,
        "pobreza_cadunico": 60,
        "baixa_renda_cadunico": 30,
        "acima_meio_sm_cadunico": 30,
        "familias_rua_bf": 18,
    }
    texto = (
        "caract_mun.$area; demografia.$centro_pop; "
        "demografia.$pop_ind_2022; demografia.$pop_ind_homem_2022; "
        "demografia.$pop_ind_mulher_2022; demografia.$pop_rua_2022; "
        "demografia.$pop_rua_pobreza; demografia.$pop_rua_br; "
        "demografia.$pop_rua_acima_br; demografia.$pop_rua_bolsaf_2022"
    )

    assert substituir_placeholders(texto, contexto, namespace="demografia") == (
        "caract_mun.593,0; 2; 1.042; 501; 541; 120; 60; 30; 30; 18"
    )


def test_demography_editorial_conditions_render_only_the_matching_blocks():
    texto = """Para quando demografia.$pop_ind_2022 for diferente de 0 e demografia.$pop_qui for igual a 0:
Tem indígenas, sem quilombolas.
Para quando demografia.$pop_ind_2010 for diferente de 0:
Também havia indígenas em 2010.
Para quando demografia.$pop_ind_2022 e demografia.$pop_qui for diferente de 0:
Tem os dois grupos.
Sequência do texto, sem condição:
Texto comum.
Para demografia.$centro_pop for igual a 0:
Sem Centro POP.
Para demografia.$centro_pop for igual a 1:
Com um Centro POP.
Para demografia.$centro_pop maior que 1:
Com vários Centros POP."""
    contexto = {
        "pop_ind_2022": 470,
        "pop_ind_2010": 579,
        "pop_qui": 0,
        "centros_pop": 1,
    }

    resultado = interpretar_blocos_condicionais(texto, contexto)

    assert "Tem indígenas, sem quilombolas." in resultado
    assert "Também havia indígenas em 2010." in resultado
    assert "Tem os dois grupos." not in resultado
    assert "Texto comum." in resultado
    assert "Com um Centro POP." in resultado
    assert "Sem Centro POP." not in resultado
    assert "Com vários Centros POP." not in resultado
    assert "Para quando" not in resultado


def test_social_development_gini_condition_renders_only_the_matching_branch():
    texto = """Síntese
Quando o índice de Gini for maior e igual a 0,5
desen_social.$nm_mun alcançou IDHM de desen_social.$idhm_2010, mas indica que desen_social.$nomesubindice3_2010 e desen_social.$analise_gini_2010 permanecem como os principais desafios do município.
Quando o índice de Gini for menor que 0,5
desen_social.$nm_mun alcançou IDHM de desen_social.$idhm_2010, mas indica que desen_social.$nomesubindice3_2010 permanece como o principal desafio do município."""

    contexto_desigual = {"nm_mun": "Canapi", "idhm_2010": 0.561, "gini_2010": 0.6}
    resultado_desigual = interpretar_blocos_condicionais(texto, contexto_desigual)
    assert "principais desafios" in resultado_desigual
    assert "principal desafio" not in resultado_desigual
    assert "Quando o índice de Gini" not in resultado_desigual

    contexto_igualitario = {"nm_mun": "Canapi", "idhm_2010": 0.561, "gini_2010": 0.4}
    resultado_igualitario = interpretar_blocos_condicionais(texto, contexto_igualitario)
    assert "principal desafio" in resultado_igualitario
    assert "principais desafios" not in resultado_igualitario


def test_social_development_gini_condition_hides_both_branches_without_data():
    texto = """Quando o índice de Gini for maior e igual a 0,5
Trecho com desigualdade.
Quando o índice de Gini for menor que 0,5
Trecho sem desigualdade."""

    resultado = interpretar_blocos_condicionais(texto, {"nm_mun": "Canapi"})

    assert "Trecho com desigualdade." not in resultado
    assert "Trecho sem desigualdade." not in resultado


def test_social_development_namespace_alias_before_dollar_is_replaced_without_prefix():
    contexto = {"nm_mun": "Canapi", "idhm_2010": 0.561}
    texto = "desen_social.$nm_mun alcançou IDHM de desen_social.$idhm_2010"

    assert substituir_placeholders(
        texto, contexto, namespace="desenvolvimento-social"
    ) == "Canapi alcançou IDHM de 0,6"


def test_hydraulics_namespace_alias_before_dollar_is_replaced_without_prefix():
    contexto = {"nm_mun": "Canapi"}
    texto = "seg_hidrica.$nm_mun"

    assert (
        substituir_placeholders(texto, contexto, namespace="hidraulica") == "Canapi"
    )


def test_demography_short_namespace_is_normalized():
    assert substituir_placeholders(
        "demo.$etaria_maior_per%", {"etaria_maior": 40, "pop_total": 100}, "demografia"
    ) == "40%"


def test_precision_suffix_overrides_the_default_one_decimal_rounding():
    contexto = {"nm_mun": "Canapi", "idhm_2010": 0.561, "gini_2010": 0.542}
    texto = (
        "desen_social.$nm_mun apresentou IDHM de desen_social.$idhm_2010:3 "
        "e Índice de Gini de desen_social.$gini_2010:3"
    )

    assert substituir_placeholders(
        texto, contexto, namespace="desenvolvimento-social"
    ) == "Canapi apresentou IDHM de 0,561 e Índice de Gini de 0,542"


def test_precision_suffix_does_not_leak_into_other_fields():
    contexto = {"idhm_2010": 0.561, "gini_2010": 0.542}
    texto = "desen_social.$idhm_2010:3 e Gini desen_social.$gini_2010"

    assert substituir_placeholders(
        texto, contexto, namespace="desenvolvimento-social"
    ) == "0,561 e Gini 0,5"


def test_social_development_gini_condition_accepts_para_prefix_and_ou_wording():
    texto = """Síntese
Para quando o índice de Gini for maior ou igual a 0,5:
Trecho com desigualdade.
Para quando o índice de Gini for menor que 0,5:
Trecho sem desigualdade."""

    resultado = interpretar_blocos_condicionais(texto, {"gini_2010": 0.6})

    assert "Trecho com desigualdade." in resultado
    assert "Trecho sem desigualdade." not in resultado
    assert "Para quando" not in resultado


def test_inline_figure_reference_is_replaced_with_the_real_figure_number():
    reset_figura_contador()
    texto = (
        "Nesse contexto, a maior concentração populacional indica algo (Figura x).\n"
        "\n"
        "Figura X- População por faixa etária e sexo."
    )

    html = texto_para_html(texto, {}, graficos_por_placeholder={})

    assert "(Figura 2)" in html
    assert "Figura 2 – População" in html
    assert "Figura x" not in html
    assert "Figura X" not in html


def test_multiple_inline_figure_mentions_in_one_paragraph_get_sequential_numbers():
    reset_figura_contador()
    texto = (
        "Os grupos prioritários somam as metas por público-alvo (Figura X), "
        "e entre as menores estão C (2%, Figura X).\n"
        "\n"
        "Figura X- Metas e doses aplicadas por público-alvo etário.\n"
        "\n"
        "Figura X- Taxa de cobertura vacinal por tipo de vacina."
    )

    html = texto_para_html(texto, {}, graficos_por_placeholder={})

    assert "(Figura 2)" in html
    assert "(2%, Figura 3)" in html
    assert "Figura 2 – Metas" in html
    assert "Figura 3 – Taxa" in html


def test_inline_figure_reference_regex_does_not_match_unrelated_words():
    reset_figura_contador()
    texto = "A figura da variação mostra crescimento. Como visto na Figura 2, o IDHM cresceu."

    html = texto_para_html(texto, {}, graficos_por_placeholder={})

    assert "A figura da variação mostra crescimento." in html
    assert "Como visto na Figura 2, o IDHM cresceu." in html


def test_single_asterisk_chart_placeholder_is_rendered():
    html = texto_para_html(
        "*grafico_faixa_etaria_e_sexo",
        {},
        namespace="demografia",
        graficos_por_placeholder={
            "grafico_faixa_etaria_e_sexo": "grafico_canapi.png"
        },
    )

    assert '<img src="/output/grafico_canapi.png"' in html
