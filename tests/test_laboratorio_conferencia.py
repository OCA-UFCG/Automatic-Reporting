from services.laboratorio import conferir_doc, conferir_tema
from utils.render.placeholders import interpretar_blocos_condicionais, registrar_versoes
from utils.render.renderer import texto_final_do_tema

TEXTO = (
    "Para quando $pop for maior que 10:\nGrande $nm_mun.\n\n"
    "Para quando $pop for menor ou igual a 10:\nPequena, com $inexistente e $vazio.\n\n"
    "Fim."
)


def test_registrar_versoes_diz_qual_versao_disparou_sem_mudar_o_texto():
    contexto = {"pop": 20, "nm_mun": "X"}
    sem_registro = interpretar_blocos_condicionais(TEXTO, contexto)
    with registrar_versoes() as versoes:
        com_registro = interpretar_blocos_condicionais(TEXTO, contexto)
    assert com_registro == sem_registro
    assert [disparou for _, disparou in versoes] == [True, False]
    assert versoes[0][0].startswith("Para quando $pop for maior que 10")


def test_registro_fica_desligado_fora_do_with():
    with registrar_versoes() as versoes:
        pass
    texto_final_do_tema(TEXTO, {"pop": 1}, "demografia")
    assert versoes == []


def test_conferir_tema_conta_versoes_e_separa_campo_inexistente_de_vazio():
    contextos = {
        "Grande (PB)": {"pop": 20, "nm_mun": "Grande (PB)", "vazio": 1},
        "Pequena (PB)": {"pop": 5, "nm_mun": "Pequena (PB)", "vazio": None},
        "Mínima (PB)": {"pop": 1, "nm_mun": "Mínima (PB)", "vazio": None},
    }
    progresso = []
    resultado = conferir_tema(TEXTO, "demografia", contextos, lambda f, t: progresso.append(f))

    assert [v["municipios"] for v in resultado["versoes"]] == [1, 2]
    assert resultado["versoes_por_municipio"] == {
        "Grande (PB)": [0], "Pequena (PB)": [1], "Mínima (PB)": [1],
    }
    crus = {c["campo"]: c for c in resultado["campos_crus"]}
    assert crus["inexistente"]["existe"] is False
    assert crus["vazio"]["existe"] is True
    assert crus["vazio"]["municipios"] == ["Pequena (PB)", "Mínima (PB)"]
    assert progresso == [1, 2, 3]
    assert resultado["erros"] == {}


def test_conferir_tema_acusa_condicao_que_o_gerador_nao_entende():
    # "for menor $campo" sem "que": o caso das revisões de Demografia (28-29/09).
    texto = "Para quando $pop for menor 10:\nTexto.\n"
    resultado = conferir_tema(texto, "demografia", {"A (PB)": {"pop": 1}})
    assert resultado["condicoes_nao_entendidas"]


def test_conferir_doc_avisa_condicao_no_resumo_do_tema():
    doc = "resumo_tema = Para quando $pop for maior que 10:\nTexto do resumo.@@\n"
    resultado = conferir_doc(doc, "demografia", {"A (PB)": {"pop": 20}})
    assert resultado["condicoes_sem_efeito"] == ["Para quando $pop for maior que 10:"]
