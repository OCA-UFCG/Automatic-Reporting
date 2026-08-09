from utils.docs import (
    extrair_descricao_tema,
    extrair_referencias,
    extrair_resumo_relatorio,
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
