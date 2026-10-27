"""Extras do município e contexto do tema, extraídos do handler de geração."""


from services import generation
from services.generation import (
    _percentuais_pequenos_com_casas,
    buscar_extras_municipio,
    linha_do_perfil,
    montar_contexto_tema,
)

CHAVES_EXTRAS = (
    "caracteristicas", "demografia", "sexo_faixa", "indigena", "quilombola",
    "publico_etario", "mortalidade_infantil", "estabelecimentos_saude",
    "perfil_saude", "taxas_educacao", "tecnologias_acesso_agua", "esgotamento",
    "perfil_desenvolvimento_social", "pib", "indicadores_economia", "importacao",
    "comercio_exterior", "rua", "indicadores",
)
EXTRAS_VAZIOS = dict.fromkeys(CHAVES_EXTRAS)
EXTRAS_COM_RUA = {**EXTRAS_VAZIOS, "rua": {"pop_rua_2026": 454}}


def test_linha_do_perfil_canoniza_nm_mun():
    assert linha_do_perfil({"nm_mun": "Recife"}, "recife", "PE")["nm_mun"] == "Recife (PE)"
    assert (
        linha_do_perfil({"nm_mun": "Campina Grande (PB)"}, "x", "PB")["nm_mun"]
        == "Campina Grande (PB)"
    )


def test_linha_do_perfil_sem_nm_mun_usa_o_nome_digitado_e_nao_muta():
    perfil = {"outra": 1}
    assert linha_do_perfil(perfil, "Olinda", "PE")["nm_mun"] == "Olinda (PE)"
    assert perfil == {"outra": 1}


def test_buscar_extras_municipio_so_consulta_temas_do_relatorio(monkeypatch):
    chamadas = set()
    for nome in dir(generation):
        if nome.startswith("buscar_") and nome not in ("buscar_perfil_municipal",):
            def stub(*_args, _nome=nome):
                chamadas.add(_nome)
            monkeypatch.setattr(generation, nome, stub)
    extras = buscar_extras_municipio("Recife", "PE", ["saude"])
    assert chamadas == {
        "buscar_caracteristicas_municipio", "buscar_publico_etario_vacinas",
        "buscar_mortalidade_infantil_serie", "buscar_estabelecimentos_saude_serie",
        "buscar_perfil_saude_municipal", "buscar_populacao_rua",
        "buscar_indicadores_municipio",
    }
    assert set(extras) == set(CHAVES_EXTRAS)
    assert extras["sexo_faixa"] is None


def test_montar_contexto_tema_nao_muta_as_entradas():
    linha, perfil = {"nm_mun": "X (PB)"}, {"nm_mun": "X"}
    copia_linha, copia_perfil = dict(linha), dict(perfil)
    ctx = montar_contexto_tema(linha, perfil, "demografia", ["demografia"], EXTRAS_COM_RUA)
    assert ctx["pop_rua_2026"] == 454
    assert linha == copia_linha and perfil == copia_perfil


def test_montar_contexto_tema_demografia_em_outro_tema_entra_cru():
    extras = {**EXTRAS_VAZIOS, "sexo_faixa": {"cor_pri_nome": "x"}}
    perfil = {"cor_pri_nome": "da view"}
    ctx = montar_contexto_tema({"nm_mun": "X (PB)"}, perfil, "saude", ["demografia", "saude"], extras)
    assert ctx["cor_pri_nome"] == "x"  # em saúde entra cru; só demografia protege a view
    ctx = montar_contexto_tema({"nm_mun": "X (PB)"}, perfil, "demografia", ["demografia", "saude"], extras)
    assert "cor_pri_nome" not in ctx  # em demografia a view prevalece (nada vem de extras)


def test_montar_contexto_tema_sem_perfil_da_view():
    ctx = montar_contexto_tema({"nm_mun": "X (PB)"}, None, "demografia", ["demografia"], EXTRAS_COM_RUA)
    assert ctx["pop_rua_2026"] == 454


def test_montar_contexto_tema_aplica_percentuais_pequenos_com_casas():
    linha = {"nm_mun": "X (PB)", "pop_total_2022": 20953, "pop_qui": 1, "pop_qui_per": 0.0}
    esperado = dict(linha)
    _percentuais_pequenos_com_casas(esperado)
    assert esperado["pop_qui_per"] != 0.0  # o helper de fato muda este caso
    ctx = montar_contexto_tema(linha, None, "demografia", ["demografia"], EXTRAS_VAZIOS)
    assert ctx["pop_qui_per"] == esperado["pop_qui_per"]
