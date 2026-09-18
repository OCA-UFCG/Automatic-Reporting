from pathlib import Path

from plotting.demografia import gerar_grafico_faixa_etaria_e_sexo


def _cidade_faixa_etaria():
    # Mesmo contexto sintético de tests/test_demografia_chart.py.
    return {
        "faixas_etarias_sexo": [
            {"faixa": "0-4", "mulheres": 1200, "homens": 1300},
            {"faixa": "5-9", "mulheres": 1400, "homens": 1500},
        ]
    }


def test_reusa_png_fresco_sem_regerar(tmp_path: Path, monkeypatch):
    from services import cache

    monkeypatch.setattr(cache, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(cache, "DATA_VERSION_FILE", tmp_path / ".data_version")

    contexto = _cidade_faixa_etaria()
    nome1 = gerar_grafico_faixa_etaria_e_sexo(contexto, tmp_path, "cidade_x")
    png = tmp_path / nome1
    mtime1 = png.stat().st_mtime_ns

    nome2 = gerar_grafico_faixa_etaria_e_sexo(contexto, tmp_path, "cidade_x")
    assert nome2 == nome1
    assert png.stat().st_mtime_ns == mtime1  # não regerou (reusou)
