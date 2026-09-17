from utils.cover import (
    INDICADORES_POR_MACROTEMA,
    montar_indicadores_macrotema,
    montar_score_macrotema,
)

# Contexto sintético no formato do que `buscar_indicadores_municipio` devolve.
# `relatorios_auto.vw_indicadores` guarda cada indicador num quarteto
# nm_/valor_/fonte_/unid_ com uma base comum, e os valores chegam como string.
# Educação é a exceção: seis colunas `per_*` soltas, sem rótulo nem fonte na
# view. Nenhum teste aqui toca o banco.
CONTEXTO = {
    "nm_pop_residente": "População residente",
    "valor_pop_residente": "419379",
    "fonte_pop_residente": "Censo demográfico 2022 (IBGE, 2023)",
    "unid_pop_residente": "Pessoas residentes",
    "nm_pop_masculina": "População masculina",
    "valor_pop_masculina": "198413",
    "fonte_pop_masculina": "Censo demográfico 2022 (IBGE, 2023)",
    "unid_pop_masculina": "Pessoas",
    # Irregular de propósito: no banco o rótulo é `nm_pop_feminina`, mas
    # valor_/fonte_/unid_ usam `pop_feminino`. Copiado da view, não inventado.
    "nm_pop_feminina": "População feminina",
    "valor_pop_feminino": "220966",
    "fonte_pop_feminino": "Censo demográfico 2022 (IBGE, 2023)",
    "unid_pop_feminino": "Pessoas",
    "valor_pop_quilombola": "0",
    "nm_pop_quilombola": "População quilombola",
    "fonte_pop_quilombola": "Censo demográfico 2022 (IBGE, 2023)",
    "unid_pop_quilombola": "Pessoas quilombolas",
    "nm_pop_indigena": "População indígena",
    "valor_pop_indigena": "470",
    "fonte_pop_indigena": "Censo demográfico 2022 (IBGE, 2023)",
    "unid_pop_indigena": "Pessoas indígenas",
    "nm_idhm": "IDHM",
    "valor_idhm": "0.770",
    "fonte_idhm": "IBGE (2010)",
    "unid_idhm": "Índice",
    "nm_renda_capita": "Renda per capita",
    "valor_renda_capita": "630.03",
    "fonte_renda_capita": "IBGE (2010)",
    "unid_renda_capita": "R$ por habitante",
    "nm_gini": "Índice de Gini",
    "valor_gini": "0.58",
    "fonte_gini": "IBGE (2010)",
    "unid_gini": "Índice de Gini",
    # Os 6 de economia (PR #126), quarteto copiado da linha real de Campina
    # Grande: `unid_` é o que faz o card sair em R$ ou US$.
    "nm_pib": "PIB",
    "valor_pib": "12908743000",
    "fonte_pib": "IBGE (2023)",
    "unid_pib": "R$",
    "nm_pib_capita": "PIB per capita",
    "valor_pib_capita": "30780.61",
    "fonte_pib_capita": "IBGE (2023)",
    "unid_pib_capita": "R$ por habitante",
    "nm_carga_tributaria": "Receita tributária municipal",
    "valor_carga_tributaria": "277942183.71",
    "fonte_carga_tributaria": "STN/FINBRA/SICONFI (2023)",
    "unid_carga_tributaria": "R$",
    "nm_exportacao": "Exportações",
    "valor_exportacao": "3560041.00",
    "fonte_exportacao": "SECEX (junho de 2026)",
    "unid_exportacao": "US$ FOB",
    "nm_importacao": "Importações",
    "valor_importacao": "10865532.00",
    "fonte_importacao": "SECEX (junho de 2026)",
    "unid_importacao": "US$ FOB",
    "nm_balanca": "Balança comercial",
    "valor_balanca": "-7305491.00",
    "fonte_balanca": "SECEX (junho de 2026)",
    "unid_balanca": "US$ FOB",
    "nm_asd": "Área suscetível à desertificação",
    "valor_asd": "590.55",
    "fonte_asd": "Xavier et al. (2019) e OCA",
    "unid_asd": "km²",
    "nm_esgotamento": "Domicílios ligados à rede geral ou pluvial",
    "valor_esgotamento": "86.62",
    "fonte_esgotamento": "IBGE (2022)",
    "unid_esgotamento": "Percentual de domicílios (%)",
    "nm_cisternas": "Cisternas e tecnologias sociais de acesso à água",
    "valor_cisternas": "2038",
    "fonte_cisternas": "SESAN (2025)",
    "unid_cisternas": "Tecnologias sociais",
    # Educação segue o mesmo quarteto, só que o valor mora em `per_<base>`.
    "nm_fundamental_incom": "Fundamental incompleto ou sem instrução",
    "per_fundamental_incom": "32.62",
    "fonte_fundamental_incom": "IBGE (2022)",
    "unid_fundamental_incom": "Percentual da população (%)",
    "nm_superior_com": "Superior completo",
    "per_superior_com": "20.85",
    "fonte_superior_com": "IBGE (2022)",
    "unid_superior_com": "Percentual da população (%)",
    "nm_alfabetizada_indigena": "População indígena alfabetizada",
    "per_alfabetizada_indigena": "90.80",
    "fonte_alfabetizada_indigena": "IBGE (2022)",
    "unid_alfabetizada_indigena": (
        "Percentual da população indígena de 15 anos ou mais (%)"
    ),
    "nm_alfabetizada_quilombola": "População quilombola alfabetizada",
    "per_alfabetizada_quilombola": "0",
    "fonte_alfabetizada_quilombola": "IBGE (2022)",
    "unid_alfabetizada_quilombola": (
        "Percentual da população quilombola de 15 anos ou mais (%)"
    ),
}


def _por_nome(indicadores: list[dict]) -> dict[str, str]:
    return {item["nome"]: item["valor"] for item in indicadores}


def test_rotulo_fonte_e_rodape_vem_da_view_nao_do_codigo():
    # O ponto da migração: o card não repete em Python o que a view já diz.
    (card,) = [
        item
        for item in montar_indicadores_macrotema("demografia", CONTEXTO)
        if item["nome"] == "População residente"
    ]

    assert card["valor"] == "419.379"
    assert card["fonte"] == "Censo demográfico 2022 (IBGE, 2023)"
    assert card["rodape"] == "Pessoas residentes"


def test_indicadores_usam_valores_do_contexto():
    valores = _por_nome(
        montar_indicadores_macrotema("desenvolvimento-social", CONTEXTO)
    )

    assert valores["IDHM"] == "0,77"
    assert valores["Renda per capita"] == "R$ 630,03"
    assert valores["Índice de Gini"] == "0,58"


def test_afixo_monetario_percentual_e_de_area_vem_da_unidade():
    # `unid_` é texto livre: só as formas monetária, percentual e de área
    # viram marca no número (ver _afixos_da_unidade). Sem isso a renda per
    # capita sairia "630,03" e o esgotamento "86,62", números que enganam.
    assert _por_nome(
        montar_indicadores_macrotema("desenvolvimento-social", CONTEXTO)
    )["Renda per capita"] == "R$ 630,03"
    assert _por_nome(montar_indicadores_macrotema("saneamento", CONTEXTO))[
        "Domicílios ligados à rede geral ou pluvial"
    ] == "86,62%"
    assert _por_nome(montar_indicadores_macrotema("meio-ambiente", CONTEXTO))[
        "Área suscetível à desertificação"
    ] == "590,55 km²"


def test_educacao_le_o_valor_em_per_e_o_resto_do_quarteto_normalmente():
    # Regressão da quebra que motivou esta branch: os cards de educação
    # apontavam para `sem_instrucao_fund_incomp_per` & cia., nomes que a view
    # não tem desde a migração — os seis saíam vazios e o bloco inteiro sumia
    # da capa. Educação é a única base cujo valor está em `per_<base>` e não
    # em `valor_<base>`; rótulo e fonte vêm da view como em todo o resto.
    cards = {item["nome"]: item for item in montar_indicadores_macrotema(
        "educacao", CONTEXTO
    )}

    assert cards["Fundamental incompleto ou sem instrução"]["valor"] == "32,62%"
    assert cards["Superior completo"]["valor"] == "20,85%"
    assert cards["População indígena alfabetizada"]["valor"] == "90,8%"
    # A fonte é a da view, não uma string montada no código.
    assert cards["Superior completo"]["fonte"] == "IBGE (2022)"


def test_alfabetizacao_some_quando_o_grupo_nao_existe_no_municipio():
    # per_alfabetizada_quilombola = 0 com pop_quilombola = 0 significa "não há
    # quilombolas aqui", não "nenhum é alfabetizado". Exibir "0%" seria uma
    # afirmação errada sobre o município.
    valores = _por_nome(montar_indicadores_macrotema("educacao", CONTEXTO))
    assert "População quilombola alfabetizada" not in valores

    com_grupo = _por_nome(
        montar_indicadores_macrotema(
            "educacao",
            {
                **CONTEXTO,
                "valor_pop_quilombola": "3008",
                "per_alfabetizada_quilombola": "79.84",
            },
        )
    )
    assert com_grupo["População quilombola alfabetizada"] == "79,84%"


def test_populacao_feminina_aparece_apesar_do_nome_irregular_na_view():
    # Regressão: a base é `pop_feminino` (valor_/fonte_/unid_), mas o rótulo na
    # view é `nm_pop_feminina`. Procurar `nm_pop_feminino` devolve None e o card
    # sumia da capa em silêncio — com o valor presente e o rótulo preenchido.
    # Não é dado faltando no banco; é nome de coluna divergente (ver
    # _ROTULO_IRREGULAR em utils/cover.py).
    valores = _por_nome(montar_indicadores_macrotema("demografia", CONTEXTO))

    assert valores["População feminina"] == "220.966"


def test_base_sem_rotulo_na_view_nao_vira_card():
    # Nenhum texto de card mora no código: sem `nm_<base>` o card não existe,
    # mesmo havendo valor. A ausência na capa é o sinal de que falta preencher
    # a coluna no banco — preencher daqui esconderia o buraco.
    valores = _por_nome(
        montar_indicadores_macrotema(
            "demografia", {**CONTEXTO, "nm_pop_indigena": None}
        )
    )

    assert "População indígena" not in valores


def test_indicador_sem_valor_no_banco_e_omitido():
    indicadores = montar_indicadores_macrotema(
        "meio-ambiente", {**CONTEXTO, "valor_asd": None}
    )

    nomes = {item["nome"] for item in indicadores}
    assert "Área suscetível à desertificação" not in nomes
    assert all(item["valor"] for item in indicadores)


def test_sem_contexto_nao_inventa_indicador():
    assert montar_indicadores_macrotema("saneamento") == []
    assert montar_indicadores_macrotema("saneamento", {}) == []


def test_saude_le_os_seis_indicadores_da_view():
    # Saúde ficou sem nenhum card desde a migração da view; as seis colunas
    # existem e são as do catálogo de big numbers.
    contexto = {
        **CONTEXTO,
        "nm_nascidos": "Nascidos vivos",
        "valor_nascidos": "5693",
        "fonte_nascidos": "DATASUS (2025)",
        "unid_nascidos": "Nascidos vivos",
        "nm_mortalidade_infantil": "Mortalidade infantil",
        "valor_mortalidade_infantil": "10.36",
        "fonte_mortalidade_infantil": "DATASUS (2025)",
        "unid_mortalidade_infantil": "Óbitos infantis por mil nascidos vivos",
    }

    cards = {item["nome"]: item for item in montar_indicadores_macrotema(
        "saude", contexto
    )}

    assert cards["Nascidos vivos"]["valor"] == "5.693"
    assert cards["Mortalidade infantil"]["valor"] == "10,36"
    assert cards["Mortalidade infantil"]["fonte"] == "DATASUS (2025)"


def test_economia_renda_nao_mostra_renda_capita_nem_gini():
    # O Doc de economia pede só 6 indicadores (PIB, PIB per capita, Receita
    # tributária, Exportação, Importação, Balança comercial); Renda per capita
    # e Índice de Gini pertencem a desenvolvimento-social, não aqui — senão o
    # mesmo número aparece em dois macrotemas.
    valores = _por_nome(montar_indicadores_macrotema("economia-renda", CONTEXTO))

    assert "Renda per capita" not in valores
    assert "Índice de Gini" not in valores


def test_economia_renda_mostra_os_6_indicadores_da_view():
    valores = _por_nome(montar_indicadores_macrotema("economia-renda", CONTEXTO))

    assert valores["PIB"] == "R$ 12.908.743.000"
    assert valores["PIB per capita"] == "R$ 30.780,61"
    assert valores["Receita tributária municipal"] == "R$ 277.942.183,71"
    assert valores["Exportações"] == "US$ 3.560.041"
    assert valores["Importações"] == "US$ 10.865.532"
    assert valores["Balança comercial"] == "US$ -7.305.491"


def test_economia_le_o_mes_de_referencia_do_secex_direto_da_view():
    # O mês do SECEX muda a cada carga. Fixar "SECEX" no código deixaria o
    # relatório do mês seguinte desatualizado — era o que `fonte_coluna` (#126)
    # resolvia caso a caso e que ler `fonte_<base>` da view agora faz por
    # padrão, para todos os cards.
    contexto = {**CONTEXTO, "fonte_exportacao": "SECEX (março de 2027)"}
    fontes = {
        item["nome"]: item["fonte"]
        for item in montar_indicadores_macrotema("economia-renda", contexto)
    }

    assert fontes["Exportações"] == "SECEX (março de 2027)"
    assert fontes["PIB"] == "IBGE (2023)"


def test_economia_sem_fonte_na_view_nao_inventa_texto_fixo():
    # Mudança de comportamento em relação à #126: não existe mais fallback
    # para um "SECEX" fixo no código. Sem `fonte_<base>`, o card sai com fonte
    # vazia — a lacuna fica visível na capa em vez de ser mascarada por um
    # texto que o banco não confirmou.
    contexto = {**CONTEXTO, "fonte_exportacao": None}
    fontes = {
        item["nome"]: item["fonte"]
        for item in montar_indicadores_macrotema("economia-renda", contexto)
    }

    assert fontes["Exportações"] == ""


def test_indicadores_diferem_entre_macrotemas():
    nomes_hidraulica = {
        item["nome"] for item in montar_indicadores_macrotema("hidraulica", CONTEXTO)
    }
    nomes_educacao = {
        item["nome"] for item in montar_indicadores_macrotema("educacao", CONTEXTO)
    }

    assert nomes_hidraulica
    assert nomes_educacao
    assert nomes_hidraulica.isdisjoint(nomes_educacao)


def test_icone_do_macrotema_e_usado_quando_o_indicador_nao_define_um():
    # "Cisternas..." não tem ícone próprio no catálogo, então cai no ícone do
    # macrotema recebido.
    indicadores = montar_indicadores_macrotema(
        "hidraulica", CONTEXTO, macrotema_icone="wrench"
    )

    por_nome = {item["nome"]: item for item in indicadores}
    assert (
        por_nome["Cisternas e tecnologias sociais de acesso à água"]["icone"]
        == "wrench"
    )


def test_indicador_com_icone_proprio_nao_usa_o_icone_do_macrotema():
    # "Domicílios ligados à rede geral ou pluvial" (base "esgotamento") tem
    # ícone dedicado no catálogo (ver _ICONE_POR_BASE) e não deve cair no
    # ícone genérico do macrotema, mesmo quando este é passado explicitamente.
    indicadores = montar_indicadores_macrotema(
        "saneamento", CONTEXTO, macrotema_icone="wrench"
    )

    por_nome = {item["nome"]: item for item in indicadores}
    assert (
        por_nome["Domicílios ligados à rede geral ou pluvial"]["icone"]
        == "esgoto"
    )


def test_catalogo_e_so_a_ordem_das_bases_da_view():
    # Nenhum rótulo, fonte ou unidade mora mais no código: o catálogo só diz
    # quais indicadores entram em cada macrotema e em que ordem.
    for specs in INDICADORES_POR_MACROTEMA.values():
        assert specs
        for base in specs:
            assert isinstance(base, str) and base


def test_score_usa_a_linha_do_tema_correspondente():
    score_demografia = montar_score_macrotema({"score_geral": "4,20"})
    score_saude = montar_score_macrotema({"score_geral": "1,80"})

    assert score_demografia["valor"] == "4,20"
    assert score_saude["valor"] == "1,80"


def test_score_usa_fallback_quando_coluna_ausente():
    score = montar_score_macrotema({})

    assert score["valor"] == "3,66"
    assert score["maximo"] == "5"
