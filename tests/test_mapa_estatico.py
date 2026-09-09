import urllib.parse

import pytest

import utils.maps as maps


def _preparar_pasta(tmp_path, monkeypatch, arquivos):
    for nome in arquivos:
        (tmp_path / nome).write_bytes(b"png")
    monkeypatch.setattr(maps, "MAPAS_DIR", tmp_path)
    monkeypatch.setattr(maps, "_INDICE_MAPAS_ESTATICOS", None)


def test_match_absorve_caixa_acento_e_apostrofo(tmp_path, monkeypatch):
    _preparar_pasta(
        tmp_path,
        monkeypatch,
        ["Fortaleza (CE).png", "Olho d_Água (PB).png", "Água Branca (AL).png"],
    )

    # caixa diferente
    assert maps.buscar_mapa_estatico("FORTALEZA (CE)") == "Fortaleza (CE).png"
    # apóstrofo no nome vs underscore no arquivo
    assert maps.buscar_mapa_estatico("Olho d'Água (PB)") == "Olho d_Água (PB).png"
    # acento
    assert maps.buscar_mapa_estatico("Agua Branca (AL)") == "Água Branca (AL).png"


def test_uf_separada_combina_com_nm_mun(tmp_path, monkeypatch):
    # runtime: nm_mun vem sem UF, a UF chega em sigla_uf
    _preparar_pasta(tmp_path, monkeypatch, ["Juazeiro do Norte (CE).png"])
    assert maps.buscar_mapa_estatico("Juazeiro do Norte", "CE") == "Juazeiro do Norte (CE).png"
    # sem a UF não casa (nome de cidade repete entre estados)
    assert maps.buscar_mapa_estatico("Juazeiro do Norte") is None


def test_cidade_sem_png_retorna_none(tmp_path, monkeypatch):
    _preparar_pasta(tmp_path, monkeypatch, ["Fortaleza (CE).png"])
    assert maps.buscar_mapa_estatico("Açu (RN)") is None


def test_reescrever_srcs_do_pdf_aponta_para_arquivo_existente(tmp_path, monkeypatch):
    # weasyprint depende de libs de sistema; pula se não instalado (roda no CI).
    pdf = pytest.importorskip("services.pdf")

    nome = "Água Branca (AL).png"
    (tmp_path / nome).write_bytes(b"png")
    monkeypatch.setattr(pdf, "MAPAS_DIR", tmp_path)

    src = urllib.parse.quote(nome)  # mesmo encoding do render_mapa_marker
    html = f'<img src="/mapas/{src}"><img src="/output/grafico.png">'
    saida = pdf._reescrever_srcs(html)

    # /output/ vira relativo; /mapas/ vira file:// apontando pro arquivo real
    assert 'src="grafico.png"' in saida
    prefixo = "file://"
    url = saida.split(f'src="{prefixo}', 1)[1].split('"', 1)[0]
    caminho = urllib.parse.unquote(url)
    import os
    assert os.path.isfile(caminho), caminho
