import pandas as pd
import pytest

from utils.data.cities import filtrar_linhas_por_cidade


def test_exact_match_com_uf():
    df = pd.DataFrame({"nm_mun": ["Presidente Dutra (BA)", "Presidente Dutra (MA)"], "valor": [1, 2]})
    resultado = filtrar_linhas_por_cidade(df, "Presidente Dutra (MA)")
    assert resultado["valor"].tolist() == [2]


def test_ambiguidade_quando_uma_linha_nao_tem_sufixo_de_estado():
    # Reproduz o bug: a planilha anota só uma das duas cidades homônimas com "(UF)".
    df = pd.DataFrame({"nm_mun": ["Presidente Dutra (BA)", "Presidente Dutra"], "valor": ["ba", "ma"]})
    # Sem UF anotada na linha de MA, não dá pra confirmar que ela é a certa.
    with pytest.raises(ValueError, match="ambígua"):
        filtrar_linhas_por_cidade(df, "Presidente Dutra (MA)")


def test_uf_informada_e_anotada_retorna_apenas_a_linha_certa():
    df = pd.DataFrame(
        {"nm_mun": ["Presidente Dutra (BA)", "Presidente Dutra (MA)"], "valor": ["ba", "ma"]}
    )
    resultado = filtrar_linhas_por_cidade(df, "Presidente Dutra (MA)")
    assert resultado["valor"].tolist() == ["ma"]


def test_uf_informada_sem_correspondencia_retorna_vazio():
    df = pd.DataFrame({"nm_mun": ["Presidente Dutra (BA)"], "valor": ["ba"]})
    resultado = filtrar_linhas_por_cidade(df, "Presidente Dutra (MA)")
    assert resultado.empty


def test_sem_uf_informada_e_duas_linhas_anotadas_levanta_erro():
    df = pd.DataFrame(
        {"nm_mun": ["Presidente Dutra (BA)", "Presidente Dutra (MA)"], "valor": ["ba", "ma"]}
    )
    with pytest.raises(ValueError, match="ambígua"):
        filtrar_linhas_por_cidade(df, "Presidente Dutra")


def test_cidade_sem_homonimo_funciona_normalmente():
    df = pd.DataFrame({"nm_mun": ["Campina Grande (PB)"], "valor": [1]})
    resultado = filtrar_linhas_por_cidade(df, "Campina Grande (PB)")
    assert resultado["valor"].tolist() == [1]
