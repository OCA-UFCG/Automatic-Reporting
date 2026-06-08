#!/usr/bin/env python3
import argparse
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT_DIR / "map_shape"
REQUIRED_FILES = (
    "BR_Municipios_2025/BR_Municipios_2025.shp",
    "BR_Municipios_2025/BR_Municipios_2025.shx",
    "BR_Municipios_2025/BR_Municipios_2025.dbf",
    "BR_UF_2025/BR_UF_2025.shp",
    "BR_UF_2025/BR_UF_2025.shx",
    "BR_UF_2025/BR_UF_2025.dbf",
)


def download(url: str, destination: Path) -> None:
    request = Request(url, headers={"User-Agent": "Automatic-Reporting map-shape downloader"})
    try:
        with urlopen(request, timeout=120) as response, destination.open("wb") as file:
            shutil.copyfileobj(response, file)
    except (HTTPError, URLError) as exc:
        raise SystemExit(f"Erro ao baixar {url}: {exc}") from exc


def is_github_release_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.netloc == "github.com" and "/releases/tag/" in parsed.path


def github_release_asset_download_url(release_url: str, asset_name: str) -> str:
    parsed = urlparse(release_url)
    path_parts = parsed.path.strip("/").split("/")
    if len(path_parts) < 5:
        raise SystemExit(f"URL de release invalida: {release_url}")

    owner, repo = path_parts[0], path_parts[1]
    tag = path_parts[-1]
    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}"
    request = Request(api_url, headers={"User-Agent": "Automatic-Reporting map-shape downloader"})

    try:
        with urlopen(request, timeout=120) as response:
            import json

            release = json.load(response)
    except (HTTPError, URLError) as exc:
        raise SystemExit(f"Erro ao consultar a release {release_url}: {exc}") from exc

    assets = release.get("assets", [])
    if not assets:
        raise SystemExit(f"A release {release_url} nao possui assets.")

    if asset_name:
        for asset in assets:
            if asset.get("name") == asset_name:
                return asset["browser_download_url"]
        names = ", ".join(asset.get("name", "") for asset in assets)
        raise SystemExit(f"Asset {asset_name!r} nao encontrado. Assets disponiveis: {names}")

    zip_assets = [asset for asset in assets if str(asset.get("name", "")).lower().endswith(".zip")]
    if len(zip_assets) == 1:
        return zip_assets[0]["browser_download_url"]

    names = ", ".join(asset.get("name", "") for asset in assets)
    raise SystemExit(
        "Informe --asset-name porque a release nao tem exatamente um .zip. "
        f"Assets disponiveis: {names}"
    )


def extract_zip(zip_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(output_dir)


def validate(output_dir: Path) -> None:
    missing = [path for path in REQUIRED_FILES if not (output_dir / path).exists()]
    if missing:
        formatted = "\n".join(f"- {path}" for path in missing)
        raise SystemExit(f"Download concluido, mas faltam arquivos esperados:\n{formatted}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Baixa as malhas cartograficas usadas pelos mapas.")
    parser.add_argument(
        "--url",
        default=os.getenv("MAP_SHAPE_ZIP_URL") or os.getenv("MAP_SHAPE_RELEASE_URL"),
        help="URL direta do .zip ou URL da release do GitHub. Tambem aceita MAP_SHAPE_ZIP_URL.",
    )
    parser.add_argument(
        "--asset-name",
        default=os.getenv("MAP_SHAPE_ASSET_NAME", ""),
        help="Nome do asset na release, se a release tiver mais de um arquivo.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Diretorio de destino. Padrao: map_shape/",
    )
    args = parser.parse_args()

    if not args.url:
        raise SystemExit("Informe --url ou defina MAP_SHAPE_ZIP_URL/MAP_SHAPE_RELEASE_URL.")

    download_url = (
        github_release_asset_download_url(args.url, args.asset_name)
        if is_github_release_url(args.url)
        else args.url
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = Path(temp_dir) / "map_shapes.zip"
        print(f"Baixando malhas de {download_url}")
        download(download_url, zip_path)
        extract_zip(zip_path, args.output_dir)

    validate(args.output_dir)
    print(f"Malhas prontas em {args.output_dir}")


if __name__ == "__main__":
    main()
