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


def test_homonimos_com_uf_em_coluna_propria():
    # Formato real das planilhas dos temas: nm_mun sem "(UF)", estado em sigla_uf.
    df = pd.DataFrame(
        {
            "nm_mun": ["Santa Luzia", "Santa Luzia", "Santa Luzia"],
            "sigla_uf": ["MA", "PB", "BA"],
            "valor": ["ma", "pb", "ba"],
        }
    )
    assert filtrar_linhas_por_cidade(df, "Santa Luzia (PB)")["valor"].tolist() == ["pb"]
    assert filtrar_linhas_por_cidade(df, "Santa Luzia (BA)")["valor"].tolist() == ["ba"]
    assert filtrar_linhas_por_cidade(df, "santa luzia (ma)")["valor"].tolist() == ["ma"]


def test_coluna_uf_sem_a_uf_pedida_mantem_o_caminho_antigo():
    # sigla_uf vazia ou em outro formato não pode transformar a busca em 404.
    df = pd.DataFrame({"nm_mun": ["Parari"], "sigla_uf": [""], "valor": [1]})
    assert filtrar_linhas_por_cidade(df, "Parari (PB)")["valor"].tolist() == [1]
    df = pd.DataFrame({"nm_mun": ["Parari"], "sigla_uf": ["Paraíba"], "valor": [1]})
    assert filtrar_linhas_por_cidade(df, "Parari (PB)")["valor"].tolist() == [1]


def test_citys_txt_usa_os_nomes_do_ibge():
    # O gate de generation.py dá 404 para cidade fora do citys.txt, e a busca na
    # view usa o nome dele: um nome velho ali deixa o município sem relatório.
    # Augusto Severo, Ererê e "São João da Manteninha" estavam assim até 29/09/2026
    # (views e malha do IBGE 2025 usam Campo Grande, Ereré e São João do Manteninha).
    # Açu e Arês viraram Assú e Arez nas tabelas do banco em 30/09/2026 (carga do
    # Time Dados com os nomes do IBGE); com o nome velho, o relatório dava 404.
    from utils.data.cities import _ler_cidades_do_arquivo

    cidades = _ler_cidades_do_arquivo()
    assert len(cidades) == len(set(cidades)) == 2074
    for nome in ("Campo Grande (RN)", "Ereré (CE)", "São João do Manteninha (MG)",
                 "Assú (RN)", "Arez (RN)"):
        assert nome in cidades
    for nome in ("Augusto Severo (RN)", "Ererê (CE)", "SÃO JOÃO DA MANTENINHA (MG)",
                 "Açu (RN)", "Arês (RN)"):
        assert nome not in cidades
    # 83 municípios de MG e ES estavam em maiúsculas; a lista vai para o frontend.
    assert [c for c in cidades if c.split(" (")[0].isupper()] == []
