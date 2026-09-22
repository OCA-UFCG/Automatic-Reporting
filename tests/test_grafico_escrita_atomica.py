from pathlib import Path

from plotting.demografia import gerar_grafico_faixa_etaria_e_sexo


def _cidade_faixa_etaria():
    # Mesmo contexto sintético de tests/test_demografia_chart.py e
    # tests/test_grafico_reuso.py.
    return {
        "faixas_etarias_sexo": [
            {"faixa": "0-4", "mulheres": 1200, "homens": 1300},
            {"faixa": "5-9", "mulheres": 1400, "homens": 1500},
        ]
    }


def test_salvar_card_grafico_nao_deixa_temp_e_grava_png_valido(tmp_path: Path):
    # Cobre `salvar_card_grafico` (plotting/__init__.py), o funil por onde todo
    # `gerar_grafico_*` passa — exercitado aqui via um chart concreto (mesmo
    # padrão de tests/test_grafico_reuso.py) em vez de chamar a função
    # diretamente, já que ela espera uma `Figure` de card já montada.
    nome = gerar_grafico_faixa_etaria_e_sexo(_cidade_faixa_etaria(), tmp_path, "cidade_y")
    png = tmp_path / nome

    assert png.is_file()
    # Nenhum .tmp do mkstemp sobrou: a escrita atômica (temp + os.replace)
    # não deixa resíduo quando dá certo.
    assert list(tmp_path.glob("*.tmp*")) == []
    # Garante que o `os.replace` publicou um PNG de verdade, não um arquivo
    # vazio/truncado no caminho certo — é essa mesma classe de corrupção que a
    # escrita atômica existe para evitar (ver comentário em
    # salvar_card_grafico e em services/pdf.py:_gerar_pdf_sync).
    assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
