#!/usr/bin/env python3
import argparse
import csv
import re
import sys
import unicodedata
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from config import OUTPUT_DIR
from utils.cities import carregar_cidades
from utils.maps import (
    carregar_malhas,
    gerar_mapa_regiao,
    localizar_municipio,
    separar_cidade_uf,
)


def slugify(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "_", text.casefold()).strip("_")


def find_city_code(row) -> str:
    for column in ("CD_MUN", "CD_MUNICIP", "CD_GEOCMU"):
        value = row.get(column)
        if value is not None:
            return str(value)
    return ""


def build_url(base_url: str, filename: str) -> str:
    return f"{base_url.rstrip('/')}/{filename}" if base_url else ""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera mapas PNG para as cidades disponibilizadas pelo endpoint /cities."
    )
    parser.add_argument("--uf", help="Gera apenas uma UF. Exemplo: PE")
    parser.add_argument("--limit", type=int, help="Limita a quantidade para testes")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Gera novamente arquivos que ja existem",
    )
    parser.add_argument(
        "--base-url",
        default="",
        help="URL base do storage para preencher a coluna url do manifesto",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=OUTPUT_DIR / "map_manifest.csv",
        help="Caminho do CSV gerado. Padrao: output/map_manifest.csv",
    )
    args = parser.parse_args()

    cidades = carregar_cidades()
    if args.uf:
        cidades = [
            cidade
            for cidade in cidades
            if separar_cidade_uf(cidade)[1] == args.uf.upper()
        ]
    if args.limit is not None:
        cidades = cidades[:args.limit]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    carregar_malhas()

    total = len(cidades)
    for index, cidade in enumerate(cidades, start=1):
        municipio = localizar_municipio(cidade)
        if municipio is None:
            print(f"[{index}/{total}] {cidade}: error")
            rows.append(
                {
                    "codigo_ibge": "",
                    "municipio": cidade,
                    "uf": separar_cidade_uf(cidade)[1],
                    "arquivo": "",
                    "url": "",
                    "status": "error",
                }
            )
            continue

        nome = str(municipio["NM_MUN"])
        uf = str(municipio["SIGLA_UF"]).upper()
        codigo_ibge = find_city_code(municipio)
        identifier = codigo_ibge or f"{slugify(nome)}_{uf.casefold()}"
        safe_report = f"municipio_{identifier}"
        filename = f"mapa_regiao_{safe_report}.png"
        output_file = OUTPUT_DIR / filename

        if output_file.exists() and not args.overwrite:
            status = "existing"
        else:
            generated_filename = gerar_mapa_regiao(cidade, safe_report)
            status = "generated" if generated_filename else "error"

        rows.append(
            {
                "codigo_ibge": codigo_ibge,
                "municipio": nome,
                "uf": uf,
                "arquivo": filename if status != "error" else "",
                "url": build_url(args.base_url, filename) if status != "error" else "",
                "status": status,
            }
        )
        print(f"[{index}/{total}] {nome} ({uf}): {status}")

    with args.manifest.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["codigo_ibge", "municipio", "uf", "arquivo", "url", "status"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Manifesto salvo em {args.manifest}")


if __name__ == "__main__":
    main()
