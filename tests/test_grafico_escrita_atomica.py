from pathlib import Path

import pytest

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


def test_salvar_card_grafico_grava_png_valido_com_format_explicito(tmp_path: Path):
    # Cobre `salvar_card_grafico` (plotting/__init__.py), o funil por onde todo
    # `gerar_grafico_*` passa — exercitado aqui via um chart concreto (mesmo
    # padrão de tests/test_grafico_reuso.py) em vez de chamar a função
    # diretamente, já que ela espera uma `Figure` de card já montada.
    #
    # Este caso NÃO prova atomicidade (não injeta falha, um único escritor
    # nunca disputa o arquivo): ele pina que o `savefig` no arquivo temporário
    # (que termina em `.tmp`, não `.png`) usa `format="png"` explícito e
    # publica um PNG de verdade — regressão real, já vista sem esse parâmetro
    # (`ValueError: Format 'tmp' is not supported`). A atomicidade em si é
    # coberta por test_salvar_card_grafico_limpa_temp_quando_os_replace_falha
    # abaixo.
    nome = gerar_grafico_faixa_etaria_e_sexo(_cidade_faixa_etaria(), tmp_path, "cidade_y")
    png = tmp_path / nome

    assert png.is_file()
    assert list(tmp_path.glob("*.tmp*")) == []
    assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_salvar_card_grafico_limpa_temp_quando_os_replace_falha(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Prova a atomicidade de fato: injeta uma falha em `os.replace` (o passo
    # que publica o temp no destino) e verifica que (a) a exceção propaga em
    # vez de ser engolida e (b) o arquivo temporário criado por `mkstemp` não
    # sobra no diretório. Contra o código antigo (`plt.savefig(chart_file,
    # ...)` direto no destino, sem temp nem `os.replace`) este teste falha:
    # não há `os.replace` para falhar, então nada levanta `OSError` e o PNG
    # final é escrito normalmente — é exatamente essa diferença que separa
    # "escrita atômica" de "escrita direta que por acaso não deixa resíduo".
    def _replace_que_falha(origem, destino):
        raise OSError("falha injetada para teste")

    monkeypatch.setattr("plotting.os.replace", _replace_que_falha)

    with pytest.raises(OSError):
        gerar_grafico_faixa_etaria_e_sexo(_cidade_faixa_etaria(), tmp_path, "cidade_z")

    assert list(tmp_path.glob("*.tmp*")) == []
    assert not (tmp_path / "grafico_faixa_etaria_e_sexo_cidade_z.png").exists()
