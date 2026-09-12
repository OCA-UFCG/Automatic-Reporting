"""Testes do importador Doc -> contrato.

Os trechos abaixo são cópias literais dos Google Docs em produção (demografia,
economia-renda, desenvolvimento-social), inclusive com os espaços duplos e o
"então :" que os editores escreveram. É de propósito: o importador precisa
aguentar o texto como ele é, não como gostaríamos que fosse.
"""

from utils.editorial.contrato import validar_contrato
from utils.editorial.importador import (
    importar_texto,
    parsear_blocos,
    parsear_condicao,
    parsear_frase_operador,
    parsear_trechos,
)


def _tipos(divergencias):
    return [d.tipo for d in divergencias]


def test_frases_do_doc_viram_operadores_nomeados():
    assert parsear_frase_operador(" for maior ou igual a 5") == ("maior_igual", 5.0)
    assert parsear_frase_operador(" for menor que 3") == ("menor", 3.0)
    assert parsear_frase_operador(" for diferente de 0") == ("diferente", 0.0)
    assert parsear_frase_operador(" de 1 a 4") == ("entre", [1.0, 4.0])


def test_maior_ou_menor_que_zero_vira_diferente_e_nao_menor():
    """A ordem da tabela de regex atual faz "menor que 0" casar dentro de
    "maior ou menor que 0"; a frase específica precisa vir antes."""
    assert parsear_frase_operador(" for maior ou menor que 0%, então:") == (
        "diferente",
        0.0,
    )


def test_negativo_positivo_e_percentual_solto_ganham_operador():
    assert parsear_frase_operador(" for negativo, então :") == ("menor", 0)
    assert parsear_frase_operador(" for positivo, então :") == ("maior", 0)
    assert parsear_frase_operador(" for 0%, então:") == ("igual", 0.0)


def test_operador_compartilhado_vale_para_os_dois_campos():
    """`$a e $b for diferente de 0`: o parser atual herda a frase do último
    campo, e o importador precisa herdar igual."""
    condicoes, _ = parsear_condicao(
        "demografia.$pop_ind_2022 e demografia.$pop_qui for diferente de 0", 1
    )

    assert condicoes == [
        {"campo": "pop_ind_2022", "op": "diferente", "valor": 0.0},
        {"campo": "pop_qui", "op": "diferente", "valor": 0.0},
    ]


def test_campo_null_sensivel_ganha_checagem_de_presenca():
    condicoes, _ = parsear_condicao("demografia.$centro_pop for igual a 0", 1)

    assert {"campo": "centro_pop", "op": "existe"} in condicoes
    assert {"campo": "centro_pop", "op": "igual", "valor": 0.0} in condicoes


def test_divergencia_de_operador_e_provada_com_valores():
    _, divergencias = parsear_condicao(
        "demografia.$cres_pop_analise for maior ou menor que 0%", 1
    )

    assert len(divergencias) == 1
    assert divergencias[0].tipo == "operador corrigido"
    assert "hoje esconde, contrato mostra" in divergencias[0].prova


def test_condicional_seguida_de_linha_em_branco_e_marcada_como_inerte():
    """Na exportação do Docs há linhas em branco entre tudo. A primeira delas
    reativa o bloco, então a condição não chega a valer para o parágrafo."""
    texto = (
        "Para quando  demografia.$dif_etaria_09_60 for negativo, então :\n"
        "\n"
        "\n"
        "A distribuição por faixa etária mostra demografia.$pop_etaria_0_9.\n"
    )
    _, divergencias = parsear_blocos(texto, "corpo")

    assert "condicional inerte hoje" in _tipos(divergencias)


def test_condicional_sem_linha_em_branco_engolindo_estrutura_e_apontada():
    texto = (
        "Quando o índice de Gini for menor que 0,5\n"
        "desen_social.$nm_mun alcançou IDHM de desen_social.$idhm_2010.\n"
        "#!Conteúdos relacionados\n"
    )
    _, divergencias = parsear_blocos(texto, "corpo")

    assert "condicional engole estrutura" in _tipos(divergencias)


def test_grupo_de_populacoes_vira_secao_que_contem_os_subordinados():
    """`bloco_populacoes_ativo` é um booleano global no parser atual; no
    contrato o aninhamento explícito ocupa o lugar do estado."""
    texto = (
        "Para quando demografia.$pop_ind_2022 for diferente de 0:\n"
        "Em 2022 havia demografia.$pop_ind_2022 pessoas indígenas.\n"
        "Para quando demografia.$pop_ind_2010 for igual a 0:\n"
        "Em 2010 não havia registro.\n"
    )
    blocos, _ = parsear_blocos(texto, "corpo")

    assert blocos[0]["tipo"] == "secao"
    assert blocos[0]["regra"]["condicoes"][0]["campo"] == "pop_ind_2022"
    assert len(blocos[0]["blocos"]) == 2
    assert blocos[0]["blocos"][1]["regra"]["condicoes"][0]["campo"] == "pop_ind_2010"


def test_paragrafo_de_situacao_de_rua_vira_tres_blocos_com_regra():
    """As duas variantes hoje escritas em Python voltam a ser texto editável."""
    texto = (
        "Outro grupo relevante para a caracterização da população municipal é "
        "o de pessoas em situação de rua. Em 2026, demografia.$pop_rua_2026.\n"
    )
    blocos, divergencias = parsear_blocos(texto, "corpo")

    assert len(blocos) == 3
    assert "prosa que morava no Python" in _tipos(divergencias)
    assert blocos[2]["regra"]["condicoes"] == [
        {"campo": "pop_rua_2022", "op": "nao_existe"}
    ]


def test_marcadores_de_grafico_legenda_e_caixa_viram_blocos_tipados():
    texto = (
        "Parágrafo.\n"
        "*grafico_visao_historica\n"
        "Figura Z – Visão histórica da população.\n"
        "#!Fontes\n"
        "* IBGE\n"
    )
    blocos, _ = parsear_blocos(texto, "corpo")
    tipos = [bloco["tipo"] for bloco in blocos]

    assert tipos == ["paragrafo", "grafico", "legenda", "caixa"]
    assert blocos[1]["grafico"] == "grafico_visao_historica"
    assert blocos[3]["blocos"][0]["tipo"] == "lista"


def test_frase_com_dois_pontos_sem_placeholder_nao_vira_condicao():
    """"Para saber mais sobre este tema:" é prosa, não instrução editorial."""
    blocos, _ = parsear_blocos("Para saber mais sobre este tema:\n", "corpo")

    assert blocos[0]["tipo"] == "paragrafo"


def test_placeholder_com_namespace_e_precisao_vira_variavel_tipada():
    trechos = parsear_trechos("Gini de demografia.$gini_2010:2 em 2010")

    assert trechos[1] == {
        "t": "var",
        "campo": "demografia.gini_2010",
        "formato": {"decimais": 2},
    }


def test_importacao_completa_produz_contrato_valido():
    texto = (
        'descricao_tema = “Um parágrafo com educacao.$matriculas.\n'
        "*grafico_matriculas\n"
        "Figura X – Matrículas por rede.\n@@\n"
        "resumo_tema = Resumo curto.@@\n"
        "referencia = IBGE, Censo 2022@@\n"
    )
    resultado = importar_texto(texto, "educacao")

    assert validar_contrato(resultado.contrato) == []
    assert resultado.contrato["moldura"]["referencias"] == ["IBGE, Censo 2022"]
    assert len(resultado.contrato["corpo"]["blocos"]) == 3


def test_comparacao_entre_campos_vira_referencia_e_e_apontada():
    condicoes, divergencias = parsear_condicao(
        "educacao.$sem_instr_2000 for igual a  educacao.$sem_instr_2022, então", 5
    )

    assert condicoes == [
        {
            "campo": "sem_instr_2000",
            "op": "igual",
            "valor": {"campo": "sem_instr_2022"},
        }
    ]
    assert _tipos(divergencias) == ["comparação entre campos"]


def test_titulo_colado_no_paragrafo_anterior_e_apontado():
    texto = "Um parágrafo qualquer.\nSíntese\nOutro parágrafo.\n"
    _, divergencias = parsear_blocos(texto, "corpo")

    assert "título sem destaque hoje" in _tipos(divergencias)
