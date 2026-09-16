import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from download_map_shapes import extract_zip


def _zip_com(tmp_path: Path, nome: str, membros: list[str]) -> Path:
    caminho = tmp_path / nome
    with zipfile.ZipFile(caminho, "w") as archive:
        for membro in membros:
            archive.writestr(membro, "x")
    return caminho


def test_achata_diretorio_raiz_unico(tmp_path):
    """Zip do Drive vem como 'Mapas_png/*.png'; o volume ja monta nesse nivel."""
    zip_path = _zip_com(tmp_path, "mapas.zip", ["Mapas_png/Abaiara (CE).png", "Mapas_png/Abaré (BA).png"])
    saida = tmp_path / "mapas_png"

    extract_zip(zip_path, saida)

    assert (saida / "Abaiara (CE).png").exists()
    assert not (saida / "Mapas_png").exists()


def test_preserva_multiplas_raizes(tmp_path):
    zip_path = _zip_com(
        tmp_path,
        "malhas.zip",
        ["BR_UF_2025/BR_UF_2025.shp", "BR_Municipios_2025/BR_Municipios_2025.shp"],
    )
    saida = tmp_path / "map_shape"

    extract_zip(zip_path, saida)

    assert (saida / "BR_UF_2025" / "BR_UF_2025.shp").exists()
