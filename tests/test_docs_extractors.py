from utils.external.docs import (
    CardDoPanorama,
    extrair_descricao_tema,
    extrair_inicio_relatorio,
    extrair_introducao,
    extrair_legenda_mapa_localizacao,
    extrair_panorama_indicadores,
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


def test_theme_description_without_closing_marker_stops_before_sources():
    texto = """descricao_tema=Texto principal do tema.
Mais um parágrafo.
#!Fontes
Painéis usados no relatório.
#!Conteúdos relacionados
Boletins do tema.
"""

    descricao, restante = extrair_descricao_tema(texto)

    assert descricao == "Texto principal do tema.\nMais um parágrafo."
    assert restante.startswith("#!Fontes")
    assert "#!Conteúdos relacionados" in restante


def test_global_report_summary_is_extracted_from_characteristics_document():
    texto = "#! Resumo\nresumo_relatorio=“Síntese de caract_mun.$nm_mun.”@@"

    resumo, restante = extrair_resumo_relatorio(texto)

    assert resumo == "Síntese de caract_mun.$nm_mun."
    assert restante == "#! Resumo"


def test_location_map_caption_is_extracted_and_removed_from_the_summary():
    texto = (
        "O município de caract_mun.$nm_mun está localizado (Figura X).\n\n\n"
        "Figura X- Localização do município caract_mun.$nm_mun (caract_mun.$sigla_uf)\n\n\n"
        "https://datanordeste.sudene.gov.br/"
    )

    legenda, restante = extrair_legenda_mapa_localizacao(texto)

    assert legenda == (
        "Figura X- Localização do município caract_mun.$nm_mun (caract_mun.$sigla_uf)"
    )
    assert "Localização do município" not in restante


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


# Formato do Doc estadual de Demografia (11/11/2026), como sai do export em txt do
# .docx: rótulos com tab na frente, linhas só com tab entre os pares.
PANORAMA_DOC_ESTADUAL = (
    "Panorama de indicadores\n"
    "População residente\n"
    "demografia.$uf_pop_total_2022\n"
    "\tPopulação masculina\n"
    "demografia.$uf_pop_homem\n"
    "\t\n"
    "\n"
    "#!Fontes\n"
    "Os dados deste relatório foram extraídos do painel = https://exemplo\n"
)


def test_panorama_vira_cards_e_sai_do_texto():
    cards, restante = extrair_panorama_indicadores(PANORAMA_DOC_ESTADUAL)

    assert cards == [
        CardDoPanorama("População residente", "demografia.$uf_pop_total_2022"),
        CardDoPanorama("População masculina", "demografia.$uf_pop_homem"),
    ]
    assert restante.startswith("#!Fontes")
    assert "Panorama" not in restante


# Formato do Doc estadual de Infraestrutura (11/11/2026): uma legenda "fonte •
# unidade" abaixo do valor, e o rótulo seguinte com tab na frente.
PANORAMA_COM_LEGENDA = (
    "Panorama de indicadores\n"
    "Domicílios ligados à categoria de rede de esgoto\n"
    "infraestrutura.$uf_esgoto_rede_2022:2%\n"
    "IBGE Censo 2022 • percentual de domicílios\n"
    "\tDomicílios com coleta de lixo\n"
    "infraestrutura.$uf_coleta_2022:2%\n"
    "\t\n"
    "Implementação dos big numbers: um campo ainda não veio no banco.\n"
)


def test_linha_com_ponto_abaixo_do_valor_vira_legenda_do_card():
    cards, restante = extrair_panorama_indicadores(PANORAMA_COM_LEGENDA)

    assert cards == [
        CardDoPanorama(
            "Domicílios ligados à categoria de rede de esgoto",
            "infraestrutura.$uf_esgoto_rede_2022:2%",
            "IBGE Censo 2022 • percentual de domicílios",
        ),
        CardDoPanorama("Domicílios com coleta de lixo", "infraestrutura.$uf_coleta_2022:2%"),
    ]
    # Sem `•`, a linha depois do último valor não é legenda: fica no texto.
    assert restante == "Implementação dos big numbers: um campo ainda não veio no banco."


def test_doc_sem_panorama_volta_intacto():
    texto = "#!Fontes\nPainel = https://exemplo"

    assert extrair_panorama_indicadores(texto) == ([], texto)


def test_rotulo_sem_valor_encerra_o_panorama_e_fica_no_texto():
    texto = "Panorama de indicadores\nPopulação\n$uf_pop\nRótulo solto\nOutra linha"

    cards, restante = extrair_panorama_indicadores(texto)

    assert cards == [CardDoPanorama("População", "$uf_pop")]
    assert restante == "Rótulo solto\nOutra linha"
