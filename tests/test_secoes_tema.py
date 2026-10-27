from services.generation import separar_secoes_do_tema

DOC = """resumo_tema = Resumo $nm_mun. @@
descricao_tema =
Texto.

Figura 1 – Pirâmide etária
@@
#!Fontes
IBGE"""


def test_separar_secoes_extrai_na_ordem_do_handler():
    secoes, _ = separar_secoes_do_tema(DOC, "demografia")
    assert secoes.resumo_tema == "Resumo $nm_mun."
    assert "Texto." in secoes.descricao_tema
    assert "#!Fontes" in secoes.resto and "descricao_tema" not in secoes.resto


def test_separar_secoes_sem_blocos_opcionais():
    secoes, _ = separar_secoes_do_tema("descricao_tema = Só isto. @@", "saneamento")
    assert secoes.resumo_tema is None and secoes.diagnostico_cidade is None
    assert secoes.relatorio_geral is None and secoes.resumo_cidade is None


def test_separar_secoes_lista_grafico_sem_legenda():
    _, faltando = separar_secoes_do_tema("descricao_tema = Sem figura. @@", "demografia")
    assert "grafico_faixa_etaria_e_sexo" in faltando
