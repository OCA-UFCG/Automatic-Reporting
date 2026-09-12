from utils.editorial.contrato import novo_contrato, validar_contrato
from utils.editorial.render import (
    CHAVE_FONTE_PAINEL,
    FONTE_PAINEL,
    renderizar_blocos,
    renderizar_contrato,
    renderizar_trechos,
)
from utils.external.docs import extrair_descricao_tema, extrair_resumo_tema
from utils.render.placeholders import interpretar_blocos_condicionais


def _paragrafo(bloco_id, texto, regra=None):
    return {
        "id": bloco_id,
        "tipo": "paragrafo",
        "regra": regra,
        "conteudo": [{"t": "texto", "v": texto}],
    }


def test_variavel_vira_placeholder_com_namespace():
    trechos = [
        {"t": "texto", "v": "Em "},
        {"t": "var", "campo": "educacao.ano_censo"},
        {"t": "texto", "v": " houve "},
        {"t": "var", "campo": "matriculas"},
    ]
    assert renderizar_trechos(trechos, {}) == "Em educacao.$ano_censo houve $matriculas"


def test_formato_com_decimais_vira_sufixo_de_precisao():
    """O pipeline já entende "$campo:2"; reusar isso evita reimplementar a
    formatação pt-BR no painel."""
    trechos = [{"t": "var", "campo": "demografia.gini", "formato": {"decimais": 2}}]
    assert renderizar_trechos(trechos, {}) == "demografia.$gini:2"


def test_bloco_com_regra_nao_atendida_some():
    blocos = [
        _paragrafo("a", "Sempre."),
        _paragrafo(
            "b", "Só com rede federal.",
            {"condicoes": [{"campo": "federal", "op": "maior", "valor": 0}]},
        ),
    ]
    assert renderizar_blocos(blocos, {"federal": 0}) == "Sempre."
    assert "Só com rede federal." in renderizar_blocos(blocos, {"federal": 3})


def test_texto_alternativo_entra_no_lugar_do_bloco():
    blocos = [
        _paragrafo(
            "a", "Texto principal.",
            {
                "condicoes": [{"campo": "x", "op": "maior", "valor": 0}],
                "sem_dado": {"acao": "texto_alternativo", "texto": "Sem dados."},
            },
        )
    ]
    assert renderizar_blocos(blocos, {}) == "Sem dados."


def test_secao_com_regra_leva_junto_os_filhos():
    blocos = [
        {
            "id": "s", "tipo": "secao", "titulo": "",
            "regra": {"condicoes": [{"campo": "pop_ind", "op": "diferente", "valor": 0}]},
            "blocos": [_paragrafo("p", "Parágrafo indígena.")],
        }
    ]
    assert renderizar_blocos(blocos, {"pop_ind": 0}) == ""
    assert "Parágrafo indígena." in renderizar_blocos(blocos, {"pop_ind": 12})


def test_ignorar_regras_emite_todas_as_variantes():
    blocos = [
        _paragrafo("a", "Variante A", {"condicoes": [{"campo": "x", "op": "maior", "valor": 0}]}),
        _paragrafo("b", "Variante B", {"condicoes": [{"campo": "x", "op": "menor", "valor": 0}]}),
    ]
    saida = renderizar_blocos(blocos, {}, ignorar_regras=True)
    assert "Variante A" in saida and "Variante B" in saida


def test_grafico_sai_como_marcador_que_o_pipeline_ja_reconhece():
    blocos = [{"id": "g", "tipo": "grafico", "regra": None, "grafico": "grafico_pib"}]
    assert renderizar_blocos(blocos, {}) == "*grafico_pib"


def test_caixa_sai_com_prefixo_de_cabecalho():
    blocos = [
        {
            "id": "c", "tipo": "caixa", "titulo": "Fontes", "regra": None,
            "blocos": [_paragrafo("p", "IBGE")],
        }
    ]
    assert renderizar_blocos(blocos, {}) == "#!Fontes\n\nIBGE"


def test_lista_sai_com_marcador_de_item():
    blocos = [
        {
            "id": "l", "tipo": "lista", "regra": None,
            "itens": [[{"t": "texto", "v": "IBGE"}], [{"t": "texto", "v": "MDIC"}]],
        }
    ]
    assert renderizar_blocos(blocos, {}) == "- IBGE\n- MDIC"


def test_contrato_renderizado_e_fatiado_de_volta_pela_cadeia_extrair():
    """A garantia central da Fase 1: o texto do painel entra no pipeline pelo
    mesmo fatiador que o texto do Google Doc."""
    contrato = novo_contrato("educacao")
    contrato["moldura"]["resumo_tema"]["blocos"] = [_paragrafo("r1", "Resumo do tema.")]
    contrato["corpo"]["blocos"] = [_paragrafo("c1", "Corpo do tema.")]
    contrato["moldura"]["referencias"] = ["IBGE, Censo 2022"]

    texto = renderizar_contrato(contrato, {})

    resumo, restante = extrair_resumo_tema(texto)
    descricao, _ = extrair_descricao_tema(restante)

    assert resumo == "Resumo do tema."
    assert descricao == "Corpo do tema."


def test_slot_fontes_sai_sem_marcador_para_virar_a_caixa_do_tema():
    """O que sobra depois da cadeia extrair_* é o que generation.py transforma
    em `fontes_html`."""
    contrato = novo_contrato("educacao")
    contrato["corpo"]["blocos"] = [_paragrafo("c1", "Corpo.")]
    contrato["moldura"]["fontes"]["blocos"] = [
        {"id": "f", "tipo": "caixa", "titulo": "Fontes", "regra": None,
         "blocos": [_paragrafo("fp", "IBGE")]}
    ]

    texto = renderizar_contrato(contrato, {})
    _, sobra = extrair_descricao_tema(texto)

    assert sobra.strip().startswith("#!Fontes")


def test_marca_do_painel_desliga_a_maquina_de_estado_dos_docs():
    """Sem o curto-circuito, interpretar_blocos_condicionais reescreveria a
    prosa do painel: ela reage ao conteúdo do parágrafo, não só às instruções
    editoriais (caso da população em situação de rua)."""
    texto = (
        "Outro grupo relevante para a caracterização da população municipal é "
        "o de pessoas em situação de rua."
    )

    sem_marca = interpretar_blocos_condicionais(texto, {"nm_mun": "Canapi"})
    com_marca = interpretar_blocos_condicionais(
        texto, {"nm_mun": "Canapi", CHAVE_FONTE_PAINEL: FONTE_PAINEL}
    )

    assert sem_marca != texto, "o caminho Docs reescreve este parágrafo"
    assert com_marca == texto, "o caminho painel deve preservá-lo"


def test_contrato_novo_e_valido():
    assert validar_contrato(novo_contrato("educacao")) == []


# -- variável nula esconde o trecho que depende dela ----------------------
#
# Regra do produto: se a variável não tem valor para aquele município, a seção
# que depende dela não aparece. O comportamento anterior — deixar `$campo`
# literal no PDF — enchia hidráulica de `$sol_predom` em cinco dos seis
# municípios de uma bateria de teste, e imprimia "aumento de
# $tend_nivel_sup_per%" em educação onde o banco traz NULL.


def _paragrafo_com_var(bloco_id, campo, prefixo="Valor: "):
    return {
        "id": bloco_id,
        "tipo": "paragrafo",
        "regra": None,
        "conteudo": [{"t": "texto", "v": prefixo}, {"t": "var", "campo": campo}],
    }


def test_bloco_com_variavel_sem_valor_nao_e_renderizado():
    blocos = [_paragrafo_com_var("p1", "sol_predom")]

    assert renderizar_blocos(blocos, {"outro_campo": 10}, namespace="hidraulica") == ""


def test_bloco_com_variavel_preenchida_continua_saindo():
    blocos = [_paragrafo_com_var("p1", "sol_predom")]

    # O marcador continua literal aqui de propósito: quem o resolve é
    # `substituir_placeholders`, adiante no pipeline. O que este teste trava é
    # que o bloco **saiu**, porque o campo tem valor no contexto.
    assert (
        renderizar_blocos(blocos, {"sol_predom": "cisterna"}, namespace="hidraulica")
        == "Valor: $sol_predom"
    )


def test_variavel_com_namespace_do_proprio_macrotema_resolve():
    """`hidraulica.$campo` num relatório de hidráulica resolve contra o contexto
    mesclado — não pode ser confundido com campo ausente."""
    blocos = [_paragrafo_com_var("p1", "hidraulica.sol_predom")]

    saida = renderizar_blocos(
        blocos, {"sol_predom": "cisterna"}, namespace="hidraulica"
    )

    assert saida == "Valor: hidraulica.$sol_predom"


def test_secao_que_perdeu_todos_os_filhos_nao_deixa_titulo_orfao():
    blocos = [
        {
            "id": "s1",
            "tipo": "secao",
            "regra": None,
            "titulo": "Tecnologias sociais de acesso à água",
            "blocos": [_paragrafo_com_var("p1", "sol_predom")],
        }
    ]

    assert renderizar_blocos(blocos, {}, namespace="hidraulica") == ""


def test_secao_mantem_titulo_quando_ao_menos_um_filho_sobrevive():
    blocos = [
        {
            "id": "s1",
            "tipo": "secao",
            "regra": None,
            "titulo": "Tecnologias sociais",
            "blocos": [
                _paragrafo_com_var("p1", "sol_predom"),
                _paragrafo("p2", "Texto sem variável nenhuma."),
            ],
        }
    ]

    saida = renderizar_blocos(blocos, {}, namespace="hidraulica")

    assert "Tecnologias sociais" in saida
    assert "Texto sem variável nenhuma." in saida
    assert "$sol_predom" not in saida


def test_conferencia_da_importacao_continua_emitindo_tudo():
    """`ignorar_regras` compara o contrato com o Doc linha a linha; se ele
    passasse a esconder bloco por falta de dado, a conferência acusaria perda
    de conteúdo que não houve."""
    blocos = [_paragrafo_com_var("p1", "sol_predom")]

    saida = renderizar_blocos(
        blocos, {}, ignorar_regras=True, namespace="hidraulica"
    )

    assert saida == "Valor: $sol_predom"


def test_contrato_inteiro_usa_o_macrotema_como_namespace():
    contrato = novo_contrato("saneamento")
    contrato["corpo"]["blocos"] = [
        _paragrafo_com_var("p1", "saneamento.esgoto_rede_2022"),
        _paragrafo("p2", "Parágrafo que não depende de dado."),
    ]

    saida = renderizar_contrato(contrato, {})

    assert "esgoto_rede_2022" not in saida
    assert "Parágrafo que não depende de dado." in saida
