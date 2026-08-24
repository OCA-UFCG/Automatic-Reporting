from utils.external.docs import (
    extrair_descricao_tema,
    extrair_inicio_relatorio,
    extrair_introducao,
    extrair_referencias,
    extrair_relatorio_geral,
    extrair_resumo_relatorio,
    limpar_texto_exportado_docs,
    remover_titulos_docs,
)


def test_all_theme_description_blocks_are_joined_and_removed():
    texto = "descricao_tema=“Primeiro bloco”@@\nEntre\ndescricao_tema=Segundo bloco@@"
    descricao, restante = extrair_descricao_tema(texto)

    assert descricao == "Primeiro bloco\n\nSegundo bloco"
    assert restante == "Entre"


def test_global_report_summary_is_extracted_from_characteristics_document():
    texto = "#! Resumo\nresumo_relatorio=“Síntese de caract_mun.$nm_mun.”@@"

    resumo, restante = extrair_resumo_relatorio(texto)

    assert resumo == "Síntese de caract_mun.$nm_mun."
    assert restante == "#! Resumo"


def test_introduction_without_closing_marker_stops_before_next_field():
    texto = """\ufeffRELATÓRIO PERSONALIZADO
caract_mun.$nm_mun (caract_mun.$sigla_uf) EM DADOS
introducao=O Data Nordeste apresenta informações municipais.

relatorio_geral=“Síntese do relatório.”@@
"""

    texto = limpar_texto_exportado_docs(texto)
    introducao, restante = extrair_introducao(texto)
    restante = remover_titulos_docs(
        restante,
        "Relatório Personalizado",
        "caract_mun.$nm_mun (caract_mun.$sigla_uf) EM DADOS",
    )

    assert introducao == "O Data Nordeste apresenta informações municipais."
    assert restante == "relatorio_geral=“Síntese do relatório.”@@"


def test_report_start_marker_includes_optional_subtitle_until_next_field():
    texto = """inicio_relatorio = RELATÓRIO PERSONALIZADO
caract_mun.$nm_mun (caract_mun.$sigla_uf) EM DADOS

introducao=Apresentação da plataforma.
"""

    inicio, restante = extrair_inicio_relatorio(texto)

    assert inicio == (
        "RELATÓRIO PERSONALIZADO\n"
        "caract_mun.$nm_mun (caract_mun.$sigla_uf) EM DADOS"
    )
    assert restante == "introducao=Apresentação da plataforma."


def test_apresentacao_is_the_new_name_for_relatorio_geral():
    apresentacao, restante = extrair_relatorio_geral(
        "apresentacao=Texto da apresentação.@@\n#! Características Gerais"
    )

    assert apresentacao == "Texto da apresentação."
    assert restante == "#! Características Gerais"


def test_references_are_extracted_and_their_heading_can_be_removed():
    texto = """#! Apresentação
#! Características Gerais
#! Referências
referencia=“Zeta, 2024.
Álvares, 2020.”@@
"""

    referencias, restante = extrair_referencias(texto)
    restante = remover_titulos_docs(
        restante, "Apresentação", "Características Gerais", "Referências"
    )

    assert referencias == ["Zeta, 2024.", "Álvares, 2020."]
    assert restante == ""


def test_presentation_marker_is_removed_with_or_without_space():
    texto = "#!Apresentação\n#! aoresentacao\n#! Hyperlink"

    restante = remover_titulos_docs(
        texto, "Apresentação", "Apresentacao", "Aoresentacao"
    )

    assert restante == "#! Hyperlink"


def test_google_docs_comments_and_exported_footnotes_are_removed():
    texto = """Texto com comentário[a] e outro marcador[b].
[a] Revisora: retirar este trecho
1 O IBGE estabeleceu uma observação usada apenas como nota.
1. Uma lista numerada legítima.
1 Demografia
"""

    resultado = limpar_texto_exportado_docs(texto)

    assert resultado == (
        "Texto com comentário e outro marcador.\n"
        "1. Uma lista numerada legítima.\n"
        "1 Demografia"
    )
