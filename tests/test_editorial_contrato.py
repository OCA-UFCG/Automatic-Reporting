import pytest

from utils.editorial.contrato import (
    SLOT_FONTES,
    SLOTS_MOLDURA,
    ErroDeContrato,
    exigir_contrato_valido,
    novo_contrato,
    validar_contrato,
)


def _com_corpo(blocos):
    contrato = novo_contrato("educacao")
    contrato["corpo"]["blocos"] = blocos
    return contrato


def test_id_duplicado_e_recusado():
    """O painel endereça a edição pelo id; dois blocos com o mesmo id tornam
    ambígua a aplicação de uma alteração."""
    bloco = {"id": "p1", "tipo": "paragrafo", "regra": None, "conteudo": []}
    erros = validar_contrato(_com_corpo([dict(bloco), dict(bloco)]))

    assert any("duplicado" in erro for erro in erros)


def test_tipo_de_bloco_desconhecido_e_recusado():
    erros = validar_contrato(
        _com_corpo([{"id": "x", "tipo": "carrossel", "regra": None}])
    )
    assert any("carrossel" in erro for erro in erros)


def test_campo_de_variavel_precisa_de_forma_valida():
    erros = validar_contrato(
        _com_corpo([
            {
                "id": "p", "tipo": "paragrafo", "regra": None,
                "conteudo": [{"t": "var", "campo": "não vale!"}],
            }
        ])
    )
    assert any("campo" in erro for erro in erros)


def test_regra_invalida_e_apontada_com_o_caminho_do_bloco():
    erros = validar_contrato(
        _com_corpo([
            {
                "id": "p", "tipo": "paragrafo", "conteudo": [],
                "regra": {"condicoes": [{"campo": "x", "op": "quase"}]},
            }
        ])
    )
    assert any("corpo.blocos[0].regra" in erro for erro in erros)


def test_slot_de_moldura_desconhecido_e_recusado():
    contrato = novo_contrato("educacao")
    contrato["moldura"]["rodape"] = {"blocos": []}

    assert any("rodape" in erro for erro in validar_contrato(contrato))


def test_validacao_junta_todos_os_erros_de_uma_vez():
    """Quem consome é o painel, que precisa mostrar tudo o que falta corrigir."""
    contrato = _com_corpo([
        {"id": "", "tipo": "inexistente", "regra": None},
        {"id": "p", "tipo": "grafico", "regra": None},
    ])
    contrato["versao"] = 0

    assert len(validar_contrato(contrato)) >= 3


def test_secao_leva_os_filhos_na_validacao():
    erros = validar_contrato(
        _com_corpo([
            {
                "id": "s", "tipo": "secao", "titulo": "T", "regra": None,
                "blocos": [{"id": "f", "tipo": "carrossel", "regra": None}],
            }
        ])
    )
    assert any("corpo.blocos[0].blocos[0]" in erro for erro in erros)


def test_exigir_contrato_valido_levanta_com_a_lista_de_erros():
    with pytest.raises(ErroDeContrato) as erro:
        exigir_contrato_valido({"versao_contrato": 99})

    assert "versao_contrato" in str(erro.value)


def test_moldura_do_contrato_novo_tem_todos_os_slots():
    moldura = novo_contrato("educacao")["moldura"]

    assert set(moldura) == {*SLOTS_MOLDURA, SLOT_FONTES, "referencias"}
