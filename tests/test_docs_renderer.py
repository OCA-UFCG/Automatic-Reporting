from utils.render.placeholders import interpretar_blocos_condicionais
from utils.render.renderer import substituir_placeholders, texto_para_html


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


def test_demography_missing_street_population_data_falls_back_to_no_records_text():
    texto = """Sequência do texto, sem condição:
Outro grupo relevante para a caracterização da população municipal é o de pessoas em situação de rua. Em 2026, demografia.$nm_mun registra demografia.$pop_rua_2026 pessoas.
Para demografia.$centro_pop for igual a 0:
Sem Centro POP.
Para demografia.$centro_pop for igual a 1:
Com um Centro POP.
Para demografia.$centro_pop maior que 1:
Com vários Centros POP."""

    resultado_sem_dados = interpretar_blocos_condicionais(texto, {"nm_mun": "Belo Monte"})
    assert "demografia.$pop_rua_2026" not in resultado_sem_dados
    assert "Não foram encontrados registros de pessoas em situação de rua" in resultado_sem_dados
    assert "Belo Monte" in resultado_sem_dados
    assert "Centro POP." not in resultado_sem_dados

    contexto_com_dados = {"nm_mun": "Cidade X", "pop_rua_2022": 40, "pop_rua_2026": 50, "centro_pop": 1}
    resultado_com_dados = interpretar_blocos_condicionais(texto, contexto_com_dados)
    assert "demografia.$pop_rua_2026 pessoas" in resultado_com_dados
    assert "Não foram encontrados registros de pessoas em situação de rua" not in resultado_com_dados
    assert "Com um Centro POP." in resultado_com_dados


def test_demography_editorial_conditions_close_2010_block_with_autodeclarada_wording():
    texto = """Para quando demografia.$pop_ind_2022 e demografia.$pop_qui for diferente de 0:
Tem os dois grupos.
Para quando demografia.$pop_ind_2010 for diferente de 0:
Também havia indígenas em 2010.
Para quando demografia.$pop_ind_2010 for igual a 0:
Não havia indígenas em 2010.

Quanto à população autodeclarada quilombola em 2022, havia quilombolas."""
    contexto = {
        "pop_ind_2022": 470,
        "pop_ind_2010": 579,
        "pop_qui": 30,
    }

    resultado = interpretar_blocos_condicionais(texto, contexto)

    assert "Tem os dois grupos." in resultado
    assert "Também havia indígenas em 2010." in resultado
    assert "Não havia indígenas em 2010." not in resultado
    # A última condição interna avaliada ("igual a 0") não é atendida, o que
    # antes desta correção deixava bloco_ativo=False e escondia o parágrafo
    # de fechamento — mesmo ele não fazendo parte do sub-bloco de 2010.
    assert "Quanto à população autodeclarada quilombola em 2022, havia quilombolas." in resultado


def test_demography_short_namespace_is_normalized():
    assert substituir_placeholders(
        "demo.$etaria_maior_per%", {"etaria_maior": 40, "pop_total": 100}, "demografia"
    ) == "40%"


def test_demography_short_namespace_swapped_dollar_typo_is_normalized():
    assert substituir_placeholders(
        "demo$.etaria_maior_per%", {"etaria_maior": 40, "pop_total": 100}, "demografia"
    ) == "40%"


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
