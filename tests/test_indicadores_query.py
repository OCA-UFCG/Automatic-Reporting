from unittest.mock import patch

from utils.queries import indicadores
from utils.queries.indicadores import buscar_indicadores_municipio

LINHA_VIEW = {
    "nm_mun": "Campina Grande",
    "cd_mun": 2504009,
    "estado": "Paraíba",
    "sigla_uf": "PB",
    "idhm_2010": "0.72",
    "indice_gini_2010": "0.58",
}


def test_remove_colunas_de_identificacao():
    # O nm_mun da view vem sem o sufixo "(UF)"; deixá-lo passar sobrescreveria o
    # nome canonicalizado em services/generation.py.
    with patch.object(indicadores, "executar_query_dict", return_value=LINHA_VIEW):
        dados = buscar_indicadores_municipio("Campina Grande", "PB")

    assert dados == {"idhm_2010": "0.72", "indice_gini_2010": "0.58"}


def test_sem_uf_nao_consulta_o_banco():
    with patch.object(indicadores, "executar_query_dict") as consulta:
        assert buscar_indicadores_municipio("Campina Grande", "") is None
        assert buscar_indicadores_municipio("", "PB") is None

    consulta.assert_not_called()


def test_municipio_fora_da_view_retorna_none():
    with patch.object(indicadores, "executar_query_dict", return_value=None):
        assert buscar_indicadores_municipio("Cidade Inexistente", "PB") is None


def test_query_limita_a_um_municipio_e_tem_timeout():
    with patch.object(indicadores, "executar_query_dict", return_value=LINHA_VIEW) as consulta:
        buscar_indicadores_municipio("Campina Grande", "PB")

    query = consulta.call_args.args[0]
    assert "statement_timeout" in query
    assert "WHERE" in query
    assert consulta.call_args.args[1] == ("Campina Grande", "PB")
