from utils.render.placeholders import interpretar_blocos_condicionais
from utils.render.renderer import (
    render_descricao_tema_html,
    reset_figura_contador,
    substituir_placeholders,
    texto_para_html,
)


def test_novas_condicoes_demografia_com_markdown_e_comparacoes():
    texto = """**Para quando** demografia.$dif\\_etaria\\_09\\_60 **for positivo, então :**
Mais crianças.

**Para quando** demografia.$dif\\_etaria\\_09\\_60 **for negativo, então :**
Mais idosos.

**Para quando** demografia.$cres\\_pop\\_analise **for 0%, então:**
População estável.

**Para quando** demografia.$cres\\_pop\\_analise for maior ou menor que 0%**, então:**
População mudou.

**Para quando demografia.$pop\\_rua\\_2022 for 0 em 2022; demografia.$pop\\_rua\\_2026 for > 1 e demografia.$pop\\_familias\\_rua\\_2026 = demografia.$pop\\_rua\\_bolsaf\\_2026:**
Todas as famílias recebem.

**Para quando demografia.$pop\\_rua\\_2022 for 0 em 2022; demografia.$pop\\_rua\\_2026 for > 1 e demografia.$pop\\_familias\\_rua\\_2026 for 0:**
Não há famílias.
"""
    contexto = {
        "dif_etaria_09_60": -20,
        "cres_pop": 0,
        "pop_rua_2022": 0,
        "pop_rua_2026": 3,
        "familias_rua_total": 2,
        "familias_rua_bf": 2,
    }
    resultado = interpretar_blocos_condicionais(texto, contexto)
    assert "Mais crianças." in resultado
    assert "Mais idosos." not in resultado
    assert "População estável." in resultado
    assert "População mudou." not in resultado
    assert "Todas as famílias recebem." in resultado
    assert "Não há famílias." not in resultado
    assert "Para quando" not in resultado


def test_novas_condicoes_rua_nao_tratam_dado_ausente_como_zero():
    texto = """Para quando demografia.$pop_rua_2022 e demografia.$pop_rua_2026 for 0:
Sem registros nos dois anos.

Para quando demografia.$pop_rua_2022 for >=1 e demografia.$pop_rua_2026 for 0:
Houve redução a zero.
"""
    assert "Sem registros" not in interpretar_blocos_condicionais(texto, {})
    assert "Houve redução" not in interpretar_blocos_condicionais(texto, {})
    assert "Sem registros" in interpretar_blocos_condicionais(
        texto, {"pop_rua_2022": 0, "pop_rua_2026": 0}
    )
    assert "Houve redução" in interpretar_blocos_condicionais(
        texto, {"pop_rua_2022": 2, "pop_rua_2026": 0}
    )


def test_condicao_todas_as_familias_nao_casa_com_zero_familias():
    texto = """Para quando demografia.$pop_rua_2022 for 0; demografia.$pop_rua_2026 for > 1 e demografia.$pop_familias_rua_2026 = demografia.$pop_rua_bolsaf_2026:
Todas recebem.

Para quando demografia.$pop_rua_2022 for 0; demografia.$pop_rua_2026 for > 1 e demografia.$pop_familias_rua_2026 for 0:
Não há famílias.
"""
    resultado = interpretar_blocos_condicionais(
        texto,
        {"pop_rua_2022": 0, "pop_rua_2026": 3, "familias_rua_total": 0, "familias_rua_bf": 0},
    )
    assert "Todas recebem." not in resultado
    assert "Não há famílias." in resultado


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


def test_frase_orfa_sem_linha_em_branco_junta_no_paragrafo_anterior():
    # Quebra de linha solta (Shift+Enter no Doc, sem linha em branco antes)
    # deixando só uma frase na segunda linha: não deve virar <p> isolado.
    texto = (
        "Primeira frase do parágrafo, com bastante contexto.\n"
        "Segunda frase, órfã."
    )

    html = texto_para_html(texto, {}, namespace="demografia")

    assert html.count("<p>") == 1
    assert (
        "<p>Primeira frase do parágrafo, com bastante contexto. "
        "Segunda frase, órfã.</p>" == html
    )


def test_frase_com_linha_em_branco_antes_nao_e_mesclada():
    # Quando há linha em branco separando, é mesmo um novo parágrafo — não
    # deve ser colado no anterior mesmo sendo uma frase só.
    texto = (
        "Primeira frase do parágrafo, com bastante contexto.\n"
        "\n"
        "Segunda frase, em parágrafo próprio."
    )

    html = texto_para_html(texto, {}, namespace="demografia")

    assert html.count("<p>") == 2


def test_linha_de_condicionante_nao_reconhecida_nao_e_mesclada_no_paragrafo_anterior():
    # Se uma linha "Para quando ...:" escapa de interpretar_blocos_condicionais
    # (ex.: por não conter um "$campo" reconhecido), ela termina em ":" — não
    # deve ser tratada como frase única e colada no parágrafo visível acima.
    texto = (
        "Primeira frase do parágrafo, com bastante contexto.\n"
        "Para quando alguma condição não reconhecida:"
    )

    html = texto_para_html(texto, {}, namespace="demografia")

    assert html.count("<p>") == 2
    assert "contexto. Para quando" not in html


def test_linha_de_condicionante_nao_reconhecida_antes_do_paragrafo_nao_recebe_merge():
    # Espelho do teste acima: a condicionante vindo ANTES (ela mesma termina
    # em ":", nunca em pontuação de frase) também não pode "receber" a frase
    # de baixo colada nela — regressão de um bug que a correção acima, sozinha,
    # não fechava (só validava a linha que entra, não a que já estava lá).
    texto = (
        "Para efeito de análise:\n"
        "O município registrou crescimento populacional."
    )

    html = texto_para_html(texto, {}, namespace="demografia")

    assert html.count("<p>") == 2
    assert "análise: O município" not in html


def test_frase_indentada_nao_e_mesclada_e_mantem_o_recuo():
    # utils/external/docs.py preserva indentação (tab/4+ espaços) como sinal
    # editorial explícito — não é ruído de Shift+Enter, não deve ser colada.
    texto = (
        "Parágrafo normal com contexto suficiente.\n"
        "\tFrase indentada única."
    )

    html = texto_para_html(texto, {}, namespace="demografia")

    assert html.count("<p") == 2
    assert '<p style="text-indent: 32px;">Frase indentada única.</p>' in html


def test_abreviacao_comum_nao_desliga_o_merge():
    # "art." não fecha frase de verdade — sem tratar isso, a linha seguinte
    # parece ter "mais de uma frase" e o merge é desligado em silêncio.
    texto = (
        "Texto base com contexto suficiente para o teste.\n"
        "Conforme o art. 5º, isso vale."
    )

    html = texto_para_html(texto, {}, namespace="demografia")

    assert html.count("<p>") == 1
    assert "Conforme o art. 5º, isso vale.</p>" in html


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


def test_source_badge_label_comes_from_the_placeholder_name():
    """O tipo do conteúdo vem do nome do campo ($nm_boletim/$nm_datastory/
    $nm_painel); antes dessa distinção todos saíam como "Narrativa de dados"."""
    texto = """#!Conteúdos relacionados

demografia.“$nm_datastory1” = https://datanordeste.sudene.gov.br/data-stories/f7d447d1
demografia.“$nm_boletim1” = https://datanordeste.sudene.gov.br/boletim/22yf24FX8

#!Fontes

demografia.“$nm_painel1” = https://datanordeste.sudene.gov.br/data-panel/populacao
"""
    contexto = {
        "nm_datastory1": "Estabelecimentos de saúde",
        "nm_boletim1": "Terceira Idade",
        "nm_painel1": "População",
    }

    caixa = "".join(render_descricao_tema_html(texto, contexto, namespace="demografia"))

    assert (
        '<a class="fonte-badge" href="https://datanordeste.sudene.gov.br/data-stories/f7d447d1">'
        "<strong>Narrativa de dados:</strong> Estabelecimentos de saúde</a>"
    ) in caixa
    assert (
        '<a class="fonte-badge" href="https://datanordeste.sudene.gov.br/boletim/22yf24FX8">'
        "<strong>Boletim:</strong> Terceira Idade</a>"
    ) in caixa
    assert (
        '<a class="fonte-badge" href="https://datanordeste.sudene.gov.br/data-panel/populacao">'
        "<strong>Painel de dados:</strong> População</a>"
    ) in caixa


def test_source_badge_label_accepts_field_names_without_the_nm_prefix():
    """O Doc de economia-renda usa "$painel1"/"$boletim1", sem "nm_"."""
    texto = """#!Fontes

economia.“$painel1” =  https://datanordeste.sudene.gov.br/data-panel/pib

economia.“$boletim1” = https://datanordeste.sudene.gov.br/boletim/4stpvtz
"""
    contexto = {"painel1": "Produto Interno Bruto", "boletim1": "Emprego e Renda"}

    caixa = "".join(render_descricao_tema_html(texto, contexto, namespace="economia-renda"))

    assert "<strong>Painel de dados:</strong> Produto Interno Bruto</a>" in caixa
    assert "<strong>Boletim:</strong> Emprego e Renda</a>" in caixa


def test_source_badge_label_falls_back_to_the_url_when_the_field_name_says_nothing():
    texto = """#!Fontes

demografia.“$conteudo1” = https://datanordeste.sudene.gov.br/boletim/22yf24FX8
"""
    contexto = {"conteudo1": "Terceira Idade"}

    caixa = "".join(render_descricao_tema_html(texto, contexto, namespace="demografia"))

    assert "<strong>Boletim:</strong> Terceira Idade</a>" in caixa


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


def test_demography_persistent_gate_with_inline_content_does_not_leak_next_paragraph():
    # Bloco persistente (indígena/quilombola) com texto colado na mesma
    # linha do "Para quando ...:". O reset de bloco_ativo=True após o
    # conteúdo inline não pode ignorar que o bloco é persistente — senão o
    # parágrafo seguinte vaza mesmo com a condição falsa.
    texto = (
        "Para quando demografia.$pop_ind_2022 for 0 e demografia.$pop_qui for 0: "
        "texto inline.\n"
        "Parágrafo seguinte que só deveria aparecer se o bloco continuasse ativo."
    )
    contexto = {"pop_ind_2022": 0, "pop_qui": 5}

    resultado = interpretar_blocos_condicionais(texto, contexto)

    assert "Parágrafo seguinte" not in resultado


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


def test_dead_leading_condition_does_not_swallow_the_fontes_marker():
    # A primeira condicional do cascateamento fica órfã depois que
    # extrair_descricao_tema varre o "descricao_tema =" que a segue (ver
    # utils/external/docs.py) — sobra só o "Para quando ...:" colado, com
    # linhas em branco, direto em cima de "#!Fontes". Se essa condição for
    # falsa para a cidade, "#!Fontes" era lido como o conteúdo guardado por
    # ela e sumia (PR #116).
    texto = (
        "Para quando seg_hidrica.$total_2025 for igual a 0, então:\n"
        "\n\n\n"
        "#!Fontes\n"
        "\n\n"
        "[Painel de dados: Cisternas](https://example.com/cisternas)\n"
    )
    contexto = {"total_2025": 1101}

    resultado = interpretar_blocos_condicionais(texto, contexto)

    assert "#!Fontes" in resultado
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
    ) == "Canapi alcançou IDHM de 0,561"


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


def test_demography_street_population_fallback_survives_guarded_conditions():
    # O Doc novo (PR #112) passou a guardar cada parágrafo de "situação de
    # rua" com sua própria condicional "Para quando ...:", em vez do
    # parágrafo único "sem condição" de antes. Ver a mera presença dessas
    # condicionais no Doc não pode desligar o fallback genérico pro resto do
    # documento quando nenhuma delas de fato bate — antes bastava passar por
    # UMA condicional de rua (batendo ou não) pra apagar o tópico inteiro.
    texto = """Para quando demografia.$pop_rua_2022 e demografia.$pop_rua_2026 for 0:
Outro grupo relevante para a caracterização da população municipal é o de pessoas em situação de rua. Não havia registros.

Para quando demografia.$pop_rua_2022 for >=1 e demografia.$pop_rua_2026 for 0:
Outro grupo relevante para a caracterização da população municipal é o de pessoas em situação de rua. Redução frente a 2022."""

    # Município nunca pesquisado (nem 2022 nem 2026): nenhuma das duas
    # condições bate — o fallback "não foram encontrados registros" precisa
    # aparecer, não pode sumir o tópico inteiro.
    resultado = interpretar_blocos_condicionais(texto, {"nm_mun": "Cidade Nova"})
    assert "Não foram encontrados registros de pessoas em situação de rua" in resultado
    assert "Cidade Nova" in resultado

    # Uma das condições realmente bate: o parágrafo condicional real aparece,
    # sem duplicar com o fallback.
    resultado_bate = interpretar_blocos_condicionais(
        texto, {"nm_mun": "Cidade X", "pop_rua_2022": 0, "pop_rua_2026": 0}
    )
    assert "Não havia registros." in resultado_bate
    assert "Não foram encontrados registros de pessoas em situação de rua" not in resultado_bate


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
    # `populacao_2010` fica fora de qualquer rede de segurança de precisão,
    # então continua no padrão de 1 casa — prova que o `:3` do campo vizinho
    # não vazou pra ele.
    contexto = {"idhm_2010": 0.561, "populacao_2010": 630.03}
    texto = "desen_social.$idhm_2010:3 e População desen_social.$populacao_2010"

    assert substituir_placeholders(
        texto, contexto, namespace="desenvolvimento-social"
    ) == "0,561 e População 630,0"


def test_renda_per_capita_usa_duas_casas_mesmo_sem_sufixo_no_doc():
    # Mesma classe de bug do IDHM/Gini: o Doc perdeu o `:2` de `$renda_2010`
    # (campo monetário) na mesma edição que perdeu o `:3` do IDHM/Gini.
    contexto = {"renda_2010": 630.03}
    texto = "R$desen_social.$renda_2010"

    assert (
        substituir_placeholders(texto, contexto, namespace="desenvolvimento-social")
        == "R$630,03"
    )


def test_precisao_padrao_editorial_nao_vaza_pra_outro_macrotema():
    # A rede de segurança é escopada por namespace: um campo `gini_urbano`
    # hipotético em economia-renda não deve herdar as 3 casas do Gini de
    # desenvolvimento social só por coincidência de prefixo.
    contexto = {"gini_urbano": 0.542}
    texto = "economia.$gini_urbano"

    assert (
        substituir_placeholders(texto, contexto, namespace="economia-renda")
        == "0,5"
    )


def test_idhm_gini_e_subindices_usam_tres_casas_mesmo_sem_sufixo_no_doc():
    # Rede de segurança: se o `:3` sumir do Doc (como já aconteceu na prática),
    # esses campos não caem pro padrão de 1 casa que corta a precisão do IDHM/
    # Gini e arrisca confundir o leitor perto de um limiar de Síntese.
    contexto = {
        "idhm_2010": 0.770,
        "gini_2010": 0.502,
        "subindice1_2010": 0.843,
    }
    texto = (
        "desen_social.$idhm_2010, desen_social.$gini_2010, "
        "desen_social.$subindice1_2010"
    )

    assert substituir_placeholders(
        texto, contexto, namespace="desenvolvimento-social"
    ) == "0,770, 0,502, 0,843"


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


def test_container_do_grafico_usa_margem_inferior_reduzida():
    # Regressão: com `margin:32px 0`, a margem cheia do contêiner somava à
    # margin-top da própria legenda (.figure-caption) e sobravam ~43px entre
    # o gráfico e o texto que o descreve.
    reset_figura_contador()
    texto = "%%grafico_teste\n\nFigura X- Legenda de teste."

    html = texto_para_html(
        texto, {}, graficos_por_placeholder={"grafico_teste": "grafico_teste.png"}
    )

    assert "margin:32px 0 8px;" in html


def test_inline_figure_reference_nao_casa_artigo_de_uma_letra():
    # Regressão: com `(?i)` no padrão, `[A-Zx]` casava minúsculas e frases como
    # "a figura a seguir" viravam "Figura N seguir" no meio do parágrafo.
    reset_figura_contador()
    texto = (
        "Como mostra a figura a seguir, e também a figura e o mapa ao lado, "
        "na figura o padrão se mantém.\n"
        "\n"
        "Figura X- População por faixa etária e sexo."
    )

    html = texto_para_html(texto, {}, graficos_por_placeholder={})

    assert "a figura a seguir" in html
    assert "a figura e o mapa ao lado" in html
    assert "na figura o padrão" in html
    assert "Figura 2 – População" in html


def test_inline_figure_reference_accepts_any_uppercase_letter_placeholder():
    reset_figura_contador()
    texto = (
        "Primeiro trecho com um dado (Figura X).\n"
        "\n"
        "Figura X- Legenda da primeira figura.\n"
        "\n"
        "Segundo trecho com outro dado (Figura Y).\n"
        "\n"
        "Figura Y- Legenda da segunda figura.\n"
        "\n"
        "Terceiro trecho com mais um dado (Figura Z).\n"
        "\n"
        "Figura Z- Legenda da terceira figura."
    )

    html = texto_para_html(texto, {}, graficos_por_placeholder={})

    assert "(Figura 2)" in html
    assert "(Figura 3)" in html
    assert "(Figura 4)" in html
    assert "Figura 2 – Legenda da primeira" in html
    assert "Figura 3 – Legenda da segunda" in html
    assert "Figura 4 – Legenda da terceira" in html
    assert "Figura Y" not in html
    assert "Figura Z" not in html


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


def test_aridez_condition_count_picks_the_matching_block():
    """meio-ambiente descreve 1, 2 ou 3 classes de aridez presentes em 1991.
    Não existe operador de "contagem" no motor — a regra editorial expressa
    isso como uma cadeia de "diferente de 0"/"igual a 0" sobre os três
    campos ordenados (aridez_cond1..3_area1991), do mesmo jeito que as
    faixas de UC acima."""
    texto = """Para meio-ambiente.$aridez_cond1_area1991 for igual a 0:
Sem dados de aridez.
Para meio-ambiente.$aridez_cond1_area1991 for diferente de 0 e meio-ambiente.$aridez_cond2_area1991 for igual a 0:
Uma condição de aridez.
Para meio-ambiente.$aridez_cond2_area1991 for diferente de 0 e meio-ambiente.$aridez_cond3_area1991 for igual a 0:
Duas condições de aridez.
Para meio-ambiente.$aridez_cond3_area1991 for diferente de 0:
Três condições de aridez."""

    sem_dados = interpretar_blocos_condicionais(texto, {})
    assert "Sem dados de aridez." in sem_dados
    assert "Uma condição de aridez." not in sem_dados
    assert "Duas condições de aridez." not in sem_dados
    assert "Três condições de aridez." not in sem_dados

    uma = interpretar_blocos_condicionais(
        texto, {"aridez_cond1_area1991": 10, "aridez_cond2_area1991": 0, "aridez_cond3_area1991": 0}
    )
    assert "Uma condição de aridez." in uma
    assert "Duas condições de aridez." not in uma
    assert "Três condições de aridez." not in uma

    duas = interpretar_blocos_condicionais(
        texto, {"aridez_cond1_area1991": 10, "aridez_cond2_area1991": 5, "aridez_cond3_area1991": 0}
    )
    assert "Duas condições de aridez." in duas
    assert "Três condições de aridez." not in duas

    tres = interpretar_blocos_condicionais(
        texto,
        {
            "aridez_cond1_area1991": 10,
            "aridez_cond2_area1991": 5,
            "aridez_cond3_area1991": 2,
        },
    )
    assert "Três condições de aridez." in tres


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


def test_field_vs_field_condition_picks_the_matching_block():
    """educacao compara dois campos entre si ($sem_instr_2000 vs
    $sem_instr_2022), não um campo contra um número literal — os operadores
    fixos exigem \\d+ e nunca casavam, então nenhum dos dois parágrafos era
    exibido, independente dos dados (bug real, não hipotético)."""
    texto = """Para quando educacao.$sem_instr_2000 for igual a educacao.$sem_instr_2022, então:
Sem variação no número de pessoas sem instrução.
Para quando educacao.$sem_instr_2000 for diferente de educacao.$sem_instr_2022, então:
Houve variação no número de pessoas sem instrução."""

    sem_variacao = interpretar_blocos_condicionais(
        texto, {"sem_instr_2000": 100, "sem_instr_2022": 100}
    )
    assert "Sem variação no número de pessoas sem instrução." in sem_variacao
    assert "Houve variação no número de pessoas sem instrução." not in sem_variacao

    com_variacao = interpretar_blocos_condicionais(
        texto, {"sem_instr_2000": 100, "sem_instr_2022": 80}
    )
    assert "Houve variação no número de pessoas sem instrução." in com_variacao
    assert "Sem variação no número de pessoas sem instrução." not in com_variacao


def test_condition_and_its_guarded_paragraph_separated_by_a_blank_line_still_gates_correctly():
    """No Doc exportado do Google Docs, a regra 'Para quando ...:' fica em um
    parágrafo próprio, separado do parágrafo que ela guarda por uma linha em
    branco (como qualquer parágrafo do Doc) — não colado na mesma linha como
    nos outros testes deste arquivo. Essa linha em branco não pode ser
    tratada como 'fim do bloco condicional': se for, o bloco reativa antes do
    parágrafo guardado ser lido, e as duas versões (igual/diferente) vazam
    juntas no relatório, não importa o dado (bug real, não hipotético)."""
    texto = """Antes do bloco condicional.

Para quando educacao.$sem_instr_2000 for igual a educacao.$sem_instr_2022, então:

TEXTO_IGUAL

Para quando educacao.$sem_instr_2000 for diferente de educacao.$sem_instr_2022, então:

TEXTO_DIFERENTE

Depois do bloco condicional."""

    igual = interpretar_blocos_condicionais(
        texto, {"sem_instr_2000": 100, "sem_instr_2022": 100}
    )
    assert "TEXTO_IGUAL" in igual
    assert "TEXTO_DIFERENTE" not in igual
    assert "Antes do bloco condicional." in igual
    assert "Depois do bloco condicional." in igual

    diferente = interpretar_blocos_condicionais(
        texto, {"sem_instr_2000": 100, "sem_instr_2022": 80}
    )
    assert "TEXTO_DIFERENTE" in diferente
    assert "TEXTO_IGUAL" not in diferente


def test_config_de_grafico_sem_margem_usa_a_padrao():
    # Regressão: uma entrada de _CONFIG_GRAFICOS que configura só a largura
    # (como a da rosca de esgotamento) derrubava a renderização inteira com
    # KeyError, porque a margem era lida por indexação direta.
    reset_figura_contador()
    texto = "%%grafico_domicilio_por_tipo_esgosto\n\nFigura X- Legenda de teste."

    html = texto_para_html(
        texto,
        {},
        graficos_por_placeholder={"grafico_domicilio_por_tipo_esgosto": "rosca.png"},
    )

    assert "margin:32px 0 8px;" in html
    assert "max-width:600px" in html


def _sintese_condicional(sufixo_esgoto: str, sufixo_coleta: str) -> str:
    # Formato real do Doc de saneamento: duas comparações campo-a-campo
    # unidas por "e", cada uma com quatro marcadores no total.
    return (
        f"Para quando infraestrutura.$esgoto_rede_2000 for {sufixo_esgoto} "
        f"infraestrutura.$esgoto_rede_2022 e infraestrutura.$coleta_2010 for "
        f"{sufixo_coleta} infraestrutura.$coleta_2022, então:\n"
    )


def test_condicao_composta_campo_a_campo_escolhe_o_ramo_certo():
    # Belém/AL: esgoto 4.4 -> 7.3 (mudou) e coleta 58.9 -> 71.1 (mudou). Antes
    # da conjunção, as quatro versões do parágrafo de síntese eram avaliadas
    # como falsas e o parágrafo sumia do relatório de todo município.
    contexto = {
        "esgoto_rede_2000": "4.4",
        "esgoto_rede_2022": 7.3,
        "coleta_2010": 58.9,
        "coleta_2022": 71.1,
    }
    ramos = {
        ("diferente de", "diferente de"): "MUDOU-MUDOU",
        ("igual a", "diferente de"): "IGUAL-MUDOU",
        ("diferente de", "igual a"): "MUDOU-IGUAL",
        ("igual a", "igual a"): "IGUAL-IGUAL",
    }
    texto = "".join(
        _sintese_condicional(*chave) + corpo + "\n\n" for chave, corpo in ramos.items()
    )

    resultado = interpretar_blocos_condicionais(texto, contexto)

    assert "MUDOU-MUDOU" in resultado
    for outro in ("IGUAL-MUDOU", "MUDOU-IGUAL", "IGUAL-IGUAL"):
        assert outro not in resultado


def test_condicao_composta_com_um_lado_igual():
    # Município onde só a coleta ficou parada.
    contexto = {
        "esgoto_rede_2000": "44.2",
        "esgoto_rede_2022": 72.0,
        "coleta_2010": 83.6,
        "coleta_2022": 83.6,
    }
    texto = (
        _sintese_condicional("diferente de", "igual a") + "ESCOLHIDO\n\n"
        + _sintese_condicional("diferente de", "diferente de") + "DESCARTADO\n"
    )

    resultado = interpretar_blocos_condicionais(texto, contexto)

    assert "ESCOLHIDO" in resultado
    assert "DESCARTADO" not in resultado


def test_campo_texto_com_unidade_por_extenso_e_lido_como_numero():
    # Regressão: `var_coleta_pp` guarda "12,2 pontos percentuais"; o sufixo
    # derrubava o valor para 0 e o relatório afirmava "valor igual ao
    # registrado em 2010" num município que variou 12,2 p.p.
    texto = (
        "Para quando infraestrutura.$var_coleta_pp for diferente de 0 ponto "
        "percentual, então:\nHOUVE-VARIACAO\n\n"
        "Para quando infraestrutura.$var_coleta_pp for igual a 0 ponto "
        "percentual, então:\nSEM-VARIACAO\n"
    )

    variou = interpretar_blocos_condicionais(
        texto, {"var_coleta_pp": "12,2 pontos percentuais"}
    )
    parado = interpretar_blocos_condicionais(
        texto, {"var_coleta_pp": "0 ponto percentual"}
    )

    assert "HOUVE-VARIACAO" in variou and "SEM-VARIACAO" not in variou
    assert "SEM-VARIACAO" in parado and "HOUVE-VARIACAO" not in parado


def test_marcador_de_grafico_apos_alternativa_falsa_nao_e_descartado():
    texto = (
        "Para quando infraestrutura.$var_coleta_pp for igual a 0 ponto "
        "percentual, então:\nSEM-VARIACAO\n"
        "*grafico_coleta_lixo\n"
        "Figura Z – Evolução da coleta de lixo.\n"
    )

    resultado = interpretar_blocos_condicionais(texto, {"var_coleta_pp": 2.7})

    assert "SEM-VARIACAO" not in resultado
    assert "*grafico_coleta_lixo" in resultado
    assert "Figura Z" in resultado


def test_conjuncao_com_numero_literal_continua_no_caminho_numerico():
    # "campo A for X e campo B for Y" não é campo-a-campo: cada lado compara
    # com um número literal e precisa seguir pelo caminho antigo.
    texto = (
        "Para quando demografia.$a for maior que 10 e demografia.$b for "
        "menor que 5, então:\nATENDE\n"
    )

    assert "ATENDE" in interpretar_blocos_condicionais(texto, {"a": 20, "b": 2})
    assert "ATENDE" not in interpretar_blocos_condicionais(texto, {"a": 20, "b": 9})


def test_condicoes_de_vacina_comparam_texto_em_vez_de_numero():
    # vacina_meta/vacina_nao_meta guardam uma lista de nomes (ou o literal
    # "todas"/"nenhuma"); o caminho numérico forçava esses valores para 0.0 e
    # "for todas"/"for nenhuma" nunca batiam (Doc de saúde, Síntese).
    texto = (
        "Para quando saude.$vacina_meta for diferente de todas e "
        "saude.$vacina_nao_meta for diferente de nenhuma, então:\nMISTA\n\n"
        "Para quando saude.$vacina_meta for todas, então:\nTODAS BATERAM\n\n"
        "Para quando saude.$vacina_nao_meta for nenhuma, então:\nNENHUMA FICOU DE FORA\n"
    )

    mista = interpretar_blocos_condicionais(
        texto, {"vacina_meta": "BCG, Hepatite B", "vacina_nao_meta": "Rotavírus"}
    )
    assert "MISTA" in mista
    assert "TODAS BATERAM" not in mista
    assert "NENHUMA FICOU DE FORA" not in mista

    todas = interpretar_blocos_condicionais(
        texto, {"vacina_meta": "Todas", "vacina_nao_meta": "Nenhuma"}
    )
    assert "TODAS BATERAM" in todas
    assert "NENHUMA FICOU DE FORA" in todas
    assert "MISTA" not in todas


def test_condicoes_de_vacina_sem_dado_nao_vazam_bloco_misto():
    # None virava "" e "" é diferente de "todas"/"nenhuma", então o bloco
    # MISTA batia para uma cidade sem levantamento de vacinação nenhum.
    texto = (
        "Para quando saude.$vacina_meta for diferente de todas e "
        "saude.$vacina_nao_meta for diferente de nenhuma, então:\nMISTA\n\n"
        "Para quando saude.$vacina_meta for todas, então:\nTODAS BATERAM\n\n"
        "Para quando saude.$vacina_nao_meta for nenhuma, então:\nNENHUMA FICOU DE FORA\n"
    )

    sem_dado = interpretar_blocos_condicionais(
        texto, {"vacina_meta": None, "vacina_nao_meta": None}
    )
    assert "MISTA" not in sem_dado
    assert "TODAS BATERAM" not in sem_dado
    assert "NENHUMA FICOU DE FORA" not in sem_dado

    parcial = interpretar_blocos_condicionais(
        texto, {"vacina_meta": None, "vacina_nao_meta": "Rotavírus"}
    )
    assert "MISTA" not in parcial


def test_condicao_de_vacina_combinada_com_campo_numerico():
    # Antes, misturar vacina_meta/vacina_nao_meta com outro campo caía
    # inteiro no caminho numérico, que força texto para 0.0 e nunca bate —
    # o parágrafo sumia em silêncio mesmo quando os dois lados batiam.
    texto = (
        "Para quando saude.$vacina_meta for todas e saude.$obitos for maior "
        "que 5, então:\nMISTO_OK\n"
    )

    assert "MISTO_OK" in interpretar_blocos_condicionais(
        texto, {"vacina_meta": "Todas", "obitos": 10}
    )
    assert "MISTO_OK" not in interpretar_blocos_condicionais(
        texto, {"vacina_meta": "Todas", "obitos": 2}
    )
    assert "MISTO_OK" not in interpretar_blocos_condicionais(
        texto, {"vacina_meta": "BCG", "obitos": 10}
    )


def test_titulo_de_secao_solto_no_meio_do_bloco_vira_heading():
    # "Síntese" é escrito no Doc sem "#!" e sem linha em branco antes, então
    # chegava colado no parágrafo anterior e saía como texto corrido, e não
    # verde como "Apresentação"/"Características Gerais".
    reset_figura_contador()
    texto = "Parágrafo anterior sem linha em branco depois.\nSíntese\nTexto da síntese."

    html = texto_para_html(
        texto, {}, graficos_por_placeholder={}, classe_paragrafo="theme-detail-text"
    )

    assert '<h2 class="theme-detail-heading">Síntese</h2>' in html
    assert '<p class="theme-detail-text">Síntese</p>' not in html
    assert "Texto da síntese." in html


def test_decimal_em_coluna_de_texto_sai_no_padrao_ptbr():
    # `esgoto_rede_2000` é coluna de texto e guarda "4.4"; sem formatação o
    # relatório misturava "4.4%" e "7,3%" na mesma frase.
    texto = "de infraestrutura.$esgoto_rede_2000% em 2000 para infraestrutura.$esgoto_rede_2022% em 2022"

    resultado = substituir_placeholders(
        texto, {"esgoto_rede_2000": "4.4", "esgoto_rede_2022": 7.3}, "saneamento"
    )

    assert resultado == "de 4,4% em 2000 para 7,3% em 2022"


def test_texto_que_nao_e_decimal_puro_fica_intacto():
    # Código de município (inteiro) não pode ganhar separador de milhar, e
    # texto com unidade por extenso não é número.
    contexto = {"cod_mun": "2801108", "var_coleta_pp": "12,2 pontos percentuais"}

    resultado = substituir_placeholders(
        "saneamento.$cod_mun / saneamento.$var_coleta_pp", contexto, "saneamento"
    )

    assert resultado == "2801108 / 12,2 pontos percentuais"
