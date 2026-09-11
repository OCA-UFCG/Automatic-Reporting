from utils.render.placeholders import interpretar_blocos_condicionais
from utils.render.renderer import (
    render_descricao_tema_html,
    reset_figura_contador,
    substituir_placeholders,
    texto_para_html,
)


def test_references_render_as_html_and_related_content_gets_boxed():
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

    # "Referências" não é uma das seções que ganham a caixa cinza — continua
    # como título solto, fora da caixa.
    assert "<h1>Referências</h1>" in html
    assert "IBGE, 2023." in html

    # "Conteúdos relacionados" (mesmo fora do descricao_tema, sobrando aqui
    # em texto_para_html) entra na mesma caixa cinza usada por
    # render_descricao_tema_html, com o cabeçalho <h3> e a lista dentro dela.
    assert '<div class="fontes-box">' in html
    assert '<h3 class="fontes-box-heading">Conteúdos relacionados</h3>' in html
    assert "<ul>" in html
    assert "https://example.com/relatorio" in html
    assert '<a href="https://example.com/relatorio">' in html


def test_fontes_box_from_texto_para_html_includes_the_explore_intro_row():
    texto = "#!Fontes\n\n[Painel: Quilombola](teste)\n"

    html = texto_para_html(texto, {}, namespace="demografia")

    assert '<div class="fontes-box-intro">' in html
    assert '<p class="fontes-box-intro-title">Continue explorando o tema</p>' in html
    assert '<a class="fonte-badge" href="teste"><strong>Painel:</strong> Quilombola</a>' in html


def test_fontes_always_comes_before_conteudos_relacionados_via_texto_para_html():
    # No Doc real, "Conteúdos relacionados" costuma vir ANTES de "Fontes" —
    # a caixa precisa reordenar para "Fontes" primeiro de qualquer forma.
    texto = (
        "#!Conteúdos relacionados\n\n"
        "[Painel: Terceira Idade](https://example.com/a)\n\n"
        "#!Fontes\n\n"
        "[Painel: Quilombola](https://example.com/b)\n"
    )

    html = texto_para_html(texto, {}, namespace="demografia")

    posicao_fontes = html.index('<h3 class="fontes-box-heading">Fontes</h3>')
    posicao_conteudos = html.index('<h3 class="fontes-box-heading">Conteúdos relacionados</h3>')
    assert posicao_fontes < posicao_conteudos


def test_fontes_and_related_content_render_from_real_doc_markup():
    texto = """#!Conteúdos relacionados

Para saber mais sobre este tema, consulte os seguintes conteúdos do Data Nordeste:

demografia.“$nm_datastory1” = https://datanordeste.sudene.gov.br/data-stories/f7d447d1017f4bf58270abba6919a9eb
[Painel: Terceira Idade] (https://datanordeste.sudene.gov.br/boletim/22yf24FX8jtrU80GS0u8el)
[Painel: População Negra](https://datanordeste.sudene.gov.br/boletim/7CMfPnYZJ4cNXYzAjQZteh)
[Painel: População Indígena](https://datanordeste.sudene.gov.br/boletim/2DEQ99895tKRWlFQxDpJp7)

#!Fontes

Os dados deste relatório foram extraídos dos seguintes painéis do Data Nordeste:

[Painel:  Perfil Demográfico]
(https://datanordeste.sudene.gov.br/data-panel/populacao)

[Painel: Quilombola](teste)
[Painel: Indígenas](teste)
[Painel: População em situação de rua](teste)
"""

    contexto = {"nm_datastory1": "Estabelecimentos de saúde"}
    partes = render_descricao_tema_html(texto, contexto, namespace="demografia")

    assert len(partes) == 1
    caixa = partes[0]
    assert caixa.startswith('<div class="fontes-box-wrap"><div class="fontes-box">')
    assert caixa.count('<h3 class="fontes-box-heading">Conteúdos relacionados</h3>') == 1
    assert caixa.count('<h3 class="fontes-box-heading">Fontes</h3>') == 1

    # A linha "Continue explorando o tema" (com QR code) mora dentro da mesma
    # caixa cinza, uma única vez, antes dos dois cabeçalhos.
    assert caixa.count('<div class="fontes-box-intro">') == 1
    assert '<p class="fontes-box-intro-title">Continue explorando o tema</p>' in caixa
    assert 'class="fontes-box-intro-qr"' in caixa
    # "Fontes" sempre aparece antes de "Conteúdos relacionados" na caixa,
    # mesmo quando o Doc traz "Conteúdos relacionados" primeiro (como aqui).
    posicao_intro = caixa.index('<div class="fontes-box-intro">')
    posicao_fontes = caixa.index('<h3 class="fontes-box-heading">Fontes</h3>')
    posicao_conteudos = caixa.index('<h3 class="fontes-box-heading">Conteúdos relacionados</h3>')
    assert posicao_intro < posicao_fontes < posicao_conteudos

    assert "Para saber mais sobre este tema" in caixa
    assert "Os dados deste relatório foram extraídos" in caixa

    assert (
        '<a class="fonte-badge" '
        'href="https://datanordeste.sudene.gov.br/data-stories/f7d447d1017f4bf58270abba6919a9eb">'
        '<strong>Narrativa de dados:</strong> Estabelecimentos de saúde</a>'
    ) in caixa
    assert (
        '<a class="fonte-badge" '
        'href="https://datanordeste.sudene.gov.br/boletim/22yf24FX8jtrU80GS0u8el">'
        '<strong>Painel:</strong> Terceira Idade</a>'
    ) in caixa
    assert (
        '<a class="fonte-badge" '
        'href="https://datanordeste.sudene.gov.br/boletim/7CMfPnYZJ4cNXYzAjQZteh">'
        '<strong>Painel:</strong> População Negra</a>'
    ) in caixa
    assert (
        '<a class="fonte-badge" '
        'href="https://datanordeste.sudene.gov.br/data-panel/populacao">'
        '<strong>Painel:</strong> Perfil Demográfico</a>'
    ) in caixa
    assert '<a class="fonte-badge" href="teste"><strong>Painel:</strong> Quilombola</a>' in caixa
    assert '<a class="fonte-badge" href="teste"><strong>Painel:</strong> Indígenas</a>' in caixa
    assert (
        '<a class="fonte-badge" href="teste">'
        '<strong>Painel:</strong> População em situação de rua</a>'
    ) in caixa


def test_narrativa_de_dados_badge_is_skipped_when_the_placeholder_has_no_value():
    texto = """#!Conteúdos relacionados

demografia.$nm_datastory1 = https://example.com/data-story
"""
    partes = render_descricao_tema_html(texto, {}, namespace="demografia")

    assert len(partes) == 1
    caixa = partes[0]
    assert "fonte-badge" not in caixa
    assert "nm_datastory1" not in caixa


def test_fontes_box_opened_with_hash_bang_heading_closes_before_a_later_regular_heading():
    texto = """#!Fontes

[Painel: Quilombola](teste)

#! Próximo tema

Texto qualquer.
"""

    partes = render_descricao_tema_html(texto, {}, namespace="demografia")

    assert len(partes) == 3
    assert partes[0].startswith('<div class="fontes-box-wrap"><div class="fontes-box">')
    assert '<h2 class="theme-detail-heading">Próximo tema</h2>' in partes[1]
    assert "Texto qualquer." in partes[2]


def test_heading_marker_does_not_require_a_space():
    html = texto_para_html("#!Alguma seção", {}, namespace="demografia")
    assert html == "<h1>Alguma seção</h1>"


def test_fontes_heading_marker_without_a_space_still_opens_the_box():
    html = texto_para_html("#!Fontes", {}, namespace="demografia")
    assert '<h3 class="fontes-box-heading">Fontes</h3>' in html


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

    # Namespace de outra view (caract_mun.$area) resolve e consome o prefixo,
    # em vez de deixar "caract_mun." órfão antes do valor.
    assert substituir_placeholders(texto, contexto, namespace="demografia") == (
        "593,0; 2; 1.042; 501; 541; 120; 60; 30; 30; 18"
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


def test_demography_street_population_2022_only_skips_2026_comparison():
    texto = """Sequência do texto, sem condição:
Outro grupo relevante para a caracterização da população municipal é o de pessoas em situação de rua. Em 2026, demografia.$nm_mun registra demografia.$pop_rua_2026 pessoas nessa condição, frente a demografia.$pop_rua_2022 em 2022, evidenciando um demografia.$var_pop_rua_analise de demografia.$var_pop_rua_abs no período."""

    contexto = {
        "nm_mun": "Cidade X",
        "pop_rua_total": 80,
        "pobreza_cadunico": 20,
        "baixa_renda_cadunico": 30,
        "acima_meio_sm_cadunico": 30,
        "familias_rua_bf": 12,
        # como calculado por buscar_populacao_rua quando familias_total > 0
        "pop_rua_pobreza_per": 25.0,
        "pop_rua_br_per": 37.5,
        "pop_rua_acima_br_per": 37.5,
    }

    interpretado = interpretar_blocos_condicionais(texto, contexto)
    resultado = substituir_placeholders(interpretado, contexto, namespace="demografia")

    assert "$pop_rua_2026" not in resultado
    assert "$var_pop_rua" not in resultado
    assert "Em 2022, Cidade X registrava 80 pessoas" in resultado
    assert "Ainda não há levantamento mais recente (2026)" in resultado


def test_demography_missing_centro_pop_does_not_render_as_zero():
    texto = """Sequência do texto, sem condição:
Outro grupo relevante para a caracterização da população municipal é o de pessoas em situação de rua. Em 2026, demografia.$nm_mun registra demografia.$pop_rua_2026 pessoas.
Para demografia.$centro_pop for igual a 0:
Sem Centro POP.
Para demografia.$centro_pop for igual a 1:
Com um Centro POP.
Para demografia.$centro_pop maior que 1:
Com vários Centros POP."""

    # centro_pop ausente do contexto (NULL no banco, sem alias "centros_pop"),
    # mas com dados de rua presentes: não pode afirmar "Sem Centro POP.".
    contexto = {"nm_mun": "Cidade X", "pop_rua_2022": 40, "pop_rua_2026": 50}
    resultado = interpretar_blocos_condicionais(texto, contexto)

    assert "Sem Centro POP." not in resultado
    assert "Com um Centro POP." not in resultado
    assert "Com vários Centros POP." not in resultado


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


def test_inline_reference_to_an_already_numbered_figure_is_not_rewritten():
    reset_figura_contador()
    texto = (
        "Como já demonstrado na Figura 1, a concentração populacional é maior "
        "na região central.\n"
        "\n"
        "Figura X- População por faixa etária e sexo."
    )

    html = texto_para_html(texto, {}, graficos_por_placeholder={})

    assert "Como já demonstrado na Figura 1," in html
    assert "Figura 2 – População" in html


def test_demography_short_namespace_swapped_dollar_typo_is_normalized():
    assert substituir_placeholders(
        "demo$.etaria_maior_per%", {"etaria_maior": 40, "pop_total": 100}, "demografia"
    ) == "40%"


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


def test_inline_figure_mentions_in_different_paragraphs_get_sequential_numbers():
    reset_figura_contador()
    texto = (
        "Os grupos prioritários somam as metas por público-alvo (Figura X).\n"
        "\n"
        "Figura X- Metas e doses aplicadas por público-alvo etário.\n"
        "\n"
        "Entre as menores estão C, com 2% (Figura X).\n"
        "\n"
        "Figura X- Taxa de cobertura vacinal por tipo de vacina."
    )

    html = texto_para_html(texto, {}, graficos_por_placeholder={})

    assert "(Figura 2)" in html
    assert "com 2% (Figura 3)" in html
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


def test_single_field_zero_one_many_condition_renders_only_the_matching_block():
    """Mesmo padrão 0/1/>1 do centro_pop (demografia), aplicado a um campo
    genérico de outro macrotema (n_uc, de meio-ambiente) — a checagem de
    NULL não deve ficar restrita ao nome 'centro_pop'."""
    texto = """Para meio-ambiente.$n_uc for igual a 0:
Sem UC.
Para meio-ambiente.$n_uc for igual a 1:
Com uma UC.
Para meio-ambiente.$n_uc maior que 1:
Com várias UCs."""

    resultado_zero = interpretar_blocos_condicionais(texto, {"n_uc": 0})
    assert "Sem UC." in resultado_zero
    assert "Com uma UC." not in resultado_zero
    assert "Com várias UCs." not in resultado_zero

    resultado_uma = interpretar_blocos_condicionais(texto, {"n_uc": 1})
    assert "Com uma UC." in resultado_uma

    resultado_varias = interpretar_blocos_condicionais(texto, {"n_uc": 3})
    assert "Com várias UCs." in resultado_varias

    # n_uc ausente do contexto (NULL no banco): nenhum bloco pode afirmar
    # "zero" só porque o valor ausente foi coagido para 0.
    resultado_sem_dado = interpretar_blocos_condicionais(texto, {})
    assert "Sem UC." not in resultado_sem_dado
    assert "Com uma UC." not in resultado_sem_dado
    assert "Com várias UCs." not in resultado_sem_dado


def test_range_and_generic_threshold_operators_pick_the_matching_block():
    """meio-ambiente precisa de faixas ("de 2 a 4") e limiares genéricos
    ("maior ou igual a 5") além dos operadores fixos originais (0/1/>1)."""
    texto = """Para meio-ambiente.$n_uc for de 2 a 4 e meio-ambiente.$n_protecao_us for igual a 0:
De 2 a 4, só Proteção Integral.
Para meio-ambiente.$n_uc for de 2 a 4 e meio-ambiente.$n_protecao_pi for igual a 0:
De 2 a 4, só Uso Sustentável.
Para meio-ambiente.$n_uc for de 2 a 4 e meio-ambiente.$n_protecao_pi for diferente de 0 e meio-ambiente.$n_protecao_us for diferente de 0:
De 2 a 4, os dois grupos.
Para meio-ambiente.$n_uc for maior ou igual a 5:
Cinco ou mais."""

    so_pi = interpretar_blocos_condicionais(
        texto, {"n_uc": 3, "n_protecao_pi": 3, "n_protecao_us": 0}
    )
    assert "De 2 a 4, só Proteção Integral." in so_pi
    assert "De 2 a 4, só Uso Sustentável." not in so_pi
    assert "De 2 a 4, os dois grupos." not in so_pi
    assert "Cinco ou mais." not in so_pi

    so_us = interpretar_blocos_condicionais(
        texto, {"n_uc": 3, "n_protecao_pi": 0, "n_protecao_us": 3}
    )
    assert "De 2 a 4, só Uso Sustentável." in so_us

    dois_grupos = interpretar_blocos_condicionais(
        texto, {"n_uc": 4, "n_protecao_pi": 2, "n_protecao_us": 2}
    )
    assert "De 2 a 4, os dois grupos." in dois_grupos

    cinco_ou_mais = interpretar_blocos_condicionais(
        texto, {"n_uc": 8, "n_protecao_pi": 3, "n_protecao_us": 5}
    )
    assert "Cinco ou mais." in cinco_ou_mais
    assert "De 2 a 4" not in cinco_ou_mais


def test_caption_is_dropped_when_its_chart_was_not_generated():
    # Municípios sem comércio exterior não geram o gráfico de países, e a
    # legenda ficava órfã no relatório (4 imagens para 6 legendas em Anadia/AL).
    reset_figura_contador()
    texto = (
        "%%grafico_fob\n"
        "\n"
        "\n"
        "Figura X- Destinos das importações ordenados pelo valor líquido FOB.\n"
        "\n"
        "%%grafico_balanca\n"
        "\n"
        "Figura X- Visão mensal da balança comercial."
    )

    html = texto_para_html(
        texto, {}, graficos_por_placeholder={"grafico_balanca": "balanca.png"}
    )

    assert "Destinos das importações" not in html
    # A legenda suprimida não consome número: a balança continua sendo a 2.
    assert "Figura 2 – Visão mensal da balança comercial." in html
    assert "balanca.png" in html


def test_caption_is_kept_when_its_chart_exists():
    reset_figura_contador()
    texto = (
        "%%grafico_fob\n"
        "\n"
        "\n"
        "Figura X- Destinos das importações ordenados pelo valor líquido FOB."
    )

    html = texto_para_html(
        texto, {}, graficos_por_placeholder={"grafico_fob": "fob.png"}
    )

    assert "Figura 2 – Destinos das importações" in html
    assert "fob.png" in html


def test_caption_without_any_chart_marker_is_still_rendered():
    # A legenda do mapa e outras sem marcador não podem ser afetadas pela
    # supressão — ela só vale para a legenda imediatamente após um marcador.
    reset_figura_contador()
    texto = (
        "%%grafico_fob\n"
        "\n"
        "Um parágrafo qualquer entre o marcador e a legenda.\n"
        "\n"
        "Figura X- Localização do município."
    )

    html = texto_para_html(texto, {}, graficos_por_placeholder={})

    assert "Figura 2 – Localização do município." in html


def test_caption_is_dropped_even_when_rendered_in_a_separate_call():
    # render_descricao_tema_html quebra o texto por linha em branco e chama
    # texto_para_html uma vez por parágrafo, então marcador e legenda chegam em
    # chamadas distintas sempre que há linha em branco entre eles no Doc.
    reset_figura_contador()

    html_marcador = texto_para_html("%%grafico_fob", {}, graficos_por_placeholder={})
    html_legenda = texto_para_html(
        "Figura X- Destinos das importações ordenados pelo valor líquido FOB.",
        {},
        graficos_por_placeholder={},
    )

    assert "Destinos das importações" not in html_marcador + html_legenda


def test_supression_does_not_leak_past_an_intervening_paragraph_across_calls():
    reset_figura_contador()

    texto_para_html("%%grafico_fob", {}, graficos_por_placeholder={})
    texto_para_html("Um parágrafo qualquer no meio.", {}, graficos_por_placeholder={})
    html = texto_para_html(
        "Figura X- Localização do município.", {}, graficos_por_placeholder={}
    )

    assert "Figura 2 – Localização do município." in html
